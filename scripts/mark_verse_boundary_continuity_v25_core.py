#!/usr/bin/env python3
import hashlib
import itertools
import math
import random
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from pathlib import Path

from mark_hebrew_glyph_annotation_competition_v19_io import (
    NS, bucket, canonical_json, read_json, read_jsonl, sha256_json,
    write_json, write_jsonl,
)
from mark_hebrew_glyph_annotation_competition_v19_projector import hist
from mark_hebrew_operator_representation_v21_core import _target_lemma_and_morph
from mark_structural_transition_consequence_v23_core import OUTCOMES

EPS = 1e-300
REPRESENTATIONS = ("lemma", "lemmaCoarseMorph", "lemmaFullMorph")


def _anon(prefix, text):
    return prefix + hashlib.sha256(text.encode("utf-8")).hexdigest()[:20]


def _length_bin(n, bins):
    for i, pair in enumerate(bins):
        lo, hi = int(pair[0]), int(pair[1])
        if lo <= n <= hi:
            return i
    raise ValueError(f"no length bin for {n}")


def _rotate_assign(items, salt):
    if len(items) < 2:
        return {}, list(items)
    ordered = sorted(items, key=lambda x: hashlib.sha256(
        (salt + x["originVerseId"]).encode("utf-8")
    ).hexdigest())
    out = {}
    for i, row in enumerate(ordered):
        donor = ordered[(i + 1) % len(ordered)]
        out[row["originVerseId"]] = donor["actualNextVerseId"]
    return out, []


def _build_shuffle_map(lanes, protocol):
    bins = protocol["shuffleControl"]["lengthBinsByLemmaTokenCount"]
    salt = protocol["shuffleControl"]["salt"]
    mapping = {}
    for lane, chapters in lanes.items():
        boundaries = []
        for chapter in chapters:
            verses = chapter["verses"]
            for i in range(len(verses) - 1):
                boundaries.append({
                    "lane": lane,
                    "book": chapter["anonymousBookId"],
                    "originVerseId": verses[i]["anonymousVerseId"],
                    "actualNextVerseId": verses[i + 1]["anonymousVerseId"],
                    "lengthBin": _length_bin(len(verses[i + 1]["tokens"]), bins),
                })
        unresolved = []
        primary = defaultdict(list)
        for row in boundaries:
            primary[(row["book"], row["lengthBin"])].append(row)
        for key in sorted(primary):
            assigned, left = _rotate_assign(primary[key], salt + ":primary:")
            mapping.update(assigned)
            unresolved.extend(left)

        book_groups = defaultdict(list)
        for row in unresolved:
            book_groups[row["book"]].append(row)
        unresolved2 = []
        for key in sorted(book_groups):
            assigned, left = _rotate_assign(book_groups[key], salt + ":book:")
            mapping.update(assigned)
            unresolved2.extend(left)

        assigned, left = _rotate_assign(unresolved2, salt + ":lane:" + lane + ":")
        mapping.update(assigned)
        # A true singleton lane is intentionally left without a control.

    # Prove no shuffled target equals the actual adjacent verse.
    actual = {}
    for chapters in lanes.values():
        for chapter in chapters:
            verses = chapter["verses"]
            for i in range(len(verses) - 1):
                actual[verses[i]["anonymousVerseId"]] = verses[i + 1]["anonymousVerseId"]
    for origin, target in mapping.items():
        if actual.get(origin) == target:
            raise ValueError("shuffle assignment accidentally preserved actual adjacency")
    return mapping


