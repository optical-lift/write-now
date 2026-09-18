#!/usr/bin/env python3
"""V48 CP1 — fit source-separated equivalent R3/R4 coordinate models.

Consumes only the frozen V46 validation+confirmation feature rows and their
canonical no-refit V46 assignments, then selects exactly the 171 V47-discovery
sources designated as the V48 coordinate-fit lane.

No persist/change target or downstream lane is opened here.
"""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import adjusted_rand_score
from sklearn.preprocessing import StandardScaler

EXPERIMENT_ID="mark:regime-boundary-dynamics:v48"
V47_SALT="mark-v47-regime-transition-grammar|"

VALIDATION_FEATURE_SHA="915a156ae27b9bc1d1539246c2ef554bf5e82d1da56c905c9e3fa934f3d13562"
CONFIRMATION_FEATURE_SHA="2064f7d8bb605199709bc72aca92176360fdfcba7aac3181c7b1e7fb6b57ab27"
VALIDATION_ASSIGN_SHA="b77417e78caaf53ccbdd4e10a1a6540b97802907a468e6fd1f1c24f10905b056"
CONFIRMATION_ASSIGN_SHA="d5adadc55517a6dbfbdd1cf060653727f614a27692822b63235fcce52a102f7c"
PARTITION_PACKET_SHA="975054fa94b75ddfdd376dc204f9fa418c63f16c2e640b9630359fa2963066c1"

COORD_SOURCE_SHA="b77f4f48353764d42888a0de4fb6f1027c78d11565b69ecefe88dd74dffbddbc"
COORD_OBS_SHA="c219978ab6ad8e81bf3ce55634ea9c167c00d4d666e214c43bef093dd2b13795"
CANONICAL_SUBSET_MAPPING_SHA="433fa6c1aaa5190522175f2545faa3c9cdff3ffab0b564bddda255d5a43e4c00"

EXPECTED_SOURCES=171
EXPECTED_ROWS=5305
REGIMES=["RG-001","RG-002","RG-003","RG-004","RG-005"]

MIN_ARI=0.85
MIN_OBS_PER_REGIME=50
MIN_SOURCES_PER_REGIME=20

R3_FEATURES=[
"mean_degree","component_per_1k_skeleton","cycle_per_1k_skeleton",
"endpoint_per_1k_skeleton","junction_per_1k_skeleton",
"topology_type_token","topology_norm_entropy","topology_top_fraction",
"topology_simpson","topology_repeated_fraction",
"critical_type_token","critical_norm_entropy","critical_top_fraction",
"critical_simpson","critical_repeated_fraction",
"path_count_per_1k_skeleton",
]+[f"degree_p{i}" for i in range(9)]+[
"pathbin_1","pathbin_2_3","pathbin_4_7","pathbin_8_15",
"pathbin_16_31","pathbin_32_63","pathbin_64_plus"
]

R4_FEATURES=[
"log_aspect","dark_fraction","skeleton_density","mean_degree",
"component_per_1k_skeleton","cycle_per_1k_skeleton",
"endpoint_per_1k_skeleton","junction_per_1k_skeleton",
"endpoint_cluster_per_1k_skeleton","junction_cluster_per_1k_skeleton",
"topology_type_token","topology_norm_entropy","topology_top_fraction",
"topology_simpson","topology_repeated_fraction",
"critical_type_token","critical_norm_entropy","critical_top_fraction",
"critical_simpson","critical_repeated_fraction",
"path_count_per_1k_skeleton",
]+[f"degree_p{i}" for i in range(9)]+[
"pathbin_1","pathbin_2_3","pathbin_4_7","pathbin_8_15",
"pathbin_16_31","pathbin_32_63","pathbin_64_plus"
]


def sha256_file(path:Path)->str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for c in iter(lambda:f.read(1024*1024),b""):
            h.update(c)
    return h.hexdigest()


def compact(obj:Any)->bytes:
    return json.dumps(obj,separators=(",",":"),ensure_ascii=False).encode()


def list_sha(values:list[str])->str:
    return hashlib.sha256(compact(values)).hexdigest()


def v47_lane(source_id:str)->str:
    d=hashlib.sha256((V47_SALT+source_id).encode()).digest()
    b=int.from_bytes(d[:4],"big")%100
    return "discovery" if b<=59 else ("validation" if b<=79 else "confirmation")


def ratio(n:float,d:float)->float:
    return float(n/d) if d else 0.0


def log1p(v:float)->float:
    return float(np.log1p(max(0.0,v)))


