#!/usr/bin/env python3
from collections import Counter, defaultdict
import math

from mark_operator_selection_grammar_v28_core import (
    EPS, REPRESENTATIONS, _dist, _mapping_for_perm, _qualify, _score,
    compare_profiles, glyph_events, hebrew_events,
)


def _build_null_cache(events, qualified, model):
    """Pre-aggregate the exact operator-balanced primary score by target/source state.

    This is algebraically identical to calling core._score(events, qualified, model, mapping)[0]
    for each residual-state permutation, but avoids revisiting every event on every permutation.
    """
    q = set(qualified)
    counts = Counter((e["operator"], e["state"], e["pos"]) for e in events if e["operator"] in q)
    op_totals = Counter()
    for (op, _s, _p), n in counts.items():
        op_totals[op] += n
    nops = len(qualified)

    supported_by_pos = defaultdict(set)
    for key in model["pSel"]:
        s, p = __import__("json").loads(key)
        supported_by_pos[p].add(s)

    contrib = {}
    for p, sources in supported_by_pos.items():
        sources = sorted(sources)
        targets = sorted(sources)
        for target in targets:
            cells = [(op, n) for (op, s, pp), n in counts.items() if s == target and pp == p and op in q]
            if not cells:
                continue
            for source in sources:
                total = 0.0
                for op, n in cells:
                    base, sel = _dist(model, target, p, source)
                    gain = math.log2(max(sel[op], EPS)) - math.log2(max(base[op], EPS))
                    total += (n / op_totals[op]) * gain / nops
                contrib[(p, target, source)] = total
    return contrib


def _null_primary(cache, mapping):
    total = 0.0
    for p, mp in mapping.items():
        for target, source in mp.items():
            total += cache.get((p, target, source), 0.0)
    return total


def evaluate_system_fast(events, model, protocol, lane, label, pthreshold):
    kept, qualified = _qualify(events, model, protocol)
    primary, secondary, positive, cf, opmeans, profile, profile_counts = _score(kept, qualified, model)
    cache = _build_null_cache(kept, qualified, model)
    perms = int(protocol["null"]["permutations"])
    ge = 0
    for i in range(perms):
        mapping = _mapping_for_perm(model, f"mark-v28:{label}:{lane}:{i}")
        null_primary = _null_primary(cache, mapping)
        ge += int(null_primary >= primary - 1e-15)
    p = (1 + ge) / (perms + 1)
    ec = protocol["evaluation"]
    sufficient = len(qualified) >= int(ec["minimumEvaluableOperators"])
    passed = sufficient and primary > 0 and p <= float(pthreshold) and positive >= float(ec["positiveOperatorFractionAtLeast"]) and cf > float(ec["counterfactualPreferenceAtLeast"])
    return {
        "lane": lane,
        "label": label,
        "evaluationEvents": len(kept),
        "evaluableOperators": len(qualified),
        "frozenOperators": len(model["operators"]),
        "operatorBalancedSelectionGainBits": primary,
        "operatorBalancedGainOverGlobalBits": secondary,
        "positiveOperatorFraction": positive,
        "counterfactualActualPreference": cf,
        "residualReassignmentP": p,
        "sufficient": sufficient,
        "pass": passed,
        "stateProfile": profile,
        "stateProfileCounts": profile_counts,
        "operatorMeans": opmeans,
    }


def evaluate_all_fast(hebrew_eval, glyph_eval, freeze, protocol):
    lanes = {"holdout": {}, "control": {}}
    gresults = {}
    for lane in ("holdout", "control"):
        g = evaluate_system_fast(glyph_events(glyph_eval[lane], protocol), freeze["glyph"], protocol, lane, "glyph", protocol["evaluation"]["glyphPAtMost"])
        gresults[lane] = g
        for rep in REPRESENTATIONS:
            h = evaluate_system_fast(hebrew_events(hebrew_eval[lane], rep, protocol), freeze["hebrew"][rep], protocol, lane, rep, protocol["evaluation"]["hebrewFamilywisePAtMost"])
            lanes[lane][rep] = {"hebrew": h, "cross": compare_profiles(h, g, protocol, rep, lane)}
    return lanes, gresults
