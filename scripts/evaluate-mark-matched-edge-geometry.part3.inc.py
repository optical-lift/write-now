pairs = [
    row for row in pairs
    if row["observationA"] in eligible_obs and row["observationB"] in eligible_obs
]
needed = {row["observationA"] for row in pairs} | {row["observationB"] for row in pairs}
observations = {}
for raw in projector_bytes.splitlines():
    if not raw.strip():
        continue
    row = json.loads(raw)
    if row["observationId"] in needed:
        observations[row["observationId"]] = row
if set(observations) != needed:
    missing = sorted(needed - set(observations))
    raise RuntimeError(f"missing v5 projector observations: {missing[:8]}")

kcand = int(parent["greedyNearestCandidatesPerCenter"])
analyses = []
for index, pair in enumerate(pairs, 1):
    A = observations[pair["observationA"]]
    B = observations[pair["observationB"]]
    analyses.append(pair_analysis(pair, A, B, matching, kcand))
    if index % 50 == 0:
        print(f"analyzed_pairs={index}/{len(pairs)}")

train_lane = discovery["trainLane"]
train_rows = [row for row in analyses if row["lane"] == train_lane]
if len(train_rows) != int(parent["expectedEligibleTrainPairs"]):
    raise RuntimeError(f"eligible train pair drift: {len(train_rows)}")
raw_turn = v5_balanced_effect(train_rows, "preservedEdgeMeanTurnRateMutation")
raw_tort = v5_balanced_effect(train_rows, "preservedEdgeMeanTortuosityMutation")
tolerance = float(parent["v5RoundedEffectReproductionTolerance"])
if abs(raw_turn - float(parent["expectedV5TurnRateBalancedEffectRounded"])) > tolerance:
    raise RuntimeError(f"failed V5 turn-rate reproduction: {raw_turn}")
if abs(raw_tort - float(parent["expectedV5TortuosityBalancedEffectRounded"])) > tolerance:
    raise RuntimeError(f"failed V5 tortuosity reproduction: {raw_tort}")

features = [item["id"] for item in protocol["residualGeometryFeatures"]]
minimum_pairs = int(discovery["minimumPairsPerLabelPerStructuralStratum"])
iterations = int(discovery["nullIterations"])
lanes = sorted({row["lane"] for row in analyses})
results = {}
for lane in lanes:
    lane_rows = [row for row in analyses if row["lane"] == lane]
    lane_result = {
        "eligiblePairs": len(lane_rows),
        "preservedPairs": sum(row["label"] == "preserved" for row in lane_rows),
        "brokenPairs": sum(row["label"] == "broken" for row in lane_rows),
        "features": {},
    }
    for feature in features:
        feature_result = conditioned_effect(lane_rows, feature, minimum_pairs)
        if lane == train_lane:
            add_null(feature_result, lane_rows, feature, minimum_pairs, iterations)
        lane_result["features"][feature] = feature_result
    results[lane] = lane_result

practical = float(protocol["interpretation"]["practicalEffectMagnitude"])
train_features = results[train_lane]["features"]
turn_effect = train_features["meanTurnRateMutation"]["balancedEffect"]
tort_effect = train_features["meanTortuosityMutation"]["balancedEffect"]
if turn_effect is None:
    conclusion = "insufficient_matched_support"
elif abs(turn_effect) < practical:
    conclusion = "v5_turn_rate_counter_signal_collapses_after_structural_matching"
elif turn_effect >= practical:
    conclusion = "turn_rate_contains_residual_conservation_after_structural_matching"
else:
    conclusion = "turn_rate_counter_signal_persists_after_structural_matching"
if tort_effect is not None and turn_effect is not None:
    if (turn_effect >= practical and abs(tort_effect) < practical) or (tort_effect >= practical and abs(turn_effect) < practical):
        conclusion = "mixed_residual_geometry_features"

