#!/usr/bin/env python3
import hashlib
import json
import math
import os
from collections import Counter, defaultdict
from pathlib import Path

protocol_path = Path(os.environ.get("MARK_MASKED_SLOT_PROTOCOL", "research/mark/discovery-experiments/masked-slot-substitution-v1.protocol.json"))
topology_dir = Path(os.environ.get("MARK_TOPOLOGY_ATLAS", "artifacts/mark-observation-topology-atlas-v1"))
parent_atlas_dir = Path(os.environ.get("MARK_PARENT_ATLAS", "artifact-staging/parent-atlas"))
out_dir = Path(os.environ.get("MARK_MASKED_SLOT_VOCAB_OUT", "artifacts/mark-masked-slot-vocabulary-v1"))

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
    return math.sqrt(sum((x-y)**2 for x, y in zip(a, b)))

def area(r):
    return max(1, int(r["width"]) * int(r["height"]))

def center(r):
    return (float(r["x"]) + float(r["width"]) / 2.0, float(r["y"]) + float(r["height"]) / 2.0)

def contains(parent, child):
    return (
        area(parent) > area(child)
        and parent["x"] <= child["x"]
        and parent["y"] <= child["y"]
        and parent["x"] + parent["width"] >= child["x"] + child["width"]
        and parent["y"] + parent["height"] >= child["y"] + child["height"]
    )

def overlap_area(a, b):
    x0 = max(a["x"], b["x"])
    y0 = max(a["y"], b["y"])
    x1 = min(a["x"] + a["width"], b["x"] + b["width"])
    y1 = min(a["y"] + a["height"], b["y"] + b["height"])
    return max(0, x1 - x0) * max(0, y1 - y0)

def kmeans(points, ids, k, max_iter=100):
    if k >= len(points):
        return None
    global_mean = [mean([p[d] for p in points]) for d in range(len(points[0]))]
    first = max(range(len(points)), key=lambda i: (distance(points[i], global_mean), ids[i]))
    chosen = [first]
    while len(chosen) < k:
        remaining = [i for i in range(len(points)) if i not in chosen]
        idx = max(remaining, key=lambda i: (min(distance(points[i], points[j]) for j in chosen), ids[i]))
        chosen.append(idx)
    cents = [list(points[i]) for i in chosen]
    assignments = None
    for _ in range(max_iter):
        new = [min(range(k), key=lambda j: (distance(p, cents[j]), j)) for p in points]
        if new == assignments:
            break
        assignments = new
        next_cents = []
        for j in range(k):
            members = [points[i] for i, a in enumerate(assignments) if a == j]
            if not members:
                return None
            next_cents.append([mean([row[d] for row in members]) for d in range(len(points[0]))])
        cents = next_cents
    return assignments, cents

def sampled_silhouette(points, assignments, k, ids, limit):
    order = sorted(range(len(ids)), key=lambda i: hashlib.sha256(ids[i].encode("utf-8")).hexdigest())[:min(limit, len(ids))]
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
        scores.append((b-a)/denom if denom else 0.0)
    return mean(scores)

def normalized_topology(row):
    centers = max(1, int(row["centerCount"]))
    out = {k: float(v) / centers for k, v in row["countFeatures"].items()}
    out["derived:centerDensityPerMillionPixelsLog1p"] = math.log1p(float(row["centerCount"]) * 1_000_000.0 / area(row["region"]))
    return out

def select_features(value_maps, minimum_support, maximum_features):
    support = Counter()
    variability = {}
    keys = set()
    for values in value_maps.values():
        keys.update(values.keys())
        for key, value in values.items():
            if abs(value) > 1e-15:
                support[key] += 1
    for key in keys:
        xs = [values.get(key, 0.0) for values in value_maps.values()]
        variability[key] = stdev(xs)
    eligible = [k for k in keys if support[k] >= minimum_support and variability[k] > 1e-12]
    eligible.sort(key=lambda k: (-support[k], -variability[k], k))
    return eligible[:maximum_features], support, variability

