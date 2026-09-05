#!/usr/bin/env python3
import itertools
import math
import random
from collections import Counter, defaultdict

from mark_hebrew_glyph_annotation_competition_v19_io import (
    canonical_json, read_json, read_jsonl, sha256_json, write_json,
)
from mark_hebrew_glyph_annotation_competition_v19_projector import glyph_segments, hist
from mark_structural_transition_consequence_v23_core import OUTCOMES as STRUCTURAL_STATES

EPS = 1e-300
END = "<UNIT_END_NO_DEPARTURE>"
OUTCOMES = tuple(list(STRUCTURAL_STATES) + [END])
HEBREW_REPS = ("lemma", "lemmaCoarseMorph", "lemmaFullMorph")


def identity_sequence(row, representation):
    return row["tokens"] if representation == "lemma" else row[representation]


def context_key(s0, s1):
    return canonical_json([s0, s1])


def profile_key(s0, s1, outcome):
    return canonical_json([s0, s1, outcome])


def _first_passage(seq, i):
    s1 = hist(seq, i + 1)
    for j in range(i + 2, len(seq) + 1):
        candidate = hist(seq, j)
        if candidate != s1:
            return candidate, j - (i + 1), False
    return END, max(0, len(seq) - (i + 1)), True


def _sequence_events(unit, seq):
    out = []
    for i, op in enumerate(seq):
        s0 = hist(seq, i)
        s1 = hist(seq, i + 1)
        outcome, distance, censored = _first_passage(seq, i)
        out.append({
            "unit": unit,
            "index": i,
            "s0": s0,
            "s1": s1,
            "context": context_key(s0, s1),
            "operator": op,
            "outcome": outcome,
            "distance": distance,
            "censoredByUnitEnd": censored,
        })
    return out


def hebrew_events(rows, representation):
    out = []
    for row in rows:
        out.extend(_sequence_events(row["anonymousUnitId"], identity_sequence(row, representation)))
    return out


def glyph_events(rows):
    out = []
    for unit, seq in glyph_segments(rows):
        out.extend(_sequence_events(unit, seq))
    return out


def _normalize(d):
    z = sum(d.values())
    if z <= 0:
        return {y: 1.0 / len(OUTCOMES) for y in OUTCOMES}
    return {y: d.get(y, 0.0) / z for y in OUTCOMES}


def _tables(events, shared_s1=None):
    allowed = set(shared_s1) if shared_s1 is not None else None
    base = defaultdict(Counter)
    base_n = Counter()
    context = defaultdict(Counter)
    context_n = Counter()
    op = defaultdict(Counter)
    op_n = Counter()
    triple = defaultdict(Counter)
    triple_n = Counter()
    total = Counter()
    total_n = 0
    for e in events:
        if allowed is not None and e["s1"] not in allowed:
            continue
        s0, s1, o, y = e["s0"], e["s1"], e["operator"], e["outcome"]
        ck = e["context"]
        base[s1][y] += 1
        base_n[s1] += 1
        context[ck][y] += 1
        context_n[ck] += 1
        op[o][y] += 1
        op_n[o] += 1
        triple[(o, ck)][y] += 1
        triple_n[(o, ck)] += 1
        total[y] += 1
        total_n += 1
    return {
        "base": base, "baseN": base_n,
        "context": context, "contextN": context_n,
        "op": op, "opN": op_n,
        "triple": triple, "tripleN": triple_n,
        "total": total, "totalN": total_n,
    }


def _shared_immediate_states(hevents, gevents, cfg):
    ht = _tables(hevents)
    gt = _tables(gevents)
    mn = int(cfg["minimumSharedImmediateStateEventsPerCorpus"])
    return sorted(
        s for s in set(ht["baseN"]) & set(gt["baseN"])
        if ht["baseN"][s] >= mn and gt["baseN"][s] >= mn
    )


