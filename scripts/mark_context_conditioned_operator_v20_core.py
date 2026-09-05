#!/usr/bin/env python3
import itertools, math, random
from collections import Counter, defaultdict

from mark_hebrew_glyph_annotation_competition_v19_io import (
    canonical_json, parse_hebrew_wlc, read_json, read_jsonl,
    sha256_json, write_json, write_jsonl,
)
from mark_hebrew_glyph_annotation_competition_v19_projector import (
    OUTCOMES, event_rows, tables,
)

EPS = 1e-300

def _normalize(d):
    z = sum(d.values())
    if z <= 0:
        return {y: 1.0 / len(OUTCOMES) for y in OUTCOMES}
    return {y: d[y] / z for y in OUTCOMES}

def _shared_states(hevents, gevents, cfg):
    ht, gt = tables(hevents), tables(gevents)
    mn = int(cfg["minimumSharedStateEventsPerCorpus"])
    states = sorted(
        s for s in set(ht[2]) & set(gt[2])
        if ht[2][s] >= mn and gt[2][s] >= mn
    )
    return states, ht, gt

def _eligible_ops(tab, states, cfg):
    mn_events = int(cfg["minimumOperatorEvents"])
    mn_pair = int(cfg["minimumOperatorStateEventsForCoverage"])
    mn_states = int(cfg["minimumCoveredSharedStates"])
    cap = int(cfg["maximumOperatorsPerCorpus"])
    rows = []
    for op, n in tab[4].items():
        covered = sum(tab[3][(s, op)] >= mn_pair for s in states)
        if n >= mn_events and covered >= mn_states:
            rows.append((op, int(n), int(covered)))
    rows.sort(key=lambda x: (-x[1], x[0]))
    return rows[:cap]

def _build_system_model(events, states, cfg):
    tab = tables(events)
    eligible = _eligible_ops(tab, states, cfg)
    ops = [x[0] for x in eligible]
    alpha = float(cfg["globalAdditiveAlpha"])
    state_backoff = float(cfg["stateBackoffPseudoCount"])
    op_backoff = float(cfg["operatorMainEffectBackoffPseudoCount"])
    interaction_backoff = float(cfg["interactionBackoffPseudoCount"])
    min_interaction = int(cfg["minimumOperatorStateEventsForInteraction"])

    global_counts = Counter()
    total = 0
    for s in states:
        global_counts.update(tab[0][s])
        total += tab[2][s]
    p_global = {
        y: (global_counts[y] + alpha) / (total + alpha * len(OUTCOMES))
        for y in OUTCOMES
    }

    p_state = {}
    for s in states:
        n = tab[2][s]
        p_state[s] = {
            y: (tab[0][s][y] + state_backoff * p_global[y]) / (n + state_backoff)
            for y in OUTCOMES
        }

    models = {}
    coverage = {x[0]: x[2] for x in eligible}
    for op in ops:
        op_counts = Counter()
        op_total = 0
        for s in states:
            op_counts.update(tab[1][(s, op)])
            op_total += tab[3][(s, op)]
        p_op = {
            y: (op_counts[y] + op_backoff * p_global[y]) / (op_total + op_backoff)
            for y in OUTCOMES
        }
        ratio = {y: p_op[y] / max(p_global[y], EPS) for y in OUTCOMES}
        states_model = {}
        for s in states:
            inv = _normalize({y: p_state[s][y] * ratio[y] for y in OUTCOMES})
            n = int(tab[3][(s, op)])
            if n >= min_interaction:
                ctx = {
                    y: (tab[1][(s, op)][y] + interaction_backoff * inv[y]) /
                       (n + interaction_backoff)
                    for y in OUTCOMES
                }
            else:
                ctx = dict(inv)
            residual = {y: ctx[y] / max(inv[y], EPS) for y in OUTCOMES}
            states_model[s] = {
                "trainEvents": n,
                "invariant": inv,
                "interactionResidual": residual,
            }
        models[op] = {
            "trainEvents": int(tab[4][op]),
            "coveredStates": int(coverage[op]),
            "states": states_model,
        }

    return {
        "operators": ops,
        "operatorSupport": {x[0]: x[1] for x in eligible},
        "models": models,
    }

