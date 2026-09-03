#!/usr/bin/env python3
import hashlib
import json
import math
import os
import random
from collections import Counter, defaultdict
from pathlib import Path

protocol_path = Path(os.environ.get("MARK_OPERATOR_PROTOCOL", "research/mark/discovery-experiments/state-operator-discovery-v1.protocol.json"))
topology_dir = Path(os.environ.get("MARK_TOPOLOGY_ATLAS", "artifacts/mark-observation-topology-atlas-v1"))
field_dir = Path(os.environ.get("MARK_LOCAL_STATE_FIELD", "artifact-staging/local-state-field"))
transition_dir = Path(os.environ.get("MARK_TRANSITION_GRAMMAR", "artifact-staging/transition-grammar"))
out_dir = Path(os.environ.get("MARK_OPERATOR_OUT", "artifacts/mark-state-operator-discovery-v1"))
phase = os.environ.get("MARK_OPERATOR_PHASE", "all").strip().lower()


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def canonical_bytes(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def canonical_sha(value):
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def mean(xs):
    return sum(xs) / len(xs) if xs else 0.0


def stdev(xs):
    if not xs:
        return 0.0
    m = mean(xs)
    return math.sqrt(mean([(x - m) ** 2 for x in xs]))


def distance(a, b):
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


def area(region):
    return max(1, int(region["width"]) * int(region["height"]))


def center(region):
    return (
        float(region["x"]) + float(region["width"]) / 2.0,
        float(region["y"]) + float(region["height"]) / 2.0,
    )


def contains(parent, child):
    return (
        area(parent) > area(child)
        and parent["x"] <= child["x"]
        and parent["y"] <= child["y"]
        and parent["x"] + parent["width"] >= child["x"] + child["width"]
        and parent["y"] + parent["height"] >= child["y"] + child["height"]
    )


def kmeans(points, k, max_iter=100):
    global_mean = [mean([p[d] for p in points]) for d in range(len(points[0]))]
    first = max(range(len(points)), key=lambda i: (distance(points[i], global_mean), tuple(points[i]), -i))
    chosen = [first]
    while len(chosen) < k:
        idx = max(
            (i for i in range(len(points)) if i not in chosen),
            key=lambda i: (min(distance(points[i], points[j]) for j in chosen), tuple(points[i]), -i),
        )
        chosen.append(idx)
    centroids = [list(points[i]) for i in chosen]
    assignments = None
    for _ in range(max_iter):
        new_assignments = [min(range(k), key=lambda j: (distance(p, centroids[j]), j)) for p in points]
        if new_assignments == assignments:
            break
        assignments = new_assignments
        next_centroids = []
        for j in range(k):
            members = [points[i] for i, a in enumerate(assignments) if a == j]
            if not members:
                return None
            next_centroids.append([mean([p[d] for p in members]) for d in range(len(points[0]))])
        centroids = next_centroids
    return assignments, centroids


def sampled_silhouette(points, assignments, k, ids, limit=1024):
    order = sorted(range(len(ids)), key=lambda i: hashlib.sha256(ids[i].encode()).hexdigest())[: min(limit, len(ids))]
    clusters = {c: [i for i in order if assignments[i] == c] for c in range(k)}
    if any(not clusters[c] for c in range(k)):
        return -1.0
    scores = []
    for i in order:
        own = assignments[i]
        own_members = [j for j in clusters[own] if j != i]
        a = mean([distance(points[i], points[j]) for j in own_members]) if own_members else 0.0
        b = min(mean([distance(points[i], points[j]) for j in clusters[c]]) for c in range(k) if c != own)
        denom = max(a, b)
        scores.append((b - a) / denom if denom else 0.0)
    return mean(scores)


def entropy(counts):
    total = sum(counts)
    if total <= 0:
        return 0.0
    h = 0.0
    for count in counts:
        if count:
            p = count / total
            h -= p * math.log(p)
    return h


def load_inputs():
    protocol = load_json(protocol_path)
    if protocol.get("schema") != "mark_state_operator_discovery_protocol_v1":
        raise RuntimeError("unexpected operator protocol")

    field = load_json(field_dir / "local-state-field-discovery.json")
    if field.get("localStateFieldDiscoverySha256") != protocol["parentEvidence"]["localStateFieldDiscoverySha256"]:
        raise RuntimeError("wrong local-state parent")
    if field.get("provenanceAvailableDuringDiscovery"):
        raise RuntimeError("local-state parent was not blind")

    transition = load_json(transition_dir / "state-transition-grammar-discovery.json")
    if transition.get("stateTransitionGrammarDiscoverySha256") != protocol["parentEvidence"]["stateTransitionGrammarDiscoverySha256"]:
        raise RuntimeError("wrong transition parent")
    if transition.get("provenanceAvailableDuringDiscovery"):
        raise RuntimeError("transition parent was not blind")

    topo_summary = load_json(topology_dir / "summary.json")
    if topo_summary.get("schema") != "mark_observation_topology_atlas_summary_v1":
        raise RuntimeError("unexpected topology atlas schema")
    if not topo_summary.get("contract", {}).get("noProvenanceConsumed"):
        raise RuntimeError("topology atlas provenance contract failed")

    compiler_custody = load_json(field_dir / "compiler-custody" / "custody.json")
    if topo_summary["physicalLedgerMerkleRoot"] != compiler_custody["physicalLedger"]["merkleRoot"]:
        raise RuntimeError("topology atlas physical Merkle mismatch")
    if topo_summary.get("sourceBlindInputSha256") != compiler_custody.get("sourceBlindInputSha256"):
        raise RuntimeError("topology atlas blind-input custody mismatch")

    states = {}
    with (field_dir / "observation-local-states.jsonl").open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            oid = row["observationId"]
            if oid in states:
                raise RuntimeError(f"duplicate frozen state observation {oid}")
            states[oid] = row

    topology = {}
    with (topology_dir / "observation-topology-atlas.jsonl").open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            oid = row["observationId"]
            if oid in topology:
                raise RuntimeError(f"duplicate topology observation {oid}")
            topology[oid] = row

    if int(topo_summary.get("observations", -1)) != len(topology):
        raise RuntimeError("topology summary observation count does not match topology rows")

    missing = sorted(set(states) - set(topology))
    if missing:
        raise RuntimeError(f"topology atlas is missing {len(missing)} frozen local-state observations")

    metadata_mismatch = []
    for oid, state in states.items():
        topo = topology[oid]
        for key in ("sourceGroupId", "lane", "region", "proposalKind", "proposalScale"):
            if state.get(key, "") != topo.get(key, ""):
                metadata_mismatch.append((oid, key))
                break
    if metadata_mismatch:
        raise RuntimeError(f"state/topology identity mismatch for {len(metadata_mismatch)} frozen observations")

    compatibility = {
        "schema": "mark_state2_alias_input_compatibility_v1",
        "physicalLedgerMerkleRoot": topo_summary["physicalLedgerMerkleRoot"],
        "sourceBlindInputSha256": topo_summary["sourceBlindInputSha256"],
        "topologyObservations": len(topology),
        "frozenLocalStateObservations": len(states),
        "extraTopologyObservationsOutsideFrozenPrimaryStateDepth": len(set(topology) - set(states)),
        "allFrozenStateObservationsPresentInTopology": True,
        "allFrozenStateObservationMetadataMatchesTopology": True,
        "contract": {
            "exactSetEqualityNotRequired": True,
            "reason": "the topology atlas covers the full sealed blind input while the frozen local-state file contains only observations eligible at its primary context-mass depth",
            "missingOrMetadataChangedFrozenStateObservationIsFatal": True,
        },
    }
    return protocol, field, transition, topo_summary, states, topology, compatibility


def build_parent_map(states):
    by_source = defaultdict(list)
    for row in states.values():
        by_source[row["sourceGroupId"]].append(row)
    parent = {}
    for source, items in by_source.items():
        for child in items:
            candidates = [
                p
                for p in items
                if p["observationId"] != child["observationId"] and contains(p["region"], child["region"])
            ]
            if candidates:
                p = min(candidates, key=lambda x: (area(x["region"]), x["observationId"]))
                parent[child["observationId"]] = p["observationId"]
    return parent


def normalized_topology(row):
    centers = max(1, int(row["centerCount"]))
    out = {key: float(value) / centers for key, value in row["countFeatures"].items()}
    out["derived:centerDensityPerMillionPixelsLog1p"] = math.log1p(
        float(row["centerCount"]) * 1_000_000.0 / area(row["region"])
    )
    return out


def incoming_geometry(parent_row, row):
    pr, cr = parent_row["region"], row["region"]
    pc, cc = center(pr), center(cr)
    return {
        "incomingGeometry:hasParent": 1.0,
        "incomingGeometry:logAreaRatio": math.log(area(cr) / area(pr)),
        "incomingGeometry:dxParentWidth": (cc[0] - pc[0]) / max(1.0, float(pr["width"])),
        "incomingGeometry:dyParentHeight": (cc[1] - pc[1]) / max(1.0, float(pr["height"])),
        "incomingGeometry:aspectDelta": math.log(
            (cr["width"] / max(1.0, float(cr["height"])))
            / (pr["width"] / max(1.0, float(pr["height"])))
        ),
    }


def fingerprints(states, topology, parent, target_state):
    norm = {oid: normalized_topology(row) for oid, row in topology.items()}
    result = {}
    for oid, state in states.items():
        if int(state["stateId"]) != target_state:
            continue
        own = norm[oid]
        fp = {f"parent:{key}": value for key, value in own.items()}
        incoming = parent.get(oid)
        if incoming is None:
            fp["incomingGeometry:hasParent"] = 0.0
        else:
            previous = norm[incoming]
            keys = set(own) | set(previous)
            for key in keys:
                fp[f"incomingDelta:{key}"] = own.get(key, 0.0) - previous.get(key, 0.0)
            fp.update(incoming_geometry(states[incoming], state))
        result[oid] = fp
    return result


def fit_cluster_phase(protocol, field, transition, topology, states, compatibility):
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "compatibility.json").write_text(json.dumps(compatibility, indent=2) + "\n", encoding="utf-8")

    parent = build_parent_map(states)
    target_state = int(protocol["target"]["parentState"])
    fps = fingerprints(states, topology, parent, target_state)
    train_ids = sorted(oid for oid in fps if states[oid]["lane"] == "train")
    if not train_ids:
        raise RuntimeError("no train-lane State 2 observations for latent alias discovery")

    signature_support = Counter()
    feature_support = Counter()
    for oid in train_ids:
        for key, value in fps[oid].items():
            if abs(value) <= 1e-15:
                continue
            feature_support[key] += 1
            if ":signature:" in key:
                signature_support[key] += 1

    min_sig = int(protocol["featureDiscovery"]["minimumTrainObservationSupportForDynamicCenterSignature"])
    eligible = []
    for key in sorted(feature_support):
        if ":signature:" in key and signature_support[key] < min_sig:
            continue
        vals = [fps[oid].get(key, 0.0) for oid in train_ids]
        sd = stdev(vals)
        if sd <= 1e-12:
            continue
        eligible.append((feature_support[key], sd, key))
    if not eligible:
        raise RuntimeError("no label-free topology features eligible for latent State 2 discovery")

    eligible.sort(key=lambda row: (-row[0], -row[1], row[2]))
    max_features = int(protocol["featureDiscovery"]["maximumTopologyFeatures"])
    selected = [row[2] for row in eligible[:max_features]]

    stats = {}
    for key in selected:
        vals = [fps[oid].get(key, 0.0) for oid in train_ids]
        stats[key] = {"mean": mean(vals), "standardDeviation": stdev(vals) or 1.0}

    def vector(oid):
        return [
            (fps[oid].get(key, 0.0) - stats[key]["mean"]) / stats[key]["standardDeviation"]
            for key in selected
        ]

    train_points = [vector(oid) for oid in train_ids]
    candidates = []
    min_cluster = int(protocol["latentStateDiscovery"]["minimumTrainObservationsPerCluster"])
    min_sources = int(protocol["latentStateDiscovery"]["minimumDistinctTrainSourcesPerCluster"])
    for k in protocol["latentStateDiscovery"]["candidateK"]:
        k = int(k)
        if k >= len(train_points):
            continue
        result = kmeans(train_points, k)
        if result is None:
            continue
        assignments, centroids = result
        sizes = [assignments.count(j) for j in range(k)]
        if min(sizes) < min_cluster:
            continue
        source_support = []
        for j in range(k):
            sources = {states[train_ids[i]]["sourceGroupId"] for i, a in enumerate(assignments) if a == j}
            source_support.append(len(sources))
        if min(source_support) < min_sources:
            continue
        score = sampled_silhouette(train_points, assignments, k, train_ids)
        candidates.append((score, k, assignments, centroids, sizes, source_support))
    if not candidates:
        raise RuntimeError("no valid label-free State 2 latent cluster solution")

    score, k, train_assignments, centroids, sizes, source_support = max(candidates, key=lambda row: (row[0], -row[1]))

    centroid_order = sorted(range(k), key=lambda j: (tuple(centroids[j]), j))
    remap = {old: new + 1 for new, old in enumerate(centroid_order)}
    stable_centroids = {remap[j]: centroids[j] for j in range(k)}

    assignments = {}
    margins = {}
    distances = {}
    for oid in sorted(fps):
        vec = vector(oid)
        ds = sorted((distance(vec, stable_centroids[cid]), cid) for cid in stable_centroids)
        assignments[oid] = ds[0][1]
        margins[oid] = ds[1][0] - ds[0][0] if len(ds) > 1 else 0.0
        distances[oid] = {str(cid): d for d, cid in ds}

    cluster_summary = {}
    for lane in ("train", "holdout", "control"):
        lane_ids = [oid for oid in assignments if states[oid]["lane"] == lane]
        cluster_summary[lane] = {
            str(cid): {
                "observations": sum(assignments[oid] == cid for oid in lane_ids),
                "distinctSourceSupport": len({states[oid]["sourceGroupId"] for oid in lane_ids if assignments[oid] == cid}),
            }
            for cid in sorted(stable_centroids)
        }

    cluster_core = {
        "schema": "mark_state2_latent_alias_definition_v1",
        "experimentId": protocol["experimentId"],
        "parentLocalStateFieldDiscoverySha256": field["localStateFieldDiscoverySha256"],
        "parentStateTransitionGrammarDiscoverySha256": transition["stateTransitionGrammarDiscoverySha256"],
        "physicalLedgerMerkleRoot": compatibility["physicalLedgerMerkleRoot"],
        "targetParentState": target_state,
        "provenanceAvailableDuringDiscovery": False,
        "childOutcomeLabelsAvailableDuringClustering": False,
        "trainState2Observations": len(train_ids),
        "allLaneState2Observations": len(assignments),
        "featureSelection": {
            "method": "label-free train support then raw variability; dynamic signatures require train support",
            "eligibleFeatureCount": len(eligible),
            "selectedFeatures": selected,
            "trainStandardization": stats,
        },
        "latentClusters": {
            "chosenK": k,
            "sampledTrainSilhouette": score,
            "candidateSolutions": [
                {
                    "k": row[1],
                    "sampledTrainSilhouette": row[0],
                    "trainClusterSizes": row[4],
                    "trainDistinctSourceSupport": row[5],
                }
                for row in sorted(candidates, key=lambda x: x[1])
            ],
            "stableTrainCentroids": {str(cid): stable_centroids[cid] for cid in sorted(stable_centroids)},
            "assignment": "nearest frozen train centroid; holdout/control never refit",
            "clusterSupportByLane": cluster_summary,
        },
        "compatibility": compatibility,
        "contract": {
            "clusterDiscoveryUsesOnlyFrozenState2IdentityNotChildOutcome": True,
            "noChildStateUsedForFeatureSelection": True,
            "noChildStateUsedForKSelection": True,
            "noChildStateUsedForCentroids": True,
            "holdoutAndControlDoNotRefit": True,
            "sourceProvenanceUnavailableUntilFinalOperatorFreeze": True,
        },
    }
    cluster_sha = canonical_sha(cluster_core)
    cluster_packet = {**cluster_core, "state2LatentAliasDefinitionSha256": cluster_sha}
    (out_dir / "state2-alias-cluster-definition.json").write_text(json.dumps(cluster_packet, indent=2) + "\n", encoding="utf-8")

    with (out_dir / "state2-latent-clusters.jsonl").open("w", encoding="utf-8") as handle:
        for oid in sorted(assignments):
            row = states[oid]
            frozen = {
                "schema": "mark_state2_latent_alias_assignment_v1",
                "observationId": oid,
                "sourceGroupId": row["sourceGroupId"],
                "lane": row["lane"],
                "region": row["region"],
                "proposalKind": row.get("proposalKind", ""),
                "proposalScale": row.get("proposalScale", ""),
                "latentAliasId": assignments[oid],
                "nearestCentroidMargin": margins[oid],
                "centroidDistances": distances[oid],
                "state2LatentAliasDefinitionSha256": cluster_sha,
            }
            handle.write(json.dumps(frozen, separators=(",", ":"), ensure_ascii=False) + "\n")

    (out_dir / "cluster-summary.txt").write_text(
        "\n".join(
            [
                f"state2_latent_alias_definition_sha256={cluster_sha}",
                f"topology_observations={compatibility['topologyObservations']}",
                f"frozen_local_state_observations={compatibility['frozenLocalStateObservations']}",
                f"extra_topology_observations={compatibility['extraTopologyObservationsOutsideFrozenPrimaryStateDepth']}",
                f"train_state2_observations={len(train_ids)}",
                f"all_lane_state2_observations={len(assignments)}",
                f"chosen_k={k}",
                f"sampled_train_silhouette={score:.9f}",
                "child_outcome_labels_available_during_clustering=false",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps(cluster_packet, indent=2))


def association_metrics(edges, cluster_by_parent, outcome_override=None):
    if not edges:
        return {
            "edges": 0,
            "outcomeCounts": {},
            "clusterCounts": {},
            "informationGain": 0.0,
            "normalizedInformationGain": 0.0,
            "clusterPurity": 0.0,
            "majorityBaseline": 0.0,
            "purityLiftOverMajority": 0.0,
            "clusterOutcomeRates": {},
        }
    outcomes = outcome_override if outcome_override is not None else [edge["childState"] for edge in edges]
    cluster_ids = sorted(set(cluster_by_parent[edge["parentObservationId"]] for edge in edges))
    outcome_ids = sorted(set(outcomes), key=str)
    table = {cid: Counter() for cid in cluster_ids}
    for edge, outcome in zip(edges, outcomes):
        table[cluster_by_parent[edge["parentObservationId"]]][outcome] += 1
    overall = Counter(outcomes)
    total = len(outcomes)
    h_y = entropy([overall[o] for o in outcome_ids])
    h_cond = 0.0
    correct = 0
    rates = {}
    for cid in cluster_ids:
        n = sum(table[cid].values())
        h_cond += (n / total) * entropy([table[cid][o] for o in outcome_ids])
        correct += max(table[cid].values()) if n else 0
        rates[str(cid)] = {str(o): table[cid][o] / n if n else 0.0 for o in outcome_ids}
    info_gain = h_y - h_cond
    purity = correct / total
    majority = max(overall.values()) / total
    return {
        "edges": total,
        "outcomeCounts": {str(k): v for k, v in sorted(overall.items(), key=lambda x: str(x[0]))},
        "clusterCounts": {str(cid): sum(table[cid].values()) for cid in cluster_ids},
        "informationGain": info_gain,
        "normalizedInformationGain": info_gain / h_y if h_y else 0.0,
        "clusterPurity": purity,
        "majorityBaseline": majority,
        "purityLiftOverMajority": purity - majority,
        "clusterOutcomeRates": rates,
    }


def contraction_quartiles(edges):
    ordered = sorted(edges, key=lambda edge: (edge["logAreaRatio"], edge["edgeId"]))
    n = len(ordered)
    return {edge["edgeId"]: min(3, (i * 4) // max(1, n)) for i, edge in enumerate(ordered)}


def reveal_phase(protocol, field, transition, states, compatibility):
    cluster_packet = load_json(out_dir / "state2-alias-cluster-definition.json")
    cluster_sha = cluster_packet.get("state2LatentAliasDefinitionSha256")
    cluster_core = {k: v for k, v in cluster_packet.items() if k != "state2LatentAliasDefinitionSha256"}
    if canonical_sha(cluster_core) != cluster_sha:
        raise RuntimeError("latent alias definition SHA mismatch")
    if cluster_packet.get("childOutcomeLabelsAvailableDuringClustering"):
        raise RuntimeError("latent alias cluster packet consumed child outcomes")

    assignments = {}
    with (out_dir / "state2-latent-clusters.jsonl").open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            if row.get("state2LatentAliasDefinitionSha256") != cluster_sha:
                raise RuntimeError("latent alias assignment belongs to different frozen definition")
            assignments[row["observationId"]] = int(row["latentAliasId"])

    parent = build_parent_map(states)
    target_state = int(protocol["target"]["parentState"])
    allowed_outcomes = sorted(int(x) for x in protocol["target"]["childOutcomes"])
    edges = []
    for child_id, parent_id in parent.items():
        if int(states[parent_id]["stateId"]) != target_state:
            continue
        if parent_id not in assignments:
            raise RuntimeError(f"State 2 parent {parent_id} lacks frozen latent alias assignment")
        p, c = states[parent_id], states[child_id]
        child_state = int(c["stateId"])
        if child_state not in allowed_outcomes:
            raise RuntimeError(f"unexpected child outcome {child_state}")
        edge_id = "A" + hashlib.sha256(f"{p['sourceGroupId']}|{parent_id}|{child_id}".encode()).hexdigest()[:20]
        edges.append(
            {
                "schema": "mark_state2_alias_exit_edge_v1",
                "edgeId": edge_id,
                "sourceGroupId": p["sourceGroupId"],
                "lane": p["lane"],
                "parentObservationId": parent_id,
                "childObservationId": child_id,
                "latentAliasId": assignments[parent_id],
                "childState": child_state,
                "parentProposalScale": p.get("proposalScale", ""),
                "parentRegion": p["region"],
                "childRegion": c["region"],
                "logAreaRatio": math.log(area(c["region"]) / area(p["region"])),
                "state2LatentAliasDefinitionSha256": cluster_sha,
            }
        )
    if not edges:
        raise RuntimeError("no State 2 containment exits available after alias freeze")

    lane_ids = ["train", "holdout", "control"]
    observed = {}
    nulls = {}
    iters = int(protocol["nullModel"]["iterations"])
    for lane in lane_ids:
        lane_edges = [edge for edge in edges if edge["lane"] == lane]
        observed[lane] = {
            "threeWay": association_metrics(lane_edges, assignments),
            "stayVsExit": association_metrics(
                lane_edges, assignments, ["stay" if edge["childState"] == target_state else "exit" for edge in lane_edges]
            ),
            "exitDirection": association_metrics(
                [edge for edge in lane_edges if edge["childState"] != target_state],
                assignments,
            ),
        }
        q = contraction_quartiles(lane_edges)
        strata = defaultdict(list)
        for i, edge in enumerate(lane_edges):
            strata[(edge["parentProposalScale"], q[edge["edgeId"]])].append(i)
        labels = [edge["childState"] for edge in lane_edges]
        null_stats = {"threeWay": [], "stayVsExit": [], "exitDirection": []}
        for iteration in range(iters):
            shuffled = labels[:]
            for key, idxs in strata.items():
                vals = [labels[i] for i in idxs]
                seed = int(hashlib.sha256(f"mark-state2-alias-null|{lane}|{iteration}|{key}".encode()).hexdigest()[:16], 16)
                rnd = random.Random(seed)
                rnd.shuffle(vals)
                for i, value in zip(idxs, vals):
                    shuffled[i] = value
            null_stats["threeWay"].append(association_metrics(lane_edges, assignments, shuffled)["normalizedInformationGain"])
            binary = ["stay" if value == target_state else "exit" for value in shuffled]
            null_stats["stayVsExit"].append(association_metrics(lane_edges, assignments, binary)["normalizedInformationGain"])
            exit_edges = [edge for edge, value in zip(lane_edges, shuffled) if value != target_state]
            exit_labels = [value for value in shuffled if value != target_state]
            null_stats["exitDirection"].append(
                association_metrics(exit_edges, assignments, exit_labels)["normalizedInformationGain"] if exit_edges else 0.0
            )
        nulls[lane] = {}
        for key, values in null_stats.items():
            obs_value = observed[lane][key]["normalizedInformationGain"]
            nulls[lane][key] = {
                "observedNormalizedInformationGain": obs_value,
                "nullMean": mean(values),
                "nullMinimum": min(values) if values else 0.0,
                "nullMaximum": max(values) if values else 0.0,
                "liftOverNullMean": obs_value - mean(values),
                "beatsAllNulls": bool(values) and obs_value > max(values),
                "nullAtLeastObserved": sum(value >= obs_value for value in values),
            }

    branch_counts = {
        lane: {str(outcome): sum(edge["lane"] == lane and edge["childState"] == outcome for edge in edges) for outcome in allowed_outcomes}
        for lane in lane_ids
    }

    cluster_exit = {}
    cluster_ids = sorted(set(assignments.values()))
    for lane in lane_ids:
        lane_edges = [edge for edge in edges if edge["lane"] == lane]
        cluster_exit[lane] = {}
        for cid in cluster_ids:
            rows = [edge for edge in lane_edges if edge["latentAliasId"] == cid]
            outcomes = Counter(edge["childState"] for edge in rows)
            exits = outcomes[1] + outcomes[3]
            cluster_exit[lane][str(cid)] = {
                "edges": len(rows),
                "distinctSourceSupport": len({edge["sourceGroupId"] for edge in rows}),
                "outcomeCounts": {str(outcome): outcomes[outcome] for outcome in allowed_outcomes},
                "stayRate": outcomes[target_state] / len(rows) if rows else 0.0,
                "exitRate": exits / len(rows) if rows else 0.0,
                "state3AmongExitsRate": outcomes[3] / exits if exits else 0.0,
            }

    with (out_dir / "state2-cluster-exit-edges.jsonl").open("w", encoding="utf-8") as handle:
        for edge in sorted(edges, key=lambda row: row["edgeId"]):
            handle.write(json.dumps(edge, separators=(",", ":"), ensure_ascii=False) + "\n")

    association = {
        "schema": "mark_state2_alias_exit_association_v1",
        "state2LatentAliasDefinitionSha256": cluster_sha,
        "childOutcomeLabelsRevealedOnlyAfterAliasFreeze": True,
        "state2ContainmentEdges": len(edges),
        "branchCounts": branch_counts,
        "associationByLane": observed,
        "nullComparisonByLane": nulls,
        "clusterExitBehaviorByLane": cluster_exit,
        "contract": {
            "frozenClusterAssignmentsUnchangedDuringReveal": True,
            "holdoutAndControlClustersNotRefit": True,
            "allThreeOutcomesRetained": True,
            "stayVsExitReportedSeparately": True,
            "exitDirectionOneVsThreeReportedSeparately": True,
        },
    }
    association_sha = canonical_sha(association)
    association["state2AliasExitAssociationSha256"] = association_sha
    (out_dir / "state2-cluster-exit-association.json").write_text(json.dumps(association, indent=2) + "\n", encoding="utf-8")

    core = {
        "schema": "mark_state_operator_discovery_v1",
        "experimentId": protocol["experimentId"],
        "phase": "blind_state2_latent_alias_breaker",
        "parentLocalStateFieldDiscoverySha256": field["localStateFieldDiscoverySha256"],
        "parentStateTransitionGrammarDiscoverySha256": transition["stateTransitionGrammarDiscoverySha256"],
        "physicalLedgerMerkleRoot": compatibility["physicalLedgerMerkleRoot"],
        "provenanceAvailableDuringDiscovery": False,
        "state2LatentAliasDefinitionSha256": cluster_sha,
        "state2AliasExitAssociationSha256": association_sha,
        "latentAliasDefinition": cluster_packet,
        "exitAssociation": association,
        "compatibility": compatibility,
        "primaryQuestion": "Does frozen State 2 contain multiple label-free physical topology aliases whose already-frozen definitions associate differently with later 2->1, 2->2 and 2->3 containment exits?",
        "primaryFalsifier": "If blind State 2 topology does not form stable train-discovered aliases, or frozen aliases do not carry exit information into holdout/control beyond the stratified null, State 2 should remain one context-dependent state at this resolution.",
        "contract": {
            "clusterDefinitionFrozenBeforeChildOutcomeReveal": True,
            "childOutcomeCannotChangeSelectedFeaturesKCentroidsOrAssignments": True,
            "allFrozenPrimaryStateRowsMustMatchTopologyIdentity": True,
            "extraFullWorldTopologyRowsDoNotMasqueradeAsStateRows": True,
            "provenanceUnavailableUntilOperatorSha": True,
            "semanticMeaningNotAssigned": True,
        },
    }
    digest = canonical_sha(core)
    packet = {**core, "stateOperatorDiscoverySha256": digest}
    (out_dir / "state-operator-discovery.json").write_text(json.dumps(packet, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    lines = [
        f"state_operator_discovery_sha256={digest}",
        f"state2_latent_alias_definition_sha256={cluster_sha}",
        f"state2_alias_exit_association_sha256={association_sha}",
        f"topology_observations={compatibility['topologyObservations']}",
        f"frozen_local_state_observations={compatibility['frozenLocalStateObservations']}",
        f"state2_containment_edges={len(edges)}",
        f"chosen_k={cluster_packet['latentClusters']['chosenK']}",
        f"sampled_train_silhouette={cluster_packet['latentClusters']['sampledTrainSilhouette']:.9f}",
    ]
    for lane in lane_ids:
        bc = branch_counts[lane]
        lines.append(f"{lane}_branch_counts=1:{bc.get('1',0)},2:{bc.get('2',0)},3:{bc.get('3',0)}")
        lines.append(
            f"{lane}_three_way_normalized_information_gain={observed[lane]['threeWay']['normalizedInformationGain']:.9f};null_mean={nulls[lane]['threeWay']['nullMean']:.9f};beats_all_nulls={str(nulls[lane]['threeWay']['beatsAllNulls']).lower()}"
        )
        lines.append(
            f"{lane}_stay_exit_normalized_information_gain={observed[lane]['stayVsExit']['normalizedInformationGain']:.9f};null_mean={nulls[lane]['stayVsExit']['nullMean']:.9f};beats_all_nulls={str(nulls[lane]['stayVsExit']['beatsAllNulls']).lower()}"
        )
        lines.append(
            f"{lane}_exit_direction_normalized_information_gain={observed[lane]['exitDirection']['normalizedInformationGain']:.9f};null_mean={nulls[lane]['exitDirection']['nullMean']:.9f};beats_all_nulls={str(nulls[lane]['exitDirection']['beatsAllNulls']).lower()}"
        )
    lines.extend(
        [
            "child_outcome_labels_revealed_only_after_alias_freeze=true",
            "provenance_available_during_discovery=false",
        ]
    )
    (out_dir / "summary.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(packet, indent=2, ensure_ascii=False))


def main():
    protocol, field, transition, _topo_summary, states, topology, compatibility = load_inputs()
    if phase in ("cluster", "all"):
        fit_cluster_phase(protocol, field, transition, topology, states, compatibility)
    if phase in ("reveal", "all"):
        reveal_phase(protocol, field, transition, states, compatibility)
    if phase not in ("cluster", "reveal", "all"):
        raise RuntimeError(f"unknown MARK_OPERATOR_PHASE {phase!r}")


if __name__ == "__main__":
    main()
