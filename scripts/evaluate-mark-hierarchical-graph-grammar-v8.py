#!/usr/bin/env python3
import functools
import hashlib
import json
import math
import os
import pickle
import statistics
import tempfile
from collections import defaultdict
from pathlib import Path

from scipy.spatial import cKDTree

from mark_graph_compression_v8_core import (
    canonical_sha,
    sha256_file,
    build_primitive_graph,
    clone_graph,
    graph_bits,
    apply_grammar,
    levenshtein_normalized,
    balanced_effect,
    add_null,
)

protocol_path = Path(os.environ.get(
    "MARK_COMPRESSION_PROTOCOL",
    "research/mark/discovery-experiments/hierarchical-graph-compression-v8.protocol.json",
))
v5_dir = Path(os.environ.get("MARK_V5_PACKET", "artifact-staging/v5"))
grammar_dir = Path(os.environ.get("MARK_COMPRESSION_GRAMMAR", "artifacts/mark-hierarchical-graph-compression-v8/grammar"))
out_dir = Path(os.environ.get("MARK_COMPRESSION_OUT", "artifacts/mark-hierarchical-graph-compression-v8/result"))


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def locate(root, name):
    hits = list(Path(root).rglob(name))
    if len(hits) != 1:
        raise RuntimeError(f"expected one {name} under {root}, found {len(hits)}")
    return hits[0]


def transform_point(u, v, name):
    if name == "IDENTITY": return u, v
    if name == "ROT90": return 1 - v, u
    if name == "ROT180": return 1 - u, 1 - v
    if name == "ROT270": return v, 1 - u
    if name == "MIRROR_X": return 1 - u, v
    if name == "MIRROR_Y": return u, 1 - v
    if name == "MIRROR_DIAGONAL": return v, u
    if name == "MIRROR_ANTIDIAGONAL": return 1 - v, 1 - u
    raise RuntimeError(name)


TRANSFORMS = [
    "IDENTITY", "ROT90", "ROT180", "ROT270",
    "MIRROR_X", "MIRROR_Y", "MIRROR_DIAGONAL", "MIRROR_ANTIDIAGONAL",
]


def normalized_points(rows, region, transform):
    w = max(1.0, float(region["width"]))
    h = max(1.0, float(region["height"]))
    x0 = float(region["x"])
    y0 = float(region["y"])
    return [
        transform_point((float(c["x"]) - x0) / w, (float(c["y"]) - y0) / h, transform)
        for c in rows
    ]


def symmetric_distance(a, b, ra, rb, transform):
    if not a or not b:
        return None
    A = normalized_points(a, ra, transform)
    B = normalized_points(b, rb, "IDENTITY")
    ta, tb = cKDTree(A), cKDTree(B)
    dab = tb.query(A, k=1, workers=1)[0]
    dba = ta.query(B, k=1, workers=1)[0]
    return (float(dab.sum()) + float(dba.sum())) / (len(A) + len(B))


def sparse_match(a, b, ra, rb, transform, kcand):
    if not a or not b:
        return []
    A = normalized_points(a, ra, transform)
    B = normalized_points(b, rb, "IDENTITY")
    swapped = False
    left, right = A, B
    if len(left) > len(right):
        left, right = right, left
        swapped = True
    k = max(1, min(int(kcand), len(right)))
    tree = cKDTree(right)
    dists, idxs = tree.query(left, k=k, workers=1)
    if k == 1:
        dists = [[float(x)] for x in dists]
        idxs = [[int(x)] for x in idxs]
    candidates = []
    for i in range(len(left)):
        for q in range(k):
            candidates.append((float(dists[i][q]), i, int(idxs[i][q])))
    candidates.sort(key=lambda x: (x[0], x[1], x[2]))
    used_l, used_r, pairs = set(), set(), []
    for distance, i, j in candidates:
        if i in used_l or j in used_r:
            continue
        used_l.add(i)
        used_r.add(j)
        pairs.append((j, i, distance) if swapped else (i, j, distance))
    return pairs


