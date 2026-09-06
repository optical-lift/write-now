#!/usr/bin/env python3
import math
import random
from collections import Counter, defaultdict

from mark_hebrew_glyph_annotation_competition_v19_io import canonical_json
from mark_hebrew_glyph_annotation_competition_v19_projector import glyph_segments, hist
from mark_structural_transition_consequence_v23_core import OUTCOMES as HIST_STATES

EPS = 1e-300
REPRESENTATIONS = ("lemma", "lemmaCoarseMorph", "lemmaFullMorph")
MASK = "<ORIGIN_MASK>"
SIGNATURE_ALPHABET_SIZE = len(HIST_STATES) * len(HIST_STATES)


def _bucket(value, pairs, labels):
    for (lo, hi), label in zip(pairs, labels):
        if int(lo) <= int(value) <= int(hi):
            return label
    raise ValueError(f"value {value} outside frozen bins")


def _pos_bucket(i, protocol):
    s = protocol["stratification"]
    return _bucket(i, s["originPositionBuckets"], s["originPositionLabels"])


def _len_bucket(n, protocol):
    s = protocol["stratification"]
    return _bucket(n, s["unitLengthBins"], s["unitLengthLabels"])


def _seq(verse, rep):
    return verse["tokens"] if rep == "lemma" else verse[rep]


def _unit_events(unit_id, seq, protocol):
    distances = tuple(int(d) for d in protocol["distances"])
    n = len(seq)
    lb = _len_bucket(n, protocol)
    out = []
    for i, op in enumerate(seq):
        masked = list(seq)
        masked[i] = MASK
        pb = _pos_bucket(i, protocol)
        origin = f"{unit_id}:{i}"
        for d in distances:
            j = i + d
            if j < 0 or j >= n:
                continue
            sig = canonical_json([hist(masked, j), hist(masked, j + 1)])
            out.append({
                "origin": origin,
                "operator": op,
                "distance": d,
                "stratum": canonical_json([pb, lb]),
                "signature": sig,
            })
    return out


def hebrew_events(chapters, rep, protocol):
    out = []
    for ch in chapters:
        for verse in ch["verses"]:
            out.extend(_unit_events(verse["anonymousVerseId"], _seq(verse, rep), protocol))
    return out


def glyph_events(rows, protocol):
    out = []
    for unit, seq in glyph_segments(rows):
        out.extend(_unit_events(unit, seq, protocol))
    return out


def _origin_support(events):
    seen = defaultdict(set)
    for e in events:
        seen[e["operator"]].add(e["origin"])
    return {o: len(v) for o, v in seen.items()}