def parse_ordered_chapters(wlc_dir, protocol):
    split = protocol["split"]
    lane_buckets = {
        "train": set(split["trainBuckets"]),
        "holdout": set(split["holdoutBuckets"]),
        "control": set(split["controlBuckets"]),
    }
    lanes = {k: [] for k in lane_buckets}

    for path in sorted(Path(wlc_dir).glob("*.xml")):
        root = ET.parse(path).getroot()
        for chapter in root.findall(".//osis:chapter", NS):
            chapter_id = chapter.attrib.get("osisID")
            if not chapter_id:
                continue
            b = bucket(chapter_id, int(split["modulus"]))
            lane = next(name for name, vals in lane_buckets.items() if b in vals)
            book = chapter_id.split(".")[0]
            verses_out = []
            for verse in chapter.findall(".//osis:verse", NS):
                verse_id = verse.attrib.get("osisID")
                if not verse_id:
                    continue
                lemma, coarse, full = [], [], []
                for w in verse.findall(".//osis:w", NS):
                    parsed = _target_lemma_and_morph(w)
                    if parsed is None:
                        continue
                    lem, c, f = parsed
                    lemma.append(lem)
                    coarse.append(f"{lem}|M={c}")
                    full.append(f"{lem}|M={f}")
                if not lemma:
                    continue
                verses_out.append({
                    "anonymousVerseId": _anon("V", verse_id),
                    "tokens": lemma,
                    "lemmaCoarseMorph": coarse,
                    "lemmaFullMorph": full,
                })
            if verses_out:
                lanes[lane].append({
                    "anonymousChapterId": _anon("C", chapter_id),
                    "anonymousBookId": _anon("B", book),
                    "lane": lane,
                    "verses": verses_out,
                })

    for lane in lanes:
        lanes[lane].sort(key=lambda x: x["anonymousChapterId"])

    shuffle_map = _build_shuffle_map(lanes, protocol)
    for chapters in lanes.values():
        for chapter in chapters:
            for verse in chapter["verses"][:-1]:
                verse["shuffleNextVerseId"] = shuffle_map.get(verse["anonymousVerseId"])
            chapter["verses"][-1]["shuffleNextVerseId"] = None

    manifest = {
        "schema": "mark_verse_boundary_continuity_chapter_packets_v25",
        "sourceCommit": protocol["hebrewSource"]["commit"],
        "chapterCounts": {lane: len(rows) for lane, rows in lanes.items()},
        "verseCounts": {
            lane: sum(len(ch["verses"]) for ch in rows) for lane, rows in lanes.items()
        },
        "tokenCounts": {
            lane: sum(len(v["tokens"]) for ch in rows for v in ch["verses"])
            for lane, rows in lanes.items()
        },
        "shuffleAssignments": sum(
            1 for rows in lanes.values() for ch in rows for v in ch["verses"]
            if v.get("shuffleNextVerseId")
        ),
        "representations": list(REPRESENTATIONS),
        "hardBoundary": "chapter",
    }
    return lanes, manifest


def identity_sequence(verse, representation):
    if representation == "lemma":
        return verse["tokens"]
    return verse[representation]


def _first_departure(seq, i):
    s0 = hist(seq, i)
    s1 = hist(seq, i + 1)
    for j in range(i + 1, len(seq)):
        state = hist(seq, j + 1)
        if state != s1:
            return s0, s1, state, j - i
    return s0, s1, None, None


def resolved_within_verse_events(chapters, representation):
    out = []
    for chapter in chapters:
        for verse in chapter["verses"]:
            seq = identity_sequence(verse, representation)
            for i, op in enumerate(seq):
                s0, s1, f, distance = _first_departure(seq, i)
                if f is None:
                    continue
                out.append({
                    "operator": op,
                    "S0": s0,
                    "S1": s1,
                    "F": f,
                    "distance": distance,
                })
    return out


def boundary_origins(chapters, representation):
    out = []
    verse_index = {
        v["anonymousVerseId"]: v
        for chapter in chapters for v in chapter["verses"]
    }
    for chapter in chapters:
        verses = chapter["verses"]
        for vi in range(len(verses) - 1):
            verse = verses[vi]
            actual_next = verses[vi + 1]
            shuffle_id = verse.get("shuffleNextVerseId")
            if not shuffle_id or shuffle_id not in verse_index:
                continue
            shuffled_next = verse_index[shuffle_id]
            seq = identity_sequence(verse, representation)
            actual_tail = identity_sequence(actual_next, representation)
            shuffled_tail = identity_sequence(shuffled_next, representation)
            for i, op in enumerate(seq):
                s0, s1, f_inside, _ = _first_departure(seq, i)
                if f_inside is not None:
                    continue
                real_combined = seq + actual_tail
                shuffle_combined = seq + shuffled_tail
                real_f = None
                real_d = None
                for k in range(len(seq), len(real_combined)):
                    st = hist(real_combined, k + 1)
                    if st != s1:
                        real_f = st
                        real_d = k - i
                        break
                shuffle_f = None
                shuffle_d = None
                for k in range(len(seq), len(shuffle_combined)):
                    st = hist(shuffle_combined, k + 1)
                    if st != s1:
                        shuffle_f = st
                        shuffle_d = k - i
                        break
                out.append({
                    "originVerseId": verse["anonymousVerseId"],
                    "operator": op,
                    "S0": s0,
                    "S1": s1,
                    "realF": real_f,
                    "shuffleF": shuffle_f,
                    "realDistance": real_d,
                    "shuffleDistance": shuffle_d,
                })
    return out


def _normalize(d):
    z = sum(d.values())
    if z <= 0:
        return {y: 1.0 / len(OUTCOMES) for y in OUTCOMES}
    return {y: d.get(y, 0.0) / z for y in OUTCOMES}