def _eligible_ops(tab, shared_s1, cfg):
    mn_events = int(cfg["minimumOperatorEvents"])
    mn_ctx_events = int(cfg["minimumOperatorContextEventsForCoverage"])
    mn_contexts = int(cfg["minimumCoveredInteractionContexts"])
    cap = int(cfg["maximumOperatorsPerSystem"])
    rows = []
    for op, n in tab["opN"].items():
        covered = 0
        for (o, ck), k in tab["tripleN"].items():
            if o != op or k < mn_ctx_events:
                continue
            _, s1 = __import__("json").loads(ck)
            if s1 in shared_s1:
                covered += 1
        if n >= mn_events and covered >= mn_contexts:
            rows.append((op, int(n), int(covered)))
    rows.sort(key=lambda x: (-x[1], x[0]))
    return rows[:cap]


def _build_model(events, shared_s1, cfg):
    tab = _tables(events, shared_s1)
    eligible = _eligible_ops(tab, shared_s1, cfg)
    ops = [x[0] for x in eligible]
    alpha = float(cfg["globalAdditiveAlpha"])
    b_back = float(cfg["immediateStateBackoffPseudoCount"])
    c_back = float(cfg["contextMainEffectBackoffPseudoCount"])
    o_back = float(cfg["operatorMainEffectBackoffPseudoCount"])
    i_back = float(cfg["interactionBackoffPseudoCount"])
    min_interaction = int(cfg["minimumTripleEventsForInteraction"])

    total_n = tab["totalN"]
    p_global = {
        y: (tab["total"][y] + alpha) / (total_n + alpha * len(OUTCOMES))
        for y in OUTCOMES
    }

    p_base = {}
    for s1 in shared_s1:
        n = tab["baseN"][s1]
        p_base[s1] = {
            y: (tab["base"][s1][y] + b_back * p_global[y]) / (n + b_back)
            for y in OUTCOMES
        }

    context_main = {}
    for ck, counts in tab["context"].items():
        s0, s1 = __import__("json").loads(ck)
        if s1 not in p_base:
            continue
        n = tab["contextN"][ck]
        dist = {
            y: (counts[y] + c_back * p_base[s1][y]) / (n + c_back)
            for y in OUTCOMES
        }
        context_main[ck] = {
            "s0": s0,
            "s1": s1,
            "trainEvents": int(n),
            "dist": dist,
            "ratio": {y: dist[y] / max(p_base[s1][y], EPS) for y in OUTCOMES},
        }

    coverage = {x[0]: x[2] for x in eligible}
    models = {}
    for op in ops:
        n = tab["opN"][op]
        p_op = {
            y: (tab["op"][op][y] + o_back * p_global[y]) / (n + o_back)
            for y in OUTCOMES
        }
        op_ratio = {y: p_op[y] / max(p_global[y], EPS) for y in OUTCOMES}
        invariant = {
            s1: _normalize({y: p_base[s1][y] * op_ratio[y] for y in OUTCOMES})
            for s1 in shared_s1
        }
        cells = {}
        for ck, cm in context_main.items():
            s0, s1 = cm["s0"], cm["s1"]
            add = _normalize({
                y: p_base[s1][y] * cm["ratio"][y] * op_ratio[y]
                for y in OUTCOMES
            })
            k = int(tab["tripleN"][(op, ck)])
            supported = k >= min_interaction
            if supported:
                ctx = {
                    y: (tab["triple"][(op, ck)][y] + i_back * add[y]) / (k + i_back)
                    for y in OUTCOMES
                }
            else:
                ctx = dict(add)
            cells[ck] = {
                "s0": s0,
                "s1": s1,
                "trainEvents": k,
                "supportedInteraction": supported,
                "additive": add,
                "residual": {y: ctx[y] / max(add[y], EPS) for y in OUTCOMES},
            }
        models[op] = {
            "trainEvents": int(n),
            "coveredInteractionContexts": int(coverage[op]),
            "operatorRatio": op_ratio,
            "invariant": invariant,
            "cells": cells,
        }

    return {
        "operators": ops,
        "operatorSupport": {x[0]: x[1] for x in eligible},
        "global": p_global,
        "base": p_base,
        "contextMain": context_main,
        "models": models,
    }


