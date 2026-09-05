#!/usr/bin/env python3
import hashlib
import itertools
import json
import math
import random
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from pathlib import Path

from mark_hebrew_glyph_annotation_competition_v19_io import (
    NS, canonical_json, read_json, read_jsonl, sha256_json, write_json, write_jsonl,
)
from mark_hebrew_glyph_annotation_competition_v19_projector import hist
from mark_hebrew_operator_representation_v21_core import _target_lemma_and_morph
from mark_verse_boundary_continuity_v25_core import _anon

EPS = 1e-300
REPRESENTATIONS = ("lemma", "lemmaCoarseMorph", "lemmaFullMorph")
RISK_OUTCOMES = ("CONTINUE", "DEPARTURE", "VERSE_BOUNDARY")


def _book_lane_map(book_ids, protocol):
    split = protocol["split"]
    salt = split["salt"]
    ordered = sorted(
        set(book_ids),
        key=lambda b: hashlib.sha256((salt + ":" + b).encode("utf-8")).hexdigest(),
    )
    residues = {
        "train": set(split["trainRankResidues"]),
        "holdout": set(split["holdoutRankResidues"]),
        "control": set(split["controlRankResidues"]),
    }
    mapping = {}
    for rank, book in enumerate(ordered):
        r = rank % 5
        lane = next(name for name, vals in residues.items() if r in vals)
        mapping[book] = lane
    return mapping, ordered


def parse_book_blocked_chapters(wlc_dir, protocol):
    raw = []
    books = []
    for path in sorted(Path(wlc_dir).glob("*.xml")):
        root = ET.parse(path).getroot()
        for chapter in root.findall(".//osis:chapter", NS):
            chapter_id = chapter.attrib.get("osisID")
            if not chapter_id:
                continue
            book = chapter_id.split(".")[0]
            books.append(book)
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
                raw.append((book, chapter_id, verses_out))

    lane_map, ordered_books = _book_lane_map(books, protocol)
    lanes = {"train": [], "holdout": [], "control": []}
    for book, chapter_id, verses in raw:
        lane = lane_map[book]
        lanes[lane].append({
            "anonymousChapterId": _anon("C", chapter_id),
            "anonymousBookId": _anon("B", book),
            "lane": lane,
            "verses": verses,
        })
    for lane in lanes:
        lanes[lane].sort(key=lambda x: x["anonymousChapterId"])

    lane_books = {
        lane: sorted({ch["anonymousBookId"] for ch in chapters})
        for lane, chapters in lanes.items()
    }
    if set(lane_books["train"]) & set(lane_books["holdout"]):
        raise ValueError("book custody overlap train/holdout")
    if set(lane_books["train"]) & set(lane_books["control"]):
        raise ValueError("book custody overlap train/control")
    if set(lane_books["holdout"]) & set(lane_books["control"]):
        raise ValueError("book custody overlap holdout/control")

    manifest = {
        "schema": "mark_competing_resolution_book_packets_v27",
        "sourceCommit": protocol["hebrewSource"]["commit"],
        "bookCounts": {lane: len(ids) for lane, ids in lane_books.items()},
        "chapterCounts": {lane: len(rows) for lane, rows in lanes.items()},
        "verseCounts": {
            lane: sum(len(ch["verses"]) for ch in rows) for lane, rows in lanes.items()
        },
        "tokenCounts": {
            lane: sum(len(v["tokens"]) for ch in rows for v in ch["verses"])
            for lane, rows in lanes.items()
        },
        "bookAssignmentDigest": hashlib.sha256(
            "|".join(
                f"{_anon('B', b)}:{lane_map[b]}" for b in ordered_books
            ).encode("utf-8")
        ).hexdigest(),
        "bookDisjointAcrossLanes": True,
        "representations": list(REPRESENTATIONS),
        "riskOutcomes": list(RISK_OUTCOMES),
    }
    return lanes, manifest


def identity_sequence(verse, representation):
    if representation == "lemma":
        return verse["tokens"]
    return verse[representation]


def elapsed_bucket(t, protocol):
    cfg = protocol["elapsedTime"]
    for (lo, hi), label in zip(cfg["buckets"], cfg["labels"]):
        if int(lo) <= int(t) <= int(hi):
            return label
    raise ValueError(f"elapsed time {t} outside frozen buckets")