def standardization(ids, values_by_id, features):
    stats = {}
    for feature in features:
        xs = [values_by_id[oid].get(feature, 0.0) for oid in ids]
        sd = stdev(xs)
        stats[feature] = {"mean": mean(xs), "sd": sd if sd > 1e-12 else 1.0}
    return stats

def vector(values, features, stats):
    return [(values.get(f, 0.0) - stats[f]["mean"]) / stats[f]["sd"] for f in features]

def choose_clustering(ids, vectors, sources, candidate_k, min_observations, min_sources, sample_limit):
    points = [vectors[oid] for oid in ids]
    candidates = []
    for k in candidate_k:
        result = kmeans(points, ids, int(k))
        if result is None:
            continue
        assignments, cents = result
        sizes = [assignments.count(j) for j in range(int(k))]
        source_support = []
        for j in range(int(k)):
            source_support.append(len({sources[ids[i]] for i, a in enumerate(assignments) if a == j}))
        if min(sizes) < min_observations or min(source_support) < min_sources:
            continue
        score = sampled_silhouette(points, assignments, int(k), ids, sample_limit)
        candidates.append({
            "k": int(k),
            "score": score,
            "assignments": assignments,
            "centroids": cents,
            "sizes": sizes,
            "sourceSupport": source_support,
        })
    if not candidates:
        raise RuntimeError("no valid clustering solution under masked-slot protocol support gates")
    return max(candidates, key=lambda row: (row["score"], -row["k"])), candidates

def stable_family_remap(centroids):
    order = sorted(range(len(centroids)), key=lambda j: (tuple(round(x, 12) for x in centroids[j]), j))
    return {old: new + 1 for new, old in enumerate(order)}

protocol = load_json(protocol_path)
if protocol.get("schema") != "mark_masked_slot_substitution_protocol_v1":
    raise RuntimeError("unexpected masked-slot protocol")

topo_summary = load_json(topology_dir / "summary.json")
parent_custody = load_json(parent_atlas_dir / "compiler" / "custody.json")
if topo_summary.get("schema") != "mark_observation_topology_atlas_summary_v1":
    raise RuntimeError("unexpected topology atlas")
if topo_summary.get("physicalLedgerMerkleRoot") != parent_custody["physicalLedger"]["merkleRoot"]:
    raise RuntimeError("topology/parent physical ledger mismatch")
if topo_summary.get("sourceBlindInputSha256") != parent_custody["sourceBlindInputSha256"]:
    raise RuntimeError("topology/parent blind-input hash mismatch")
if not topo_summary.get("contract", {}).get("noProvenanceConsumed"):
    raise RuntimeError("topology atlas consumed provenance")

rows = {}
with (topology_dir / "observation-topology-atlas.jsonl").open(encoding="utf-8") as handle:
    for line in handle:
        if not line.strip():
            continue
        row = json.loads(line)
        oid = row["observationId"]
        if oid in rows:
            raise RuntimeError(f"duplicate observation {oid}")
        rows[oid] = row
if len(rows) != int(topo_summary["observations"]):
    raise RuntimeError("topology row count differs from summary")

by_source = defaultdict(list)
for row in rows.values():
    by_source[row["sourceGroupId"]].append(row)

parent = {}
for source, items in by_source.items():
    for child in items:
        candidates = [
            p for p in items
            if p["observationId"] != child["observationId"] and contains(p["region"], child["region"])
        ]
        if candidates:
            p = min(candidates, key=lambda r: (area(r["region"]), r["observationId"]))
            parent[child["observationId"]] = p["observationId"]

children = defaultdict(list)
for child_id, parent_id in parent.items():
    children[parent_id].append(child_id)
for parent_id in children:
    children[parent_id].sort()

norm = {oid: normalized_topology(row) for oid, row in rows.items()}