def center_mapping(A, B, kcand):
    by_a, by_b = defaultdict(list), defaultdict(list)
    for center in A["centers"]:
        by_a[center["kind"]].append(center)
    for center in B["centers"]:
        by_b[center["kind"]].append(center)
    scored = []
    for order, transform in enumerate(TRANSFORMS):
        numerator = 0.0
        denominator = 0
        for kind in ("ENDPOINT", "JUNCTION"):
            distance = symmetric_distance(by_a[kind], by_b[kind], A["region"], B["region"], transform)
            if distance is not None:
                weight = len(by_a[kind]) + len(by_b[kind])
                numerator += distance * weight
                denominator += weight
        scored.append((float("inf") if denominator == 0 else numerator / denominator, order, transform))
    best = min(scored)[2]
    mapping = {}
    for kind in ("ENDPOINT", "JUNCTION"):
        aa, bb = by_a[kind], by_b[kind]
        for ia, ib, _ in sparse_match(aa, bb, A["region"], B["region"], best, kcand):
            mapping[aa[ia]["eventId"]] = bb[ib]["eventId"]
    return mapping, best


def evaluate_observation(row, grammar_packet):
    record = {
        "observationId": row["observationId"],
        "sourceGroupId": row["sourceGroupId"],
        "lane": row["lane"],
        "variants": {},
    }
    cache = {
        "region": row["region"],
        "centers": [
            {"eventId": c["eventId"], "kind": c["kind"], "x": c["x"], "y": c["y"]}
            for c in row["centers"]
        ],
        "ancestry": {},
    }
    for variant in ("lengthAware", "topology"):
        base = build_primitive_graph(row, variant, track_members=True)
        raw_bits = graph_bits(base)
        cache["ancestry"][variant] = {}
        model_record = {"rawBits": raw_bits}
        for model_name in ("flat", "hierarchical"):
            graph = clone_graph(base, track_members=True)
            grammar = grammar_packet["models"][variant][model_name]
            result = apply_grammar(graph, grammar, track_members=True)
            model_record[f"{model_name}Bits"] = result["dataBits"]
            model_record[f"{model_name}RuleUses"] = result["ruleUses"]
            model_record[f"{model_name}ResidualNodes"] = result["residualNodes"]
            model_record[f"{model_name}ResidualEdges"] = result["residualEdges"]
            cache["ancestry"][variant][model_name] = result["ancestry"]
        record["variants"][variant] = model_record
    return record, cache


def aggregate_compression(rows, grammar_packet, variant):
    lanes = {}
    for lane in sorted({row["lane"] for row in rows}):
        lane_rows = [row for row in rows if row["lane"] == lane]
        raw = sum(row["variants"][variant]["rawBits"] for row in lane_rows)
        flat = sum(row["variants"][variant]["flatBits"] for row in lane_rows)
        hier = sum(row["variants"][variant]["hierarchicalBits"] for row in lane_rows)
        by_source = defaultdict(lambda: {"raw": 0, "flat": 0, "hierarchical": 0})
        for row in lane_rows:
            source = row["sourceGroupId"]
            by_source[source]["raw"] += row["variants"][variant]["rawBits"]
            by_source[source]["flat"] += row["variants"][variant]["flatBits"]
            by_source[source]["hierarchical"] += row["variants"][variant]["hierarchicalBits"]
        source_wins = sum(v["hierarchical"] < v["flat"] for v in by_source.values())
        lanes[lane] = {
            "observations": len(lane_rows),
            "sourceGroups": len(by_source),
            "rawDataBits": raw,
            "flatDataBits": flat,
            "hierarchicalDataBits": hier,
            "flatVsRawReductionFraction": 0.0 if raw == 0 else 1.0 - flat / raw,
            "hierarchicalVsRawReductionFraction": 0.0 if raw == 0 else 1.0 - hier / raw,
            "hierarchicalVsFlatReductionFraction": 0.0 if flat == 0 else 1.0 - hier / flat,
            "sourceGroupsHierarchicalBeatsFlat": source_wins,
            "sourceGroupHierarchicalBeatFraction": 0.0 if not by_source else source_wins / len(by_source),
            "sourceGroupTotals": dict(sorted(by_source.items())),
        }
    train_flat = grammar_packet["models"][variant]["flat"]
    train_hier = grammar_packet["models"][variant]["hierarchical"]
    if "train" in lanes:
        if lanes["train"]["flatDataBits"] != int(train_flat["trainDataBits"]):
            raise RuntimeError(f"frozen flat grammar replay drift for {variant}")
        if lanes["train"]["hierarchicalDataBits"] != int(train_hier["trainDataBits"]):
            raise RuntimeError(f"frozen hierarchical grammar replay drift for {variant}")
        if lanes["train"]["rawDataBits"] != int(train_flat["rawDataBits"]):
            raise RuntimeError(f"raw training code replay drift for {variant}")
    return {
        "lanes": lanes,
        "trainFlatModelBits": int(train_flat["modelBits"]),
        "trainHierarchicalModelBits": int(train_hier["modelBits"]),
        "trainFlatTotalBits": int(train_flat["trainTotalBits"]),
        "trainHierarchicalTotalBits": int(train_hier["trainTotalBits"]),
        "rawTrainTotalBits": int(grammar_packet["rawTrainTotalBits"][variant]),
    }


