#!/usr/bin/env python3
import json
import os
from collections import Counter, defaultdict
from pathlib import Path

from mark_operator_algebra_v9_core import (
    build_graph, canonical_sha, iter_compositions, iter_transitions, map_state,
    nested_counts_to_rows, build_probability_functions, weighted_tv,
)

protocol_path = Path(os.environ.get("MARK_V9_PROTOCOL", "research/mark/discovery-experiments/operator-composition-algebra-v9.protocol.json"))
train_path = Path(os.environ.get("MARK_V9_TRAIN", "artifact-staging/v9-split/train.jsonl"))
split_manifest_path = Path(os.environ.get("MARK_V9_SPLIT_MANIFEST", "artifact-staging/v9-split/split-manifest.json"))
out_dir = Path(os.environ.get("MARK_V9_FREEZE", "artifacts/mark-operator-composition-algebra-v9-freeze"))


def load_json(path): return json.loads(Path(path).read_text(encoding="utf-8"))

def read_train_rows():
    with train_path.open("r", encoding="utf-8") as handle:
        for raw in handle:
            row = json.loads(raw)
            if row.get("lane") != "train":
                raise RuntimeError("inducer received a non-train observation")
            yield row


def freeze_variant(protocol, variant):
    cfg = protocol["primitiveGraph"]
    state_cfg = protocol["interfaceState"]
    op_cfg = protocol["operator"]
    comp_cfg = protocol["composition"]
    law_cfg = protocol["lawDiscovery"]

    state_count = Counter(); state_sources = defaultdict(set)
    op_count = Counter(); op_sources = defaultdict(set); catalog = {}
    train_observations = 0; raw_transitions = 0; raw_sequences = 0

    for row in read_train_rows():
        train_observations += 1
        graph = build_graph(row, cfg, variant)
        source = row["sourceGroupId"]
        for occ in iter_transitions(graph, cfg):
            raw_transitions += 1
            for state in (occ["inputState"], occ["outputState"]):
                state_count[state] += 1; state_sources[state].add(source)
            op = occ["operatorId"]
            op_count[op] += 1; op_sources[op].add(source)
            catalog.setdefault(op, {
                "operatorId": op,
                "reverseOperatorId": occ["reverseOperatorId"],
                "descriptor": occ["descriptor"],
            })

    print(f"[{variant}] pass1 observations={train_observations} transitions={raw_transitions}", flush=True)
    common_states = {
        state for state, count in state_count.items()
        if count >= int(state_cfg["trainMinimumOccurrences"])
        and len(state_sources[state]) >= int(state_cfg["trainMinimumDistinctSources"])
    }
    eligible_ops = {
        op for op, count in op_count.items()
        if count >= int(op_cfg["minimumTrainOccurrences"])
        and len(op_sources[op]) >= int(op_cfg["minimumDistinctTrainSources"])
    }
    states = sorted(common_states) + ["OTHER"]

    base1 = Counter(); base2 = Counter(); op1 = Counter(); a2 = Counter(); b2 = Counter(); pair2 = Counter()
    pair_support = Counter(); pair_sources = defaultdict(set); pair_input_support = Counter()
    covered_sequences = 0

    for row in read_train_rows():
        graph = build_graph(row, cfg, variant)
        source = row["sourceGroupId"]
        for occ in iter_transitions(graph, cfg):
            i = map_state(occ["inputState"], common_states); o = map_state(occ["outputState"], common_states)
            base1[(i, o)] += 1
            if occ["operatorId"] in eligible_ops:
                op1[(occ["operatorId"], i, o)] += 1
        for seq in iter_compositions(graph, cfg):
            raw_sequences += 1
            i = map_state(seq["state0"], common_states); o = map_state(seq["state2"], common_states)
            base2[(i, o)] += 1
            A, B = seq["operatorA"], seq["operatorB"]
            if A not in eligible_ops or B not in eligible_ops:
                continue
            covered_sequences += 1
            a2[(A, i, o)] += 1; b2[(B, i, o)] += 1; pair2[(A, B, i, o)] += 1
            pair_support[(A, B)] += 1; pair_sources[(A, B)].add(source); pair_input_support[(A, B, i)] += 1

    print(f"[{variant}] pass2 sequences={raw_sequences} covered={covered_sequences} counts_pair={len(pair2)}", flush=True)
    model = {
        "variant": variant,
        "states": states,
        "stateInventory": {
            "rawDistinctStates": len(state_count),
            "frozenStatesIncludingOther": len(states),
            "commonStateOccurrences": sum(state_count[s] for s in common_states),
            "allStateOccurrences": sum(state_count.values()),
        },
        "operators": [
            {
                **catalog[op],
                "trainOccurrences": op_count[op],
                "distinctTrainSources": len(op_sources[op]),
                "selfReverse": catalog[op]["reverseOperatorId"] == op,
            }
            for op in sorted(eligible_ops)
        ],
        "operatorInventory": {
            "rawDistinctOperators": len(op_count),
            "eligibleOperators": len(eligible_ops),
            "eligibleOperatorOccurrences": sum(op_count[op] for op in eligible_ops),
            "allOperatorOccurrences": sum(op_count.values()),
        },
        "trainCoverage": {
            "observations": train_observations,
            "rawTransitions": raw_transitions,
            "rawCompositionPaths": raw_sequences,
            "coveredCompositionPaths": covered_sequences,
            "coveredPathFraction": covered_sequences / max(1, raw_sequences),
        },
        "smoothing": {
            "globalAdditiveAlpha": float(comp_cfg["globalAdditiveAlpha"]),
            "operatorBackoffPseudoCount": float(comp_cfg["operatorBackoffPseudoCount"]),
            "baselineBackoffPseudoCount": float(comp_cfg["baselineBackoffPseudoCount"]),
        },
        "counts": {
            "baseOneStep": nested_counts_to_rows(base1, ("inputState", "outputState")),
            "baseTwoStep": nested_counts_to_rows(base2, ("inputState", "outputState")),
            "operatorOneStep": nested_counts_to_rows(op1, ("operatorId", "inputState", "outputState")),
            "firstOperatorTwoStep": nested_counts_to_rows(a2, ("operatorId", "inputState", "outputState")),
            "secondOperatorTwoStep": nested_counts_to_rows(b2, ("operatorId", "inputState", "outputState")),
            "directPairTwoStep": nested_counts_to_rows(pair2, ("operatorA", "operatorB", "inputState", "outputState")),
        },
        "pairSupport": [
            {"operatorA": a, "operatorB": b, "occurrences": pair_support[(a,b)], "distinctSources": len(pair_sources[(a,b)])}
            for a,b in sorted(pair_support)
        ],
    }

    # Candidate-law discovery is allowed only on the primary train representation.
    if variant == law_cfg["variant"]:
        print(f"[{variant}] starting law discovery", flush=True)
        probs = build_probability_functions(model)
        state_list = probs["states"]
        min_pair = int(law_cfg["minimumPairOccurrences"])
        min_src = int(law_cfg["minimumPairDistinctSources"])
        max_candidates = int(law_cfg["maximumCandidatesPerLaw"])
        supported_pairs = {
            pair for pair, count in pair_support.items()
            if count >= min_pair and len(pair_sources[pair]) >= min_src
        }
        op_meta = {row["operatorId"]: row for row in model["operators"]}

        def input_weights(pair):
            return Counter({i: count for (a,b,i), count in pair_input_support.items() if (a,b) == pair})

        # Idempotence: compare K_A*K_A with K_A on inputs actually used by A,A paths.
        idem = []
        for A,B in supported_pairs:
            if A != B: continue
            weights = input_weights((A,B))
            tv = weighted_tv(
                lambda i,o,A=A: probs["pcomp"](A,A,i,o),
                lambda i,o,A=A: probs["pop"](A,i,o),
                state_list, weights,
            )
            if tv is not None and tv <= float(law_cfg["idempotence"]["maximumTrainKernelTv"]):
                idem.append({"operatorA": A, "operatorB": A, "trainKernelTv": tv, "trainOccurrences": pair_support[(A,A)], "distinctTrainSources": len(pair_sources[(A,A)])})
        print(f"[{variant}] idempotence candidates pre-sort={len(idem)}", flush=True)
        idem.sort(key=lambda r: (r["trainKernelTv"], -r["distinctTrainSources"], -r["trainOccurrences"], r["operatorA"]))

        # Cancellation: composite returns exact interface state more strongly than either single operator.
        cancel = []
        for A,B in supported_pairs:
            weights = input_weights((A,B)); total = sum(weights.values())
            if not total: continue
            comp_identity = sum(w * probs["pcomp"](A,B,i,i) for i,w in weights.items()) / total
            a_identity = sum(w * probs["pop"](A,i,i) for i,w in weights.items()) / total
            b_identity = sum(w * probs["pop"](B,i,i) for i,w in weights.items()) / total
            gain = comp_identity - max(a_identity, b_identity)
            if comp_identity >= float(law_cfg["cancellation"]["minimumTrainCompositeIdentityProbability"]) and gain >= float(law_cfg["cancellation"]["minimumTrainIdentityGainOverEitherSingle"]):
                cancel.append({"operatorA": A, "operatorB": B, "trainCompositeIdentityProbability": comp_identity, "trainIdentityGainOverEitherSingle": gain, "trainOccurrences": pair_support[(A,B)], "distinctTrainSources": len(pair_sources[(A,B)])})
        print(f"[{variant}] cancellation candidates pre-sort={len(cancel)}", flush=True)
        cancel.sort(key=lambda r: (-r["trainIdentityGainOverEitherSingle"], -r["trainCompositeIdentityProbability"], -r["distinctTrainSources"], r["operatorA"], r["operatorB"]))

        # Order sensitivity: A*B vs B*A on inputs observed in both orders. Avoid pure path-reversal cases when both operators are self-reverse.
        order = []
        seen = set()
        for A,B in sorted(supported_pairs):
            if A == B or (B,A) not in supported_pairs: continue
            unordered = tuple(sorted((A,B)))
            if unordered in seen: continue
            seen.add(unordered)
            if op_meta[A]["selfReverse"] and op_meta[B]["selfReverse"]:
                continue
            wa = input_weights((A,B)); wb = input_weights((B,A))
            common_weights = Counter({s: min(wa[s], wb[s]) for s in set(wa) & set(wb) if min(wa[s], wb[s]) > 0})
            tv = weighted_tv(
                lambda i,o,A=A,B=B: probs["pcomp"](A,B,i,o),
                lambda i,o,A=A,B=B: probs["pcomp"](B,A,i,o),
                state_list, common_weights,
            )
            if tv is not None and tv >= float(law_cfg["orderSensitivity"]["minimumTrainKernelTv"]):
                order.append({"operatorA": A, "operatorB": B, "trainKernelTv": tv, "trainOccurrencesAB": pair_support[(A,B)], "trainOccurrencesBA": pair_support[(B,A)], "distinctTrainSourcesAB": len(pair_sources[(A,B)]), "distinctTrainSourcesBA": len(pair_sources[(B,A)])})
        print(f"[{variant}] order candidates pre-sort={len(order)}", flush=True)
        order.sort(key=lambda r: (-r["trainKernelTv"], -min(r["distinctTrainSourcesAB"], r["distinctTrainSourcesBA"]), r["operatorA"], r["operatorB"]))

        # Conditional composition: directly observed pair consequences change with incoming interface state.
        conditional = []
        min_input = int(law_cfg["conditionalComposition"]["minimumOccurrencesPerInputState"])
        min_dom = float(law_cfg["conditionalComposition"]["minimumTrainDominantOutcomeProbability"])
        min_distinct = int(law_cfg["conditionalComposition"]["minimumDistinctInputStatesWithDifferentDominantOutcomes"])
        for A,B in supported_pairs:
            mappings = []
            for i in state_list:
                n = pair_input_support[(A,B,i)]
                if n < min_input: continue
                outcomes = [(o, pair2[(A,B,i,o)]) for o in state_list]
                out, count = max(outcomes, key=lambda x: (x[1], x[0]))
                prob = count / n if n else 0.0
                if prob >= min_dom:
                    mappings.append({"inputState": i, "dominantOutputState": out, "trainOccurrences": n, "trainDominantProbability": prob})
            if len({m["dominantOutputState"] for m in mappings}) >= min_distinct:
                score = min(m["trainDominantProbability"] for m in mappings)
                conditional.append({"operatorA": A, "operatorB": B, "trainMinimumDominantProbability": score, "frozenInputOutcomes": mappings, "trainOccurrences": pair_support[(A,B)], "distinctTrainSources": len(pair_sources[(A,B)])})
        print(f"[{variant}] conditional candidates pre-sort={len(conditional)}", flush=True)
        conditional.sort(key=lambda r: (-r["trainMinimumDominantProbability"], -len(r["frozenInputOutcomes"]), -r["distinctTrainSources"], r["operatorA"], r["operatorB"]))

        model["candidateLaws"] = {
            "idempotence": idem[:max_candidates],
            "cancellation": cancel[:max_candidates],
            "orderSensitivity": order[:max_candidates],
            "conditionalComposition": conditional[:max_candidates],
            "supportedPairCount": len(supported_pairs),
        }
    return model

