#!/usr/bin/env python3
import json
import math
import random
from collections import Counter, defaultdict

from mark_operator_temporal_footprint_v29_core import (
    EPS,
    _probabilities,
    build_model,
    hebrew_events,
)

REPRESENTATION = "lemmaFullMorph"
CLASSES = (
    "sameLemmaDifferentFullMorph",
    "differentLemmaSameFullMorph",
    "bothChangedControl",
)


def _split_operator(op):
    if "|M=" not in op:
        raise ValueError(f"full-morph operator lacks |M=: {op!r}")
    return tuple(op.rsplit("|M=", 1))


def _origin_position_profiles(events, operators):
    opset = set(operators)
    seen = set()
    counts = defaultdict(Counter)
    for e in events:
        op = e["operator"]
        if op not in opset:
            continue
        key = (op, e["origin"])
        if key in seen:
            continue
        seen.add(key)
        pos_bucket, _ = json.loads(e["stratum"])
        counts[op][pos_bucket] += 1
    out = {}
    for op in operators:
        c = counts[op]
        total = sum(c.values())
        out[op] = {k: v / total for k, v in c.items()} if total else {}
    return out


def _l1(a, b):
    keys = set(a) | set(b)
    return sum(abs(a.get(k, 0.0) - b.get(k, 0.0)) for k in keys)


def _candidate_ok(kind, a, b):
    if a == b:
        return False
    la, ma = _split_operator(a)
    lb, mb = _split_operator(b)
    if kind == "sameLemmaDifferentFullMorph":
        return la == lb and ma != mb
    if kind == "differentLemmaSameFullMorph":
        return la != lb and ma == mb
    if kind == "bothChangedControl":
        return la != lb and ma != mb
    raise ValueError(kind)


def _match_substitutes(model, events):
    operators = list(model["operators"])
    support = model["operatorOriginSupport"]
    bins = model["operatorFrequencyBin"]
    profiles = _origin_position_profiles(events, operators)
    maps = {kind: {} for kind in CLASSES}
    diagnostics = {kind: {} for kind in CLASSES}

    for kind in CLASSES:
        for op in operators:
            candidates = [x for x in operators if _candidate_ok(kind, op, x)]
            if not candidates:
                continue

            def cost(x):
                freq_bin = abs(int(bins[x]) - int(bins[op]))
                log_freq = abs(math.log2(max(support[x], 1) / max(support[op], 1)))
                position = _l1(profiles[op], profiles[x])
                return (freq_bin, log_freq, position, x)

            sub = min(candidates, key=cost)
            maps[kind][op] = sub
            diagnostics[kind][op] = {
                "substitute": sub,
                "frequencyBinDistance": abs(int(bins[sub]) - int(bins[op])),
                "absoluteLog2FrequencyRatio": abs(math.log2(max(support[sub], 1) / max(support[op], 1))),
                "positionProfileL1": _l1(profiles[op], profiles[sub]),
            }
    return maps, diagnostics


def freeze_model(train_rows, protocol):
    events = hebrew_events(train_rows, REPRESENTATION, protocol)
    model = build_model(events, protocol)
    substitutes, match_diagnostics = _match_substitutes(model, events)
    return {
        "representation": REPRESENTATION,
        "model": model,
        "substitutes": substitutes,
        "matchDiagnostics": match_diagnostics,
        "candidateCounts": {kind: len(substitutes[kind]) for kind in CLASSES},
        "trainEvents": len(events),
    }


def _qualified_operators(events, model, submap, protocol):
    minimum = int(protocol["evaluation"]["minimumEvaluationEventsPerOperatorDistance"])
    distances = [int(d) for d in protocol["distances"]]
    allowed = set(model["operators"]) & set(submap)
    counts = Counter(
        (e["operator"], int(e["distance"]))
        for e in events
        if e["operator"] in allowed
    )
    return sorted(
        op for op in allowed
        if all(counts[(op, d)] >= minimum for d in distances)
    )


def _damage_by_operator(events, model, submap, qualified, protocol):
    q = set(qualified)
    sums = defaultdict(float)
    counts = Counter()
    for e in events:
        op = e["operator"]
        d = int(e["distance"])
        if op not in q:
            continue
        sub = submap[op]
        _, actual = _probabilities(model, d, op, e["stratum"], e["signature"])
        _, counterfactual = _probabilities(
            model, d, op, e["stratum"], e["signature"], source_op=sub
        )
        damage = math.log2(max(actual, EPS)) - math.log2(max(counterfactual, EPS))
        sums[(op, d)] += damage
        counts[(op, d)] += 1
    return {
        op: {d: sums[(op, d)] / counts[(op, d)] for d in map(int, protocol["distances"])}
        for op in qualified
    }


