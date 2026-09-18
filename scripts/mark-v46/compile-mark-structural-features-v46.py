#!/usr/bin/env python3
"""Mark V46 source-blind physical feature compiler.

This compiler intentionally defines a V46-native physical representation.
It does NOT claim byte/equation equivalence to the frozen V5 critical-edge
projector or V45 operator algebra. Features requiring that exact machinery are
reported as unavailable rather than approximated under a V45 name.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import time
import zipfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import cv2
import numpy as np
import skimage
from skimage.morphology import skeletonize

SCHEMA = "mark_structural_feature_row_v46_v1"
SUMMARY_SCHEMA = "mark_structural_feature_summary_v46_v1"
EXPERIMENT_ID = "mark:structural-regime-atlas:v46"
PARTITION_PREFIX = "mark-v46-structural-regime-atlas|"

DIRS = [
    (-1, 0), (-1, 1), (0, 1), (1, 1),
    (1, 0), (1, -1), (0, -1), (-1, -1),
]


def compact_bytes(value: Any) -> bytes:
    return json.dumps(value, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def list_sha256(values: list[str]) -> str:
    return hashlib.sha256(compact_bytes(values)).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def partition_lane(source_group_id: str) -> str:
    digest = hashlib.sha256((PARTITION_PREFIX + source_group_id).encode("utf-8")).digest()
    bucket = int.from_bytes(digest[:4], "big") % 100
    if bucket <= 59:
        return "discovery"
    if bucket <= 79:
        return "validation"
    return "confirmation"


def transform_dir(dy: int, dx: int, rotation: int, reflect: bool) -> tuple[int, int]:
    if reflect:
        dx = -dx
    for _ in range(rotation % 4):
        dy, dx = dx, -dy
    return dy, dx


def canonical_mask_lookup() -> np.ndarray:
    coord_to_index = {coord: i for i, coord in enumerate(DIRS)}
    lookup = np.zeros(256, dtype=np.uint8)
    for mask in range(256):
        variants = []
        for reflect in (False, True):
            for rotation in range(4):
                out = 0
                for i, (dy, dx) in enumerate(DIRS):
                    if mask & (1 << i):
                        nd = transform_dir(dy, dx, rotation, reflect)
                        out |= 1 << coord_to_index[nd]
                variants.append(out)
        lookup[mask] = min(variants)
    return lookup


CANONICAL_MASK = canonical_mask_lookup()
NEIGHBOR_KERNEL = np.ones((3, 3), dtype=np.uint8)
NEIGHBOR_KERNEL[1, 1] = 0


def shift_bool(a: np.ndarray, dy: int, dx: int) -> np.ndarray:
    out = np.zeros_like(a, dtype=bool)
    y_src0 = max(0, -dy)
    y_src1 = a.shape[0] - max(0, dy)
    x_src0 = max(0, -dx)
    x_src1 = a.shape[1] - max(0, dx)
    y_dst0 = max(0, dy)
    y_dst1 = a.shape[0] - max(0, -dy)
    x_dst0 = max(0, dx)
    x_dst1 = a.shape[1] - max(0, -dx)
    if y_src1 > y_src0 and x_src1 > x_src0:
        out[y_dst0:y_dst1, x_dst0:x_dst1] = a[y_src0:y_src1, x_src0:x_src1]
    return out


def neighborhood_masks(skeleton: np.ndarray) -> np.ndarray:
    masks = np.zeros(skeleton.shape, dtype=np.uint8)
    for i, (dy, dx) in enumerate(DIRS):
        neighbor_at_direction = shift_bool(skeleton, -dy, -dx)
        masks |= (neighbor_at_direction.astype(np.uint8) << i)
    masks[~skeleton] = 0
    return masks


def distribution_stats(counts: np.ndarray) -> dict[str, Any]:
    total = int(counts.sum())
    nonzero = counts[counts > 0]
    distinct = int(nonzero.size)
    if total == 0:
        return {
            "tokens": 0,
            "distinctTypes": 0,
            "typeTokenRatio": 0.0,
            "entropyBits": 0.0,
            "normalizedEntropy": 0.0,
            "topTypeFraction": 0.0,
            "simpsonConcentration": 0.0,
            "repeatedTokenFraction": 0.0,
        }
    probs = nonzero.astype(np.float64) / total
    h = float(-(probs * np.log2(probs)).sum())
    repeated = int(nonzero[nonzero > 1].sum())
    return {
        "tokens": total,
        "distinctTypes": distinct,
        "typeTokenRatio": float(distinct / total),
        "entropyBits": h,
        "normalizedEntropy": float(h / math.log2(distinct)) if distinct > 1 else 0.0,
        "topTypeFraction": float(nonzero.max() / total),
        "simpsonConcentration": float((probs * probs).sum()),
        "repeatedTokenFraction": float(repeated / total),
    }


def length_bins(lengths: list[int]) -> dict[str, int]:
    bins = {"1": 0, "2_3": 0, "4_7": 0, "8_15": 0, "16_31": 0, "32_63": 0, "64_plus": 0}
    for n in lengths:
        if n <= 1: bins["1"] += 1
        elif n <= 3: bins["2_3"] += 1
        elif n <= 7: bins["4_7"] += 1
        elif n <= 15: bins["8_15"] += 1
        elif n <= 31: bins["16_31"] += 1
        elif n <= 63: bins["32_63"] += 1
        else: bins["64_plus"] += 1
    return bins


def finite_float(value: float) -> float:
    if not math.isfinite(value):
        return 0.0
    return float(value)


def feature_row(image: np.ndarray, observation: dict[str, Any], lane: str) -> dict[str, Any]:
    region = observation["region"]
    x, y = int(region["x"]), int(region["y"])
    w, h = int(region["width"]), int(region["height"])
    crop = image[y:y+h, x:x+w]
    if crop.shape != (h, w):
        raise RuntimeError(f"crop bounds mismatch for {observation['id']}: expected {(h,w)} got {crop.shape}")
    if crop.size == 0:
        raise RuntimeError(f"empty crop for {observation['id']}")

    threshold, _ = cv2.threshold(crop, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    dark = crop <= threshold
    skeleton = skeletonize(dark).astype(bool)
    sk_u8 = skeleton.astype(np.uint8)

    degree_map = cv2.filter2D(sk_u8, cv2.CV_16U, NEIGHBOR_KERNEL, borderType=cv2.BORDER_CONSTANT)
    degrees = degree_map[skeleton].astype(np.int64)
    degree_hist = np.bincount(degrees, minlength=9)[:9] if degrees.size else np.zeros(9, dtype=np.int64)

    component_count = int(cv2.connectedComponents(sk_u8, connectivity=8)[0] - 1) if skeleton.any() else 0
    vertices = int(skeleton.sum())
    adjacency_edges = int(degrees.sum() // 2) if degrees.size else 0
    cycle_rank = max(0, adjacency_edges - vertices + component_count)

    endpoint_mask = skeleton & (degree_map == 1)
    junction_mask = skeleton & (degree_map >= 3)
    isolated_mask = skeleton & (degree_map == 0)
    path_mask = skeleton & (degree_map == 2)
    endpoint_clusters = int(cv2.connectedComponents(endpoint_mask.astype(np.uint8), connectivity=8)[0] - 1) if endpoint_mask.any() else 0
    junction_clusters = int(cv2.connectedComponents(junction_mask.astype(np.uint8), connectivity=8)[0] - 1) if junction_mask.any() else 0

    path_labels_count, _, path_stats, _ = cv2.connectedComponentsWithStats(path_mask.astype(np.uint8), connectivity=8)
    path_lengths = [int(path_stats[i, cv2.CC_STAT_AREA]) for i in range(1, path_labels_count)]

    n_masks = neighborhood_masks(skeleton)
    raw_tokens = n_masks[skeleton]
    canonical_tokens = CANONICAL_MASK[raw_tokens] if raw_tokens.size else np.array([], dtype=np.uint8)
    token_counts = np.bincount(canonical_tokens, minlength=256) if canonical_tokens.size else np.zeros(256, dtype=np.int64)
    critical = skeleton & (degree_map != 2)
    critical_tokens = CANONICAL_MASK[n_masks[critical]] if critical.any() else np.array([], dtype=np.uint8)
    critical_counts = np.bincount(critical_tokens, minlength=256) if critical_tokens.size else np.zeros(256, dtype=np.int64)

    top_types = []
    if token_counts.sum() > 0:
        order = sorted((int(i) for i in np.flatnonzero(token_counts)), key=lambda i: (-int(token_counts[i]), i))[:8]
        top_types = [{"token": f"T{i:03d}", "count": int(token_counts[i])} for i in order]

    area = int(w * h)
    path_arr = np.asarray(path_lengths, dtype=np.float64)
    return {
        "schema": SCHEMA,
        "experimentId": EXPERIMENT_ID,
        "observationId": observation["id"],
        "sourceGroupId": observation["sourceGroupId"],
        "v46Lane": lane,
        "region": {"x": x, "y": y, "width": w, "height": h},
        "proposalKind": str(observation.get("proposalKind", "")),
        "proposalScale": str(observation.get("proposalScale", "")),
        "segmentation": {
            "polarity": "dark_on_light",
            "thresholdMethod": "opencv_otsu",
            "otsuThreshold": finite_float(float(threshold)),
            "foregroundRule": "gray <= otsuThreshold",
        },
        "graphMorphology": {
            "observationAreaPixels": area,
            "aspectRatio": finite_float(w / h if h else 0.0),
            "darkPixelCount": int(dark.sum()),
            "darkPixelFraction": finite_float(float(dark.mean())),
            "skeletonPixelCount": vertices,
            "skeletonDensity": finite_float(vertices / area if area else 0.0),
            "connectedComponents": component_count,
            "adjacencyEdges8": adjacency_edges,
            "cycleRank8": cycle_rank,
            "isolatedPixels": int(isolated_mask.sum()),
            "endpointPixels": int(endpoint_mask.sum()),
            "pathPixels": int(path_mask.sum()),
            "junctionPixels": int(junction_mask.sum()),
            "endpointClusters8": endpoint_clusters,
            "junctionClusters8": junction_clusters,
            "degreeHistogram": {str(i): int(degree_hist[i]) for i in range(9)},
            "meanSkeletonDegree": finite_float(float(degrees.mean())) if degrees.size else 0.0,
        },
        "v46LocalTopologyEcology": {
            **distribution_stats(token_counts),
            "critical": distribution_stats(critical_counts),
            "topTypes": top_types,
            "tokenDefinition": "8-neighbor skeleton occupancy mask canonicalized over D4 rotation/reflection",
        },
        "degree2PathSegments": {
            "count": len(path_lengths),
            "pixelLengthMean": finite_float(float(path_arr.mean())) if path_arr.size else 0.0,
            "pixelLengthMedian": finite_float(float(np.median(path_arr))) if path_arr.size else 0.0,
            "pixelLengthMax": int(path_arr.max()) if path_arr.size else 0,
            "lengthBins": length_bins(path_lengths),
        },
        "featureAvailability": {
            "graph_morphology": "MEASURED",
            "operator_ecology": "PARTIAL_V46_LOCAL_TOPOLOGY_ONLY",
            "v45_law_ecology": "UNAVAILABLE_EXACT_V5_PROJECTOR_NOT_PRESENT",
            "higher_order_operator_programs": "UNAVAILABLE_IN_FEATURE_COMPILER_V1",
            "cross_scale_persistence_transition": "DEFERRED_TO_SOURCE_LOCAL_DISCOVERY_JOIN",
        },
    }


def verify_inputs(input_doc: dict[str, Any], exclusions: dict[str, Any], partitions: dict[str, Any], lane: str) -> tuple[list[dict[str, Any]], set[str]]:
    if input_doc.get("schema") != "mark_observable_input_blind_v1":
        raise RuntimeError("unexpected blind input schema")
    supplied = input_doc.get("blindInputSha256")
    core = {k: v for k, v in input_doc.items() if k != "blindInputSha256"}
    computed = hashlib.sha256(compact_bytes(core)).hexdigest()
    if supplied != computed:
        raise RuntimeError(f"blind input SHA mismatch: {computed} != {supplied}")
    if exclusions.get("count") != 435 or len(exclusions.get("observation_ids", [])) != 435:
        raise RuntimeError("V46 exclusion packet does not contain exactly 435 observations")
    excluded_ids = sorted(exclusions["observation_ids"])
    if list_sha256(excluded_ids) != "1735dbadeb93241237af7af3efbe22a7b4a942a80cf94db301e43caaef827076":
        raise RuntimeError("exclusion ID-list hash drift")
    if lane not in partitions.get("source_partitions", {}):
        raise RuntimeError(f"lane absent from partition freeze: {lane}")

    source_ids = sorted(s["sourceGroupId"] for s in input_doc["sources"] if partition_lane(s["sourceGroupId"]) == lane)
    frozen_lane = partitions["source_partitions"][lane]
    if source_ids != frozen_lane["source_group_ids"]:
        raise RuntimeError(f"{lane} source IDs differ from partition freeze")
    if list_sha256(source_ids) != frozen_lane["source_list_sha256"]:
        raise RuntimeError(f"{lane} source-list SHA drift")

    excluded = set(excluded_ids)
    source_set = set(source_ids)
    observations = [o for o in input_doc["observations"] if o["sourceGroupId"] in source_set and o["id"] not in excluded]
    observations.sort(key=lambda o: (o["sourceGroupId"], o["id"]))
    obs_ids = sorted(o["id"] for o in observations)
    if len(observations) != int(frozen_lane["observation_count"]):
        raise RuntimeError(f"{lane} observation count drift: {len(observations)} != {frozen_lane['observation_count']}")
    if list_sha256(obs_ids) != frozen_lane["observation_id_list_sha256"]:
        raise RuntimeError(f"{lane} observation-list SHA drift")
    return observations, source_set


def self_test() -> None:
    corner_masks = []
    for a, b in [(0, 2), (2, 4), (4, 6), (6, 0), (0, 6)]:
        corner_masks.append(int(CANONICAL_MASK[(1 << a) | (1 << b)]))
    assert len(set(corner_masks)) == 1, corner_masks

    img = np.full((9, 9), 255, dtype=np.uint8)
    img[4, 2:7] = 0
    img[2:7, 4] = 0
    obs = {"id":"OTEST", "sourceGroupId":"STEST", "region":{"x":0,"y":0,"width":9,"height":9}, "proposalKind":"test", "proposalScale":"test"}
    row = feature_row(img, obs, "discovery")
    g = row["graphMorphology"]
    assert g["connectedComponents"] == 1
    assert g["cycleRank8"] == 4
    assert g["junctionPixels"] >= 1
    assert g["endpointPixels"] == 4
    print("V46 feature compiler self-test PASS")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", type=Path)
    ap.add_argument("--sealed-zip", type=Path)
    ap.add_argument("--exclusions", type=Path)
    ap.add_argument("--partition-freeze", type=Path)
    ap.add_argument("--lane", choices=["discovery", "validation", "confirmation"], default="discovery")
    ap.add_argument("--out", type=Path)
    ap.add_argument("--limit", type=int, default=0, help="testing only; forbidden for scientific freeze")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        self_test()
        return
    for name in ("input", "sealed_zip", "exclusions", "partition_freeze", "out"):
        if getattr(args, name) is None:
            ap.error(f"--{name.replace('_','-')} is required unless --self-test is used")

    start = time.time()
    input_doc = json.loads(args.input.read_text(encoding="utf-8"))
    exclusions = json.loads(args.exclusions.read_text(encoding="utf-8"))
    partitions = json.loads(args.partition_freeze.read_text(encoding="utf-8"))
    observations, _ = verify_inputs(input_doc, exclusions, partitions, args.lane)
    if args.limit:
        observations = observations[:args.limit]

    source_meta = {s["sourceGroupId"]: s for s in input_doc["sources"]}
    by_source: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for obs in observations:
        by_source[obs["sourceGroupId"]].append(obs)

    args.out.mkdir(parents=True, exist_ok=True)
    rows_path = args.out / "structural-features.jsonl"
    rows_hasher = hashlib.sha256()
    row_count = 0
    source_count = 0
    total_area = 0
    total_skeleton = 0
    availability_counts: Counter[str] = Counter()

    with zipfile.ZipFile(args.sealed_zip) as zf, rows_path.open("wb") as writer:
        for source_group_id in sorted(by_source):
            source = source_meta[source_group_id]
            member = "mark-conveyor-input-v1/" + source["capturePath"]
            try:
                raw = zf.read(member)
            except KeyError as e:
                raise RuntimeError(f"capture missing from sealed artifact: {member}") from e
            image = cv2.imdecode(np.frombuffer(raw, np.uint8), cv2.IMREAD_GRAYSCALE)
            if image is None:
                raise RuntimeError(f"failed to decode {member}")
            source_count += 1
            for observation in by_source[source_group_id]:
                row = feature_row(image, observation, args.lane)
                payload = compact_bytes(row) + b"\n"
                writer.write(payload)
                rows_hasher.update(payload)
                row_count += 1
                total_area += int(row["graphMorphology"]["observationAreaPixels"])
                total_skeleton += int(row["graphMorphology"]["skeletonPixelCount"])
                for k, v in row["featureAvailability"].items():
                    availability_counts[f"{k}:{v}"] += 1

    rows_sha = rows_hasher.hexdigest()
    scientific_freeze_eligible = args.limit == 0 and row_count == int(partitions["source_partitions"][args.lane]["observation_count"])
    summary = {
        "schema": SUMMARY_SCHEMA,
        "experimentId": EXPERIMENT_ID,
        "lane": args.lane,
        "scientificFreezeEligible": scientific_freeze_eligible,
        "sourceBlindInputSha256": input_doc["blindInputSha256"],
        "sealedEvidenceZipSha256": sha256_file(args.sealed_zip),
        "exclusionIdListSha256": "1735dbadeb93241237af7af3efbe22a7b4a942a80cf94db301e43caaef827076",
        "partitionSourceListSha256": partitions["source_partitions"][args.lane]["source_list_sha256"],
        "partitionObservationListSha256": partitions["source_partitions"][args.lane]["observation_id_list_sha256"],
        "sources": source_count,
        "observations": row_count,
        "rowsSha256": rows_sha,
        "totalObservationAreaPixels": total_area,
        "totalSkeletonPixels": total_skeleton,
        "featureAvailabilityCounts": dict(sorted(availability_counts.items())),
        "environment": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "opencv": cv2.__version__,
            "scikitImage": skimage.__version__,
        },
        "featureContract": {
            "sourceBlind": True,
            "semanticLabelsConsumed": False,
            "provenanceConsumed": False,
            "newSourceAcquisition": False,
            "threshold": "OpenCV Otsu on exact observation crop",
            "foreground": "gray <= Otsu threshold",
            "skeleton": "skimage.morphology.skeletonize binary mask",
            "graphAdjacency": "8-neighbor pixel graph",
            "localTopologyToken": "8-neighbor occupancy bitmask canonicalized over D4 rotations/reflections",
            "normalizationAtCompiler": "none; raw deterministic features only",
            "missingValueRule": "feature families requiring unavailable exact machinery are named UNAVAILABLE/PARTIAL; numeric features mathematically defined on empty skeleton are zero; no imputation",
            "v45ExactnessClaimed": False,
            "v45SubstitutionForbidden": True,
        },
        "runtimeSeconds": time.time() - start,
    }
    (args.out / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    contract = {
        "schema": "mark_structural_feature_contract_v46_v1",
        "experimentId": EXPERIMENT_ID,
        "measurable": {
            "graph_morphology": "MEASURED",
            "operator_ecology": "PARTIAL: V46 local D4 topology-token ecology only",
            "v45_law_ecology": "UNAVAILABLE: exact V5 critical-edge projector is absent from the V46 parent branch; no approximate substitution",
            "higher_order_operator_programs": "UNAVAILABLE in feature compiler v1; may be added as a preserved discovery attempt",
            "cross_scale_persistence_transition": "DEFERRED: requires source-local joins over compiled records, not additional pixel extraction",
        },
        "normalization": "none in compiler output",
        "missingValues": "no imputation; unavailable feature families remain explicit status fields",
        "rowSchema": SCHEMA,
        "rowsSha256": rows_sha,
    }
    (args.out / "feature-contract.json").write_text(json.dumps(contract, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