protocol = load_json(protocol_path)
if protocol.get("schema") != "mark_operator_composition_algebra_protocol_v9":
    raise RuntimeError("unexpected V9 protocol schema")
split_manifest = load_json(split_manifest_path)
if split_manifest.get("experimentId") != protocol["experimentId"]:
    raise RuntimeError("split manifest experiment mismatch")

protocol_sha = canonical_sha(protocol)
variants = {}
for variant in (protocol["primitiveGraph"]["primaryVariant"], protocol["primitiveGraph"]["ablationVariant"]):
    variants[variant] = freeze_variant(protocol, variant)

core = {
    "schema": "mark_operator_composition_algebra_freeze_v9",
    "experimentId": protocol["experimentId"],
    "protocolSha256": protocol_sha,
    "parentV5RunId": int(protocol["parentV5"]["expectedRunId"]),
    "parentEdgePairManifestSha256": split_manifest["parentEdgePairManifestSha256"],
    "parentCriticalEdgeWorldSha256": split_manifest["parentCriticalEdgeWorldSha256"],
    "parentProjectorRowsSha256": split_manifest["parentProjectorRowsSha256"],
    "splitSha256": split_manifest["splitSha256"],
    "holdoutOpenedDuringInduction": False,
    "roleLabelsOpened": False,
    "variants": variants,
}
freeze_sha = canonical_sha(core)
packet = {**core, "operatorAlgebraFreezeSha256": freeze_sha}
out_dir.mkdir(parents=True, exist_ok=True)
(out_dir / "operator-algebra-freeze.json").write_text(json.dumps(packet, indent=2) + "\n", encoding="utf-8")
summary = [f"operator_algebra_freeze_sha256={freeze_sha}", f"protocol_sha256={protocol_sha}"]
for variant, model in variants.items():
    summary += [
        f"variant={variant};states={len(model['states'])};eligible_operators={model['operatorInventory']['eligibleOperators']};train_path_coverage={model['trainCoverage']['coveredPathFraction']:.6f}",
    ]
    if "candidateLaws" in model:
        for law in ("idempotence", "cancellation", "orderSensitivity", "conditionalComposition"):
            summary.append(f"law={law};frozen_candidates={len(model['candidateLaws'][law])}")
(out_dir / "summary.txt").write_text("\n".join(summary) + "\n", encoding="utf-8")
print("\n".join(summary))