candidate_ids = sorted(parent)
if not candidate_ids:
    raise RuntimeError("no maskable contained observations")

sources = {oid: rows[oid]["sourceGroupId"] for oid in candidate_ids}
lanes = {oid: rows[oid]["lane"] for oid in candidate_ids}
train_ids = [oid for oid in candidate_ids if lanes[oid] == "train"]
if len(train_ids) < 100:
    raise RuntimeError("too few train observations for masked-slot discovery")

# Slot context is deliberately built without the target's topology, without any ancestor topology,
# and without topology from any sibling whose region overlaps the target region.
base_context = {}
sibling_value_maps = {}
disjoint_sibling_counts = {}
for oid in candidate_ids:
    target = rows[oid]
    parent_id = parent[oid]
    p = rows[parent_id]
    tr, pr = target["region"], p["region"]
    tc, pc = center(tr), center(pr)
    values = {
        "slot:logAreaRatio": math.log(area(tr) / area(pr)),
        "slot:dxParentWidth": (tc[0] - pc[0]) / max(1.0, float(pr["width"])),
        "slot:dyParentHeight": (tc[1] - pc[1]) / max(1.0, float(pr["height"])),
        "slot:aspectDelta": math.log(
            (float(tr["width"]) / max(1.0, float(tr["height"]))) /
            (float(pr["width"]) / max(1.0, float(pr["height"])))
        ),
    }
    grand_id = parent.get(parent_id)
    values["slot:hasGrandparent"] = 1.0 if grand_id else 0.0
    if grand_id:
        gr = rows[grand_id]["region"]
        gc = center(gr)
        values.update({
            "slot:parentLogAreaRatioToGrandparent": math.log(area(pr) / area(gr)),
            "slot:parentDxGrandparentWidth": (pc[0] - gc[0]) / max(1.0, float(gr["width"])),
            "slot:parentDyGrandparentHeight": (pc[1] - gc[1]) / max(1.0, float(gr["height"])),
        })
    else:
        values.update({
            "slot:parentLogAreaRatioToGrandparent": 0.0,
            "slot:parentDxGrandparentWidth": 0.0,
            "slot:parentDyGrandparentHeight": 0.0,
        })

    disjoint = []
    for sib_id in children[parent_id]:
        if sib_id == oid:
            continue
        if overlap_area(tr, rows[sib_id]["region"]) == 0:
            disjoint.append(sib_id)
    disjoint_sibling_counts[oid] = len(disjoint)
    values["slot:disjointSiblingCountLog1p"] = math.log1p(len(disjoint))
    values["slot:hasDisjointSibling"] = 1.0 if disjoint else 0.0
    if disjoint:
        rel_areas = [area(rows[s]["region"]) / area(pr) for s in disjoint]
        values["slot:meanDisjointSiblingAreaFraction"] = mean(rel_areas)
        values["slot:maxDisjointSiblingAreaFraction"] = max(rel_areas)
    else:
        values["slot:meanDisjointSiblingAreaFraction"] = 0.0
        values["slot:maxDisjointSiblingAreaFraction"] = 0.0

    agg = defaultdict(list)
    for sib_id in disjoint:
        for key, value in norm[sib_id].items():
            agg[key].append(value)
    sibling_value_maps[oid] = {f"siblingMean:{k}": mean(vs) for k, vs in agg.items()}
    base_context[oid] = values

train_sibling_maps = {oid: sibling_value_maps[oid] for oid in train_ids}
sib_cfg = protocol["slotDiscovery"]["disjointSiblingTopology"]
selected_sibling_features, sibling_support, sibling_variability = select_features(
    train_sibling_maps,
    int(sib_cfg["minimumTrainTargetSupport"]),
    int(sib_cfg["maximumFeatures"]),
)

context_values = {}
for oid in candidate_ids:
    values = dict(base_context[oid])
    for feature in selected_sibling_features:
        values[feature] = sibling_value_maps[oid].get(feature, 0.0)
    context_values[oid] = values