def freeze_model(hebrew_rows, glyph_rows, protocol):
    cfg = protocol["training"]
    gevents = glyph_events(glyph_rows)
    systems = {}
    for rep in HEBREW_REPS:
        hevents = hebrew_events(hebrew_rows, rep)
        shared = _shared_immediate_states(hevents, gevents, cfg)
        systems[rep] = {
            "sharedImmediateStates": shared,
            "hebrew": _build_model(hevents, shared, cfg),
            "glyph": _build_model(gevents, shared, cfg),
            "trainEventCounts": {"hebrew": len(hevents), "glyph": len(gevents)},
        }
    return {"outcomes": list(OUTCOMES), "systems": systems}


def _context_main_for(model, s0, s1):
    ck = context_key(s0, s1)
    if ck in model["contextMain"]:
        return model["contextMain"][ck]["dist"], model["contextMain"][ck]["ratio"]
    base = model["base"][s1]
    return base, {y: 1.0 for y in OUTCOMES}


def _cell_distributions(model, op, s0, s1, residual_source=None):
    ck = context_key(s0, s1)
    base = model["base"][s1]
    pcontext, ctx_ratio = _context_main_for(model, s0, s1)
    om = model["models"][op]
    pinv = om["invariant"][s1]
    padd = _normalize({y: base[y] * ctx_ratio[y] * om["operatorRatio"][y] for y in OUTCOMES})
    source = residual_source if residual_source is not None else ck
    cell = om["cells"].get(source)
    if cell is not None and cell["supportedInteraction"] and cell["s1"] == s1:
        residual = cell["residual"]
    else:
        residual = {y: 1.0 for y in OUTCOMES}
    pctx = _normalize({y: padd[y] * residual[y] for y in OUTCOMES})
    return pcontext, pinv, padd, pctx


def _aggregate_eval(events, model, shared_s1):
    allowed_s1 = set(shared_s1)
    allowed_ops = set(model["operators"])
    counts = defaultdict(Counter)
    metadata = {}
    distances = defaultdict(list)
    censored = Counter()
    total = Counter()
    for e in events:
        if e["s1"] not in allowed_s1 or e["operator"] not in allowed_ops:
            continue
        key = (e["operator"], e["context"])
        counts[key][e["outcome"]] += 1
        metadata[e["context"]] = (e["s0"], e["s1"])
        total[e["operator"]] += 1
        if e["censoredByUnitEnd"]:
            censored[e["operator"]] += 1
        else:
            distances[e["operator"]].append(e["distance"])
    return counts, metadata, total, distances, censored


def _qualify(counts, metadata, total, model, protocol):
    ecfg = protocol["evaluation"]
    mn_events = int(ecfg["minimumEvaluationEventsPerOperator"])
    mn_contexts = int(ecfg["minimumEvaluationInteractionContextsPerOperator"])
    out = []
    for op in model["operators"]:
        contexts = 0
        for (o, ck), cnt in counts.items():
            if o != op or not cnt:
                continue
            cell = model["models"][op]["cells"].get(ck)
            if cell is not None and cell["supportedInteraction"]:
                contexts += 1
        if total[op] >= mn_events and contexts >= mn_contexts:
            out.append(op)
    return out


def _score_actual_operator(op, counts, metadata, model):
    n_total = 0
    sums = {"interaction": 0.0, "overContext": 0.0, "overInvariant": 0.0}
    profile = defaultdict(lambda: [0.0, 0])
    for (o, ck), cnt in counts.items():
        if o != op or not cnt:
            continue
        s0, s1 = metadata[ck]
        pcontext, pinv, padd, pctx = _cell_distributions(model, op, s0, s1)
        for y, k in cnt.items():
            ig = math.log2(max(pctx[y], EPS)) - math.log2(max(padd[y], EPS))
            cg = math.log2(max(pctx[y], EPS)) - math.log2(max(pcontext[y], EPS))
            og = math.log2(max(pctx[y], EPS)) - math.log2(max(pinv[y], EPS))
            sums["interaction"] += k * ig
            sums["overContext"] += k * cg
            sums["overInvariant"] += k * og
            n_total += k
            pk = profile_key(s0, s1, y)
            profile[pk][0] += k * ig
            profile[pk][1] += k
    return {
        "events": n_total,
        "interaction": sums["interaction"] / n_total if n_total else 0.0,
        "overContext": sums["overContext"] / n_total if n_total else 0.0,
        "overInvariant": sums["overInvariant"] / n_total if n_total else 0.0,
        "trajectoryGains": {k: v[0] / v[1] for k, v in profile.items() if v[1]},
    }