def row_features(row:dict[str,Any])->dict[str,float]:
    g=row["graphMorphology"]; e=row["v46LocalTopologyEcology"]
    c=e["critical"]; p=row["degree2PathSegments"]; degree=g["degreeHistogram"]
    sk=float(g["skeletonPixelCount"]); area=float(g["observationAreaPixels"])
    degree_total=sum(float(degree[str(i)]) for i in range(9))
    path_count=float(p["count"]); lb=p["lengthBins"]
    length_total=sum(float(v) for v in lb.values())
    out={
        "log_aspect":float(np.log(max(float(g["aspectRatio"]),1e-9))),
        "dark_fraction":float(g["darkPixelFraction"]),
        "skeleton_density":float(g["skeletonDensity"]),
        "mean_degree":float(g["meanSkeletonDegree"]),
        "component_per_1k_skeleton":1000.0*ratio(float(g["connectedComponents"]),sk),
        "cycle_per_1k_skeleton":1000.0*ratio(float(g["cycleRank8"]),sk),
        "endpoint_per_1k_skeleton":1000.0*ratio(float(g["endpointPixels"]),sk),
        "junction_per_1k_skeleton":1000.0*ratio(float(g["junctionPixels"]),sk),
        "endpoint_cluster_per_1k_skeleton":1000.0*ratio(float(g["endpointClusters8"]),sk),
        "junction_cluster_per_1k_skeleton":1000.0*ratio(float(g["junctionClusters8"]),sk),
        "topology_type_token":float(e["typeTokenRatio"]),
        "topology_norm_entropy":float(e["normalizedEntropy"]),
        "topology_top_fraction":float(e["topTypeFraction"]),
        "topology_simpson":float(e["simpsonConcentration"]),
        "topology_repeated_fraction":float(e["repeatedTokenFraction"]),
        "critical_type_token":float(c["typeTokenRatio"]),
        "critical_norm_entropy":float(c["normalizedEntropy"]),
        "critical_top_fraction":float(c["topTypeFraction"]),
        "critical_simpson":float(c["simpsonConcentration"]),
        "critical_repeated_fraction":float(c["repeatedTokenFraction"]),
        "path_count_per_1k_skeleton":1000.0*ratio(path_count,sk),
    }
    for i in range(9):
        out[f"degree_p{i}"]=ratio(float(degree[str(i)]),degree_total)
    for name in ["1","2_3","4_7","8_15","16_31","32_63","64_plus"]:
        out[f"pathbin_{name}"]=ratio(float(lb[name]),length_total)
    return out


def verify_hash(path:Path,expected:str,label:str):
    got=sha256_file(path)
    if got!=expected:
        raise RuntimeError(f"{label} SHA drift: {got} != {expected}")


def source_pool(partition_packet:dict[str,Any])->list[str]:
    all_src=sorted(
        partition_packet["source_partitions"]["validation"]["source_group_ids"]+
        partition_packet["source_partitions"]["confirmation"]["source_group_ids"]
    )
    selected=sorted(s for s in all_src if v47_lane(s)=="discovery")
    if len(selected)!=EXPECTED_SOURCES or list_sha(selected)!=COORD_SOURCE_SHA:
        raise RuntimeError("coordinate-fit source set drift")
    return selected


def load_features(paths:list[Path],selected:set[str]):
    rows=[]
    for path in paths:
        with path.open() as f:
            for line in f:
                r=json.loads(line)
                if r.get("schema")!="mark_structural_feature_row_v46_v1":
                    raise RuntimeError("feature row schema drift")
                if r["sourceGroupId"] in selected:
                    rows.append(r)
    rows.sort(key=lambda r:(r["sourceGroupId"],r["observationId"]))
    ids=sorted(r["observationId"] for r in rows)
    if len(rows)!=EXPECTED_ROWS or list_sha(ids)!=COORD_OBS_SHA:
        raise RuntimeError("coordinate-fit observation set drift")
    return rows


def load_canonical(paths:list[Path],selected:set[str]):
    arr=[]
    for path in paths:
        with path.open() as f:
            for line in f:
                r=json.loads(line)
                if r["sourceGroupId"] in selected:
                    arr.append({"sourceGroupId":r["sourceGroupId"],"observationId":r["observationId"],"regimeId":r["regimeId"]})
    arr.sort(key=lambda r:(r["sourceGroupId"],r["observationId"]))
    if len(arr)!=EXPECTED_ROWS:
        raise RuntimeError("canonical assignment count drift")
    if hashlib.sha256(compact(arr)).hexdigest()!=CANONICAL_SUBSET_MAPPING_SHA:
        raise RuntimeError("canonical subset mapping SHA drift")
    mapping={r["observationId"]:r["regimeId"] for r in arr}
    return arr,mapping


def matrix(rows,names):
    X=np.asarray([[row_features(r)[n] for n in names] for r in rows],dtype=np.float64)
    if not np.isfinite(X).all():
        raise RuntimeError("non-finite feature matrix")
    return X