def _frequency_bins(operators, support, n_bins):
    ordered = sorted(operators, key=lambda o: (support[o], o))
    bins = defaultdict(list)
    if not ordered:
        return {}, {}
    for rank, op in enumerate(ordered):
        b = min(n_bins - 1, (rank * n_bins) // len(ordered))
        bins[b].append(op)
    opbin = {op: b for b, ops in bins.items() for op in ops}
    return dict(bins), opbin


def _counter_record(cnt):
    return {"counts": dict(cnt), "total": int(sum(cnt.values()))}


def build_model(events, protocol):
    cfg = protocol["training"]
    support = _origin_support(events)
    eligible = [(o, n) for o, n in support.items() if n >= int(cfg["minimumOperatorEvents"])]
    eligible.sort(key=lambda x: (-x[1], x[0]))
    operators = [o for o, _ in eligible[:int(cfg["maximumOperatorsPerSystem"])]]
    opset = set(operators)
    kept = [e for e in events if e["operator"] in opset]
    bins, opbin = _frequency_bins(operators, support, int(cfg["operatorFrequencyMatchBins"]))

    by_d = {}
    min_stratum = int(cfg["minimumSignatureEventsPerStratum"])
    for d in map(int, protocol["distances"]):
        rows = [e for e in kept if e["distance"] == d]
        global_counts = Counter(e["signature"] for e in rows)
        base_counts = defaultdict(Counter)
        op_counts = defaultdict(Counter)
        for e in rows:
            base_counts[e["stratum"]][e["signature"]] += 1
            op_counts[(e["operator"], e["stratum"])][e["signature"]] += 1
        baseline = {}
        for st, cnt in base_counts.items():
            rec = _counter_record(cnt)
            rec["active"] = rec["total"] >= min_stratum
            baseline[st] = rec
        operator = {
            canonical_json([op, st]): _counter_record(cnt)
            for (op, st), cnt in op_counts.items()
        }
        by_d[str(d)] = {
            "trainEvents": len(rows),
            "globalCounts": dict(global_counts),
            "globalTotal": int(sum(global_counts.values())),
            "baseline": baseline,
            "operator": operator,
        }
    return {
        "operators": operators,
        "operatorOriginSupport": {o: int(support[o]) for o in operators},
        "frequencyBins": {str(b): ops for b, ops in bins.items()},
        "operatorFrequencyBin": {o: int(b) for o, b in opbin.items()},
        "distances": by_d,
        "trainEvents": len(kept),
        "smoothing": {
            "globalAlpha": float(cfg["globalAlpha"]),
            "baselineBackoffPseudoCount": float(cfg["baselineBackoffPseudoCount"]),
            "operatorBackoffPseudoCount": float(cfg["operatorBackoffPseudoCount"]),
            "signatureAlphabetSize": SIGNATURE_ALPHABET_SIZE,
        },
    }


def freeze_models(hebrew_train, glyph_train, protocol):
    return {
        "signatureAlphabetSize": SIGNATURE_ALPHABET_SIZE,
        "hebrew": {
            rep: build_model(hebrew_events(hebrew_train, rep, protocol), protocol)
            for rep in REPRESENTATIONS
        },
        "glyph": build_model(glyph_events(glyph_train, protocol), protocol),
    }


def _probabilities(model, d, op, st, sig, source_op=None):
    dm = model["distances"][str(d)]
    sm = model["smoothing"]
    alpha = sm["globalAlpha"]
    k = sm["signatureAlphabetSize"]
    gt = dm["globalTotal"]
    pglobal = (dm["globalCounts"].get(sig, 0) + alpha) / (gt + alpha * k)

    brec = dm["baseline"].get(st)
    if brec and brec.get("active"):
        bp = sm["baselineBackoffPseudoCount"]
        base = (brec["counts"].get(sig, 0) + bp * pglobal) / (brec["total"] + bp)
    else:
        base = pglobal

    src = op if source_op is None else source_op
    orec = dm["operator"].get(canonical_json([src, st]))
    if orec:
        opseudo = sm["operatorBackoffPseudoCount"]
        cond = (orec["counts"].get(sig, 0) + opseudo * base) / (orec["total"] + opseudo)
    else:
        cond = base
    return base, cond


def _qualify(events, model, protocol):
    ec = protocol["evaluation"]
    opset = set(model["operators"])
    kept = [e for e in events if e["operator"] in opset]
    counts = Counter((e["distance"], e["operator"]) for e in kept)
    qualified = {}
    for d in map(int, protocol["distances"]):
        qualified[d] = sorted(
            o for o in model["operators"]
            if counts[(d, o)] >= int(ec["minimumEvaluationEventsPerOperatorDistance"])
        )
    return kept, qualified


def _score_cache(events, model, qualified):
    qsets = {d: set(ops) for d, ops in qualified.items()}
    cell_counts = defaultdict(Counter)
    strata_by_target = defaultdict(set)
    for e in events:
        d, op = int(e["distance"]), e["operator"]
        if op in qsets.get(d, set()):
            cell_counts[(d, op, e["stratum"])][e["signature"]] += 1
            strata_by_target[(d, op)].add(e["stratum"])

    cache = {}
    allops = set(model["operators"])
    for d, qops in qualified.items():
        for target in qops:
            b = model["operatorFrequencyBin"].get(target)
            sources = [o for o in model["frequencyBins"].get(str(b), []) if o in allops]
            if target not in sources:
                sources.append(target)
            for source in sources:
                total_gain = 0.0
                n = 0
                for st in strata_by_target.get((d, target), ()):
                    cnt = cell_counts[(d, target, st)]
                    for sig, c in cnt.items():
                        base, cond = _probabilities(model, d, target, st, sig, source)
                        total_gain += c * (math.log2(max(cond, EPS)) - math.log2(max(base, EPS)))
                        n += c
                cache[(d, target, source)] = (total_gain / n if n else 0.0, n)
    return cache


def _actual_curve(cache, qualified):
    curve = {}
    for d, ops in qualified.items():
        vals = [cache[(d, o, o)][0] for o in ops if cache.get((d, o, o), (0,0))[1] > 0]
        curve[d] = sum(vals) / len(vals) if vals else None
    return curve


def _perm_mapping(model, seed):
    rng = random.Random(seed)
    mapping = {}
    for _, ops in sorted(model["frequencyBins"].items()):
        ops = sorted(ops)
        shuffled = list(ops)
        rng.shuffle(shuffled)
        mapping.update(dict(zip(ops, shuffled)))
    return mapping


def _curve_stats(curve):
    vals = [(d, g) for d, g in curve.items() if g is not None]
    positive_mass = sum(max(g, 0.0) for _, g in vals)
    peak_d, peak = max(vals, key=lambda x: x[1]) if vals else (None, 0.0)
    pre = sum(max(g, 0.0) for d, g in vals if d < 0)
    post = sum(max(g, 0.0) for d, g in vals if d > 0)
    denom = positive_mass
    center = (sum(d * max(g, 0.0) for d, g in vals) / denom) if denom > 0 else None
    return positive_mass, peak_d, peak, pre, post, center


def evaluate_system(events, model, protocol, lane, label):
    kept, qualified = _qualify(events, model, protocol)
    minimum_ops = int(protocol["evaluation"]["minimumEvaluableOperatorsPerDistance"])
    supported = {d: ops for d, ops in qualified.items() if len(ops) >= minimum_ops}
    cache = _score_cache(kept, model, supported)
    actual = _actual_curve(cache, supported)
    posmass, peak_d, peak, pre, post, center = _curve_stats(actual)

    perms = int(protocol["null"]["permutations"])
    ge_mass = 0
    ge_peak = 0
    for pidx in range(perms):
        null_curve = {}
        for d, ops in supported.items():
            mapping = _perm_mapping(model, f"mark-v29:{label}:{lane}:{d}:{pidx}")
            vals = []
            for target in ops:
                source = mapping.get(target, target)
                rec = cache.get((d, target, source))
                if rec and rec[1] > 0:
                    vals.append(rec[0])
            null_curve[d] = sum(vals) / len(vals) if vals else None
        nmass, _, npeak, _, _, _ = _curve_stats(null_curve)
        ge_mass += int(nmass >= posmass - 1e-15)
        ge_peak += int(npeak >= peak - 1e-15)
    p_mass = (1 + ge_mass) / (perms + 1)
    p_peak = (1 + ge_peak) / (perms + 1)
    sufficient = len(supported) >= int(protocol["evaluation"]["minimumDistancesWithSupport"])
    passed = sufficient and posmass > 0 and p_mass <= float(protocol["evaluation"]["positiveFootprintMassPAtMost"])
    return {
        "lane": lane,
        "label": label,
        "evaluationEvents": len(kept),
        "frozenOperators": len(model["operators"]),
        "supportedDistances": len(supported),
        "operatorsPerDistance": {str(d): len(ops) for d, ops in supported.items()},
        "gainCurve": {str(d): actual[d] for d in sorted(actual)},
        "positiveFootprintMass": posmass,
        "positiveFootprintMassP": p_mass,
        "familywisePeakDistance": peak_d,
        "familywisePeakGain": peak,
        "familywisePeakP": p_peak,
        "preOperatorPositiveMass": pre,
        "postOperatorPositiveMass": post,
        "centerOfPositiveMass": center,
        "sufficient": sufficient,
        "pass": passed,
    }


def _pearson(xs, ys):
    if len(xs) < 2:
        return 0.0
    mx, my = sum(xs)/len(xs), sum(ys)/len(ys)
    dx, dy = [x-mx for x in xs], [y-my for y in ys]
    den = math.sqrt(sum(x*x for x in dx) * sum(y*y for y in dy))
    return sum(x*y for x, y in zip(dx,dy)) / den if den else 0.0


def compare_curves(h, g, protocol, rep, lane):
    hc = {int(k):v for k,v in h["gainCurve"].items() if v is not None}
    gc = {int(k):v for k,v in g["gainCurve"].items() if v is not None}
    ds = sorted(set(hc) & set(gc))
    minimum = int(protocol["crossSystem"]["minimumCommonSupportedDistances"])
    if len(ds) < minimum:
        return {"commonDistances":len(ds),"pearsonR":0.0,"permutationP":1.0,"sufficient":False,"pass":False}
    x = [hc[d] for d in ds]
    y = [gc[d] for d in ds]
    r = _pearson(x,y)
    rng = random.Random(f"mark-v29-cross:{rep}:{lane}")
    nperm = int(protocol["crossSystem"]["permutations"])
    ge = 0
    for _ in range(nperm):
        yp = list(y)
        rng.shuffle(yp)
        ge += int(_pearson(x,yp) >= r - 1e-15)
    p = (1+ge)/(nperm+1)
    passed = h["pass"] and g["pass"] and r > 0 and p <= float(protocol["crossSystem"]["pAtMost"])
    return {"commonDistances":len(ds),"pearsonR":r,"permutationP":p,"sufficient":True,"pass":passed}


def evaluate_all(hebrew_eval, glyph_eval, freeze, protocol):
    lanes = {"holdout":{}, "control":{}}
    glyph = {}
    for lane in ("holdout","control"):
        g = evaluate_system(glyph_events(glyph_eval[lane], protocol), freeze["glyph"], protocol, lane, "glyph")
        glyph[lane] = g
        for rep in REPRESENTATIONS:
            h = evaluate_system(hebrew_events(hebrew_eval[lane], rep, protocol), freeze["hebrew"][rep], protocol, lane, rep)
            lanes[lane][rep] = {"hebrew":h, "cross":compare_curves(h,g,protocol,rep,lane)}
    return lanes, glyph


def adjudicate(lanes, glyph):
    hpass = [rep for rep in REPRESENTATIONS if all(lanes[l][rep]["hebrew"]["pass"] for l in ("holdout","control"))]
    gpass = all(glyph[l]["pass"] for l in ("holdout","control"))
    cross = [rep for rep in hpass if gpass and all(lanes[l][rep]["cross"]["pass"] for l in ("holdout","control"))]
    if cross:
        return "CROSS_SYSTEM_TEMPORAL_FOOTPRINT_ALIGNED"
    if len(hpass) > 1:
        return "MULTIPLE_HEBREW_REPRESENTATIONS_HAVE_TEMPORAL_FOOTPRINT"
    if len(hpass) == 1:
        return {
            "lemma":"LEMMA_HAS_TEMPORAL_FOOTPRINT",
            "lemmaCoarseMorph":"COARSE_MORPH_HAS_TEMPORAL_FOOTPRINT",
            "lemmaFullMorph":"FULL_MORPH_HAS_TEMPORAL_FOOTPRINT",
        }[hpass[0]]
    if gpass:
        return "GLYPH_ONLY_TEMPORAL_FOOTPRINT"
    sufficient = any(lanes[l][r]["hebrew"]["sufficient"] for l in ("holdout","control") for r in REPRESENTATIONS) or any(glyph[l]["sufficient"] for l in ("holdout","control"))
    return "NO_TRANSFERABLE_TEMPORAL_FOOTPRINT" if sufficient else "INSUFFICIENT_TEMPORAL_SUPPORT"
