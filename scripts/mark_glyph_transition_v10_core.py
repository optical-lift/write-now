#!/usr/bin/env python3
import hashlib
import json
import math
from collections import Counter, defaultdict

BOUNDARIES = {"<DOC>", "<LINE>", "<WORD>"}
OTHER = "OTHER"


def canonical_json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def canonical_sha(value):
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def read_jsonl(path, expected_lane=None):
    rows = []
    with open(path, "r", encoding="utf-8") as handle:
        for raw in handle:
            if not raw.strip():
                continue
            row = json.loads(raw)
            if row.get("schema") != "mark_glyph_transition_blind_inscription_v10":
                raise RuntimeError("unexpected blind inscription schema")
            if expected_lane is not None and row.get("lane") != expected_lane:
                raise RuntimeError(f"expected lane {expected_lane}, received {row.get('lane')}")
            rows.append(row)
    rows.sort(key=lambda r: r["anonymousInscriptionId"])
    return rows


def sequence_stream(words, variant):
    if variant not in ("boundaryAware", "lineOnly"):
        raise RuntimeError(f"unknown V10 sequence variant {variant}")
    stream = ["<DOC>"]
    have_word_on_line = False
    for token in words:
        if token == "\n":
            if stream[-1] != "<LINE>":
                stream.append("<LINE>")
            have_word_on_line = False
            continue
        if have_word_on_line and variant == "boundaryAware":
            stream.append("<WORD>")
        for char in token:
            stream.append(char)
        have_word_on_line = True
    if stream[-1] == "<LINE>":
        stream.pop()
    stream.append("<DOC>")
    return stream


def is_operator(token):
    return token not in BOUNDARIES and token != OTHER