def _precompute_null_scores(op, counts, metadata, model):
    # For each target evaluation context, precompute its interaction score under
    # every train-supported residual source from the same immediate-state row.
    targets = []
    row_sources = defaultdict(list)
    om = model["models"][op]
    for ck, cell in om["cells"].items():
        if cell["supportedInteraction"]:
            row_sources[cell["s1"]].append(ck)
    for s1 in row_sources:
        row_sources[s1].sort()

    for (o, ck), cnt in counts.items():
        if o != op or not cnt:
            continue
        s0, s1 = metadata[ck]
        target_cell = om["cells"].get(ck)
        target_supported = target_cell is not None and target_cell["supportedInteraction"]
        sources = row_sources.get(s1, []) if target_supported else []
        if not sources:
            targets.append((ck, s1, sum(cnt.values()), None, {None: 0.0}))
            continue
        score_by_source = {}
        _, _, padd, _ = _cell_distributions(model, op, s0, s1, residual_source="__IDENTITY__")
        for source in sources:
            _, _, _, pctx = _cell_distributions(model, op, s0, s1, residual_source=source)
            score = 0.0
            for y, k in cnt.items():
                score += k * (math.log2(max(pctx[y], EPS)) - math.log2(max(padd[y], EPS)))
            score_by_source[source] = score
        targets.append((ck, s1, sum(cnt.values()), sources, score_by_source))
    return targets, row_sources


def _null_operator_score(precomputed, row_sources, rng):
    mappings = {}
    for s1, sources in row_sources.items():
        shuffled = list(sources)
        rng.shuffle(shuffled)
        mappings[s1] = dict(zip(sources, shuffled))
    total_score = 0.0
    total_n = 0
    for ck, s1, n, sources, score_by_source in precomputed:
        if sources is None:
            total_n += n
            continue
        source = mappings[s1].get(ck, ck)
        total_score += score_by_source.get(source, score_by_source.get(ck, 0.0))
        total_n += n
    return total_score / total_n if total_n else 0.0


def _distance_summary(ops, total, distances, censored):
    all_dist = []
    c = 0
    n = 0
    for op in ops:
        all_dist.extend(distances[op])
        c += censored[op]
        n += total[op]
    all_dist.sort()
    if all_dist:
        mean = sum(all_dist) / len(all_dist)
        mid = len(all_dist) // 2
        median = all_dist[mid] if len(all_dist) % 2 else (all_dist[mid - 1] + all_dist[mid]) / 2
    else:
        mean = 0.0
        median = 0.0
    return {
        "nonCensoredEvents": len(all_dist),
        "meanStepsToFirstDeparture": mean,
        "medianStepsToFirstDeparture": median,
        "unitEndNoDepartureFraction": c / n if n else 0.0,
    }


