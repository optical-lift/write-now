#!/usr/bin/env python3
import itertools
import math
import random
from collections import Counter, defaultdict

from mark_hebrew_glyph_annotation_competition_v19_io import (
    canonical_json, read_json, read_jsonl, sha256_json, write_json,
)
from mark_hebrew_glyph_annotation_competition_v19_projector import (
    glyph_segments, hist,
)

EPS = 1e-300
START = "<START>"
HEBREW_REPS = ("lemma", "lemmaCoarseMorph", "lemmaFullMorph")


def identity_sequence(row, representation):
    if representation == "lemma":
        return row["tokens"]
    return row[representation]


def _restricted_growth(n):
    if n == 0:
        yield []
        return
    def rec(prefix, mx):
        if len(prefix) == n:
            yield prefix
            return
        for x in range(mx + 2):
            yield from rec(prefix + [x], max(mx, x))
    yield from rec([0], 0)


def structural_outcomes():
    out = []
    for n in range(0, 5):
        for pat in _restricted_growth(n):
            row = [START] * (4 - n) + [f"A{x}" for x in pat]
            out.append(canonical_json(row))
    return sorted(set(out))


OUTCOMES = tuple(structural_outcomes())


def hebrew_transition_events(rows, representation):
    out = []
    for row in rows:
        seq = identity_sequence(row, representation)
        for i, op in enumerate(seq):
            out.append({
                "unit": row["anonymousUnitId"],
                "index": i,
                "state": hist(seq, i),
                "operator": op,
                "outcome": hist(seq, i + 1),
            })
    return out


def glyph_transition_events(rows):
    out = []
    for unit, seq in glyph_segments(rows):
        for i, op in enumerate(seq):
            out.append({
                "unit": unit,
                "index": i,
                "state": hist(seq, i),
                "operator": op,
                "outcome": hist(seq, i + 1),
            })
    return out


def _normalize(d):
    z = sum(d.values())
    if z <= 0:
        return {y: 1.0 / len(OUTCOMES) for y in OUTCOMES}
    return {y: d.get(y, 0.0) / z for y in OUTCOMES}


def _tables(events):
    state = defaultdict(Counter)
    sop = defaultdict(Counter)
    sn = Counter()
    sopn = Counter()
    opn = Counter()
    for e in events:
        s, o, y = e["state"], e["operator"], e["outcome"]
        state[s][y] += 1
        sop[(s, o)][y] += 1
        sn[s] += 1
        sopn[(s, o)] += 1
        opn[o] += 1
    return state, sop, sn, sopn, opn


def _shared_states(hevents, gevents, cfg):
    ht = _tables(hevents)
    gt = _tables(gevents)
    mn = int(cfg["minimumSharedStateEventsPerCorpus"])
    states = sorted(
        s for s in set(ht[2]) & set(gt[2])
        if ht[2][s] >= mn and gt[2][s] >= mn
    )
    return states


def _eligible_ops(tab, states, cfg):
    mn_events = int(cfg["minimumOperatorEvents"])
    mn_pair = int(cfg["minimumOperatorStateEventsForCoverage"])
    mn_states = int(cfg["minimumCoveredSharedStates"])
    cap = int(cfg["maximumOperatorsPerSystem"])
    rows = []
    for op, n in tab[4].items():
        covered = sum(tab[3][(s, op)] >= mn_pair for s in states)
        if n >= mn_events and covered >= mn_states:
            rows.append((op, int(n), int(covered)))
    rows.sort(key=lambda x: (-x[1], x[0]))
    return rows[:cap]


def _build_model(events, states, cfg):
    tab = _tables(events)
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

    coverage = {x[0]: x[2] for x in eligible}
    models = {}
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
        state_models = {}
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
            state_models[s] = {
                "trainEvents": n,
                "invariant": inv,
                "interactionResidual": residual,
            }
        models[op] = {
            "trainEvents": int(tab[4][op]),
            "coveredStates": int(coverage[op]),
            "states": state_models,
        }

    return {
        "operators": ops,
        "operatorSupport": {x[0]: x[1] for x in eligible},
        "stateOnly": p_state,
        "models": models,
    }


def freeze_model(hebrew_rows, glyph_rows, protocol):
    cfg = protocol["training"]
    gevents = glyph_transition_events(glyph_rows)
    systems = {}
    for rep in HEBREW_REPS:
        hevents = hebrew_transition_events(hebrew_rows, rep)
        states = _shared_states(hevents, gevents, cfg)
        systems[rep] = {
            "sharedStates": states,
            "hebrew": _build_model(hevents, states, cfg),
            "glyph": _build_model(gevents, states, cfg),
            "trainEventCounts": {"hebrew": len(hevents), "glyph": len(gevents)},
        }
    return {
        "outcomes": list(OUTCOMES),
        "systems": systems,
    }


def _aggregate(events, states, operators):
    ss, oo = set(states), set(operators)
    counts = defaultdict(Counter)
    kept = 0
    for e in events:
        if e["state"] in ss and e["operator"] in oo:
            counts[(e["operator"], e["state"])][e["outcome"]] += 1
            kept += 1
    return counts, kept


def _qualify(counts, model, protocol):
    ecfg = protocol["evaluation"]
    mn_events = int(ecfg["minimumEvaluationEventsPerOperator"])
    mn_contexts = int(ecfg["minimumEvaluationContextsPerOperator"])
    out = []
    for op in model["operators"]:
        states = model["models"][op]["states"]
        n = sum(sum(counts[(op, s)].values()) for s in states)
        c = sum(bool(counts[(op, s)]) for s in states)
        if n >= mn_events and c >= mn_contexts:
            out.append(op)
    return out