def fold_for_doc(doc_id, folds=5):
    digest = hashlib.sha256(doc_id.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big") % folds


def map_state(token, common_states):
    if token in BOUNDARIES:
        return token
    return token if token in common_states else OTHER


def derive_train_inventory(rows, protocol, variant):
    elig = protocol["eligibility"]
    state_count = Counter()
    state_docs = defaultdict(set)
    glyph_count = Counter()
    glyph_docs = defaultdict(set)
    total_operator_events = 0

    for row in rows:
        doc = row["anonymousInscriptionId"]
        stream = sequence_stream(row["words"], variant)
        for token in stream:
            state_count[token] += 1
            state_docs[token].add(doc)
        for token in stream[1:-1]:
            if is_operator(token):
                glyph_count[token] += 1
                glyph_docs[token].add(doc)
                total_operator_events += 1

    common_states = {
        state for state, count in state_count.items()
        if state not in BOUNDARIES
        and count >= int(elig["minimumTrainStateOccurrences"])
        and len(state_docs[state]) >= int(elig["minimumDistinctTrainInscriptionsPerState"])
    }
    eligible_glyphs = {
        glyph for glyph, count in glyph_count.items()
        if count >= int(elig["minimumTrainGlyphOccurrences"])
        and len(glyph_docs[glyph]) >= int(elig["minimumDistinctTrainInscriptions"])
    }
    states = sorted(common_states) + [OTHER, "<DOC>", "<LINE>"]
    if variant == "boundaryAware":
        states.append("<WORD>")

    return {
        "states": states,
        "commonStates": common_states,
        "eligibleGlyphs": eligible_glyphs,
        "stateCount": state_count,
        "stateDocs": state_docs,
        "glyphCount": glyph_count,
        "glyphDocs": glyph_docs,
        "totalOperatorEvents": total_operator_events,
    }


def count_events(rows, variant, common_states, eligible_glyphs):
    base = Counter()
    operator = Counter()
    operator_input = Counter()
    classless_events = 0
    covered_events = 0
    by_doc = defaultdict(list)

    for row in rows:
        doc = row["anonymousInscriptionId"]
        stream = sequence_stream(row["words"], variant)
        for pos in range(1, len(stream) - 1):
            glyph = stream[pos]
            if not is_operator(glyph):
                continue
            incoming = map_state(stream[pos - 1], common_states)
            outgoing = map_state(stream[pos + 1], common_states)
            base[(incoming, outgoing)] += 1
            classless_events += 1
            if glyph in eligible_glyphs:
                operator[(glyph, incoming, outgoing)] += 1
                operator_input[(glyph, incoming)] += 1
                covered_events += 1
                by_doc[doc].append((glyph, incoming, outgoing))
    return {
        "base": base,
        "operator": operator,
        "operatorInput": operator_input,
        "allEvents": classless_events,
        "coveredEvents": covered_events,
        "byDoc": by_doc,
    }


def probability_functions(states, base, operator, model_cfg):
    alpha = float(model_cfg["globalAdditiveAlpha"])
    op_lambda = float(model_cfg["operatorBackoffPseudoCount"])
    base_total = Counter()
    op_total = Counter()
    for (incoming, outgoing), count in base.items():
        base_total[incoming] += count
    for (glyph, incoming, outgoing), count in operator.items():
        op_total[(glyph, incoming)] += count
    nstates = max(1, len(states))

    def p0(incoming, outgoing):
        return (base[(incoming, outgoing)] + alpha) / (base_total[incoming] + alpha * nstates)

    def pop(glyph, incoming, outgoing):
        total = op_total[(glyph, incoming)]
        back = p0(incoming, outgoing)
        if total <= 0:
            return back
        return (operator[(glyph, incoming, outgoing)] + op_lambda * back) / (total + op_lambda)

    return p0, pop


def operator_fingerprints(states, eligible_glyphs, counts, model_cfg):
    p0, pop = probability_functions(states, counts["base"], counts["operator"], model_cfg)
    totals = Counter()
    for (glyph, incoming), count in counts["operatorInput"].items():
        totals[glyph] += count
    vectors = {}
    for glyph in sorted(eligible_glyphs):
        total = max(1, totals[glyph])
        vector = []
        for incoming in states:
            input_count = counts["operatorInput"][(glyph, incoming)]
            weight = math.sqrt(input_count / total) if input_count else 0.0
            for outgoing in states:
                vector.append(weight * (pop(glyph, incoming, outgoing) - p0(incoming, outgoing)))
        vectors[glyph] = vector
    return vectors


def squared_distance(a, b):
    return sum((x - y) * (x - y) for x, y in zip(a, b))


def agglomerative_average_link(vectors, target_k):
    glyphs = sorted(vectors)
    if not glyphs:
        return {}
    target_k = max(1, min(int(target_k), len(glyphs)))
    pair_distance = {}
    for i, a in enumerate(glyphs):
        for b in glyphs[i + 1:]:
            pair_distance[(a, b)] = squared_distance(vectors[a], vectors[b])

    clusters = [tuple([glyph]) for glyph in glyphs]

    def glyph_distance(a, b):
        if a == b:
            return 0.0
        key = (a, b) if a < b else (b, a)
        return pair_distance[key]

    def cluster_distance(left, right):
        total = 0.0
        n = 0
        for a in left:
            for b in right:
                total += glyph_distance(a, b)
                n += 1
        return total / max(1, n)

    while len(clusters) > target_k:
        best = None
        for i in range(len(clusters)):
            for j in range(i + 1, len(clusters)):
                left, right = clusters[i], clusters[j]
                candidate = (cluster_distance(left, right), left, right, i, j)
                if best is None or candidate[:3] < best[:3]:
                    best = candidate
        _, left, right, i, j = best
        merged = tuple(sorted(left + right))
        clusters = [cluster for index, cluster in enumerate(clusters) if index not in (i, j)]
        clusters.append(merged)
        clusters.sort()

    clusters.sort(key=lambda c: (c[0], len(c), c))
    membership = {}
    for class_index, cluster in enumerate(clusters):
        class_id = f"C{class_index + 1:02d}"
        for glyph in cluster:
            membership[glyph] = class_id
    return membership


def class_counts(rows, variant, common_states, eligible_glyphs, membership):
    counts = Counter()
    totals = Counter()
    for row in rows:
        stream = sequence_stream(row["words"], variant)
        for pos in range(1, len(stream) - 1):
            glyph = stream[pos]
            if glyph not in eligible_glyphs:
                continue
            incoming = map_state(stream[pos - 1], common_states)
            outgoing = map_state(stream[pos + 1], common_states)
            class_id = membership[glyph]
            counts[(class_id, incoming, outgoing)] += 1
            totals[(class_id, incoming)] += 1
    return counts, totals


def pclass_factory(states, p0, counts, totals, model_cfg):
    lam = float(model_cfg["classBackoffPseudoCount"])

    def pclass(class_id, incoming, outgoing):
        total = totals[(class_id, incoming)]
        back = p0(incoming, outgoing)
        if total <= 0:
            return back
        return (counts[(class_id, incoming, outgoing)] + lam * back) / (total + lam)

    return pclass


def score_events(rows, variant, common_states, eligible_glyphs, states, base, operator, membership, class_tab, class_totals, model_cfg):
    p0, pop = probability_functions(states, base, operator, model_cfg)
    pclass = pclass_factory(states, p0, class_tab, class_totals, model_cfg)
    total_all = 0
    total_covered = 0
    loss0 = 0.0
    loss_op = 0.0
    loss_class = 0.0
    per_doc = defaultdict(lambda: [0.0, 0.0, 0])
    glyph_eval_count = Counter()

    for row in rows:
        doc = row["anonymousInscriptionId"]
        stream = sequence_stream(row["words"], variant)
        for pos in range(1, len(stream) - 1):
            glyph = stream[pos]
            if not is_operator(glyph):
                continue
            total_all += 1
            if glyph not in eligible_glyphs:
                continue
            incoming = map_state(stream[pos - 1], common_states)
            outgoing = map_state(stream[pos + 1], common_states)
            class_id = membership[glyph]
            q0 = max(p0(incoming, outgoing), 1e-300)
            qop = max(pop(glyph, incoming, outgoing), 1e-300)
            qc = max(pclass(class_id, incoming, outgoing), 1e-300)
            l0 = -math.log2(q0)
            lop = -math.log2(qop)
            lc = -math.log2(qc)
            total_covered += 1
            loss0 += l0
            loss_op += lop
            loss_class += lc
            per_doc[doc][0] += l0
            per_doc[doc][1] += lop
            per_doc[doc][2] += 1
            glyph_eval_count[glyph] += 1

    if total_covered <= 0:
        return {
            "allEvents": total_all,
            "coveredEvents": 0,
            "coveredFraction": 0.0,
            "distinctCoveredInscriptions": 0,
            "baselineBitsPerEvent": None,
            "operatorBitsPerEvent": None,
            "classBitsPerEvent": None,
            "operatorGainBitsPerEvent": None,
            "classGainBitsPerEvent": None,
            "classRetentionOfOperatorGain": None,
            "inscriptionFractionOperatorBeatsBaseline": None,
            "glyphEvaluationCounts": {},
        }

    baseline_bpe = loss0 / total_covered
    operator_bpe = loss_op / total_covered
    class_bpe = loss_class / total_covered
    operator_gain = baseline_bpe - operator_bpe
    class_gain = baseline_bpe - class_bpe
    retention = class_gain / operator_gain if operator_gain > 0 else 0.0
    comparable_docs = [v for v in per_doc.values() if v[2] > 0]
    wins = sum(1 for l0, lop, n in comparable_docs if lop < l0)

    return {
        "allEvents": total_all,
        "coveredEvents": total_covered,
        "coveredFraction": total_covered / max(1, total_all),
        "distinctCoveredInscriptions": len(comparable_docs),
        "baselineBitsPerEvent": baseline_bpe,
        "operatorBitsPerEvent": operator_bpe,
        "classBitsPerEvent": class_bpe,
        "operatorGainBitsPerEvent": operator_gain,
        "classGainBitsPerEvent": class_gain,
        "classRetentionOfOperatorGain": retention,
        "inscriptionFractionOperatorBeatsBaseline": wins / max(1, len(comparable_docs)),
        "glyphEvaluationCounts": dict(sorted(glyph_eval_count.items())),
    }


def cv_select_class_count(rows, variant, common_states, eligible_glyphs, states, protocol):
    candidates = [k for k in protocol["functionalClasses"]["candidateClassCounts"] if k <= len(eligible_glyphs)]
    if not candidates:
        return 1, [{"classCount": 1, "scoreBits": None, "events": 0}]
    folds = 5
    aggregate = {k: {"weighted": 0.0, "events": 0, "folds": 0} for k in candidates}

    for fold in range(folds):
        fit_rows = [r for r in rows if fold_for_doc(r["anonymousInscriptionId"], folds) != fold]
        val_rows = [r for r in rows if fold_for_doc(r["anonymousInscriptionId"], folds) == fold]
        fit_counts = count_events(fit_rows, variant, common_states, eligible_glyphs)
        vectors = operator_fingerprints(states, eligible_glyphs, fit_counts, protocol["model"])
        p0, _ = probability_functions(states, fit_counts["base"], fit_counts["operator"], protocol["model"])

        for k in candidates:
            membership = agglomerative_average_link(vectors, k)
            ctab, ctotals = class_counts(fit_rows, variant, common_states, eligible_glyphs, membership)
            pc = pclass_factory(states, p0, ctab, ctotals, protocol["model"])
            loss = 0.0
            events = 0
            for row in val_rows:
                stream = sequence_stream(row["words"], variant)
                for pos in range(1, len(stream) - 1):
                    glyph = stream[pos]
                    if glyph not in eligible_glyphs:
                        continue
                    incoming = map_state(stream[pos - 1], common_states)
                    outgoing = map_state(stream[pos + 1], common_states)
                    q = max(pc(membership[glyph], incoming, outgoing), 1e-300)
                    loss += -math.log2(q)
                    events += 1
            if events <= 0:
                continue
            nonempty_contexts = sum(1 for value in ctotals.values() if value > 0)
            penalty = 0.5 * nonempty_contexts * math.log(max(2, events)) / max(1, events) / math.log(2)
            score = loss / events + penalty
            aggregate[k]["weighted"] += score * events
            aggregate[k]["events"] += events
            aggregate[k]["folds"] += 1

    rows_out = []
    for k in candidates:
        item = aggregate[k]
        score = item["weighted"] / item["events"] if item["events"] else float("inf")
        rows_out.append({"classCount": k, "scoreBits": score, "events": item["events"], "folds": item["folds"]})
    rows_out.sort(key=lambda r: (r["scoreBits"], r["classCount"]))
    return rows_out[0]["classCount"], rows_out


def counter_to_rows(counter, names):
    rows = []
    for key, count in counter.items():
        if not isinstance(key, tuple):
            key = (key,)
        row = {name: value for name, value in zip(names, key)}
        row["count"] = int(count)
        rows.append(row)
    rows.sort(key=lambda r: tuple(str(r[n]) for n in names))
    return rows


def rows_to_counter(rows, names):
    result = Counter()
    for row in rows:
        result[tuple(row[name] for name in names)] = int(row["count"])
    return result


def freeze_variant(train_rows, protocol, variant):
    inventory = derive_train_inventory(train_rows, protocol, variant)
    common_states = inventory["commonStates"]
    eligible_glyphs = inventory["eligibleGlyphs"]
    states = inventory["states"]
    counts = count_events(train_rows, variant, common_states, eligible_glyphs)
    class_count, cv = cv_select_class_count(
        train_rows, variant, common_states, eligible_glyphs, states, protocol
    )
    vectors = operator_fingerprints(states, eligible_glyphs, counts, protocol["model"])
    membership = agglomerative_average_link(vectors, class_count)
    ctab, ctotals = class_counts(train_rows, variant, common_states, eligible_glyphs, membership)

    classes = defaultdict(list)
    for glyph, class_id in membership.items():
        classes[class_id].append(glyph)

    return {
        "variant": variant,
        "states": states,
        "commonStates": sorted(common_states),
        "eligibleGlyphs": sorted(eligible_glyphs),
        "trainInventory": {
            "inscriptions": len(train_rows),
            "allOperatorEvents": inventory["totalOperatorEvents"],
            "eligibleGlyphCount": len(eligible_glyphs),
            "commonStateCount": len(common_states),
            "eligibleGlyphOccurrences": sum(inventory["glyphCount"][g] for g in eligible_glyphs),
            "eligibleGlyphDistinctInscriptionCounts": {
                glyph: len(inventory["glyphDocs"][glyph]) for glyph in sorted(eligible_glyphs)
            },
            "eligibleGlyphTrainOccurrences": {
                glyph: inventory["glyphCount"][glyph] for glyph in sorted(eligible_glyphs)
            },
        },
        "counts": {
            "baseline": counter_to_rows(counts["base"], ("inputState", "outputState")),
            "operator": counter_to_rows(counts["operator"], ("glyph", "inputState", "outputState")),
            "class": counter_to_rows(ctab, ("classId", "inputState", "outputState")),
        },
        "classSelection": {
            "selectedClassCount": class_count,
            "crossValidation": cv,
        },
        "classMembership": dict(sorted(membership.items())),
        "classes": {class_id: sorted(glyphs) for class_id, glyphs in sorted(classes.items())},
    }


def thaw_variant(model_variant):
    base = rows_to_counter(model_variant["counts"]["baseline"], ("inputState", "outputState"))
    operator = rows_to_counter(model_variant["counts"]["operator"], ("glyph", "inputState", "outputState"))
    class_tab = rows_to_counter(model_variant["counts"]["class"], ("classId", "inputState", "outputState"))
    class_totals = Counter()
    for (class_id, incoming, outgoing), count in class_tab.items():
        class_totals[(class_id, incoming)] += count
    return base, operator, class_tab, class_totals