def pair_metrics(pair, A, B, kcand):
    mapping, transform = center_mapping(A, B, kcand)
    if not mapping:
        return None
    features = {}
    for variant in ("lengthAware", "topology"):
        for model_name in ("flat", "hierarchical"):
            values = []
            aa = A["ancestry"][variant][model_name]
            bb = B["ancestry"][variant][model_name]
            for aid, bid in mapping.items():
                values.append(levenshtein_normalized(aa.get(aid, []), bb.get(bid, [])))
            features[f"{variant}{model_name.title()}AncestryMutation"] = statistics.mean(values) if values else None
    return {
        "pairId": f"{pair['observationA']}::{pair['observationB']}",
        "observationA": pair["observationA"],
        "observationB": pair["observationB"],
        "lane": pair["lane"],
        "label": pair["label"],
        "occupantFamilyA": pair["occupantFamilyA"],
        "occupantFamilyB": pair["occupantFamilyB"],
        "mappedCenters": len(mapping),
        "bestD4Transform": transform,
        **features,
    }


def compression_gate(compression, variant, holdout_lane, min_source_fraction):
    lane = compression[variant]["lanes"].get(holdout_lane)
    if not lane:
        return {"pass": False, "reason": "missing_holdout_lane"}
    c1 = lane["hierarchicalDataBits"] < lane["flatDataBits"]
    c2 = lane["sourceGroupHierarchicalBeatFraction"] >= min_source_fraction
    c3 = compression[variant]["trainHierarchicalTotalBits"] < compression[variant]["trainFlatTotalBits"]
    return {
        "pass": bool(c1 and c2 and c3),
        "aggregateHeldoutHierarchicalBeatsFlat": c1,
        "heldoutSourceGroupBeatFraction": lane["sourceGroupHierarchicalBeatFraction"],
        "heldoutSourceGroupThreshold": min_source_fraction,
        "trainingTotalHierarchicalBeatsFlat": c3,
    }


def role_gate(role_results, variant, practical, null_max, holdout_min):
    feature = f"{variant}HierarchicalAncestryMutation"
    train = role_results["train"][feature]
    holdout = role_results.get("holdout", {}).get(feature)
    train_effect = train["balancedEffect"]
    null = train.get("null")
    train_pass = bool(
        train_effect is not None and train_effect >= practical and null is not None
        and null["absoluteNullAtLeastObserved"] <= null_max
    )
    holdout_effect = None if not holdout else holdout["balancedEffect"]
    holdout_pass = bool(holdout_effect is not None and holdout_effect >= holdout_min)
    return {
        "pass": bool(train_pass and holdout_pass),
        "feature": feature,
        "trainPass": train_pass,
        "holdoutPass": holdout_pass,
        "trainEffect": train_effect,
        "holdoutEffect": holdout_effect,
        "trainNullAbsoluteAtLeastObserved": None if null is None else null["absoluteNullAtLeastObserved"],
    }


protocol = load_json(protocol_path)
if protocol.get("schema") != "mark_hierarchical_graph_compression_protocol_v8":
    raise RuntimeError("unexpected V8 protocol")
parent = protocol["parentV5"]
role_cfg = protocol["roleSpecificity"]

manifest = load_json(locate(v5_dir, "edge-pair-manifest.json"))
world = load_json(locate(v5_dir, "critical-edge-world.json"))
projector_path = locate(v5_dir, "critical-edge-observations.jsonl")
grammar_path = locate(grammar_dir, "hierarchical-graph-grammar-freeze.json")
grammar_packet = load_json(grammar_path)