def freeze_model(hebrew_rows, glyph_rows, protocol):
    cfg = protocol["training"]
    hevents = event_rows(hebrew_rows, "hebrew")
    gevents = event_rows(glyph_rows, "glyph")
    states, _, _ = _shared_states(hevents, gevents, cfg)
    return {
        "outcomes": list(OUTCOMES),
        "sharedStates": states,
        "systems": {
            "hebrew": _build_system_model(hevents, states, cfg),
            "glyph": _build_system_model(gevents, states, cfg),
        },
        "trainEventCounts": {"hebrew": len(hevents), "glyph": len(gevents)},
    }

def _dist_with_residual(inv, residual):
    return _normalize({y: inv[y] * residual[y] for y in OUTCOMES})

def _aggregate_eval(rows, kind, freeze):
    ev = event_rows(rows, kind)
    states = set(freeze["sharedStates"])
    ops = set(freeze["systems"][kind]["operators"])
    counts = defaultdict(Counter)
    for e in ev:
        if e["state"] in states and e["operator"] in ops:
            counts[(e["operator"], e["state"])][e["outcome"]] += 1
    return counts, len(ev)

def _qualify_operators(counts, system_model, protocol):
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

def _operator_gain(op, counts, op_model, state_source=None):
    total = 0
    score = 0.0
    by_state = {}
    for s in sorted(op_model["states"]):
        cnt = counts[(op, s)]
        n = sum(cnt.values())
        if not n:
            continue
        src = state_source[s] if state_source is not None else s
        inv = op_model["states"][s]["invariant"]
        residual = op_model["states"][src]["interactionResidual"]
        ctx = _dist_with_residual(inv, residual)
        local = 0.0
        for y, k in cnt.items():
            d = math.log2(max(ctx[y], EPS)) - math.log2(max(inv[y], EPS))
            score += k * d
            local += k * d
            total += k
        by_state[s] = local / n
    return (score / total if total else 0.0), by_state, total

def _balanced_gain(ops, counts, system_model, mappings=None):
    vals = []
    state_op = defaultdict(list)
    details = {}
    for op in ops:
        mapping = mappings.get(op) if mappings else None
        g, by_state, n = _operator_gain(op, counts, system_model["models"][op], mapping)
        vals.append(g)
        details[op] = {"gainBitsPerEvent": g, "evaluationEvents": n, "stateGains": by_state}
        for s, v in by_state.items():
            state_op[s].append(v)
    state_profile = {s: sum(vs) / len(vs) for s, vs in state_op.items() if vs}
    return (sum(vals) / len(vals) if vals else 0.0), vals, state_profile, details

def _permute_mappings(ops, system_model, rng):
    maps = {}
    for op in ops:
        states = sorted(system_model["models"][op]["states"])
        shuffled = list(states)
        rng.shuffle(shuffled)
        maps[op] = dict(zip(states, shuffled))
    return maps

def evaluate_system(rows, kind, freeze, protocol, lane):
    system = freeze["systems"][kind]
    counts, raw_events = _aggregate_eval(rows, kind, freeze)
    ops = _qualify_operators(counts, system, protocol)
    obs, vals, profile, details = _balanced_gain(ops, counts, system)
    ecfg = protocol["evaluation"]
    seed = ecfg["hebrewPermutationSeed"] if kind == "hebrew" else ecfg["glyphPermutationSeed"]
    rng = random.Random(seed + ":" + lane)
    null = []
    for _ in range(int(ecfg["permutationCount"])):
        mappings = _permute_mappings(ops, system, rng)
        x, _, _, _ = _balanced_gain(ops, counts, system, mappings)
        null.append(x)
    p = (1 + sum(x >= obs - 1e-15 for x in null)) / (len(null) + 1)
    positive = (sum(v > 0 for v in vals) / len(vals)) if vals else 0.0
    gates = ecfg["withinSystemGatesPerLane"]
    enough = len(ops) >= int(ecfg["minimumEvaluableOperatorsPerCorpus"])
    passed = (
        enough
        and obs > float(gates["operatorBalancedContextGainGreaterThan"])
        and p <= float(gates["interactionPermutationPAtMost"])
        and positive >= float(gates["positiveOperatorFractionAtLeast"])
    )
    return {
        "kind": kind,
        "lane": lane,
        "rawEvents": raw_events,
        "evaluableOperators": len(ops),
        "frozenOperators": len(system["operators"]),
        "operatorBalancedContextGainBitsPerEvent": obs,
        "positiveOperatorFraction": positive,
        "permutationP": p,
        "pass": passed,
        "stateProfile": profile,
        "operators": details,
    }

