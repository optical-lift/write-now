
primary_ids = [item["id"] for item in observables if item.get("primary")]
practical = float(discovery["practicalEffectMagnitude"])
null_max = int(discovery["evidenceNullAbsoluteCountMaximum"])
transfer_min = float(protocol["transfer"]["sameDirectionMinimumMagnitude"])


def cleveland_gate(feature_id):
    result = results[train_lane]["features"][feature_id]
    effect = result["balancedEffect"]
    null = result.get("null")
    return bool(
        effect is not None
        and effect >= practical
        and null is not None
        and null["absoluteNullAtLeastObserved"] <= null_max
    )


def lane_gate(lane, feature_id):
    if lane not in results:
        return False
    effect = results[lane]["features"][feature_id]["balancedEffect"]
    return bool(effect is not None and effect >= transfer_min)


r1_topology = "r1TopologyTokenMutation"
r2_topology = "r2TopologyTokenMutation"
r1_length = "r1LengthAwareTokenMutation"
r2_length = "r2LengthAwareTokenMutation"
r1_transfer = cleveland_gate(r1_topology) and lane_gate("holdout", r1_topology)
r2_transfer = cleveland_gate(r2_topology) and lane_gate("holdout", r2_topology)
if r2_transfer:
    structural_adjudication = "radius2_composes_candidate_structural_syllables"
elif r1_transfer:
    structural_adjudication = "radius1_only_local_wiring_syntax"
else:
    structural_adjudication = "no_transferable_local_motif_signal"

length_notes = []
for radius, topology_id, length_id in (
    (1, r1_topology, r1_length),
    (2, r2_topology, r2_length),
):
    top = results[train_lane]["features"][topology_id]["balancedEffect"]
    lng = results[train_lane]["features"][length_id]["balancedEffect"]
    if top is None or lng is None:
        length_notes.append({"radius": radius, "adjudication": "insufficient"})
    elif lng - top >= practical:
        length_notes.append({"radius": radius, "adjudication": "normalized_length_materially_refines_motif"})
    elif top >= lng:
        length_notes.append({"radius": radius, "adjudication": "topology_equals_or_exceeds_length_aware"})
    else:
        length_notes.append({"radius": radius, "adjudication": "length_aware_slightly_stronger_but_below_material_difference"})

three_lane = {
    feature_id: cleveland_gate(feature_id) and lane_gate("holdout", feature_id) and lane_gate("control", feature_id)
    for feature_id in primary_ids
}

core = {
    "schema": "mark_local_wiring_motif_correspondence_result_v7",
    "experimentId": protocol["experimentId"],
    "parentV5RunId": int(parent["expectedRunId"]),
    "parentEdgePairManifestSha256": manifest_sha,
    "parentCriticalEdgeWorldSha256": world_sha,
    "parentProjectorRowsSha256": world["projectorRowsSha256"],
    "eligiblePairs": len(pair_rows),
    "eligibleTrainPairs": len(train_rows),
    "motifConstruction": motif_cfg,
    "canonicalization": protocol["canonicalization"],
    "effectSemantics": "positive = rooted local wiring motif mutation is smaller in role-preserving pairs; negative = motif mutation is larger in role-preserving pairs",
    "laneResults": results,
    "descriptiveTrainInventory": inventory,
    "adjudication": {
        "structural": structural_adjudication,
        "radius1Transfer": r1_transfer,
        "radius2Transfer": r2_transfer,
        "lengthRole": length_notes,
        "threeLanePrimaryClaims": three_lane,
    },
    "contract": {
        "consumesFrozenV5ArtifactOnly": True,
        "sourcePixelsConsumed": False,
        "topologyReprojected": False,
        "v6GeometryArtifactConsumed": False,
        "roleLabelsDoNotAffectCenterMapping": True,
        "unmatchedNeighborsRemainInsideMotifs": True,
        "residualPathGeometryExcluded": True,
        "positionAndOrientationExcludedFromFingerprint": True,
        "pairIsStatisticalUnit": True,
        "nullShufflesAtObservationPairLevelWithinPhysicalFamilyPair": True,
        "inventoryUsesNoRoleLabels": True,
        "otherExperimentStateMutated": False,
    },
}
digest = canonical_sha(core)
packet = {**core, "localWiringMotifCorrespondenceSha256": digest}
out_dir.mkdir(parents=True, exist_ok=True)
(out_dir / "local-wiring-motif-correspondence.json").write_text(json.dumps(packet, indent=2) + "\n", encoding="utf-8")
with (out_dir / "pair-motif-mutations.jsonl").open("w", encoding="utf-8") as handle:
    for row in pair_rows:
        handle.write(json.dumps(row, separators=(",", ":"), ensure_ascii=False) + "\n")