manifest_sha = manifest.get("edgePairManifestSha256")
world_sha = world.get("criticalEdgeWorldSha256")
if canonical_sha({k: v for k, v in manifest.items() if k != "edgePairManifestSha256"}) != manifest_sha:
    raise RuntimeError("V5 edge pair manifest SHA mismatch")
if canonical_sha({k: v for k, v in world.items() if k != "criticalEdgeWorldSha256"}) != world_sha:
    raise RuntimeError("V5 critical edge world SHA mismatch")
if manifest_sha != parent["expectedEdgePairManifestSha256"] or world_sha != parent["expectedCriticalEdgeWorldSha256"]:
    raise RuntimeError("wrong frozen V5 parent")
if sha256_file(projector_path) != world["projectorRowsSha256"]:
    raise RuntimeError("V5 projector row hash mismatch")
if grammar_packet.get("schema") != "mark_hierarchical_graph_grammar_freeze_v8":
    raise RuntimeError("wrong V8 grammar packet schema")
freeze_digest = grammar_packet.get("grammarFreezeSha256")
if canonical_sha({k: v for k, v in grammar_packet.items() if k != "grammarFreezeSha256"}) != freeze_digest:
    raise RuntimeError("V8 grammar freeze hash mismatch")
if grammar_packet["parentProjectorRowsSha256"] != world["projectorRowsSha256"]:
    raise RuntimeError("grammar packet parent drift")
if grammar_packet.get("roleLabelsOpenedDuringInduction") is not False:
    raise RuntimeError("grammar induction label custody failed")

# Only after the grammar packet is present, hashed, and verified do we locate/open role labels.
role_pair_path = locate(v5_dir, "role-pair-labels.jsonl")
role_bytes = role_pair_path.read_bytes()
if hashlib.sha256(role_bytes).hexdigest() != manifest["parentRolePairRowsSha256"]:
    raise RuntimeError("V5 role-pair row hash mismatch")
if grammar_packet["parentRolePairRowsSha256ExpectedButNotOpened"] != manifest["parentRolePairRowsSha256"]:
    raise RuntimeError("grammar freeze expected role-row hash drift")
pairs = [json.loads(raw) for raw in role_bytes.splitlines() if raw.strip()]
eligible = set(world["pairEligibleObservationIds"])
pairs = [p for p in pairs if p["observationA"] in eligible and p["observationB"] in eligible]
needed = {p["observationA"] for p in pairs} | {p["observationB"] for p in pairs}

cache_root = Path(tempfile.mkdtemp(prefix="mark-v8-observation-cache-"))
observation_rows = []
seen = set()
with projector_path.open("r", encoding="utf-8") as handle:
    for line_no, raw in enumerate(handle, 1):
        if not raw.strip():
            continue
        row = json.loads(raw)
        oid = row["observationId"]
        if oid not in needed:
            continue
        compression_record, cache = evaluate_observation(row, grammar_packet)
        observation_rows.append(compression_record)
        with (cache_root / f"{oid}.pkl").open("wb") as out:
            pickle.dump(cache, out, protocol=pickle.HIGHEST_PROTOCOL)
        seen.add(oid)
        if len(seen) % 25 == 0:
            print(f"evaluated_observations={len(seen)}/{len(needed)} line={line_no}")
if seen != needed:
    missing = sorted(needed - seen)
    raise RuntimeError(f"missing V5 observations for V8: {missing[:8]}")

compression = {
    variant: aggregate_compression(observation_rows, grammar_packet, variant)
    for variant in ("lengthAware", "topology")
}

@functools.lru_cache(maxsize=8)
def load_cache(oid):
    with (cache_root / f"{oid}.pkl").open("rb") as handle:
        return pickle.load(handle)

kcand = int(parent["greedyNearestCandidatesPerCenter"])
pair_rows = []
for index, pair in enumerate(pairs, 1):
    result = pair_metrics(pair, load_cache(pair["observationA"]), load_cache(pair["observationB"]), kcand)
    if result is not None:
        pair_rows.append(result)
    if index % 50 == 0:
        print(f"role_pairs_analyzed={index}/{len(pairs)} retained={len(pair_rows)}")

train_rows = [row for row in pair_rows if row["lane"] == "train"]
if len(train_rows) < 50:
    raise RuntimeError(f"insufficient Cleveland pair support: {len(train_rows)}")