def evaluate_system(rows, kind, representation, pair, protocol, lane):
    events = hebrew_events(rows, representation) if kind == "hebrew" else glyph_events(rows)
    model = pair[kind]
    counts, metadata, total, distances, censored = _aggregate_eval(
        events, model, pair["sharedImmediateStates"]
    )
    ops = _qualify(counts, metadata, total, model, protocol)
    details = {op: _score_actual_operator(op, counts, metadata, model) for op in ops}
    interaction_vals = [details[op]["interaction"] for op in ops]
    context_vals = [details[op]["overContext"] for op in ops]
    invariant_vals = [details[op]["overInvariant"] for op in ops]
    obs_interaction = sum(interaction_vals) / len(interaction_vals) if interaction_vals else 0.0
    obs_context = sum(context_vals) / len(context_vals) if context_vals else 0.0
    obs_invariant = sum(invariant_vals) / len(invariant_vals) if invariant_vals else 0.0

    precomputed = {}
    for op in ops:
        precomputed[op] = _precompute_null_scores(op, counts, metadata, model)
    rng = random.Random(f"mark-v24:{kind}:{representation}:{lane}")
    null = []
    for _ in range(int(protocol["evaluation"]["permutationCount"])):
        vals = []
        for op in ops:
            pc, rowsources = precomputed[op]
            vals.append(_null_operator_score(pc, rowsources, rng))
        null.append(sum(vals) / len(vals) if vals else 0.0)
    p = (1 + sum(x >= obs_interaction - 1e-15 for x in null)) / (len(null) + 1)
    positive = sum(v > 0 for v in interaction_vals) / len(interaction_vals) if interaction_vals else 0.0

    ecfg = protocol["evaluation"]
    gate = ecfg["withinSystemGatesPerLane"]
    threshold = (
        float(ecfg["hebrewFamilywiseInteractionPAtMost"])
        if kind == "hebrew" else float(ecfg["glyphInteractionPAtMost"])
    )
    enough = len(ops) >= int(ecfg["minimumEvaluableOperatorsPerSystem"])
    passed = (
        enough
        and obs_interaction > float(gate["operatorBalancedInteractionGainOverAdditiveGreaterThan"])
        and obs_context > float(gate["operatorBalancedGainOverContextOnlyGreaterThan"])
        and obs_invariant > float(gate["operatorBalancedGainOverInvariantOperatorGreaterThan"])
        and positive >= float(gate["positiveInteractionOperatorFractionAtLeast"])
        and p <= threshold
    )
    return {
        "kind": kind,
        "representation": representation,
        "lane": lane,
        "rawEvents": len(events),
        "coveredEvents": sum(total[op] for op in ops),
        "evaluableOperators": len(ops),
        "frozenOperators": len(model["operators"]),
        "sharedImmediateStates": list(pair["sharedImmediateStates"]),
        "operatorBalancedInteractionGainOverAdditiveBitsPerEvent": obs_interaction,
        "operatorBalancedGainOverContextOnlyBitsPerEvent": obs_context,
        "operatorBalancedGainOverInvariantOperatorBitsPerEvent": obs_invariant,
        "positiveInteractionOperatorFraction": positive,
        "permutationP": p,
        "pass": passed,
        "distanceDiagnostics": _distance_summary(ops, total, distances, censored),
        "operators": details,
    }


def _pearson(a, b):
    if len(a) != len(b) or len(a) < 2:
        return 0.0
    ma, mb = sum(a) / len(a), sum(b) / len(b)
    xa, xb = [x - ma for x in a], [x - mb for x in b]
    da = math.sqrt(sum(x * x for x in xa))
    db = math.sqrt(sum(x * x for x in xb))
    if not da or not db:
        return 0.0
    return sum(x * y for x, y in zip(xa, xb)) / (da * db)


