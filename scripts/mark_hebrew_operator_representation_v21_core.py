#!/usr/bin/env python3
import itertools
import math
import random
import re
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from pathlib import Path

from mark_hebrew_glyph_annotation_competition_v19_io import (
    NS, bucket, canonical_json, coarse_morph_family, read_json, read_jsonl,
    sha256_json, write_json, write_jsonl,
)
from mark_hebrew_glyph_annotation_competition_v19_projector import (
    OUTCOMES, consequence, event_rows, hist,
)
from mark_context_conditioned_operator_v20_core import (
    EPS, _balanced_gain, _build_system_model, _dist_with_residual,
    _pearson, _permute_mappings, _qualify_operators, compare_profiles,
)

MISSING = "<MISSING>"
REPRESENTATIONS = ("lemma", "lemmaCoarseMorph", "lemmaFullMorph")


def _target_lemma_and_morph(w):
    lemma_parts = w.attrib.get("lemma", "").split("/")
    morph_parts = w.attrib.get("morph", "").split("/")
    idx = None
    num = None
    for i, part in enumerate(lemma_parts):
        m = re.search(r"\d+", part)
        if m:
            idx = i
            num = m.group(0)
            break
    if num is None:
        return None
    full = morph_parts[idx].strip() if idx is not None and idx < len(morph_parts) else ""
    if not full:
        full = MISSING
    coarse = coarse_morph_family(full)
    if not coarse:
        coarse = MISSING
    lemma = "H" + str(int(num))
    return lemma, coarse, full


def parse_hebrew_representations(wlc_dir, protocol):
    split = protocol["hebrewSplit"]
    bucket_sets = {
        "train": set(split["trainBuckets"]),
        "holdout": set(split["holdoutBuckets"]),
        "control": set(split["controlBuckets"]),
    }
    lanes = {name: [] for name in bucket_sets}
    counts = Counter()

    for path in sorted(Path(wlc_dir).glob("*.xml")):
        root = ET.parse(path).getroot()
        for verse in root.findall(".//osis:verse", NS):
            verse_id = verse.attrib.get("osisID")
            if not verse_id:
                continue
            b = bucket(verse_id, int(split["modulus"]))
            lane = next(name for name, vals in bucket_sets.items() if b in vals)
            lemma_tokens = []
            coarse_ops = []
            full_ops = []
            for w in verse.findall(".//osis:w", NS):
                parsed = _target_lemma_and_morph(w)
                if parsed is None:
                    continue
                lemma, coarse, full = parsed
                lemma_tokens.append(lemma)
                coarse_ops.append(f"{lemma}|M={coarse}")
                full_ops.append(f"{lemma}|M={full}")
            if not lemma_tokens:
                continue
            row = {
                "anonymousUnitId": "V" + __import__("hashlib").sha256(verse_id.encode()).hexdigest()[:20],
                "lane": lane,
                "tokens": lemma_tokens,
                "lemmaCoarseMorph": coarse_ops,
                "lemmaFullMorph": full_ops,
            }
            lanes[lane].append(row)
            counts[lane] += len(lemma_tokens)

    for lane in lanes:
        lanes[lane].sort(key=lambda row: row["anonymousUnitId"])

    manifest = {
        "schema": "mark_hebrew_operator_representation_split_v21",
        "sourceCommit": protocol["hebrewSource"]["commit"],
        "unitCounts": {lane: len(rows) for lane, rows in lanes.items()},
        "tokenCounts": dict(counts),
        "representations": list(REPRESENTATIONS),
        "stateAndOutcomeUseBaseLemmaOnly": True,
    }
    return lanes, manifest


def representation_events(rows, representation):
    out = []
    for row in rows:
        base = row["tokens"]
        if representation == "lemma":
            ops = base
        else:
            ops = row[representation]
        if len(base) != len(ops):
            raise ValueError(f"representation length mismatch in {row['anonymousUnitId']}")
        for i, op in enumerate(ops):
            out.append({
                "unit": row["anonymousUnitId"],
                "state": hist(base, i),
                "operator": op,
                "baseLemma": base[i],
                "outcome": consequence(base, i),
            })
    return out


def _training_cfg(protocol):
    cfg = dict(protocol["training"])
    cfg["maximumOperatorsPerCorpus"] = int(cfg["maximumRefinedOperatorsPerRepresentation"])
    return cfg