base_context_features = sorted(base_context[train_ids[0]].keys())
context_features = base_context_features + selected_sibling_features
context_stats = standardization(train_ids, context_values, context_features)
context_vectors = {oid: vector(context_values[oid], context_features, context_stats) for oid in candidate_ids}

occ_cfg = protocol["occupantDiscovery"]
train_occupant_maps = {oid: norm[oid] for oid in train_ids}
occupant_features, occupant_support, occupant_variability = select_features(
    train_occupant_maps,
    int(occ_cfg["minimumTrainObservationSupport"]),
    int(occ_cfg["maximumFeatures"]),
)
if not occupant_features:
    raise RuntimeError("no eligible occupant topology features")
occupant_stats = standardization(train_ids, norm, occupant_features)
occupant_vectors = {oid: vector(norm[oid], occupant_features, occupant_stats) for oid in candidate_ids}

cluster_cfg = protocol["clustering"]
slot_best, slot_candidates = choose_clustering(
    train_ids, context_vectors, sources,
    cluster_cfg["slotCandidateK"],
    int(cluster_cfg["minimumClusterObservations"]),
    int(cluster_cfg["minimumClusterDistinctSources"]),
    int(cluster_cfg["silhouetteSampleLimit"]),
)
occupant_best, occupant_candidates = choose_clustering(
    train_ids, occupant_vectors, sources,
    cluster_cfg["occupantCandidateK"],
    int(cluster_cfg["minimumClusterObservations"]),
    int(cluster_cfg["minimumClusterDistinctSources"]),
    int(cluster_cfg["silhouetteSampleLimit"]),
)

slot_remap = stable_family_remap(slot_best["centroids"])
occ_remap = stable_family_remap(occupant_best["centroids"])
slot_centroids = {slot_remap[j]: slot_best["centroids"][j] for j in range(slot_best["k"])}
occ_centroids = {occ_remap[j]: occupant_best["centroids"][j] for j in range(occupant_best["k"])}

def assign(vec, centroids):
    return min(centroids, key=lambda family: (distance(vec, centroids[family]), family))

slot_assignment = {oid: assign(context_vectors[oid], slot_centroids) for oid in candidate_ids}
occupant_assignment = {oid: assign(occupant_vectors[oid], occ_centroids) for oid in candidate_ids}

def candidate_summary(candidates):
    return [
        {
            "k": row["k"],
            "sampledSilhouette": row["score"],
            "clusterSizes": row["sizes"],
            "clusterDistinctSourceSupport": row["sourceSupport"],
        }
        for row in sorted(candidates, key=lambda x: x["k"])
    ]

out_dir.mkdir(parents=True, exist_ok=True)
slot_path = out_dir / "slot-assignments.jsonl"
occ_path = out_dir / "occupant-assignments.jsonl"

slot_hasher = hashlib.sha256()
with slot_path.open("wb") as handle:
    for oid in candidate_ids:
        row = rows[oid]
        payload = {
            "schema": "mark_masked_slot_assignment_v1",
            "observationId": oid,
            "sourceGroupId": row["sourceGroupId"],
            "lane": row["lane"],
            "slotFamily": slot_assignment[oid],
            "parentObservationId": parent[oid],
            "proposalScale": row.get("proposalScale", ""),
            "region": row["region"],
            "disjointSiblingCount": disjoint_sibling_counts[oid],
        }
        b = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8") + b"\n"
        handle.write(b)
        slot_hasher.update(b)

occ_hasher = hashlib.sha256()
with occ_path.open("wb") as handle:
    for oid in candidate_ids:
        row = rows[oid]
        payload = {
            "schema": "mark_masked_occupant_assignment_v1",
            "observationId": oid,
            "sourceGroupId": row["sourceGroupId"],
            "lane": row["lane"],
            "occupantFamily": occupant_assignment[oid],
        }
        b = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8") + b"\n"
        handle.write(b)
        occ_hasher.update(b)