def fit_r3(X):
    scaler=StandardScaler().fit(X)
    Z=scaler.transform(X)
    pca=PCA(n_components=0.95,svd_solver="full").fit(Z)
    P=pca.transform(Z)
    km=KMeans(n_clusters=5,random_state=4601,n_init=20,max_iter=500,algorithm="lloyd").fit(P)
    return scaler,pca,km,P


def best_alignment(raw_labels, canonical_labels):
    canon_idx=np.asarray([REGIMES.index(r) for r in canonical_labels],dtype=int)
    best=None
    for perm in itertools.permutations(range(5)):
        mapped=np.asarray([perm[int(x)] for x in raw_labels],dtype=int)
        agree=int((mapped==canon_idx).sum())
        if best is None or agree>best[0] or (agree==best[0] and perm<best[1]):
            best=(agree,perm,mapped)
    agree,perm,mapped=best
    raw_to_regime={str(raw):REGIMES[canon] for raw,canon in enumerate(perm)}
    return agree/len(mapped),raw_to_regime,mapped,canon_idx


def source_relative(X,sources):
    out=X.copy()
    source_medians={}
    for src in sorted(set(sources.tolist())):
        idx=np.flatnonzero(sources==src)
        med=np.median(X[idx],axis=0)
        out[idx]-=med
        source_medians[src]=med.tolist()
    return out,source_medians


def model_scaler(s):
    return {"mean":s.mean_.tolist(),"scale":s.scale_.tolist(),"var":s.var_.tolist()}