def freeze_model(hebrew_train_rows, inherited_v20_freeze, protocol):
    if inherited_v20_freeze.get("freezeAdjudication") != "FEASIBLE":
        raise ValueError("inherited V20 freeze is not FEASIBLE")
    states = list(inherited_v20_freeze["sharedStates"])
    cfg = _training_cfg(protocol)

    refined = {}
    train_counts = {}
    for rep in ("lemmaCoarseMorph", "lemmaFullMorph"):
        events = representation_events(hebrew_train_rows, rep)
        refined[rep] = _build_system_model(events, states, cfg)
        train_counts[rep] = len(events)

    return {
        "sharedStates": states,
        "outcomes": list(OUTCOMES),
        "inheritedV20FreezeSha256": inherited_v20_freeze["freezeSha256"],
        "systems": {
            "lemma": inherited_v20_freeze["systems"]["hebrew"],
            "glyph": inherited_v20_freeze["systems"]["glyph"],
            "lemmaCoarseMorph": refined["lemmaCoarseMorph"],
            "lemmaFullMorph": refined["lemmaFullMorph"],
        },
        "trainEventCounts": {
            "lemmaCoarseMorph": train_counts["lemmaCoarseMorph"],
            "lemmaFullMorph": train_counts["lemmaFullMorph"],
        },
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


def evaluate_representation(rows, representation, system_model, freeze, protocol, lane):
    events = representation_events(rows, representation)
    counts, covered_events = _aggregate_counts(
        events, freeze["sharedStates"], system_model["operators"]
    )
    ops = _qualify_operators(counts, system_model, protocol)
    obs, vals, profile, details = _balanced_gain(ops, counts, system_model)

    seed = protocol["evaluation"]["representationSeeds"][representation]
    rng = random.Random(seed + ":" + lane)
    null = []
    for _ in range(int(protocol["evaluation"]["permutationCount"])):
        mappings = _permute_mappings(ops, system_model, rng)
        x, _, _, _ = _balanced_gain(ops, counts, system_model, mappings)
        null.append(x)
    p = (1 + sum(x >= obs - 1e-15 for x in null)) / (len(null) + 1)
    positive = sum(v > 0 for v in vals) / len(vals) if vals else 0.0

    gates = protocol["evaluation"]["withinRepresentationGatesPerLane"]
    enough = len(ops) >= int(protocol["evaluation"]["minimumEvaluableOperatorsPerRepresentation"])
    passed = (
        enough
        and obs > float(gates["operatorBalancedContextGainGreaterThan"])
        and p <= float(gates["interactionPermutationPAtMost"])
        and positive >= float(gates["positiveOperatorFractionAtLeast"])
    )
    return {
        "representation": representation,
        "lane": lane,
        "rawEvents": len(events),
        "coveredEvents": covered_events,
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
    counts, covered_events = _aggregate_counts(
        events, freeze["sharedStates"], system_model["operators"]
    )
    ops = _qualify_operators(counts, system_model, protocol)
    obs, vals, profile, details = _balanced_gain(ops, counts, system_model)

    seed = protocol["evaluation"]["representationSeeds"]["glyph"]
    rng = random.Random(seed + ":" + lane)
    null = []
    for _ in range(int(protocol["evaluation"]["permutationCount"])):
        mappings = _permute_mappings(ops, system_model, rng)
        x, _, _, _ = _balanced_gain(ops, counts, system_model, mappings)
        null.append(x)
    p = (1 + sum(x >= obs - 1e-15 for x in null)) / (len(null) + 1)
    positive = sum(v > 0 for v in vals) / len(vals) if vals else 0.0
    gates = protocol["evaluation"]["withinRepresentationGatesPerLane"]
    enough = len(ops) >= int(protocol["evaluation"]["minimumEvaluableOperatorsPerRepresentation"])
    passed = (
        enough
        and obs > float(gates["operatorBalancedContextGainGreaterThan"])
        and p <= float(gates["interactionPermutationPAtMost"])
        and positive >= float(gates["positiveOperatorFractionAtLeast"])
    )
    return {
        "representation": "glyph",
        "lane": lane,
        "rawEvents": len(events),
        "coveredEvents": covered_events,
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


def _context_gain_for_event(event, model):
    state_model = model["states"][event["state"]]
    inv = state_model["invariant"]
    ctx = _dist_with_residual(inv, state_model["interactionResidual"])
    y = event["outcome"]
    return math.log2(max(ctx[y], EPS)) - math.log2(max(inv[y], EPS))


def paired_refinement(rows, representation, lemma_result, refined_result, freeze, protocol, lane):
    lemma_model = freeze["systems"]["lemma"]
    refined_model = freeze["systems"][representation]
    lemma_eval = set(lemma_result["evaluableOperatorIds"])
    refined_eval = set(refined_result["evaluableOperatorIds"])
    states = set(freeze["sharedStates"])

    diffs = defaultdict(list)
    child_seen = defaultdict(set)
    for e in representation_events(rows, representation):
        if e["state"] not in states:
            continue
        parent = e["baseLemma"]
        child = e["operator"]
        if parent not in lemma_eval or child not in refined_eval:
            continue
        lemma_event = dict(e)
        lemma_event["operator"] = parent
        d_refined = _context_gain_for_event(e, refined_model["models"][child])
        d_lemma = _context_gain_for_event(lemma_event, lemma_model["models"][parent])
        diffs[parent].append(d_refined - d_lemma)
        child_seen[parent].add(child)

    cfg = protocol["evaluation"]["pairedRefinement"]
    min_events = int(cfg["minimumCommonEventsPerParentLemma"])
    parent_values = {}
    for parent, vals in sorted(diffs.items()):
        if len(vals) >= min_events:
            parent_values[parent] = {
                "commonEvents": len(vals),
                "distinctRefinedOperators": len(child_seen[parent]),
                "meanDeltaBitsPerEvent": sum(vals) / len(vals),
            }

    values = [row["meanDeltaBitsPerEvent"] for row in parent_values.values()]
    observed = sum(values) / len(values) if values else 0.0
    positive = sum(v > 0 for v in values) / len(values) if values else 0.0
    baseline_n = max(1, lemma_result["evaluableOperators"])
    coverage = len(values) / baseline_n

    if values and len(values) <= 12:
        null = []
        for signs in itertools.product((-1.0, 1.0), repeat=len(values)):
            null.append(sum(s * v for s, v in zip(signs, values)) / len(values))
        p = sum(x >= observed - 1e-15 for x in null) / len(null)
    elif values:
        rng = random.Random("mark-v21-paired:" + representation + ":" + lane)
        null = []
        for _ in range(int(protocol["evaluation"]["permutationCount"])):
            null.append(sum((1 if rng.random() < 0.5 else -1) * v for v in values) / len(values))
        p = (1 + sum(x >= observed - 1e-15 for x in null)) / (len(null) + 1)
    else:
        p = 1.0

    gate = cfg["gate"]
    passed = (
        len(values) >= int(cfg["minimumEligibleParentLemmas"])
        and coverage >= float(cfg["minimumParentCoverageFractionOfEvaluableLemmaBaseline"])
        and observed > float(gate["parentBalancedDeltaGreaterThan"])
        and p <= float(gate["pairedSignFlipPAtMost"])
        and positive >= float(gate["positiveParentFractionAtLeast"])
    )
    return {
        "representation": representation,
        "lane": lane,
        "eligibleParentLemmas": len(values),
        "baselineEvaluableLemmas": lemma_result["evaluableOperators"],
        "parentCoverageFraction": coverage,
        "parentBalancedDeltaBitsPerEvent": observed,
        "positiveParentFraction": positive,
        "signFlipP": p,
        "pass": passed,
        "parents": parent_values,
    }


def adjudicate(lanes, paired, profiles, freeze, protocol):
    minimum = int(protocol["evaluation"]["minimumEvaluableOperatorsPerRepresentation"])
    refined_train_feasible = any(
        len(freeze["systems"][rep]["operators"]) >= minimum
        for rep in ("lemmaCoarseMorph", "lemmaFullMorph")
    )
    if not refined_train_feasible:
        return "INSUFFICIENT_REFINED_SUPPORT"

    lemma_pass = all(lanes[l]["lemma"]["pass"] for l in ("holdout", "control"))
    if lemma_pass:
        return "LEMMA_CONTEXT_CONDITIONING_REPLICATES"

    glyph_pass = all(lanes[l]["glyph"]["pass"] for l in ("holdout", "control"))
    rescue = {}
    align = {}
    for rep in ("lemmaCoarseMorph", "lemmaFullMorph"):
        rescue[rep] = all(
            lanes[l][rep]["pass"] and paired[rep][l]["pass"]
            for l in ("holdout", "control")
        )
        align[rep] = (
            rescue[rep]
            and glyph_pass
            and all(profiles[rep][l]["pass"] for l in ("holdout", "control"))
        )

    rescued = [rep for rep, ok in rescue.items() if ok]
    aligned = [rep for rep, ok in align.items() if ok]

    if len(rescued) == 2:
        if len(aligned) == 2:
            return "MULTIPLE_MORPH_REPRESENTATIONS_RESCUE_AND_ALIGN"
        if len(aligned) == 1:
            return "MULTIPLE_MORPH_REPRESENTATIONS_RESCUE_PARTIAL_ALIGNMENT"
        return "MULTIPLE_MORPH_REPRESENTATIONS_RESCUE_WITHOUT_GLYPH_ALIGNMENT"

    if rescued == ["lemmaFullMorph"]:
        return (
            "FULL_MORPH_RESCUES_HEBREW_OPERATOR_UNIT_AND_ALIGNS_GLYPH_CONTEXTS"
            if align["lemmaFullMorph"]
            else "FULL_MORPH_RESCUES_HEBREW_OPERATOR_UNIT_WITHOUT_GLYPH_ALIGNMENT"
        )
    if rescued == ["lemmaCoarseMorph"]:
        return (
            "COARSE_MORPH_RESCUES_HEBREW_OPERATOR_UNIT_AND_ALIGNS_GLYPH_CONTEXTS"
            if align["lemmaCoarseMorph"]
            else "COARSE_MORPH_RESCUES_HEBREW_OPERATOR_UNIT_WITHOUT_GLYPH_ALIGNMENT"
        )

    return "MORPH_REFINEMENT_DOES_NOT_RESCUE"