slot_sizes = {str(f): sum(slot_assignment[oid] == f for oid in train_ids) for f in sorted(slot_centroids)}
slot_sources = {str(f): len({sources[oid] for oid in train_ids if slot_assignment[oid] == f}) for f in sorted(slot_centroids)}
occ_sizes = {str(f): sum(occupant_assignment[oid] == f for oid in train_ids) for f in sorted(occ_centroids)}
occ_sources = {str(f): len({sources[oid] for oid in train_ids if occupant_assignment[oid] == f}) for f in sorted(occ_centroids)}

core = {
    "schema": "mark_masked_slot_vocabulary_v1",
    "experimentId": protocol["experimentId"],
    "physicalLedgerMerkleRoot": topo_summary["physicalLedgerMerkleRoot"],
    "sourceBlindInputSha256": topo_summary["sourceBlindInputSha256"],
    "topologyRowsSha256": topo_summary["rowsSha256"],
    "provenanceAvailableDuringDiscovery": False,
    "maskableObservations": len(candidate_ids),
    "trainMaskableObservations": len(train_ids),
    "slotVocabulary": {
        "features": context_features,
        "trainStandardization": context_stats,
        "chosenK": slot_best["k"],
        "centroids": {str(k): v for k, v in sorted(slot_centroids.items())},
        "trainFamilySizes": slot_sizes,
        "trainFamilyDistinctSourceSupport": slot_sources,
        "candidateSolutions": candidate_summary(slot_candidates),
        "selectedDisjointSiblingTopologyFeatures": selected_sibling_features,
    },
    "occupantVocabulary": {
        "features": occupant_features,
        "trainStandardization": occupant_stats,
        "chosenK": occupant_best["k"],
        "centroids": {str(k): v for k, v in sorted(occ_centroids.items())},
        "trainFamilySizes": occ_sizes,
        "trainFamilyDistinctSourceSupport": occ_sources,
        "candidateSolutions": candidate_summary(occupant_candidates),
    },
    "assignmentFiles": {
        "slotAssignmentsSha256": slot_hasher.hexdigest(),
        "occupantAssignmentsSha256": occ_hasher.hexdigest(),
    },
    "contract": {
        "slotFamiliesDiscoveredOnTrainOnly": True,
        "occupantFamiliesDiscoveredOnTrainOnly": True,
        "holdoutAndControlAssignedWithoutRefit": True,
        "targetTopologyUnavailableToSlotDefinition": True,
        "parentAndAncestorTopologyUnavailableToSlotDefinition": True,
        "overlappingSiblingTopologyUnavailableToSlotDefinition": True,
        "onlyDisjointSiblingTopologyMayDescribeNeighborOccupants": True,
        "slotAndOccupantVocabulariesFrozenBeforeTheirAssociationIsComputed": True,
        "noLocalStateIdsConsumed": True,
        "noTransitionGrammarConsumed": True,
        "noProvenanceConsumed": True,
    },
}
digest = canonical_sha(core)
packet = {**core, "maskedSlotVocabularySha256": digest}
(out_dir / "masked-slot-vocabulary.json").write_text(json.dumps(packet, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
(out_dir / "summary.txt").write_text("\n".join([
    f"masked_slot_vocabulary_sha256={digest}",
    f"maskable_observations={len(candidate_ids)}",
    f"train_maskable_observations={len(train_ids)}",
    f"slot_families={slot_best['k']}",
    f"occupant_families={occupant_best['k']}",
    f"slot_silhouette={slot_best['score']:.6f}",
    f"occupant_silhouette={occupant_best['score']:.6f}",
    "target_topology_available_to_slot_definition=false",
    "state_vocabulary_consumed=false",
]) + "\n", encoding="utf-8")
print(json.dumps(packet, indent=2, ensure_ascii=False))