def _dist_with_residual(inv, residual):
    return _normalize({y: inv[y] * residual[y] for y in OUTCOMES})


def _operator_scores(op, counts, model, state_mapping=None):
    interaction_sum = 0.0
    total_sum = 0.0
    n_total = 0
    transition = defaultdict(lambda: [0.0, 0])
    for s in sorted(model["models"][op]["states"]):
        cnt = counts[(op, s)]
        if not cnt:
            continue
        source = state_mapping[s] if state_mapping is not None else s
        inv = model["models"][op]["states"][s]["invariant"]
        residual = model["models"][op]["states"][source]["interactionResidual"]
        ctx = _dist_with_residual(inv, residual)
        pstate = model["stateOnly"][s]
        for y, k in cnt.items():
            ig = math.log2(max(ctx[y], EPS)) - math.log2(max(inv[y], EPS))
            tg = math.log2(max(ctx[y], EPS)) - math.log2(max(pstate[y], EPS))
            interaction_sum += k * ig
            total_sum += k * tg
            n_total += k
            key = canonical_json([s, y])
            transition[key][0] += k * ig
            transition[key][1] += k
    return {
        "interaction": interaction_sum / n_total if n_total else 0.0,
        "total": total_sum / n_total if n_total else 0.0,
        "events": n_total,
        "transitionGains": {
            k: v[0] / v[1] for k, v in transition.items() if v[1]
        },
    }


def _permute_mappings(ops, model, rng):
    maps = {}
    for op in ops:
        states = sorted(model["models"][op]["states"])
        shuffled = list(states)
        rng.shuffle(shuffled)
        maps[op] = dict(zip(states, shuffled))
    return maps


def _balanced_scores(ops, counts, model, mappings=None):
    rows = {}
    ints, totals = [], []
    for op in ops:
        row = _operator_scores(op, counts, model, mappings.get(op) if mappings else None)
        rows[op] = row
        ints.append(row["interaction"])
        totals.append(row["total"])
    return (
        sum(ints) / len(ints) if ints else 0.0,
        sum(totals) / len(totals) if totals else 0.0,
        ints,
        rows,
    )


def evaluate_system(rows, kind, representation, pair, protocol, lane):
    events = (
        hebrew_transition_events(rows, representation)
        if kind == "hebrew" else glyph_transition_events(rows)
    )
    model = pair[kind]
    counts, covered = _aggregate(events, pair["sharedStates"], model["operators"])
    ops = _qualify(counts, model, protocol)
    obs_interaction, obs_total, vals, details = _balanced_scores(ops, counts, model)

    seed = f"mark-v23:{kind}:{representation}:{lane}"
    rng = random.Random(seed)
    null = []
    for _ in range(int(protocol["evaluation"]["permutationCount"])):
        mappings = _permute_mappings(ops, model, rng)
        x, _, _, _ = _balanced_scores(ops, counts, model, mappings)
        null.append(x)
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


def compare_transition_profiles(hresult, gresult, protocol, lane, representation):
    cfg = protocol["evaluation"]["transitionProfile"]
    mn = int(cfg["minimumOperatorsPerTransitionCell"])

    def supported(result):
        vals = defaultdict(list)
        for op_row in result["operators"].values():
            for key, gain in op_row["transitionGains"].items():
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
        incoming, outgoing = parsed[k]
        rows[incoming].append((k, outgoing))

    rng = random.Random(f"mark-v23-transition-profile:{representation}:{lane}")
    null = []
    for _ in range(int(protocol["evaluation"]["permutationCount"])):
        permuted = dict((k, gp[k][0]) for k in keys)
        for incoming, cells in rows.items():
            ks = [x[0] for x in cells]
            vals = [gp[k][0] for k in ks]
            rng.shuffle(vals)
            for k, v in zip(ks, vals):
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
        if len(freeze["systems"][rep]["sharedStates"]) >= 3
        and len(freeze["systems"][rep]["hebrew"]["operators"]) >= minimum
        and len(freeze["systems"][rep]["glyph"]["operators"]) >= minimum
    ]
    if not feasible:
        return "INSUFFICIENT_STRUCTURAL_SUPPORT"

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
        return "MULTIPLE_RELATIONAL_TRANSFORMATIONS_RECOVERED_WITH_ALIGNMENT"
    if len(aligned) == 1:
        return {
            "lemma": "LEMMA_RELATIONAL_TRANSFORMATION_RECOVERED_AND_ALIGNS_GLYPHS",
            "lemmaCoarseMorph": "COARSE_RELATIONAL_TRANSFORMATION_RECOVERED_AND_ALIGNS_GLYPHS",
            "lemmaFullMorph": "FULL_RELATIONAL_TRANSFORMATION_RECOVERED_AND_ALIGNS_GLYPHS",
        }[aligned[0]]
    if len(recovered) > 1:
        return "MULTIPLE_RELATIONAL_TRANSFORMATIONS_RECOVERED_WITHOUT_ALIGNMENT"
    if len(recovered) == 1:
        return {
            "lemma": "LEMMA_RELATIONAL_TRANSFORMATION_RECOVERED_WITHOUT_ALIGNMENT",
            "lemmaCoarseMorph": "COARSE_RELATIONAL_TRANSFORMATION_RECOVERED_WITHOUT_ALIGNMENT",
            "lemmaFullMorph": "FULL_RELATIONAL_TRANSFORMATION_RECOVERED_WITHOUT_ALIGNMENT",
        }[recovered[0]]
    if glyph_ok:
        return "GLYPH_ONLY_STRUCTURAL_TRANSFORMATION"
    return "NO_STRUCTURAL_TRANSFORMATION_MODEL_PREDICTIVE"