core = {
    "schema": "mark_matched_edge_geometry_result_v6",
    "experimentId": protocol["experimentId"],
    "parentV5RunId": int(parent["expectedRunId"]),
    "parentEdgePairManifestSha256": manifest_sha,
    "parentCriticalEdgeWorldSha256": world_sha,
    "parentProjectorRowsSha256": world["projectorRowsSha256"],
    "eligiblePairs": len(analyses),
    "v5NegativeResultReproduction": {
        "trainEligiblePairs": len(train_rows),
        "turnRateBalancedEffect": raw_turn,
        "tortuosityBalancedEffect": raw_tort,
        "reproducedWithinRoundedTolerance": True,
    },
    "matchingContract": matching,
    "effectSemantics": "positive = residual path-geometry mutation is smaller in role-preserving pairs after structural conditioning; negative = residual path-geometry mutation is larger in role-preserving pairs",
    "laneResults": results,
    "conclusion": conclusion,
    "limits": {
        "availableResidualGeometry": ["turnRate", "tortuosity"],
        "unavailableWithoutReprojection": ["curvatureSequence", "directionSequence", "localWiggleSpectrum"],
        "noUnavailableFeatureWasInferredFromPathHash": True,
    },
    "contract": {
        "consumesFrozenV5ArtifactOnly": True,
        "sourcePixelsConsumed": False,
        "topologyReprojected": False,
        "roleLabelsDoNotAffectCenterMapping": True,
        "residualGeometryExcludedFromStructuralKey": True,
        "parallelPathsNotPairedByResidualGeometry": True,
        "physicalFamilyPairConditionedExactly": True,
        "nullShufflesLabelsAtObservationPairLevelWithinPhysicalFamilyPair": True,
        "otherExperimentStateMutated": False,
    },
}
digest = canonical_sha(core)
packet = {**core, "matchedEdgeGeometrySha256": digest}
out_dir.mkdir(parents=True, exist_ok=True)
(out_dir / "matched-edge-geometry.json").write_text(json.dumps(packet, indent=2) + "\n", encoding="utf-8")
with (out_dir / "pair-matched-geometry.jsonl").open("w", encoding="utf-8") as handle:
    for row in analyses:
        handle.write(json.dumps(row, separators=(",", ":"), ensure_ascii=False) + "\n")

summary = [
    f"matched_edge_geometry_sha256={digest}",
    f"parent_v5_edge_world_sha256={world_sha}",
    f"eligible_pairs={len(analyses)}",
    f"eligible_train_pairs={len(train_rows)}",
    f"v5_turn_rate_effect_reproduced={raw_turn:.6f}",
    f"v5_tortuosity_effect_reproduced={raw_tort:.6f}",
    f"conclusion={conclusion}",
]
for lane in lanes:
    for feature in features:
        result = results[lane]["features"][feature]
        effect = result["balancedEffect"]
        null = result.get("null")
        summary.append(
            f"lane={lane};feature={feature};effect={'NA' if effect is None else f'{effect:.6f}'};"
            f"families={result['supportedFamilies']};strata={result['supportedStructuralStrata']};"
            f"pairs={result['supportedPairs']};edge_bucket_support={result['edgeBucketSupportFraction']:.6f};"
            f"null_abs_at_least_observed={-1 if not null else null['absoluteNullAtLeastObserved']}"
        )
(out_dir / "summary.txt").write_text("\n".join(summary) + "\n", encoding="utf-8")

md = [
    "### Mark matched-edge geometry v6 — frozen downstream result",
    "",
    f"- Parent V5 edge world: `{world_sha}`",
    f"- Eligible pairs: **{len(analyses)}** total / **{len(train_rows)}** Cleveland train",
    f"- V5 turn-rate counter-signal reproduced: **{raw_turn:.6f}**",
    f"- V5 tortuosity counter-signal reproduced: **{raw_tort:.6f}**",
    f"- Corrected conclusion: **{conclusion}**",
    "",
    "| Lane | Residual feature | Matched effect | Families | Structural strata | Pairs | Edge-bucket support | Null ≥ |",
    "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
]
for lane in lanes:
    for feature in features:
        result = results[lane]["features"][feature]
        effect = result["balancedEffect"]
        null = result.get("null")
        md.append(
            f"| {lane} | {feature} | {'NA' if effect is None else f'{effect:.6f}'} | "
            f"{result['supportedFamilies']} | {result['supportedStructuralStrata']} | {result['supportedPairs']} | "
            f"{result['edgeBucketSupportFraction']:.3f} | {'—' if not null else null['absoluteNullAtLeastObserved']} / {iterations} |"
        )
md += [
    "",
    "Positive means residual shape changes less in role-preserving pairs after structural matching; negative means it changes more.",
    "Turn rate and tortuosity were excluded from the matching key. Curvature sequence, direction sequence, and local wiggle are not present in the frozen V5 packet and were not inferred from path hashes.",
]
(out_dir / "summary.md").write_text("\n".join(md) + "\n", encoding="utf-8")
print("\n".join(summary))