def compare_profiles(hresult, gresult, protocol, lane, representation):
    cfg = protocol["evaluation"]["transitionProfile"]
    mn = int(cfg["minimumOperatorsPerTransitionCell"])

    def supported(result):
        vals = defaultdict(list)
        for op_row in result["operators"].values():
            for key, gain in op_row["trajectoryGains"].items():
                vals[key].append(gain)
        return {
            key: (sum(xs) / len(xs), len(xs))
            for key, xs in vals.items() if len(xs) >= mn
        }

    hp = supported(hresult)
    gp = supported(gresult)
    keys = sorted(set(hp) & set(gp))
    if len(keys) < int(cfg["minimumCommonTransitionCells"]):
        return {
            "representation": representation,
            "lane": lane,
            "commonTransitionCells": keys,
            "correlation": 0.0,
            "permutationP": 1.0,
            "pass": False,
            "hebrewProfile": hp,
            "glyphProfile": gp,
        }
    hv = [hp[k][0] for k in keys]
    gv = [gp[k][0] for k in keys]
    obs = _pearson(hv, gv)

    parsed = {k: __import__("json").loads(k) for k in keys}
    rows = defaultdict(list)
    for k in keys:
        s0, s1, outcome = parsed[k]
        rows[(s0, s1)].append(k)
    rng = random.Random(f"mark-v24-profile:{representation}:{lane}")
    null = []
    for _ in range(int(protocol["evaluation"]["permutationCount"])):
        permuted = {k: gp[k][0] for k in keys}
        for row_keys in rows.values():
            vals = [gp[k][0] for k in row_keys]
            rng.shuffle(vals)
            for k, v in zip(row_keys, vals):
                permuted[k] = v
        null.append(_pearson(hv, [permuted[k] for k in keys]))
    p = (1 + sum(x >= obs - 1e-15 for x in null)) / (len(null) + 1)
    gate = cfg["gate"]
    passed = obs > float(gate["correlationGreaterThan"]) and p <= float(gate["permutationPAtMost"])
    return {
        "representation": representation,
        "lane": lane,
        "commonTransitionCells": keys,
        "correlation": obs,
        "permutationP": p,
        "pass": passed,
        "hebrewProfile": hp,
        "glyphProfile": gp,
    }


def adjudicate(results, profiles, freeze, protocol):
    minimum = int(protocol["evaluation"]["minimumEvaluableOperatorsPerSystem"])
    feasible = [
        rep for rep in HEBREW_REPS
        if len(freeze["systems"][rep]["sharedImmediateStates"]) >= 3
        and len(freeze["systems"][rep]["hebrew"]["operators"]) >= minimum
        and len(freeze["systems"][rep]["glyph"]["operators"]) >= minimum
    ]
    if not feasible:
        return "INSUFFICIENT_FIRST_PASSAGE_SUPPORT"

    recovered, aligned, glyph_ok = [], [], []
    for rep in feasible:
        hp = all(results[l][rep]["hebrew"]["pass"] for l in ("holdout", "control"))
        gp = all(results[l][rep]["glyph"]["pass"] for l in ("holdout", "control"))
        ap = hp and gp and all(profiles[rep][l]["pass"] for l in ("holdout", "control"))
        if hp:
            recovered.append(rep)
        if gp:
            glyph_ok.append(rep)
        if ap:
            aligned.append(rep)

    if len(aligned) > 1:
        return "MULTIPLE_FIRST_PASSAGE_CONTEXTS_RECOVERED_WITH_ALIGNMENT"
    if len(aligned) == 1:
        return {
            "lemma": "LEMMA_FIRST_PASSAGE_CONTEXT_RECOVERED_AND_ALIGNS_GLYPHS",
            "lemmaCoarseMorph": "COARSE_FIRST_PASSAGE_CONTEXT_RECOVERED_AND_ALIGNS_GLYPHS",
            "lemmaFullMorph": "FULL_FIRST_PASSAGE_CONTEXT_RECOVERED_AND_ALIGNS_GLYPHS",
        }[aligned[0]]
    if len(recovered) > 1:
        return "MULTIPLE_FIRST_PASSAGE_CONTEXTS_RECOVERED_WITHOUT_ALIGNMENT"
    if len(recovered) == 1:
        return {
            "lemma": "LEMMA_FIRST_PASSAGE_CONTEXT_RECOVERED_WITHOUT_ALIGNMENT",
            "lemmaCoarseMorph": "COARSE_FIRST_PASSAGE_CONTEXT_RECOVERED_WITHOUT_ALIGNMENT",
            "lemmaFullMorph": "FULL_FIRST_PASSAGE_CONTEXT_RECOVERED_WITHOUT_ALIGNMENT",
        }[recovered[0]]
    if glyph_ok:
        return "GLYPH_ONLY_FIRST_PASSAGE_CONTEXT"
    return "NO_FIRST_PASSAGE_CONTEXT_INTERACTION_PREDICTIVE"
