#!/usr/bin/env python3
"""V47 discovery-only pairwise regime-transition harvest.

Joins the frozen V46 regime mapping to the already-frozen V47 discovery
geometry, evaluates the preregistered pairwise rules, and compares each
transition to 100 deterministic source-and-scale-preserving label permutations.

Validation and confirmation geometry are not accepted by this runner.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy as np

EXPERIMENT_ID = "mark:regime-transition-grammar:v47"
GEOMETRY_SHA256 = "480c174ff503ad877f5d08cdf0dae78007750334873045bd0d8e91a9e8513f55"
MAPPING_SHA256 = "633918a3bad435adfdef9859a33743b9fa88bfcf59a79a4ed8a59b71141d9d90"
EXPECTED_ROWS = 5305
EXPECTED_SOURCES = 171
NULL_ITERATIONS = 100
REGIMES = ["RG-001","RG-002","RG-003","RG-004","RG-005"]

MIN_OCC = 20
MIN_SOURCES = 10
MIN_CONDITIONAL = 0.50
MIN_LIFT = 1.25
NULL_Q = 0.99
MAX_CANDIDATES = 15


def sha256_file(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):
            h.update(chunk)
    return h.hexdigest()


def null_seed(iteration: int) -> int:
    material=f"{EXPERIMENT_ID}|pairwise-null|{iteration}".encode()
    return int.from_bytes(hashlib.sha256(material).digest()[:8],"big",signed=False)


def key_string(cscale: str, crg: str, pscale: str, prg: str) -> str:
    return f"{cscale}|{crg}->{pscale}|{prg}"


def load_geometry(path: Path) -> tuple[list[dict[str,Any]],dict[str,dict[str,Any]]]:
    if sha256_file(path)!=GEOMETRY_SHA256:
        raise RuntimeError("discovery geometry SHA-256 drift")
    rows=[]; by_id={}
    with path.open() as f:
        for line in f:
            r=json.loads(line)
            if r.get("schema")!="mark_regime_transition_geometry_row_v47_v1":
                raise RuntimeError("geometry schema drift")
            if "regimeId" in r:
                raise RuntimeError("regime label found in frozen geometry")
            rows.append(r); by_id[r["observationId"]]=r
    if len(rows)!=EXPECTED_ROWS or len(set(r["sourceGroupId"] for r in rows))!=EXPECTED_SOURCES:
        raise RuntimeError("discovery geometry inventory drift")
    if len(by_id)!=len(rows):
        raise RuntimeError("duplicate geometry observation ID")
    return rows,by_id


def load_mapping(path: Path) -> dict[str,str]:
    if sha256_file(path)!=MAPPING_SHA256:
        raise RuntimeError("fixed regime mapping SHA-256 drift")
    arr=json.loads(path.read_text())
    out={}
    for r in arr:
        rg=r["regimeId"]
        if rg not in REGIMES:
            raise RuntimeError("unexpected regime ID")
        oid=r["observationId"]
        if oid in out:
            raise RuntimeError("duplicate regime mapping")
        out[oid]=rg
    return out


def build_edges(rows: list[dict[str,Any]], mapping: dict[str,str]) -> list[dict[str,str]]:
    row_ids={r["observationId"] for r in rows}
    missing=sorted(row_ids-set(mapping))
    if missing:
        raise RuntimeError(f"missing frozen regime assignments: {len(missing)}")
    edges=[]
    for r in rows:
        pid=r["parentObservationId"]
        if pid is None:
            continue
        if pid not in row_ids:
            raise RuntimeError("parent outside discovery geometry")
        p=next_row[pid]
        edges.append({
            "sourceGroupId":r["sourceGroupId"],
            "childObservationId":r["observationId"],
            "parentObservationId":pid,
            "childScale":r["proposalScale"],
            "parentScale":r["parentScale"],
            "childRegime":mapping[r["observationId"]],
            "parentRegime":mapping[pid],
        })
    return edges


def score_edges(edges: list[dict[str,str]], labels: dict[str,str]) -> tuple[dict[str,dict[str,Any]],dict[str,int],dict[str,int]]:
    key_counts=Counter()
    key_sources=defaultdict(set)
    child_context=Counter()
    scale_parent=Counter()
    scale_total=Counter()
    for e in edges:
        crg=labels[e["childObservationId"]]
        prg=labels[e["parentObservationId"]]
        cs=e["childScale"]; ps=e["parentScale"]
        k=key_string(cs,crg,ps,prg)
        key_counts[k]+=1
        key_sources[k].add(e["sourceGroupId"])
        child_context[(cs,crg,ps)]+=1
        scale_parent[(cs,ps,prg)]+=1
        scale_total[(cs,ps)]+=1
    scores={}
    for k,n in sorted(key_counts.items()):
        left,right=k.split("->")
        cs,crg=left.split("|"); ps,prg=right.split("|")
        denom=child_context[(cs,crg,ps)]
        baseline=scale_parent[(cs,ps,prg)]/scale_total[(cs,ps)]
        cond=n/denom if denom else 0.0
        lift=cond/baseline if baseline else 0.0
        scores[k]={
            "occurrences":int(n),
            "distinctSources":len(key_sources[k]),
            "conditionalProbability":float(cond),
            "scalePairParentMarginal":float(baseline),
            "lift":float(lift),
        }
    return scores,{str(k):int(v) for k,v in child_context.items()},{str(k):int(v) for k,v in scale_total.items()}


def permuted_labels(rows: list[dict[str,Any]], base: dict[str,str], iteration: int) -> dict[str,str]:
    strata=defaultdict(list)
    for r in rows:
        strata[(r["sourceGroupId"],r["proposalScale"])].append(r["observationId"])
    rng=np.random.default_rng(null_seed(iteration))
    out={}
    for stratum in sorted(strata):
        ids=sorted(strata[stratum])
        values=np.asarray([base[oid] for oid in ids],dtype=object)
        perm=rng.permutation(len(values))
        for oid,idx in zip(ids,perm):
            out[oid]=str(values[int(idx)])
    return out


def source_distribution(edges: list[dict[str,str]], labels: dict[str,str], target: str) -> dict[str,Any]:
    per_source=Counter()
    for e in edges:
        k=key_string(e["childScale"],labels[e["childObservationId"]],e["parentScale"],labels[e["parentObservationId"]])
        if k==target:
            per_source[e["sourceGroupId"]]+=1
    counts=sorted(per_source.values())
    return {
        "distinctSources":len(counts),
        "minOccurrencesPerSupportingSource":min(counts) if counts else 0,
        "medianOccurrencesPerSupportingSource":float(np.median(counts)) if counts else 0.0,
        "maxOccurrencesPerSupportingSource":max(counts) if counts else 0,
    }


def main() -> None:
    ap=argparse.ArgumentParser()
    ap.add_argument("--geometry",type=Path,required=True)
    ap.add_argument("--mapping",type=Path,required=True)
    ap.add_argument("--out",type=Path,required=True)
    args=ap.parse_args()

    global next_row
    rows,next_row=load_geometry(args.geometry)
    mapping=load_mapping(args.mapping)
    edges=build_edges(rows,mapping)

    observed,child_context,scale_total=score_edges(edges,mapping)
    all_keys=sorted(observed)
    null_lifts={k:[] for k in all_keys}

    for i in range(NULL_ITERATIONS):
        labels=permuted_labels(rows,mapping,i)
        scores,_,_=score_edges(edges,labels)
        for k in all_keys:
            null_lifts[k].append(float(scores.get(k,{}).get("lift",0.0)))

    adjudicated=[]
    for k in all_keys:
        s=observed[k]
        null=np.asarray(null_lifts[k],dtype=float)
        q99=float(np.quantile(null,NULL_Q))
        excess=float(s["lift"]-q99)
        gates={
            "occurrences":s["occurrences"]>=MIN_OCC,
            "distinctSources":s["distinctSources"]>=MIN_SOURCES,
            "conditionalProbability":s["conditionalProbability"]>=MIN_CONDITIONAL,
            "lift":s["lift"]>=MIN_LIFT,
            "aboveNullQ99":s["lift"]>q99,
        }
        adjudicated.append({
            "transitionKey":k,
            **s,
            "nullMeanLift":float(null.mean()),
            "nullQ99Lift":q99,
            "nullExcessLift":excess,
            "allGatesPass":all(gates.values()),
            "gates":gates,
            "sourceSupport":source_distribution(edges,mapping,k),
        })

    eligible=[r for r in adjudicated if r["allGatesPass"]]
    eligible.sort(key=lambda r:(-r["distinctSources"],-r["nullExcessLift"],-r["occurrences"],r["transitionKey"]))
    harvested=eligible[:MAX_CANDIDATES]
    harvested_keys={r["transitionKey"] for r in harvested}
    for r in adjudicated:
        r["harvested"]=r["transitionKey"] in harvested_keys

    out={
        "schema":"mark_regime_transition_pairwise_discovery_v47_v1",
        "experimentId":EXPERIMENT_ID,
        "geometrySha256":GEOMETRY_SHA256,
        "mappingSha256":MAPPING_SHA256,
        "rows":len(rows),
        "sources":len(set(r["sourceGroupId"] for r in rows)),
        "linkedEdges":len(edges),
        "null":{
            "iterations":NULL_ITERATIONS,
            "seedFormula":"first 64 bits of SHA256('mark:regime-transition-grammar:v47|pairwise-null|ITERATION') interpreted unsigned big-endian",
            "shuffle":"within each sourceGroupId x proposalScale stratum",
            "quantile":NULL_Q,
        },
        "candidateThresholds":{
            "minimumOccurrences":MIN_OCC,
            "minimumDistinctSources":MIN_SOURCES,
            "minimumConditionalProbability":MIN_CONDITIONAL,
            "minimumLift":MIN_LIFT,
            "requireObservedLiftStrictlyAboveNullQ99":True,
            "maximumHarvested":MAX_CANDIDATES,
        },
        "observedTransitionKeys":len(adjudicated),
        "eligibleBeforeCap":len(eligible),
        "harvestedCount":len(harvested),
        "harvested":[r["transitionKey"] for r in harvested],
        "transitions":adjudicated,
        "validationOpened":False,
        "confirmationOpened":False,
        "provenanceConsumed":False,
    }
    args.out.mkdir(parents=True,exist_ok=True)
    (args.out/"pairwise-discovery.json").write_text(json.dumps(out,indent=2)+"\n")
    print(json.dumps({
        "linkedEdges":len(edges),
        "observedTransitionKeys":len(adjudicated),
        "eligibleBeforeCap":len(eligible),
        "harvestedCount":len(harvested),
        "harvested":out["harvested"],
    },indent=2))

if __name__=="__main__":
    main()
