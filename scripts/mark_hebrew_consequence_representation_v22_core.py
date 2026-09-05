#!/usr/bin/env python3
import itertools
import math
import random
from collections import Counter, defaultdict

from mark_hebrew_glyph_annotation_competition_v19_io import (
    read_json, read_jsonl, sha256_json, write_json, write_jsonl,
)
from mark_hebrew_glyph_annotation_competition_v19_projector import (
    OUTCOMES, consequence, event_rows, hist,
)
from mark_context_conditioned_operator_v20_core import (
    EPS, _balanced_gain, _build_system_model, _dist_with_residual,
    _pearson, _permute_mappings,
)

REPRESENTATIONS = ("lemma", "lemmaCoarseMorph", "lemmaFullMorph")
PRIMARY = ("lemmaCoarseMorph", "lemmaFullMorph")


def identity_sequence(row, representation):
    if representation == "lemma":
        return row["tokens"]
    return row[representation]


def cell_id(operator_representation, consequence_representation):
    return f"{operator_representation}__{consequence_representation}"


def cell_events(rows, operator_representation, consequence_representation):
    out = []
    for row in rows:
        base = row["tokens"]
        operators = identity_sequence(row, operator_representation)
        targets = identity_sequence(row, consequence_representation)
        if not (len(base) == len(operators) == len(targets)):
            raise ValueError(f"representation length mismatch in {row['anonymousUnitId']}")
        for i, op in enumerate(operators):
            out.append({
                "unit": row["anonymousUnitId"],
                "index": i,
                "state": hist(base, i),
                "operator": op,
                "baseLemma": base[i],
                "outcome": consequence(targets, i),
            })
    return out


def _training_cfg(protocol):
    cfg = dict(protocol["training"])
    cfg["maximumOperatorsPerCorpus"] = int(cfg["maximumOperatorsPerCell"])
    return cfg


def freeze_model(hebrew_train_rows, inherited_v20_freeze, protocol):
    if inherited_v20_freeze.get("freezeAdjudication") != "FEASIBLE":
        raise ValueError("inherited V20 freeze is not FEASIBLE")
    if inherited_v20_freeze.get("freezeSha256") != protocol["lineage"]["v20FreezeSha256"]:
        raise ValueError("inherited V20 freeze SHA mismatch")
    if inherited_v20_freeze.get("protocolSha256") != protocol["lineage"]["v20ProtocolSha256"]:
        raise ValueError("inherited V20 protocol SHA mismatch")

    states = list(inherited_v20_freeze["sharedStates"])
    cfg = _training_cfg(protocol)
    cells = {}
    train_counts = {}

    for op_rep in REPRESENTATIONS:
        for cons_rep in REPRESENTATIONS:
            cid = cell_id(op_rep, cons_rep)
            if op_rep == "lemma" and cons_rep == "lemma":
                cells[cid] = inherited_v20_freeze["systems"]["hebrew"]
                train_counts[cid] = inherited_v20_freeze["trainEventCounts"]["hebrew"]
            else:
                events = cell_events(hebrew_train_rows, op_rep, cons_rep)
                cells[cid] = _build_system_model(events, states, cfg)
                train_counts[cid] = len(events)

    return {
        "sharedStates": states,
        "outcomes": list(OUTCOMES),
        "inheritedV20FreezeSha256": inherited_v20_freeze["freezeSha256"],
        "cells": cells,
        "glyph": inherited_v20_freeze["systems"]["glyph"],
        "trainEventCounts": train_counts,
    }


def _aggregate_counts(events, states, operators):
    state_set = set(states)
    op_set = set(operators)
    counts = defaultdict(Counter)
    kept = 0
    for e in events:
        if e["state"] in state_set and e["operator"] in op_set:
            counts[(e["operator"], e["state"])][e["outcome"]] += 1
            kept += 1
    return counts, kept


def _qualify(counts, system_model, protocol):
    ecfg = protocol["evaluation"]
    mn_events = int(ecfg["minimumEvaluationEventsPerOperator"])
    mn_contexts = int(ecfg["minimumEvaluationContextsPerOperator"])
    out = []
    for op in system_model["operators"]:
        states = system_model["models"][op]["states"]
        n = sum(sum(counts[(op, s)].values()) for s in states)
        c = sum(bool(counts[(op, s)]) for s in states)
        if n >= mn_events and c >= mn_contexts:
            out.append(op)
    return out


def _cell_seed(op_rep, cons_rep):
    if op_rep == "lemma" and cons_rep == "lemma":
        return "mark-v20-hebrew-context-interaction"
    return f"mark-v22:{op_rep}:{cons_rep}"