def _dist(counts, prior, pseudo):
    n = sum(counts.values())
    return {
        y: (counts[y] + pseudo * prior[y]) / (n + pseudo)
        for y in OUTCOMES
    }


def build_destination_model(events, protocol):
    cfg = protocol["training"]
    opn = Counter(e["operator"] for e in events)
    op_states = defaultdict(set)
    for e in events:
        op_states[e["operator"]].add(e["S1"])
    eligible = [
        (op, n) for op, n in opn.items()
        if n >= int(cfg["minimumResolvedEventsPerOperator"])
        and len(op_states[op]) >= int(cfg["minimumResolvedS1StatesPerOperator"])
    ]
    eligible.sort(key=lambda x: (-x[1], x[0]))
    operators = [x[0] for x in eligible[:int(cfg["maximumOperatorsPerRepresentation"])]]
    op_set = set(operators)
    kept = [e for e in events if e["operator"] in op_set]

    alpha = float(cfg["globalAdditiveAlpha"])
    global_counts = Counter(e["F"] for e in kept)
    total = sum(global_counts.values())
    p_global = {
        y: (global_counts[y] + alpha) / (total + alpha * len(OUTCOMES))
        for y in OUTCOMES
    }
    base_counts = defaultdict(Counter)
    context_counts = defaultdict(Counter)
    operator_counts = defaultdict(Counter)
    for e in kept:
        base_counts[e["S1"]][e["F"]] += 1
        context_counts[canonical_json([e["S0"], e["S1"]])][e["F"]] += 1
        operator_counts[canonical_json([e["S1"], e["operator"]])][e["F"]] += 1

    base = {
        s1: _dist(c, p_global, float(cfg["stateBackoffPseudoCount"]))
        for s1, c in base_counts.items()
    }
    context = {}
    for key, c in context_counts.items():
        s0, s1 = __import__("json").loads(key)
        prior = base.get(s1, p_global)
        context[key] = _dist(c, prior, float(cfg["contextBackoffPseudoCount"]))
    operator = {}
    for key, c in operator_counts.items():
        s1, op = __import__("json").loads(key)
        prior = base.get(s1, p_global)
        operator[key] = _dist(c, prior, float(cfg["operatorBackoffPseudoCount"]))

    return {
        "operators": operators,
        "operatorTrainSupport": {op: int(opn[op]) for op in operators},
        "resolvedTrainEvents": len(kept),
        "pGlobal": p_global,
        "base": base,
        "context": context,
        "operator": operator,
    }


def additive_distribution(model, s0, s1, op):
    base = model["base"].get(s1, model["pGlobal"])
    ctx = model["context"].get(canonical_json([s0, s1]), base)
    opd = model["operator"].get(canonical_json([s1, op]), base)
    return _normalize({
        y: ctx[y] * opd[y] / max(base[y], EPS)
        for y in OUTCOMES
    })


def freeze_models(train_chapters, protocol):
    systems = {}
    for rep in REPRESENTATIONS:
        events = resolved_within_verse_events(train_chapters, rep)
        systems[rep] = build_destination_model(events, protocol)
    return {"outcomes": list(OUTCOMES), "systems": systems}


def _signflip(values, seed, permutations):
    if not values:
        return 1.0
    obs = sum(values) / len(values)
    if len(values) <= 12:
        null = [
            sum(s * v for s, v in zip(signs, values)) / len(values)
            for signs in itertools.product((-1.0, 1.0), repeat=len(values))
        ]
        return sum(x >= obs - 1e-15 for x in null) / len(null)
    rng = random.Random(seed)
    null = []
    for _ in range(permutations):
        null.append(sum((1 if rng.random() < 0.5 else -1) * v for v in values) / len(values))
    return (1 + sum(x >= obs - 1e-15 for x in null)) / (len(null) + 1)


