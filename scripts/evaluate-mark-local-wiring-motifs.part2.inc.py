
def shuffled_labels(rows, iteration):
    by_family = defaultdict(list)
    for row in rows:
        by_family[(row["occupantFamilyA"], row["occupantFamilyB"])].append(row)
    override = {}
    for (family_a, family_b), family_rows in sorted(by_family.items()):
        preserved_count = sum(row["label"] == "preserved" for row in family_rows)
        ordered = sorted(
            family_rows,
            key=lambda row: (
                hashlib.sha256(
                    f"local-motif-v7-null|{iteration}|{family_a}|{family_b}|{row['pairId']}".encode()
                ).hexdigest(),
                row["pairId"],
            ),
        )
        for index, row in enumerate(ordered):
            override[row["pairId"]] = "preserved" if index < preserved_count else "broken"
    return override


def add_null(result, rows, feature, iterations):
    observed = result["balancedEffect"]
    if observed is None:
        result["null"] = None
        return
    values = []
    for iteration in range(iterations):
        null_result = balanced_effect(rows, feature, shuffled_labels(rows, iteration))
        effect = null_result["balancedEffect"]
        if effect is not None:
            values.append(effect)
    if not values:
        result["null"] = None
        return
    result["null"] = {
        "iterationsRequested": iterations,
        "iterationsWithSupport": len(values),
        "mean": statistics.mean(values),
        "min": min(values),
        "max": max(values),
        "absoluteNullAtLeastObserved": sum(abs(x) >= abs(observed) for x in values),
        "nullAtLeastObserved": sum(x >= observed for x in values),
        "nullAtMostObserved": sum(x <= observed for x in values),
    }


def build_inventory(graphs, observation_ids, motif_cfg):
    inventory = {}
    for radius in motif_cfg["radii"]:
        for variant in ("topology", "lengthAware"):
            fingerprints = defaultdict(lambda: {"roots": 0, "sources": set()})
            total_roots = 0
            for oid in sorted(observation_ids):
                graph = graphs[oid]
                for root in sorted(graph["centers"]):
                    motif = motif_signature(graph, root, radius, variant, motif_cfg)
                    record = fingerprints[motif["fingerprint"]]
                    record["roots"] += 1
                    record["sources"].add(graph["sourceGroupId"])
                    total_roots += 1
            recurring = {fp for fp, record in fingerprints.items() if len(record["sources"]) >= 2}
            recurring_roots = sum(fingerprints[fp]["roots"] for fp in recurring)
            key = f"r{radius}{'Topology' if variant == 'topology' else 'LengthAware'}"
            inventory[key] = {
                "roots": total_roots,
                "distinctFingerprints": len(fingerprints),
                "crossSourceRecurringFingerprints": len(recurring),
                "rootsInCrossSourceRecurringFingerprints": recurring_roots,
                "crossSourceRecurringRootFraction": recurring_roots / max(1, total_roots),
                "topRecurring": [
                    {
                        "fingerprint": fp,
                        "roots": record["roots"],
                        "distinctSources": len(record["sources"]),
                    }
                    for fp, record in sorted(
                        fingerprints.items(),
                        key=lambda item: (-len(item[1]["sources"]), -item[1]["roots"], item[0]),
                    )[:20]
                ],
            }
    return inventory


protocol = load_json(protocol_path)
if protocol.get("schema") != "mark_local_wiring_motif_correspondence_protocol_v7":
    raise RuntimeError("unexpected v7 protocol")
parent = protocol["parentV5"]
motif_cfg = protocol["motifConstruction"]
discovery = protocol["discovery"]
observables = protocol["observables"]

manifest = load_json(locate("edge-pair-manifest.json"))
world = load_json(locate("critical-edge-world.json"))
role_pair_path = locate("role-pair-labels.jsonl")
projector_path = locate("critical-edge-observations.jsonl")

manifest_sha = manifest.get("edgePairManifestSha256")
world_sha = world.get("criticalEdgeWorldSha256")
if canonical_sha({k: v for k, v in manifest.items() if k != "edgePairManifestSha256"}) != manifest_sha:
    raise RuntimeError("v5 edge pair manifest SHA mismatch")
if canonical_sha({k: v for k, v in world.items() if k != "criticalEdgeWorldSha256"}) != world_sha:
    raise RuntimeError("v5 critical edge world SHA mismatch")
if manifest_sha != parent["expectedEdgePairManifestSha256"]:
    raise RuntimeError("wrong parent v5 edge pair manifest")
if world_sha != parent["expectedCriticalEdgeWorldSha256"]:
    raise RuntimeError("wrong parent v5 critical edge world")
projector_bytes = projector_path.read_bytes()
if hashlib.sha256(projector_bytes).hexdigest() != world["projectorRowsSha256"]:
    raise RuntimeError("v5 projector rows SHA mismatch")
role_bytes = role_pair_path.read_bytes()
if hashlib.sha256(role_bytes).hexdigest() != manifest["parentRolePairRowsSha256"]:
    raise RuntimeError("v5 role pair rows SHA mismatch")

pairs = [json.loads(raw) for raw in role_bytes.splitlines() if raw.strip()]
eligible_obs = set(world["pairEligibleObservationIds"])
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

graphs = {oid: build_graph(row, motif_cfg) for oid, row in observations.items()}
kcand = int(parent["greedyNearestCandidatesPerCenter"])
pair_rows = []
for index, pair in enumerate(pairs, 1):
    result = pair_motif_metrics(
        pair,
        observations[pair["observationA"]],
        observations[pair["observationB"]],
        graphs[pair["observationA"]],
        graphs[pair["observationB"]],
        observables,
        motif_cfg,
        kcand,
    )
    if result is not None:
        pair_rows.append(result)
    if index % 50 == 0:
        print(f"analyzed_pairs={index}/{len(pairs)} retained={len(pair_rows)}")

train_lane = discovery["trainLane"]
train_rows = [row for row in pair_rows if row["lane"] == train_lane]
if len(train_rows) < 50:
    raise RuntimeError(f"insufficient Cleveland motif pairs: {len(train_rows)}")
if len(train_rows) != int(parent["expectedEligibleTrainPairs"]):
    raise RuntimeError(f"eligible train pair drift: {len(train_rows)}")

iterations = int(discovery["nullIterations"])
results = {}
for lane in sorted({row["lane"] for row in pair_rows}):
    lane_rows = [row for row in pair_rows if row["lane"] == lane]
    lane_result = {
        "eligiblePairs": len(lane_rows),
        "preservedPairs": sum(row["label"] == "preserved" for row in lane_rows),
        "brokenPairs": sum(row["label"] == "broken" for row in lane_rows),
        "medianMappedRoots": statistics.median(row["mappedRoots"] for row in lane_rows) if lane_rows else 0,
        "features": {},
    }
    for item in observables:
        feature_result = balanced_effect(lane_rows, item["id"])
        if lane == train_lane:
            add_null(feature_result, lane_rows, item["id"], iterations)
        lane_result["features"][item["id"]] = feature_result
    results[lane] = lane_result

train_observation_ids = {
    oid for row in train_rows for oid in (row["observationA"], row["observationB"])
}
inventory = build_inventory(graphs, train_observation_ids, motif_cfg)