def evaluate_cell(rows, op_rep, cons_rep, system_model, freeze, protocol, lane):
    events = cell_events(rows, op_rep, cons_rep)
    counts, covered = _aggregate_counts(events, freeze["sharedStates"], system_model["operators"])
    ops = _qualify(counts, system_model, protocol)
    obs, vals, profile, details = _balanced_gain(ops, counts, system_model)

    rng = random.Random(_cell_seed(op_rep, cons_rep) + ":" + lane)
    null = []
    for _ in range(int(protocol["evaluation"]["permutationCount"])):
        mappings = _permute_mappings(ops, system_model, rng)
        x, _, _, _ = _balanced_gain(ops, counts, system_model, mappings)
        null.append(x)
    p = (1 + sum(x >= obs - 1e-15 for x in null)) / (len(null) + 1)
    positive = sum(v > 0 for v in vals) / len(vals) if vals else 0.0

    gate = protocol["evaluation"]["withinCellGatesPerLane"]
    enough = len(ops) >= int(protocol["evaluation"]["minimumEvaluableOperatorsPerCell"])
    passed = (
        enough
        and obs > float(gate["operatorBalancedContextGainGreaterThan"])
        and p <= float(gate["interactionPermutationPAtMost"])
        and positive >= float(gate["positiveOperatorFractionAtLeast"])
    )
    return {
        "operatorRepresentation": op_rep,
        "consequenceRepresentation": cons_rep,
        "lane": lane,
        "rawEvents": len(events),
        "coveredEvents": covered,
        "evaluableOperators": len(ops),
        "frozenOperators": len(system_model["operators"]),
        "evaluableOperatorIds": ops,
        "operatorBalancedContextGainBitsPerEvent": obs,
        "positiveOperatorFraction": positive,
        "permutationP": p,
        "pass": passed,
        "stateProfile": profile,
        "operators": details,
    }


def evaluate_glyph(rows, system_model, freeze, protocol, lane):
    events = event_rows(rows, "glyph")
    counts, covered = _aggregate_counts(events, freeze["sharedStates"], system_model["operators"])
    ops = _qualify(counts, system_model, protocol)
    obs, vals, profile, details = _balanced_gain(ops, counts, system_model)

    rng = random.Random("mark-v20-glyph-context-interaction:" + lane)
    null = []
    for _ in range(int(protocol["evaluation"]["permutationCount"])):
        mappings = _permute_mappings(ops, system_model, rng)
        x, _, _, _ = _balanced_gain(ops, counts, system_model, mappings)
        null.append(x)
    p = (1 + sum(x >= obs - 1e-15 for x in null)) / (len(null) + 1)
    positive = sum(v > 0 for v in vals) / len(vals) if vals else 0.0
    gate = protocol["evaluation"]["withinCellGatesPerLane"]
    enough = len(ops) >= int(protocol["evaluation"]["minimumEvaluableOperatorsPerCell"])
    passed = (
        enough
        and obs > float(gate["operatorBalancedContextGainGreaterThan"])
        and p <= float(gate["interactionPermutationPAtMost"])
        and positive >= float(gate["positiveOperatorFractionAtLeast"])
    )
    return {
        "operatorRepresentation": "glyph",
        "consequenceRepresentation": "glyph",
        "lane": lane,
        "rawEvents": len(events),
        "coveredEvents": covered,
        "evaluableOperators": len(ops),
        "frozenOperators": len(system_model["operators"]),
        "evaluableOperatorIds": ops,
        "operatorBalancedContextGainBitsPerEvent": obs,
        "positiveOperatorFraction": positive,
        "permutationP": p,
        "pass": passed,
        "stateProfile": profile,
        "operators": details,
    }


def _context_gain(event, model):
    sm = model["states"][event["state"]]
    inv = sm["invariant"]
    ctx = _dist_with_residual(inv, sm["interactionResidual"])
    y = event["outcome"]
    return math.log2(max(ctx[y], EPS)) - math.log2(max(inv[y], EPS))


def _signflip(values, seed, permutations):
    if not values:
        return 1.0
    observed = sum(values) / len(values)
    if len(values) <= 12:
        null = [
            sum(s * v for s, v in zip(signs, values)) / len(values)
            for signs in itertools.product((-1.0, 1.0), repeat=len(values))
        ]
        return sum(x >= observed - 1e-15 for x in null) / len(null)
    rng = random.Random(seed)
    null = []
    for _ in range(permutations):
        null.append(sum((1 if rng.random() < 0.5 else -1) * v for v in values) / len(values))
    return (1 + sum(x >= observed - 1e-15 for x in null)) / (len(null) + 1)