def _median(xs):
    if not xs:
        return None
    ys = sorted(xs)
    n = len(ys)
    return ys[n // 2] if n % 2 else (ys[n // 2 - 1] + ys[n // 2]) / 2.0


def evaluate_representation(chapters, representation, model, protocol, lane):
    origins = [
        e for e in boundary_origins(chapters, representation)
        if e["operator"] in set(model["operators"])
    ]
    real_resolved = [e for e in origins if e["realF"] is not None]
    shuffle_resolved = [e for e in origins if e["shuffleF"] is not None]
    common = [e for e in origins if e["realF"] is not None and e["shuffleF"] is not None]

    by_op = defaultdict(list)
    for e in common:
        dist = additive_distribution(model, e["S0"], e["S1"], e["operator"])
        delta = math.log2(max(dist[e["realF"]], EPS)) - math.log2(max(dist[e["shuffleF"]], EPS))
        by_op[e["operator"]].append(delta)

    min_events = int(protocol["evaluation"]["minimumBoundaryOriginsPerOperator"])
    op_means = {
        op: sum(vals) / len(vals)
        for op, vals in by_op.items() if len(vals) >= min_events
    }
    values = list(op_means.values())
    observed = sum(values) / len(values) if values else 0.0
    positive = sum(v > 0 for v in values) / len(values) if values else 0.0
    p = _signflip(
        values,
        f"mark-v25:{representation}:{lane}",
        int(protocol["evaluation"]["permutationCount"]),
    )
    real_fraction = len(real_resolved) / len(origins) if origins else 0.0
    shuffle_fraction = len(shuffle_resolved) / len(origins) if origins else 0.0
    gate = protocol["evaluation"]["primaryGatePerLane"]
    sufficient = (
        len(op_means) >= int(protocol["evaluation"]["minimumEvaluableOperators"])
        and len(common) >= int(gate["minimumCommonResolvedOrigins"])
    )
    recovery_guard = real_fraction >= shuffle_fraction - 1e-15
    passed = (
        sufficient
        and observed > float(gate["operatorBalancedRealMinusShuffleBitsGreaterThan"])
        and p <= float(gate["pairedSignFlipPAtMost"])
        and positive >= float(gate["positiveOperatorFractionAtLeast"])
        and recovery_guard
    )
    real_only = sum(e["realF"] is not None and e["shuffleF"] is None for e in origins)
    shuffle_only = sum(e["realF"] is None and e["shuffleF"] is not None for e in origins)
    rd = [e["realDistance"] for e in real_resolved if e["realDistance"] is not None]
    sd = [e["shuffleDistance"] for e in shuffle_resolved if e["shuffleDistance"] is not None]
    return {
        "representation": representation,
        "lane": lane,
        "eligibleBoundaryOrigins": len(origins),
        "commonResolvedOrigins": len(common),
        "evaluableOperators": len(op_means),
        "frozenOperators": len(model["operators"]),
        "operatorBalancedRealMinusShuffleBits": observed,
        "positiveOperatorFraction": positive,
        "signFlipP": p,
        "realRecoveryFraction": real_fraction,
        "shuffleRecoveryFraction": shuffle_fraction,
        "recoveryGuardPass": recovery_guard,
        "realOnlyResolved": real_only,
        "shuffleOnlyResolved": shuffle_only,
        "realMeanDistance": sum(rd) / len(rd) if rd else None,
        "realMedianDistance": _median(rd),
        "shuffleMeanDistance": sum(sd) / len(sd) if sd else None,
        "shuffleMedianDistance": _median(sd),
        "sufficient": sufficient,
        "pass": passed,
        "operators": {
            op: {"commonResolvedOrigins": len(by_op[op]), "meanDeltaBits": mean}
            for op, mean in sorted(op_means.items())
        },
    }


def adjudicate(results, freeze, protocol):
    reps = list(REPRESENTATIONS)
    sufficiently_tested = [
        rep for rep in reps
        if all(results[lane][rep]["sufficient"] for lane in ("holdout", "control"))
    ]
    if not sufficiently_tested:
        return "INSUFFICIENT_BOUNDARY_SUPPORT"
    passed = [
        rep for rep in sufficiently_tested
        if all(results[lane][rep]["pass"] for lane in ("holdout", "control"))
    ]
    if len(passed) > 1:
        return "MULTIPLE_REPRESENTATIONS_SUPPORT_VERSE_BOUNDARY_CONTINUITY"
    if len(passed) == 1:
        return {
            "lemma": "LEMMA_SUPPORTS_VERSE_BOUNDARY_CONTINUITY",
            "lemmaCoarseMorph": "COARSE_MORPH_SUPPORTS_VERSE_BOUNDARY_CONTINUITY",
            "lemmaFullMorph": "FULL_MORPH_SUPPORTS_VERSE_BOUNDARY_CONTINUITY",
        }[passed[0]]
    any_lane_pass = any(results[lane][rep]["pass"] for rep in sufficiently_tested for lane in ("holdout", "control"))
    if any_lane_pass:
        return "REAL_CONTINUATION_SIGNAL_DOES_NOT_REPLICATE"
    all_nonpositive = all(
        results[lane][rep]["operatorBalancedRealMinusShuffleBits"] <= 0
        for rep in sufficiently_tested for lane in ("holdout", "control")
    )
    if all_nonpositive:
        return "SHUFFLED_CONTINUATION_MATCHES_OR_BEATS_REAL"
    return "NO_VERSE_BOUNDARY_CONTINUITY_SIGNAL"