if len(train_rows) != int(parent["expectedEligibleTrainPairs"]):
    raise RuntimeError(f"eligible Cleveland pair drift: {len(train_rows)}")

features = [
    "lengthAwareHierarchicalAncestryMutation",
    "lengthAwareFlatAncestryMutation",
    "topologyHierarchicalAncestryMutation",
    "topologyFlatAncestryMutation",
]
role_results = {}
for lane in sorted({row["lane"] for row in pair_rows}):
    lane_rows = [row for row in pair_rows if row["lane"] == lane]
    role_results[lane] = {}
    for feature in features:
        result = balanced_effect(lane_rows, feature)
        if lane == "train":
            add_null(result, lane_rows, feature, int(role_cfg["nullIterations"]))
        role_results[lane][feature] = result

min_source_fraction = 0.60
compression_gates = {
    variant: compression_gate(compression, variant, "holdout", min_source_fraction)
    for variant in ("lengthAware", "topology")
}
role_gates = {
    variant: role_gate(
        role_results,
        variant,
        float(role_cfg["practicalEffectMagnitude"]),
        int(role_cfg["evidenceNullAbsoluteCountMaximum"]),
        float(role_cfg["holdoutSameDirectionMinimumMagnitude"]),
    )
    for variant in ("lengthAware", "topology")
}

length_comp = compression_gates["lengthAware"]["pass"]
length_role = role_gates["lengthAware"]["pass"]
raw_total = compression["lengthAware"]["rawTrainTotalBits"]
flat_total = compression["lengthAware"]["trainFlatTotalBits"]
hier_total = compression["lengthAware"]["trainHierarchicalTotalBits"]
if flat_total >= raw_total and hier_total >= raw_total:
    adjudication = "grammar_family_does_not_compress_beyond_raw"
elif length_comp and length_role:
    adjudication = "hierarchical_generative_architecture_tracks_preserved_role"
elif length_comp:
    adjudication = "hierarchical_compression_without_role_specificity"
elif length_role:
    adjudication = "role_signal_without_hierarchical_compression"
else:
    adjudication = "flat_or_nonhierarchical_structure_suffices_under_v8"

topology_same = compression_gates["topology"]["pass"] and role_gates["topology"]["pass"]
if topology_same and length_comp and length_role:
    length_adjudication = "topology_ablation_reaches_same_full_adjudication_length_not_required"
elif length_comp and length_role and not topology_same:
    length_adjudication = "only_length_aware_reaches_full_adjudication_do_not_call_length_causal"
else:
    length_adjudication = "no_full_primary_hierarchy_claim_to_ablate"

flat_effect = role_results["train"]["lengthAwareFlatAncestryMutation"]["balancedEffect"]
hier_effect = role_results["train"]["lengthAwareHierarchicalAncestryMutation"]["balancedEffect"]
hier_minus_flat = None if flat_effect is None or hier_effect is None else hier_effect - flat_effect

core = {
    "schema": "mark_hierarchical_graph_compression_result_v8",
    "experimentId": protocol["experimentId"],
    "grammarFreezeSha256": freeze_digest,
    "parentEdgePairManifestSha256": manifest_sha,
    "parentCriticalEdgeWorldSha256": world_sha,
    "parentProjectorRowsSha256": world["projectorRowsSha256"],
    "parentRolePairRowsSha256": manifest["parentRolePairRowsSha256"],
    "eligiblePairs": len(pair_rows),
    "eligibleTrainPairs": len(train_rows),
    "compression": compression,
    "compressionGates": compression_gates,
    "roleResults": role_results,
    "roleGates": role_gates,
    "hierarchicalMinusFlatTrainRoleEffect": hier_minus_flat,
    "adjudication": adjudication,
    "lengthAblationAdjudication": length_adjudication,
    "contract": {
        "grammarFrozenBeforeRoleLabelsOpened": True,
        "v7ArtifactConsumed": False,
        "v7RadiusVocabularyConsumed": False,
        "sourcePixelsConsumed": False,
        "topologyReprojected": False,
        "residualGeometryConsumed": False,
        "roleLabelsUsedForGrammarInduction": False,
        "pairIsRoleStatisticalUnit": True,
        "centerCorrespondenceOpenedOnlyAfterGrammarFreeze": True,
        "flatAndHierarchicalRulesNeverRefitOnHoldout": True,
    },
}
digest = canonical_sha(core)
packet = {**core, "hierarchicalGraphCompressionSha256": digest}
out_dir.mkdir(parents=True, exist_ok=True)
(out_dir / "hierarchical-graph-compression-correspondence.json").write_text(json.dumps(packet, indent=2) + "\n", encoding="utf-8")
with (out_dir / "observation-compression.jsonl").open("w", encoding="utf-8") as handle:
    for row in sorted(observation_rows, key=lambda r: r["observationId"]):
        handle.write(json.dumps(row, separators=(",", ":")) + "\n")