def origin_trajectories(chapters, representation, protocol):
    out = []
    for chapter in chapters:
        for verse in chapter["verses"]:
            seq = identity_sequence(verse, representation)
            n = len(seq)
            for i, op in enumerate(seq):
                s0 = hist(seq, i)
                s1 = hist(seq, i + 1)
                rows = []
                terminal_cause = None
                terminal_step = None
                if i == n - 1:
                    rows.append({
                        "elapsed": 0,
                        "timeBucket": elapsed_bucket(0, protocol),
                        "outcome": "VERSE_BOUNDARY",
                    })
                    terminal_cause = "VERSE_BOUNDARY"
                    terminal_step = 0
                else:
                    for j in range(i + 1, n):
                        t = j - i
                        st = hist(seq, j + 1)
                        if st != s1:
                            outcome = "DEPARTURE"
                        elif j == n - 1:
                            outcome = "VERSE_BOUNDARY"
                        else:
                            outcome = "CONTINUE"
                        rows.append({
                            "elapsed": t,
                            "timeBucket": elapsed_bucket(t, protocol),
                            "outcome": outcome,
                        })
                        if outcome != "CONTINUE":
                            terminal_cause = outcome
                            terminal_step = t
                            break
                if terminal_cause is None or terminal_step is None:
                    raise ValueError("origin trajectory failed to terminate")
                out.append({
                    "operator": op,
                    "S0": s0,
                    "S1": s1,
                    "rows": rows,
                    "terminalCause": terminal_cause,
                    "terminalStep": terminal_step,
                })
    return out


def _normalize(d):
    z = sum(d.values())
    if z <= 0:
        return {y: 1.0 / len(RISK_OUTCOMES) for y in RISK_OUTCOMES}
    return {y: d.get(y, 0.0) / z for y in RISK_OUTCOMES}


def _dist(counts, prior, pseudo):
    n = sum(counts.values())
    return {
        y: (counts[y] + pseudo * prior[y]) / (n + pseudo)
        for y in RISK_OUTCOMES
    }


def _model_parts(model, s0, s1, op, tb):
    time = model["time"].get(tb, model["pGlobal"])
    bkey = canonical_json([s1, tb])
    base = model["base"].get(bkey, time)
    ckey = canonical_json([s0, s1, tb])
    ctx = model["context"].get(ckey, base)
    okey = canonical_json([s1, op, tb])
    opd = model["operator"].get(okey, base)
    add = _normalize({
        y: ctx[y] * opd[y] / max(base[y], EPS)
        for y in RISK_OUTCOMES
    })
    ikey = canonical_json([s0, s1, op, tb])
    interaction = model.get("interaction", {}).get(ikey, add)
    return {
        "time": time,
        "base": base,
        "context": ctx,
        "operator": opd,
        "additive": add,
        "interaction": interaction,
    }


