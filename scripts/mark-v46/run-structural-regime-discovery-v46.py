#!/usr/bin/env python3
"""V46 discovery-only structural regime attempt runner.

Runs a frozen first attempt set against the already-frozen discovery feature
artifact. It never reads source provenance, validation rows, confirmation rows,
OCR, semantic labels, or Song data.

Every representation/k attempt is retained in the output. No cluster receives a
semantic name.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import adjusted_rand_score, silhouette_score
from sklearn.preprocessing import StandardScaler

EXPERIMENT_ID = "mark:structural-regime-atlas:v46"
EXPECTED_ROWS_SHA256 = "0d45b335f8b468bed999d2455b4385b32bb742d7f1c7cf542a54b147ac976caf"
EXPECTED_ROWS = 13482
EXPECTED_SOURCES = 431
KS = list(range(2, 11))
SEEDS = [4601, 4602, 4603]
HOLDOUT_FOLDS = 4
SILHOUETTE_SAMPLE = 5000


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def stable_fold(source_group_id: str) -> int:
    digest = hashlib.sha256(("mark-v46-discovery-holdback|" + source_group_id).encode()).digest()
    return int.from_bytes(digest[:4], "big") % HOLDOUT_FOLDS


def safe_ratio(n: float, d: float) -> float:
    return float(n / d) if d else 0.0


def log1p(v: float) -> float:
    return float(math.log1p(max(0.0, v)))


def row_features(row: dict[str, Any]) -> dict[str, float]:
    g = row["graphMorphology"]
    e = row["v46LocalTopologyEcology"]
    c = e["critical"]
    p = row["degree2PathSegments"]
    degree = g["degreeHistogram"]
    sk = float(g["skeletonPixelCount"])
    area = float(g["observationAreaPixels"])
    degree_total = sum(float(degree[str(i)]) for i in range(9))
    path_count = float(p["count"])
    lb = p["lengthBins"]
    length_total = sum(float(v) for v in lb.values())

    out: dict[str, float] = {
        "log_area": log1p(area),
        "log_aspect": float(math.log(max(float(g["aspectRatio"]), 1e-9))),
        "dark_fraction": float(g["darkPixelFraction"]),
        "log_skeleton": log1p(sk),
        "skeleton_density": float(g["skeletonDensity"]),
        "log_components": log1p(float(g["connectedComponents"])),
        "log_edges": log1p(float(g["adjacencyEdges8"])),
        "log_cycles": log1p(float(g["cycleRank8"])),
        "mean_degree": float(g["meanSkeletonDegree"]),
        "component_per_1k_skeleton": 1000.0 * safe_ratio(float(g["connectedComponents"]), sk),
        "cycle_per_1k_skeleton": 1000.0 * safe_ratio(float(g["cycleRank8"]), sk),
        "endpoint_per_1k_skeleton": 1000.0 * safe_ratio(float(g["endpointPixels"]), sk),
        "junction_per_1k_skeleton": 1000.0 * safe_ratio(float(g["junctionPixels"]), sk),
        "endpoint_cluster_per_1k_skeleton": 1000.0 * safe_ratio(float(g["endpointClusters8"]), sk),
        "junction_cluster_per_1k_skeleton": 1000.0 * safe_ratio(float(g["junctionClusters8"]), sk),
        "topology_distinct_log": log1p(float(e["distinctTypes"])),
        "topology_type_token": float(e["typeTokenRatio"]),
        "topology_entropy": float(e["entropyBits"]),
        "topology_norm_entropy": float(e["normalizedEntropy"]),
        "topology_top_fraction": float(e["topTypeFraction"]),
        "topology_simpson": float(e["simpsonConcentration"]),
        "topology_repeated_fraction": float(e["repeatedTokenFraction"]),
        "critical_distinct_log": log1p(float(c["distinctTypes"])),
        "critical_type_token": float(c["typeTokenRatio"]),
        "critical_entropy": float(c["entropyBits"]),
        "critical_norm_entropy": float(c["normalizedEntropy"]),
        "critical_top_fraction": float(c["topTypeFraction"]),
        "critical_simpson": float(c["simpsonConcentration"]),
        "critical_repeated_fraction": float(c["repeatedTokenFraction"]),
        "path_count_log": log1p(path_count),
        "path_count_per_1k_skeleton": 1000.0 * safe_ratio(path_count, sk),
        "path_mean_log": log1p(float(p["pixelLengthMean"])),
        "path_median_log": log1p(float(p["pixelLengthMedian"])),
        "path_max_log": log1p(float(p["pixelLengthMax"])),
    }
    for i in range(9):
        out[f"degree_p{i}"] = safe_ratio(float(degree[str(i)]), degree_total)
    for name in ["1", "2_3", "4_7", "8_15", "16_31", "32_63", "64_plus"]:
        out[f"pathbin_{name}"] = safe_ratio(float(lb[name]), length_total)
    return out


FULL = [
    "log_area","log_aspect","dark_fraction","log_skeleton","skeleton_density",
    "log_components","log_edges","log_cycles","mean_degree",
    "component_per_1k_skeleton","cycle_per_1k_skeleton",
    "endpoint_per_1k_skeleton","junction_per_1k_skeleton",
    "endpoint_cluster_per_1k_skeleton","junction_cluster_per_1k_skeleton",
    "topology_distinct_log","topology_type_token","topology_entropy","topology_norm_entropy",
    "topology_top_fraction","topology_simpson","topology_repeated_fraction",
    "critical_distinct_log","critical_type_token","critical_entropy","critical_norm_entropy",
    "critical_top_fraction","critical_simpson","critical_repeated_fraction",
    "path_count_log","path_count_per_1k_skeleton","path_mean_log","path_median_log","path_max_log",
] + [f"degree_p{i}" for i in range(9)] + [
    "pathbin_1","pathbin_2_3","pathbin_4_7","pathbin_8_15","pathbin_16_31","pathbin_32_63","pathbin_64_plus"
]

NORMALIZED = [
    "log_aspect","dark_fraction","skeleton_density","mean_degree",
    "component_per_1k_skeleton","cycle_per_1k_skeleton",
    "endpoint_per_1k_skeleton","junction_per_1k_skeleton",
    "endpoint_cluster_per_1k_skeleton","junction_cluster_per_1k_skeleton",
    "topology_type_token","topology_norm_entropy","topology_top_fraction","topology_simpson","topology_repeated_fraction",
    "critical_type_token","critical_norm_entropy","critical_top_fraction","critical_simpson","critical_repeated_fraction",
    "path_count_per_1k_skeleton",
] + [f"degree_p{i}" for i in range(9)] + [
    "pathbin_1","pathbin_2_3","pathbin_4_7","pathbin_8_15","pathbin_16_31","pathbin_32_63","pathbin_64_plus"
]

TOPOLOGY = [
    "mean_degree","component_per_1k_skeleton","cycle_per_1k_skeleton",
    "endpoint_per_1k_skeleton","junction_per_1k_skeleton",
    "topology_type_token","topology_norm_entropy","topology_top_fraction","topology_simpson","topology_repeated_fraction",
    "critical_type_token","critical_norm_entropy","critical_top_fraction","critical_simpson","critical_repeated_fraction",
    "path_count_per_1k_skeleton",
] + [f"degree_p{i}" for i in range(9)] + [
    "pathbin_1","pathbin_2_3","pathbin_4_7","pathbin_8_15","pathbin_16_31","pathbin_32_63","pathbin_64_plus"
]

REPRESENTATIONS = {
    "R1_FULL_MORPHOLOGY": FULL,
    "R2_SCALE_NORMALIZED": NORMALIZED,
    "R3_TOPOLOGY_ECOLOGY": TOPOLOGY,
    "R4_SOURCE_RELATIVE_NORMALIZED": NORMALIZED,
}


def load_rows(path: Path):
    rows = []
    sources = []
    obs = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            row = json.loads(line)
            if row.get("schema") != "mark_structural_feature_row_v46_v1" or row.get("v46Lane") != "discovery":
                raise RuntimeError("non-discovery or wrong-schema row encountered")
            rows.append(row_features(row))
            sources.append(row["sourceGroupId"])
            obs.append(row["observationId"])
    if len(rows) != EXPECTED_ROWS or len(set(sources)) != EXPECTED_SOURCES:
        raise RuntimeError("discovery feature row/source count drift")
    return rows, np.asarray(sources), np.asarray(obs)


def matrix(rows: list[dict[str,float]], names: list[str]) -> np.ndarray:
    X = np.asarray([[r[n] for n in names] for r in rows], dtype=np.float64)
    if not np.isfinite(X).all():
        raise RuntimeError("non-finite feature")
    return X


def source_relative(X: np.ndarray, sources: np.ndarray) -> np.ndarray:
    out = X.copy()
    for source in sorted(set(sources.tolist())):
        idx = np.flatnonzero(sources == source)
        out[idx] -= np.median(X[idx], axis=0)
    return out


def preprocess(X: np.ndarray):
    scaler = StandardScaler()
    Z = scaler.fit_transform(X)
    pca = PCA(n_components=0.95, svd_solver="full")
    P = pca.fit_transform(Z)
    return scaler, pca, P


def total_ss(P: np.ndarray) -> float:
    centered = P - P.mean(axis=0)
    return float((centered * centered).sum())


def label_stats(labels: np.ndarray, sources: np.ndarray, k: int) -> dict[str,Any]:
    counts = np.bincount(labels, minlength=k)
    fractions = counts / len(labels)
    cluster_sources = [len(set(sources[labels == j].tolist())) for j in range(k)]
    probs = counts[counts > 0] / len(labels)
    balance_entropy = float(-(probs * np.log2(probs)).sum() / math.log2(k)) if k > 1 else 0.0
    max_source_share = 0.0
    for j in range(k):
        members = sources[labels == j]
        if len(members):
            c = Counter(members.tolist())
            max_source_share = max(max_source_share, max(c.values()) / len(members))
    return {
        "clusterCounts": counts.tolist(),
        "clusterFractions": fractions.tolist(),
        "minClusterFraction": float(fractions.min()),
        "minDistinctSourcesPerCluster": int(min(cluster_sources)),
        "medianDistinctSourcesPerCluster": float(np.median(cluster_sources)),
        "balanceEntropy": balance_entropy,
        "maximumSingleSourceShareAnyCluster": float(max_source_share),
    }


def run_attempt(name: str, X: np.ndarray, sources: np.ndarray, obs: np.ndarray, k: int) -> tuple[dict[str,Any], np.ndarray]:
    scaler, pca, P = preprocess(X)
    full = KMeans(n_clusters=k, random_state=SEEDS[0], n_init=20, max_iter=500, algorithm="lloyd")
    labels = full.fit_predict(P)
    tss = total_ss(P)
    compactness = 1.0 - float(full.inertia_ / tss) if tss else 0.0

    sample_n = min(SILHOUETTE_SAMPLE, len(P))
    sample_idx = np.linspace(0, len(P)-1, sample_n, dtype=int)
    sil = float(silhouette_score(P[sample_idx], labels[sample_idx], metric="euclidean"))

    seed_aris = []
    for seed in SEEDS[1:]:
        km = KMeans(n_clusters=k, random_state=seed, n_init=20, max_iter=500, algorithm="lloyd")
        alt = km.fit_predict(P)
        seed_aris.append(float(adjusted_rand_score(labels, alt)))

    folds = np.asarray([stable_fold(s) for s in sources])
    hold_aris = []
    for fold in range(HOLDOUT_FOLDS):
        train = folds != fold
        test = folds == fold
        train_scaler = StandardScaler().fit(X[train])
        Zt = train_scaler.transform(X[train])
        train_pca = PCA(n_components=0.95, svd_solver="full").fit(Zt)
        Pt = train_pca.transform(Zt)
        Ph = train_pca.transform(train_scaler.transform(X[test]))
        km = KMeans(n_clusters=k, random_state=SEEDS[0], n_init=20, max_iter=500, algorithm="lloyd")
        km.fit(Pt)
        pred = km.predict(Ph)
        hold_aris.append(float(adjusted_rand_score(labels[test], pred)))

    stats = label_stats(labels, sources, k)
    eligible = (
        float(np.mean(hold_aris)) >= 0.60
        and float(np.mean(seed_aris)) >= 0.85
        and stats["minClusterFraction"] >= 0.015
        and stats["minDistinctSourcesPerCluster"] >= 15
    )
    result = {
        "attemptId": f"{name}:K{k}",
        "representation": name,
        "k": k,
        "rows": len(P),
        "rawFeatureCount": X.shape[1],
        "pcaComponents": int(P.shape[1]),
        "pcaExplainedVariance": float(pca.explained_variance_ratio_.sum()),
        "silhouette": sil,
        "residualCompactness": compactness,
        "seedARI": seed_aris,
        "meanSeedARI": float(np.mean(seed_aris)),
        "sourceHoldbackARI": hold_aris,
        "meanSourceHoldbackARI": float(np.mean(hold_aris)),
        **stats,
        "selectionEligible": bool(eligible),
        "selectionContract": {
            "minimumMeanSourceHoldbackARI": 0.60,
            "minimumMeanSeedARI": 0.85,
            "minimumClusterFraction": 0.015,
            "minimumDistinctSourcesPerCluster": 15,
        },
    }
    return result, labels


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--features", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    args = ap.parse_args()

    if sha256_file(args.features) != EXPECTED_ROWS_SHA256:
        raise RuntimeError("feature artifact SHA-256 drift")

    start = time.time()
    rows, sources, obs = load_rows(args.features)
    args.out.mkdir(parents=True, exist_ok=True)

    attempts = []
    label_store: dict[str,list[int]] = {}
    representation_metadata = {}

    for name, names in REPRESENTATIONS.items():
        X = matrix(rows, names)
        if name == "R4_SOURCE_RELATIVE_NORMALIZED":
            X = source_relative(X, sources)
        representation_metadata[name] = {
            "featureNames": names,
            "sourceRelativeMedianCentering": name == "R4_SOURCE_RELATIVE_NORMALIZED",
            "standardization": "StandardScaler",
            "dimensionReduction": "PCA retaining >=95% variance",
            "clustering": "KMeans Lloyd",
            "kValues": KS,
            "seeds": SEEDS,
        }
        for k in KS:
            result, labels = run_attempt(name, X, sources, obs, k)
            attempts.append(result)
            label_store[result["attemptId"]] = labels.astype(int).tolist()
            print(json.dumps({k: result[k] for k in ["attemptId","silhouette","residualCompactness","meanSeedARI","meanSourceHoldbackARI","minClusterFraction","minDistinctSourcesPerCluster","selectionEligible"]}))

    # This runner does not force a winner. It reports the discovery Pareto material.
    # Selection is a separate recorded discovery decision after every first-set attempt exists.
    packet = {
        "schema":"mark_structural_regime_discovery_attempts_v46_v1",
        "experimentId":EXPERIMENT_ID,
        "featureArtifactSha256":EXPECTED_ROWS_SHA256,
        "rows":len(rows),
        "sources":len(set(sources.tolist())),
        "representations":representation_metadata,
        "attempts":attempts,
        "selectionPerformed":False,
        "provenanceOpened":False,
        "validationOpened":False,
        "confirmationOpened":False,
        "runtimeSeconds":time.time()-start,
    }
    (args.out/"attempts.json").write_text(json.dumps(packet,indent=2)+"\n")
    assignments = {
        "schema":"mark_structural_regime_discovery_assignments_v46_v1",
        "observationIds":obs.tolist(),
        "attemptLabels":label_store,
    }
    (args.out/"attempt-assignments.json").write_text(json.dumps(assignments,separators=(",",":"))+"\n")
    print(json.dumps({"attempts":len(attempts),"eligible":sum(a["selectionEligible"] for a in attempts),"runtimeSeconds":packet["runtimeSeconds"]},indent=2))


if __name__ == "__main__":
    main()