with (out_dir / "pair-derivation-mutations.jsonl").open("w", encoding="utf-8") as handle:
    for row in pair_rows:
        handle.write(json.dumps(row, separators=(",", ":")) + "\n")

summary = [
    f"hierarchical_graph_compression_sha256={digest}",
    f"grammar_freeze_sha256={freeze_digest}",
    f"eligible_pairs={len(pair_rows)}",
    f"eligible_train_pairs={len(train_rows)}",
    f"adjudication={adjudication}",
    f"length_ablation_adjudication={length_adjudication}",
]
for variant in ("lengthAware", "topology"):
    gate = compression_gates[variant]
    rg = role_gates[variant]
    holdout = compression[variant]["lanes"].get("holdout", {})
    summary.append(
        f"variant={variant};compression_gate={str(gate['pass']).lower()};"
        f"heldout_hier_vs_flat_reduction={holdout.get('hierarchicalVsFlatReductionFraction')};"
        f"heldout_source_win_fraction={holdout.get('sourceGroupHierarchicalBeatFraction')};"
        f"role_gate={str(rg['pass']).lower()};train_role_effect={rg['trainEffect']};"
        f"holdout_role_effect={rg['holdoutEffect']};train_null_abs={rg['trainNullAbsoluteAtLeastObserved']}"
    )
(out_dir / "summary.txt").write_text("\n".join(summary) + "\n", encoding="utf-8")

md = [
    "### Mark hierarchical graph compression v8 — frozen result",
    "",
    f"- Grammar freeze: `{freeze_digest}`",
    f"- Eligible pairs: **{len(pair_rows)}** total / **{len(train_rows)}** Cleveland train",
    f"- Adjudication: **{adjudication}**",
    f"- Length ablation: **{length_adjudication}**",
    "",
    "| Variant | Cleveland raw total bits | Cleveland flat total bits | Cleveland hierarchical total bits | Bavaria hier vs flat | Bavaria source groups hier wins | Cleveland hierarchy role effect | Cleveland null ≥ | Bavaria hierarchy role effect |",
    "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
]
for variant in ("lengthAware", "topology"):
    holdout = compression[variant]["lanes"].get("holdout", {})
    rg = role_gates[variant]
    train_effect_text = "NA" if rg["trainEffect"] is None else f"{rg['trainEffect']:.6f}"
    holdout_effect_text = "NA" if rg["holdoutEffect"] is None else f"{rg['holdoutEffect']:.6f}"
    null_text = "—" if rg["trainNullAbsoluteAtLeastObserved"] is None else f"{rg['trainNullAbsoluteAtLeastObserved']} / {role_cfg['nullIterations']}"
    md.append(
        f"| {variant} | {compression[variant]['rawTrainTotalBits']} | {compression[variant]['trainFlatTotalBits']} | "
        f"{compression[variant]['trainHierarchicalTotalBits']} | {holdout.get('hierarchicalVsFlatReductionFraction', 0):.6f} | "
        f"{holdout.get('sourceGroupHierarchicalBeatFraction', 0):.3f} | {train_effect_text} | {null_text} | {holdout_effect_text} |"
    )
md += [
    "",
    "The compressor never receives V7 radius-2 motif identities. It learns binary connected productions directly from the frozen V5 critical-edge graph and freezes them before preserved/broken labels are opened.",
    "A hierarchical grammar claim requires recursive compression to beat the flat dictionary on Cleveland total code length, Bavaria aggregate data length, and at least 60% of Bavaria source groups, plus ancestry conservation to pass the Cleveland role/null gate and transfer to Bavaria.",
]
(out_dir / "summary.md").write_text("\n".join(md) + "\n", encoding="utf-8")
print("\n".join(summary))