def model_pca(p):
    return {
        "nComponents":int(p.n_components_),
        "components":p.components_.tolist(),
        "mean":p.mean_.tolist(),
        "explainedVariance":p.explained_variance_.tolist(),
        "explainedVarianceRatio":p.explained_variance_ratio_.tolist(),
        "explainedVarianceRatioTotal":float(p.explained_variance_ratio_.sum()),
    }


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--validation-features",type=Path,required=True)
    ap.add_argument("--confirmation-features",type=Path,required=True)
    ap.add_argument("--validation-assignments",type=Path,required=True)
    ap.add_argument("--confirmation-assignments",type=Path,required=True)
    ap.add_argument("--partition-packet",type=Path,required=True)
    ap.add_argument("--out",type=Path,required=True)
    args=ap.parse_args()

    verify_hash(args.validation_features,VALIDATION_FEATURE_SHA,"validation features")
    verify_hash(args.confirmation_features,CONFIRMATION_FEATURE_SHA,"confirmation features")
    verify_hash(args.validation_assignments,VALIDATION_ASSIGN_SHA,"validation assignments")
    verify_hash(args.confirmation_assignments,CONFIRMATION_ASSIGN_SHA,"confirmation assignments")
    verify_hash(args.partition_packet,PARTITION_PACKET_SHA,"partition packet")

    partition=json.loads(args.partition_packet.read_text())
    selected_sources=source_pool(partition); selected=set(selected_sources)
    rows=load_features([args.validation_features,args.confirmation_features],selected)
    canonical_arr,canonical_map=load_canonical([args.validation_assignments,args.confirmation_assignments],selected)

    obs_ids=[r["observationId"] for r in rows]
    sources=np.asarray([r["sourceGroupId"] for r in rows],dtype=object)
    canonical_labels=[canonical_map[oid] for oid in obs_ids]

    X3=matrix(rows,R3_FEATURES)
    s3,p3,k3,P3=fit_r3(X3)
    accuracy,raw_to_regime,aligned_idx,canon_idx=best_alignment(k3.labels_,canonical_labels)
    aligned_labels=np.asarray([REGIMES[int(i)] for i in aligned_idx],dtype=object)
    ari=float(adjusted_rand_score(canon_idx,aligned_idx))

    regime_counts=Counter(aligned_labels.tolist())
    regime_sources=defaultdict(set)
    for src,rg in zip(sources,aligned_labels):
        regime_sources[str(rg)].add(str(src))

    gates={
        "alignedARI":ari>=MIN_ARI,
        "minimumObservationsPerAlignedRegime":min(regime_counts[r] for r in REGIMES)>=MIN_OBS_PER_REGIME,
        "minimumSourcesPerAlignedRegime":min(len(regime_sources[r]) for r in REGIMES)>=MIN_SOURCES_PER_REGIME,
    }
    if not all(gates.values()):
        status="EQUIVALENCE_GATE_FAILED"
    else:
        status="EQUIVALENCE_GATE_PASSED"

    # Canonical-order centers, so all downstream distances use RG-001..RG-005 order.
    aligned_centers=np.zeros_like(k3.cluster_centers_)
    for raw_str,rg in raw_to_regime.items():
        aligned_centers[REGIMES.index(rg)]=k3.cluster_centers_[int(raw_str)]

    X4=matrix(rows,R4_FEATURES)
    X4rel,source_medians=source_relative(X4,sources)
    s4=StandardScaler().fit(X4rel)
    Z4=s4.transform(X4rel)
    p4=PCA(n_components=0.95,svd_solver="full").fit(Z4)
    P4=p4.transform(Z4)

    args.out.mkdir(parents=True,exist_ok=True)

    r3_model={
        "schema":"mark_regime_boundary_r3_equivalent_model_v48_v1",
        "experimentId":EXPERIMENT_ID,
        "coordinateFitSources":EXPECTED_SOURCES,
        "coordinateFitObservations":EXPECTED_ROWS,
        "featureNames":R3_FEATURES,
        "standardScaler":model_scaler(s3),
        "pca":model_pca(p3),
        "kmeans":{
            "k":5,"randomState":4601,"nInit":20,"maxIter":500,"algorithm":"lloyd",
            "rawCentersPca":k3.cluster_centers_.tolist(),
            "alignedCentersPcaRGOrder":aligned_centers.tolist(),
            "inertia":float(k3.inertia_),
        },
        "alignment":{
            "rawClusterToRegime":raw_to_regime,
            "agreementFraction":float(accuracy),
            "adjustedRandIndex":ari,
            "regimeObservationCounts":{r:int(regime_counts[r]) for r in REGIMES},
            "regimeSourceCounts":{r:len(regime_sources[r]) for r in REGIMES},
            "gates":gates,
            "status":status,
        },
    }
    (args.out/"r3-equivalent-model.json").write_text(json.dumps(r3_model,indent=2)+"\n")

    r4_model={
        "schema":"mark_regime_boundary_r4_source_relative_model_v48_v1",
        "experimentId":EXPERIMENT_ID,
        "coordinateFitSources":EXPECTED_SOURCES,
        "coordinateFitObservations":EXPECTED_ROWS,
        "featureNames":R4_FEATURES,
        "sourceRelativeOperation":"subtract within-source feature-wise median before global StandardScaler",
        "projectionContract":"for any later source, compute that source's own feature-wise median from all V48-eligible observations for that source, subtract it, then apply this frozen scaler/PCA; no target labels enter centering",
        "standardScaler":model_scaler(s4),
        "pca":model_pca(p4),
    }
    (args.out/"r4-source-relative-model.json").write_text(json.dumps(r4_model,indent=2)+"\n")

    assignments=[]
    for oid,src,canon,raw,aligned,p3row,p4row in zip(obs_ids,sources,canonical_labels,k3.labels_,aligned_labels,P3,P4):
        assignments.append({
            "sourceGroupId":str(src),
            "observationId":oid,
            "canonicalV46Regime":canon,
            "rawEquivalentCluster":int(raw),
            "alignedEquivalentRegime":str(aligned),
            "r3Pca":p3row.tolist(),
            "r4SourceRelativePca":p4row.tolist(),
        })
    with (args.out/"coordinate-fit-assignments.jsonl").open("w") as f:
        for row in assignments:
            f.write(json.dumps(row,separators=(",",":"))+"\n")

    summary={
        "schema":"mark_regime_boundary_cp1_summary_v48_v1",
        "experimentId":EXPERIMENT_ID,
        "status":status,
        "coordinateFitSources":EXPECTED_SOURCES,
        "coordinateFitObservations":EXPECTED_ROWS,
        "sourceListSha256":COORD_SOURCE_SHA,
        "observationListSha256":COORD_OBS_SHA,
        "canonicalSubsetMappingSha256":CANONICAL_SUBSET_MAPPING_SHA,
        "r3":{
            "rawFeatureCount":len(R3_FEATURES),
            "pcaComponents":int(p3.n_components_),
            "explainedVarianceRatio":float(p3.explained_variance_ratio_.sum()),
            "alignedAgreementFraction":float(accuracy),
            "alignedARI":ari,
            "regimeObservationCounts":{r:int(regime_counts[r]) for r in REGIMES},
            "regimeSourceCounts":{r:len(regime_sources[r]) for r in REGIMES},
            "gates":gates,
        },
        "r4":{
            "rawFeatureCount":len(R4_FEATURES),
            "pcaComponents":int(p4.n_components_),
            "explainedVarianceRatio":float(p4.explained_variance_ratio_.sum()),
        },
        "targetsConsumed":False,
        "boundaryDevelopmentOpened":False,
        "boundaryValidationOpened":False,
        "finalConfirmationOpened":False,
        "provenanceConsumed":False,
    }
    (args.out/"cp1-summary.json").write_text(json.dumps(summary,indent=2)+"\n")
    print(json.dumps(summary,indent=2))


if __name__=="__main__":
    main()