def _band_mean(curve, distances):
    return sum(curve[int(d)] for d in distances) / len(distances)


def _class_statistics(damage, protocol):
    bands = protocol["bands"]
    per_operator = {}
    for op, curve in damage.items():
        pre = _band_mean(curve, bands["pre"])
        local = _band_mean(curve, bands["local"])
        far = _band_mean(curve, bands["far"])
        per_operator[op] = {
            "distanceDamage": {str(d): curve[int(d)] for d in map(int, protocol["distances"])},
            "preDamage": pre,
            "localDamage": local,
            "farDamage": far,
            "dLocal": local - (pre + far) / 2.0,
        }
    if not per_operator:
        return per_operator, None
    n = len(per_operator)
    distance_curve = {
        str(d): sum(v["distanceDamage"][str(d)] for v in per_operator.values()) / n
        for d in map(int, protocol["distances"])
    }
    summary = {
        "qualifiedOperators": n,
        "meanDistanceDamage": distance_curve,
        "meanPreDamage": sum(v["preDamage"] for v in per_operator.values()) / n,
        "meanLocalDamage": sum(v["localDamage"] for v in per_operator.values()) / n,
        "meanFarDamage": sum(v["farDamage"] for v in per_operator.values()) / n,
        "meanDLocal": sum(v["dLocal"] for v in per_operator.values()) / n,
        "positiveOperatorShare": sum(v["dLocal"] > 0 for v in per_operator.values()) / n,
    }
    return per_operator, summary


def _sign_flip_p(per_operator, observed, protocol, lane, kind):
    values = [per_operator[o]["dLocal"] for o in sorted(per_operator)]
    nperm = int(protocol["null"]["permutations"])
    ge = 0
    for pidx in range(nperm):
        rng = random.Random(f"mark-v30:{lane}:{kind}:{pidx}")
        null = sum((1 if rng.getrandbits(1) else -1) * v for v in values) / len(values)
        ge += int(null >= observed - 1e-15)
    return (1 + ge) / (nperm + 1)


def evaluate_class(events, model, submap, protocol, lane, kind):
    qualified = _qualified_operators(events, model, submap, protocol)
    damage = _damage_by_operator(events, model, submap, qualified, protocol)
    per_operator, summary = _class_statistics(damage, protocol)
    minimum = int(protocol["evaluation"]["minimumQualifiedOperatorsPerClass"])
    if summary is None:
        return {
            "class": kind,
            "lane": lane,
            "qualifiedOperators": 0,
            "sufficient": False,
            "pass": False,
        }
    sufficient = summary["qualifiedOperators"] >= minimum
    p = _sign_flip_p(per_operator, summary["meanDLocal"], protocol, lane, kind) if sufficient else 1.0
    passed = (
        sufficient
        and summary["meanDLocal"] > 0
        and p <= float(protocol["evaluation"]["primaryPAtMost"])
    )
    return {
        "class": kind,
        "lane": lane,
        **summary,
        "signFlipP": p,
        "sufficient": sufficient,
        "pass": passed,
    }


def evaluate_lane(rows, freeze, protocol, lane):
    events = hebrew_events(rows, REPRESENTATION, protocol)
    model = freeze["model"]
    return {
        kind: evaluate_class(events, model, freeze["substitutes"][kind], protocol, lane, kind)
        for kind in CLASSES
    }


def adjudicate(lanes):
    enough = any(
        lanes[lane][kind]["sufficient"]
        for lane in ("holdout", "control")
        for kind in CLASSES[:2]
    )
    if not enough:
        return "INSUFFICIENT_MATCHED_PERTURBATION_SUPPORT"
    morph = all(lanes[l]["sameLemmaDifferentFullMorph"]["pass"] for l in ("holdout", "control"))
    lexical = all(lanes[l]["differentLemmaSameFullMorph"]["pass"] for l in ("holdout", "control"))
    if morph and lexical:
        return "COMPOSITE_OPERATOR_IDENTITY_LOAD_BEARING"
    if morph:
        return "FULL_MORPHOLOGY_LOAD_BEARING"
    if lexical:
        return "LEXICAL_IDENTITY_LOAD_BEARING"
    return "PROXIMAL_FOOTPRINT_NOT_OPERATOR_SPECIFIC"