def paired_axis(rows, resolution, axis, diagonal_result, baseline_result, freeze, protocol, lane):
    if resolution not in PRIMARY:
        raise ValueError("paired axis only defined for primary morphology resolutions")
    diag_id = cell_id(resolution, resolution)
    if axis == "consequence":
        base_id = cell_id(resolution, "lemma")
    elif axis == "operator":
        base_id = cell_id("lemma", resolution)
    else:
        raise ValueError("unknown axis")

    diag_model = freeze["cells"][diag_id]
    base_model = freeze["cells"][base_id]
    diag_eval = set(diagonal_result["evaluableOperatorIds"])
    base_eval = set(baseline_result["evaluableOperatorIds"])
    states = set(freeze["sharedStates"])

    diffs = defaultdict(list)
    diag_events = cell_events(rows, resolution, resolution)
    if axis == "consequence":
        base_events = cell_events(rows, resolution, "lemma")
    else:
        base_events = cell_events(rows, "lemma", resolution)
    if len(diag_events) != len(base_events):
        raise ValueError("paired event length mismatch")

    for d, b in zip(diag_events, base_events):
        if d["unit"] != b["unit"] or d["index"] != b["index"] or d["state"] != b["state"]:
            raise ValueError("paired event alignment mismatch")
        if d["state"] not in states:
            continue
        if d["operator"] not in diag_eval or b["operator"] not in base_eval:
            continue
        dg = _context_gain(d, diag_model["models"][d["operator"]])
        bg = _context_gain(b, base_model["models"][b["operator"]])
        diffs[d["operator"]].append(dg - bg)

    cfg = protocol["evaluation"]["pairedAxisComparisons"]
    minimum_events = int(cfg["minimumCommonEventsPerOperator"])
    rows_out = {}
    for op, vals in sorted(diffs.items()):
        if len(vals) >= minimum_events:
            rows_out[op] = {
                "commonEvents": len(vals),
                "meanDeltaBitsPerEvent": sum(vals) / len(vals),
            }

    values = [v["meanDeltaBitsPerEvent"] for v in rows_out.values()]
    observed = sum(values) / len(values) if values else 0.0
    positive = sum(v > 0 for v in values) / len(values) if values else 0.0
    coverage = len(values) / max(1, diagonal_result["evaluableOperators"])
    p = _signflip(
        values,
        f"mark-v22-axis:{resolution}:{axis}:{lane}",
        int(protocol["evaluation"]["permutationCount"]),
    )
    gate = cfg["gate"]
    passed = (
        len(values) >= int(cfg["minimumEligibleOperators"])
        and coverage >= float(cfg["minimumCoverageFraction"])
        and observed > float(gate["operatorBalancedDeltaGreaterThan"])
        and p <= float(gate["pairedSignFlipPAtMost"])
        and positive >= float(gate["positiveOperatorFractionAtLeast"])
    )
    return {
        "resolution": resolution,
        "axis": axis,
        "lane": lane,
        "diagonalCell": diag_id,
        "baselineCell": base_id,
        "eligibleOperators": len(values),
        "diagonalEvaluableOperators": diagonal_result["evaluableOperators"],
        "coverageFraction": coverage,
        "operatorBalancedDeltaBitsPerEvent": observed,
        "positiveOperatorFraction": positive,
        "signFlipP": p,
        "pass": passed,
        "operators": rows_out,
    }


def compare_profiles(hebrew_result, glyph_result, protocol, lane):
    cfg = protocol["evaluation"]["contextProfile"]
    mn_ops = int(cfg["minimumOperatorsPerState"])

    def supported(result):
        vals = defaultdict(list)
        for row in result["operators"].values():
            for state, gain in row["stateGains"].items():
                vals[state].append(gain)
        return {
            s: (sum(xs) / len(xs), len(xs))
            for s, xs in vals.items() if len(xs) >= mn_ops
        }

    hp = supported(hebrew_result)
    gp = supported(glyph_result)
    states = sorted(set(hp) & set(gp))
    if len(states) < int(cfg["minimumCommonStates"]):
        return {
            "lane": lane,
            "commonStates": states,
            "correlation": 0.0,
            "permutationP": 1.0,
            "pass": False,
            "hebrewProfile": hp,
            "glyphProfile": gp,
        }
    hv = [hp[s][0] for s in states]
    gv = [gp[s][0] for s in states]
    obs = _pearson(hv, gv)
    if len(states) <= 8:
        null = [_pearson(hv, list(p)) for p in itertools.permutations(gv)]
    else:
        rng = random.Random("mark-v22-profile:" + lane)
        null = []
        for _ in range(int(protocol["evaluation"]["permutationCount"])):
            p = list(gv)
            rng.shuffle(p)
            null.append(_pearson(hv, p))
    pval = sum(x >= obs - 1e-15 for x in null) / len(null) if null else 1.0
    gate = cfg["gate"]
    passed = obs > float(gate["correlationGreaterThan"]) and pval <= float(gate["statePermutationPAtMost"])
    return {
        "lane": lane,
        "commonStates": states,
        "correlation": obs,
        "permutationP": pval,
        "pass": passed,
        "hebrewProfile": hp,
        "glyphProfile": gp,
    }