def _pearson(a, b):
    if len(a) != len(b) or len(a) < 2:
        return 0.0
    ma, mb = sum(a) / len(a), sum(b) / len(b)
    xa, xb = [x - ma for x in a], [x - mb for x in b]
    da = math.sqrt(sum(x*x for x in xa))
    db = math.sqrt(sum(x*x for x in xb))
    if not da or not db:
        return 0.0
    return sum(x*y for x, y in zip(xa, xb)) / (da * db)

def compare_profiles(hebrew_result, glyph_result, protocol, lane):
    cfg = protocol["evaluation"]["contextProfile"]
    mn_ops = int(cfg["minimumOperatorsPerState"])

    def profile_with_support(result):
        sums = defaultdict(list)
        for row in result["operators"].values():
            for s, v in row["stateGains"].items():
                sums[s].append(v)
        return {
            s: (sum(vs) / len(vs), len(vs))
            for s, vs in sums.items() if len(vs) >= mn_ops
        }

    hp = profile_with_support(hebrew_result)
    gp = profile_with_support(glyph_result)
    states = sorted(set(hp) & set(gp))
    enough = len(states) >= int(cfg["minimumCommonStates"])
    if not enough:
        return {
            "lane": lane, "commonStates": states, "correlation": 0.0,
            "permutationP": 1.0, "pass": False,
            "hebrewProfile": hp, "glyphProfile": gp,
        }

    hv = [hp[s][0] for s in states]
    gv = [gp[s][0] for s in states]
    obs = _pearson(hv, gv)

    if len(states) <= 8:
        null = [_pearson(hv, list(p)) for p in itertools.permutations(gv)]
    else:
        rng = random.Random("mark-v20-profile:" + lane)
        null = []
        for _ in range(int(protocol["evaluation"]["permutationCount"])):
            p = list(gv)
            rng.shuffle(p)
            null.append(_pearson(hv, p))
    p = (sum(x >= obs - 1e-15 for x in null)) / len(null) if null else 1.0
    gate = cfg["gate"]
    passed = (
        obs > float(gate["correlationGreaterThan"])
        and p <= float(gate["statePermutationPAtMost"])
    )
    return {
        "lane": lane,
        "commonStates": states,
        "correlation": obs,
        "permutationP": p,
        "pass": passed,
        "hebrewProfile": hp,
        "glyphProfile": gp,
    }

def adjudicate(lanes, profiles, freeze, protocol):
    ecfg = protocol["evaluation"]
    feasible = (
        len(freeze["sharedStates"]) >= int(ecfg["contextProfile"]["minimumCommonStates"])
        and all(
            len(freeze["systems"][k]["operators"]) >= int(ecfg["minimumEvaluableOperatorsPerCorpus"])
            for k in ("hebrew", "glyph")
        )
    )
    if not feasible:
        return "INSUFFICIENT_CONTEXT_SUPPORT"
    hp = all(lanes[x]["hebrew"]["pass"] for x in ("holdout", "control"))
    gp = all(lanes[x]["glyph"]["pass"] for x in ("holdout", "control"))
    xp = all(profiles[x]["pass"] for x in ("holdout", "control"))
    if hp and gp and xp:
        return "CONTEXT_CONDITIONED_OPERATOR_EFFECTS_ALIGN_ACROSS_SYSTEMS"
    if hp and gp:
        return "CONTEXT_CONDITIONED_EFFECTS_TRANSFER_WITHOUT_CROSS_SYSTEM_ALIGNMENT"
    if hp and not gp:
        return "HEBREW_ONLY_CONTEXT_CONDITIONING"
    if gp and not hp:
        return "GLYPH_ONLY_CONTEXT_CONDITIONING"
    return "CONTEXT_INVARIANT_OPERATOR_MODEL_SUFFICIENT"