summary_lines = [
    f"local_wiring_motif_correspondence_sha256={digest}",
    f"parent_v5_edge_world_sha256={world_sha}",
    f"eligible_pairs={len(pair_rows)}",
    f"eligible_train_pairs={len(train_rows)}",
    f"structural_adjudication={structural_adjudication}",
]
for lane in sorted(results):
    for item in observables:
        feature_id = item["id"]
        result = results[lane]["features"][feature_id]
        effect = result["balancedEffect"]
        null = result.get("null")
        summary_lines.append(
            f"lane={lane};feature={feature_id};primary={str(bool(item.get('primary'))).lower()};"
            f"effect={'NA' if effect is None else f'{effect:.6f}'};families={result['supportedFamilies']};"
            f"pairs={result['pairsWithValue']};null_abs_at_least_observed={-1 if not null else null['absoluteNullAtLeastObserved']}"
        )
for key, record in sorted(inventory.items()):
    summary_lines.append(
        f"inventory={key};roots={record['roots']};distinct={record['distinctFingerprints']};"
        f"cross_source_recurring={record['crossSourceRecurringFingerprints']};"
        f"recurring_root_fraction={record['crossSourceRecurringRootFraction']:.6f}"
    )
(out_dir / "summary.txt").write_text("\n".join(summary_lines) + "\n", encoding="utf-8")

md = [
    "### Mark local wiring motif correspondence v7 — frozen result",
    "",
    f"- Parent V5 edge world: `{world_sha}`",
    f"- Eligible pairs: **{len(pair_rows)}** total / **{len(train_rows)}** Cleveland train",
    f"- Structural adjudication: **{structural_adjudication}**",
    "",
    "| Lane | Motif observable | Effect | Families | Pairs | Cleveland null ≥ |",
    "| --- | --- | ---: | ---: | ---: | ---: |",
]
for lane in sorted(results):
    for item in observables:
        feature_id = item["id"]
        result = results[lane]["features"][feature_id]
        effect = result["balancedEffect"]
        null = result.get("null")
        md.append(
            f"| {lane} | {feature_id}{' ★' if item.get('primary') else ''} | "
            f"{'NA' if effect is None else f'{effect:.6f}'} | {result['supportedFamilies']} | "
            f"{result['pairsWithValue']} | {'—' if not null else f\"{null['absoluteNullAtLeastObserved']} / {iterations}\"} |"
        )
md += [
    "",
    "★ = predeclared primary graded motif observable. Positive means the local wiring neighborhood changes less in role-preserving pairs.",
    "",
    "#### Blind train inventory",
    "",
    "| Motif view | Roots | Distinct fingerprints | Cross-source recurring fingerprints | Roots in recurring fingerprints |",
    "| --- | ---: | ---: | ---: | ---: |",
]
for key, record in sorted(inventory.items()):
    md.append(
        f"| {key} | {record['roots']} | {record['distinctFingerprints']} | "
        f"{record['crossSourceRecurringFingerprints']} | {record['crossSourceRecurringRootFraction']:.3f} |"
    )
md += [
    "",
    "Motifs include every local neighbor whether or not that neighbor survives cross-observation correspondence. Turn rate, tortuosity, turn count, path hash, absolute position, orientation, center IDs, and source IDs are excluded from motif identity.",
    "Cross-source recurrence is descriptive only; it cannot substitute for preserved-vs-broken correspondence evidence.",
]
(out_dir / "summary.md").write_text("\n".join(md) + "\n", encoding="utf-8")
print("\n".join(summary_lines))