def reproduction_check(lanes, glyph, baseline_manifest):
    tol = float(baseline_manifest["numericTolerance"])
    checks = []
    for lane in ("holdout", "control"):
        observed = lanes[lane][cell_id("lemma", "lemma")]
        expected = baseline_manifest["expectedLemmaLemma"][lane]
        for key in ("operatorBalancedContextGainBitsPerEvent", "positiveOperatorFraction", "permutationP"):
            checks.append(abs(float(observed[key]) - float(expected[key])) <= tol)
        for key in ("evaluableOperators", "frozenOperators"):
            checks.append(int(observed[key]) == int(expected[key]))

        observed_g = glyph[lane]
        expected_g = baseline_manifest["expectedGlyph"][lane]
        for key in ("operatorBalancedContextGainBitsPerEvent", "positiveOperatorFraction", "permutationP"):
            checks.append(abs(float(observed_g[key]) - float(expected_g[key])) <= tol)
        for key in ("evaluableOperators", "frozenOperators"):
            checks.append(int(observed_g[key]) == int(expected_g[key]))
    return all(checks)


def adjudicate(lanes, axes, profiles, glyph, freeze, baseline_ok, protocol):
    if not baseline_ok:
        return "IMPLEMENTATION_DRIFT"

    minimum = int(protocol["evaluation"]["minimumEvaluableOperatorsPerCell"])
    if not any(
        len(freeze["cells"][cell_id(r, r)]["operators"]) >= minimum
        for r in PRIMARY
    ):
        return "INSUFFICIENT_CELL_SUPPORT"

    rescued = {}
    aligned = {}
    glyph_pass = all(glyph[l]["pass"] for l in ("holdout", "control"))
    for r in PRIMARY:
        cid = cell_id(r, r)
        rescued[r] = all(
            lanes[l][cid]["pass"]
            and axes[r]["consequence"][l]["pass"]
            and axes[r]["operator"][l]["pass"]
            for l in ("holdout", "control")
        )
        aligned[r] = rescued[r] and glyph_pass and all(profiles[r][l]["pass"] for l in ("holdout", "control"))

    coarse = "lemmaCoarseMorph"
    full = "lemmaFullMorph"
    if rescued[coarse] and rescued[full] and aligned[coarse] and aligned[full]:
        return "BOTH_MATCHED_CONSEQUENCES_RESCUE_AND_ALIGN"
    if rescued[full] and not rescued[coarse]:
        return "FULL_MATCHED_CONSEQUENCE_RESCUES_AND_ALIGNS_GLYPH_CONTEXTS" if aligned[full] else "FULL_MATCHED_CONSEQUENCE_RESCUES_WITHOUT_GLYPH_ALIGNMENT"
    if rescued[coarse] and not rescued[full]:
        return "COARSE_MATCHED_CONSEQUENCE_RESCUES_AND_ALIGNS_GLYPH_CONTEXTS" if aligned[coarse] else "COARSE_MATCHED_CONSEQUENCE_RESCUES_WITHOUT_GLYPH_ALIGNMENT"
    if rescued[coarse] and rescued[full]:
        return "BOTH_MATCHED_CONSEQUENCES_RESCUE_WITHOUT_FULL_ALIGNMENT"

    any_nonbaseline_both = False
    for op_rep in REPRESENTATIONS:
        for cons_rep in REPRESENTATIONS:
            cid = cell_id(op_rep, cons_rep)
            if cid == cell_id("lemma", "lemma"):
                continue
            if all(lanes[l][cid]["pass"] for l in ("holdout", "control")):
                any_nonbaseline_both = True
    if any_nonbaseline_both:
        return "CONSEQUENCE_RESOLUTION_CHANGES_SIGNAL_WITHOUT_MATCHED_RESCUE"
    return "NO_RECURRENCE_CONSEQUENCE_REPRESENTATION_RESCUES"
