#!/usr/bin/env python3
import math
import random

from mark_structural_transition_consequence_v23_core import (
    EPS, OUTCOMES, _aggregate, _balanced_scores, _dist_with_residual,
    _qualify, glyph_transition_events, hebrew_transition_events,
)


def _precompute_permuted_interaction_scores(ops, counts, model):
    """Exact cached form of the frozen V23 residual-block permutation score."""
    out = {}
    for op in ops:
        states = sorted(model["models"][op]["states"])
        n_total = sum(sum(counts[(op, s)].values()) for s in states)
        matrix = {}
        for actual in states:
            cnt = counts[(op, actual)]
            inv = model["models"][op]["states"][actual]["invariant"]
            for source in states:
                residual = model["models"][op]["states"][source]["interactionResidual"]
                ctx = _dist_with_residual(inv, residual)
                score = 0.0
                for y, k in cnt.items():
                    score += k * (
                        math.log2(max(ctx[y], EPS)) - math.log2(max(inv[y], EPS))
                    )
                matrix[(actual, source)] = score / n_total if n_total else 0.0
        out[op] = (states, matrix)
    return out


def evaluate_system_fast(rows, kind, representation, pair, protocol, lane):
    events = (
        hebrew_transition_events(rows, representation)
        if kind == "hebrew" else glyph_transition_events(rows)
    )
    model = pair[kind]
    counts, covered = _aggregate(events, pair["sharedStates"], model["operators"])
    ops = _qualify(counts, model, protocol)
    obs_interaction, obs_total, vals, details = _balanced_scores(ops, counts, model)

    cached = _precompute_permuted_interaction_scores(ops, counts, model)
    seed = f"mark-v23:{kind}:{representation}:{lane}"
    rng = random.Random(seed)
    null = []
    for _ in range(int(protocol["evaluation"]["permutationCount"])):
        op_scores = []
        for op in ops:
            states, matrix = cached[op]
            shuffled = list(states)
            rng.shuffle(shuffled)
            op_scores.append(sum(matrix[(a, s)] for a, s in zip(states, shuffled)))
        null.append(sum(op_scores) / len(op_scores) if op_scores else 0.0)

    p = (1 + sum(x >= obs_interaction - 1e-15 for x in null)) / (len(null) + 1)
    positive = sum(v > 0 for v in vals) / len(vals) if vals else 0.0

    ecfg = protocol["evaluation"]
    gate = ecfg["withinSystemGatesPerLane"]
    threshold = (
        float(ecfg["hebrewFamilywiseInteractionPAtMost"])
        if kind == "hebrew" else float(ecfg["glyphInteractionPAtMost"])
    )
    enough = len(ops) >= int(ecfg["minimumEvaluableOperatorsPerSystem"])
    passed = (
        enough
        and obs_interaction > float(gate["operatorBalancedInteractionGainGreaterThan"])
        and obs_total > float(gate["operatorBalancedTotalGainOverStateOnlyGreaterThan"])
        and positive >= float(gate["positiveInteractionOperatorFractionAtLeast"])
        and p <= threshold
    )
    return {
        "kind": kind,
        "representation": representation,
        "lane": lane,
        "rawEvents": len(events),
        "coveredEvents": covered,
        "evaluableOperators": len(ops),
        "frozenOperators": len(model["operators"]),
        "sharedStates": list(pair["sharedStates"]),
        "operatorBalancedInteractionGainBitsPerEvent": obs_interaction,
        "operatorBalancedTotalGainOverStateOnlyBitsPerEvent": obs_total,
        "positiveInteractionOperatorFraction": positive,
        "permutationP": p,
        "pass": passed,
        "operators": details,
    }