def build_competing_model(trajectories, protocol):
    cfg = protocol["training"]
    origin_counts = Counter(t["operator"] for t in trajectories)
    op_s1 = defaultdict(set)
    for t in trajectories:
        op_s1[t["operator"]].add(t["S1"])
    eligible = [
        (op, n) for op, n in origin_counts.items()
        if n >= int(cfg["minimumOriginsPerOperator"])
        and len(op_s1[op]) >= int(cfg["minimumS1StatesPerOperator"])
    ]
    eligible.sort(key=lambda x: (-x[1], x[0]))
    operators = [x[0] for x in eligible[:int(cfg["maximumOperatorsPerRepresentation"])]]
    op_set = set(operators)
    kept = [t for t in trajectories if t["operator"] in op_set]

    risk = []
    for t in kept:
        for row in t["rows"]:
            risk.append({
                "operator": t["operator"],
                "S0": t["S0"],
                "S1": t["S1"],
                "timeBucket": row["timeBucket"],
                "outcome": row["outcome"],
            })

    alpha = float(cfg["globalAdditiveAlpha"])
    global_counts = Counter(r["outcome"] for r in risk)
    total = sum(global_counts.values())
    p_global = {
        y: (global_counts[y] + alpha) / (total + alpha * len(RISK_OUTCOMES))
        for y in RISK_OUTCOMES
    }

    time_counts = defaultdict(Counter)
    base_counts = defaultdict(Counter)
    context_counts = defaultdict(Counter)
    operator_counts = defaultdict(Counter)
    interaction_counts = defaultdict(Counter)
    for r in risk:
        tb = r["timeBucket"]
        y = r["outcome"]
        time_counts[tb][y] += 1
        base_counts[canonical_json([r["S1"], tb])][y] += 1
        context_counts[canonical_json([r["S0"], r["S1"], tb])][y] += 1
        operator_counts[canonical_json([r["S1"], r["operator"], tb])][y] += 1
        interaction_counts[canonical_json([r["S0"], r["S1"], r["operator"], tb])][y] += 1

    time = {
        tb: _dist(c, p_global, float(cfg["timeBackoffPseudoCount"]))
        for tb, c in time_counts.items()
    }
    base = {}
    for key, c in base_counts.items():
        s1, tb = json.loads(key)
        base[key] = _dist(c, time.get(tb, p_global), float(cfg["baseBackoffPseudoCount"]))
    context = {}
    for key, c in context_counts.items():
        s0, s1, tb = json.loads(key)
        prior = base.get(canonical_json([s1, tb]), time.get(tb, p_global))
        context[key] = _dist(c, prior, float(cfg["contextBackoffPseudoCount"]))
    operator = {}
    for key, c in operator_counts.items():
        s1, op, tb = json.loads(key)
        prior = base.get(canonical_json([s1, tb]), time.get(tb, p_global))
        operator[key] = _dist(c, prior, float(cfg["operatorBackoffPseudoCount"]))

    partial = {
        "pGlobal": p_global,
        "time": time,
        "base": base,
        "context": context,
        "operator": operator,
    }
    interaction = {}
    min_rows = int(cfg["minimumInteractionRiskRows"])
    for key, c in interaction_counts.items():
        if sum(c.values()) < min_rows:
            continue
        s0, s1, op, tb = json.loads(key)
        prior = _model_parts(partial, s0, s1, op, tb)["additive"]
        interaction[key] = _dist(c, prior, float(cfg["interactionBackoffPseudoCount"]))

    return {
        "operators": operators,
        "operatorTrainOrigins": {op: int(origin_counts[op]) for op in operators},
        "trainOrigins": len(kept),
        "trainRiskRows": len(risk),
        "pGlobal": p_global,
        "time": time,
        "base": base,
        "context": context,
        "operator": operator,
        "interaction": interaction,
        "interactionCells": len(interaction),
    }


def freeze_models(train_chapters, protocol):
    systems = {}
    for rep in REPRESENTATIONS:
        trajectories = origin_trajectories(train_chapters, rep, protocol)
        systems[rep] = build_competing_model(trajectories, protocol)
    return {"riskOutcomes": list(RISK_OUTCOMES), "systems": systems}


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


def _logp(dist, outcome):
    return math.log2(max(dist[outcome], EPS))


def _timing_logp(dist, outcome):
    terminal = dist["DEPARTURE"] + dist["VERSE_BOUNDARY"]
    p = dist["CONTINUE"] if outcome == "CONTINUE" else terminal
    return math.log2(max(p, EPS))


def _cause_logp(dist, cause):
    z = dist["DEPARTURE"] + dist["VERSE_BOUNDARY"]
    p = dist[cause] / max(z, EPS)
    return math.log2(max(p, EPS))


def evaluate_representation(chapters, representation, model, protocol, lane):
    frozen_ops = set(model["operators"])
    trajectories = [
        t for t in origin_trajectories(chapters, representation, protocol)
        if t["operator"] in frozen_ops
    ]
    by_op = defaultdict(list)
    terminal_counts = Counter()
    terminal_steps = []
    for t in trajectories:
        ll_interaction = 0.0
        ll_additive = 0.0
        ll_context = 0.0
        ll_operator = 0.0
        timing_interaction = 0.0
        timing_additive = 0.0
        for row in t["rows"]:
            parts = _model_parts(model, t["S0"], t["S1"], t["operator"], row["timeBucket"])
            y = row["outcome"]
            ll_interaction += _logp(parts["interaction"], y)
            ll_additive += _logp(parts["additive"], y)
            ll_context += _logp(parts["context"], y)
            ll_operator += _logp(parts["operator"], y)
            timing_interaction += _timing_logp(parts["interaction"], y)
            timing_additive += _timing_logp(parts["additive"], y)
        denom = max(len(t["rows"]), 1)
        terminal = t["rows"][-1]
        parts_terminal = _model_parts(
            model, t["S0"], t["S1"], t["operator"], terminal["timeBucket"]
        )
        cause = t["terminalCause"]
        cause_gain = _cause_logp(parts_terminal["interaction"], cause) - _cause_logp(parts_terminal["additive"], cause)
        by_op[t["operator"]].append({
            "interaction": (ll_interaction - ll_additive) / denom,
            "overContext": (ll_interaction - ll_context) / denom,
            "overOperator": (ll_interaction - ll_operator) / denom,
            "timing": (timing_interaction - timing_additive) / denom,
            "cause": cause_gain,
        })
        terminal_counts[cause] += 1
        terminal_steps.append(t["terminalStep"])

    min_origins = int(protocol["evaluation"]["minimumEvaluationOriginsPerOperator"])
    op_metrics = {}
    for op, vals in by_op.items():
        if len(vals) < min_origins:
            continue
        op_metrics[op] = {
            k: sum(v[k] for v in vals) / len(vals)
            for k in ("interaction", "overContext", "overOperator", "timing", "cause")
        }
        op_metrics[op]["evaluationOrigins"] = len(vals)

    def balanced(metric):
        vals = [m[metric] for m in op_metrics.values()]
        return sum(vals) / len(vals) if vals else 0.0

    primary_values = [m["interaction"] for m in op_metrics.values()]
    interaction_gain = balanced("interaction")
    over_context = balanced("overContext")
    over_operator = balanced("overOperator")
    timing_gain = balanced("timing")
    cause_gain = balanced("cause")
    positive = sum(v > 0 for v in primary_values) / len(primary_values) if primary_values else 0.0
    p = _signflip(
        primary_values,
        f"mark-v27:{representation}:{lane}",
        int(protocol["evaluation"]["permutationCount"]),
    )
    sufficient = len(op_metrics) >= int(protocol["evaluation"]["minimumEvaluableOperators"])
    gate = protocol["evaluation"]["primaryGatePerLane"]
    passed = (
        sufficient
        and interaction_gain > float(gate["operatorBalancedInteractionGainGreaterThan"])
        and over_context > float(gate["operatorBalancedGainOverContextOnlyGreaterThan"])
        and over_operator > float(gate["operatorBalancedGainOverOperatorOnlyGreaterThan"])
        and positive >= float(gate["positiveInteractionOperatorFractionAtLeast"])
        and p <= float(gate["pairedSignFlipPAtMost"])
    )
    total_terminal = sum(terminal_counts.values())
    return {
        "representation": representation,
        "lane": lane,
        "evaluationOrigins": len(trajectories),
        "evaluableOperators": len(op_metrics),
        "frozenOperators": len(model["operators"]),
        "operatorBalancedInteractionGain": interaction_gain,
        "operatorBalancedGainOverContextOnly": over_context,
        "operatorBalancedGainOverOperatorOnly": over_operator,
        "positiveInteractionOperatorFraction": positive,
        "signFlipP": p,
        "operatorBalancedTimingInteractionGain": timing_gain,
        "operatorBalancedCauseInteractionGain": cause_gain,
        "departureFraction": terminal_counts["DEPARTURE"] / total_terminal if total_terminal else 0.0,
        "verseBoundaryFraction": terminal_counts["VERSE_BOUNDARY"] / total_terminal if total_terminal else 0.0,
        "meanResolutionStep": sum(terminal_steps) / len(terminal_steps) if terminal_steps else None,
        "medianResolutionStep": _median(terminal_steps),
        "sufficient": sufficient,
        "pass": passed,
        "operators": {op: vals for op, vals in sorted(op_metrics.items())},
    }


def adjudicate(results):
    testable = [
        rep for rep in REPRESENTATIONS
        if all(results[lane][rep]["sufficient"] for lane in ("holdout", "control"))
    ]
    if not testable:
        return "INSUFFICIENT_COMPETING_RESOLUTION_SUPPORT"
    passed = [
        rep for rep in testable
        if all(results[lane][rep]["pass"] for lane in ("holdout", "control"))
    ]
    if len(passed) > 1:
        return "MULTIPLE_REPRESENTATIONS_SUPPORT_CONTEXT_CONDITIONED_COMPETING_RESOLUTION"
    if len(passed) == 1:
        return {
            "lemma": "LEMMA_SUPPORTS_CONTEXT_CONDITIONED_COMPETING_RESOLUTION",
            "lemmaCoarseMorph": "COARSE_MORPH_SUPPORTS_CONTEXT_CONDITIONED_COMPETING_RESOLUTION",
            "lemmaFullMorph": "FULL_MORPH_SUPPORTS_CONTEXT_CONDITIONED_COMPETING_RESOLUTION",
        }[passed[0]]
    any_lane_pass = any(results[lane][rep]["pass"] for rep in testable for lane in ("holdout", "control"))
    if any_lane_pass:
        return "COMPETING_RESOLUTION_INTERACTION_DOES_NOT_REPLICATE"
    return "NO_CONTEXT_CONDITIONED_COMPETING_RESOLUTION"
