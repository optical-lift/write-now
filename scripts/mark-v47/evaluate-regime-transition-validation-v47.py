#!/usr/bin/env python3
"""No-refit validation for the seven frozen V47 pairwise transition rules."""
from __future__ import annotations

import argparse, hashlib, json, math
from collections import Counter, defaultdict
from pathlib import Path

GEOMETRY_SHA="2108eec52d9f20539305a98a56d59dd0abc9d0904d3ca8f02fb541e221cefe40"
MAPPING_SHA="633918a3bad435adfdef9859a33743b9fa88bfcf59a79a4ed8a59b71141d9d90"
PAIRWISE_SHA="e0623f374b3d065288ded3c9c4a1ff636835632b8675ba081045bedfabe564ff"
EXPECTED_ROWS=2332
EXPECTED_SOURCES=59
EXPECTED_EDGES=2273
MIN_CONTEXT=10
MIN_TARGET_SOURCES=3
MIN_COND=0.50
MIN_LIFT=1.25


def sha(path:Path)->str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for c in iter(lambda:f.read(1024*1024),b""): h.update(c)
    return h.hexdigest()


def load_geometry(path:Path):
    if sha(path)!=GEOMETRY_SHA: raise RuntimeError("validation geometry hash drift")
    rows=[]; by_id={}
    with path.open() as f:
        for line in f:
            r=json.loads(line)
            if r.get("schema")!="mark_regime_transition_geometry_row_v47_v1": raise RuntimeError("geometry schema drift")
            if "regimeId" in r: raise RuntimeError("regime leaked into geometry")
            rows.append(r); by_id[r["observationId"]]=r
    if len(rows)!=EXPECTED_ROWS or len(set(r["sourceGroupId"] for r in rows))!=EXPECTED_SOURCES: raise RuntimeError("validation geometry inventory drift")
    return rows,by_id


def load_mapping(path:Path):
    if sha(path)!=MAPPING_SHA: raise RuntimeError("mapping hash drift")
    arr=json.loads(path.read_text()); return {r["observationId"]:r["regimeId"] for r in arr}


def parse_key(k:str):
    left,right=k.split("->")
    cs,crg=left.split("|"); ps,prg=right.split("|")
    return cs,crg,ps,prg


def bernoulli_logloss(hits:int,total:int,p:float)->float:
    if total<=0: return 0.0
    eps=1e-15
    p=min(1-eps,max(eps,p))
    misses=total-hits
    return -(hits*math.log2(p)+misses*math.log2(1-p))/total


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--geometry",type=Path,required=True)
    ap.add_argument("--mapping",type=Path,required=True)
    ap.add_argument("--pairwise-discovery",type=Path,required=True)
    ap.add_argument("--out",type=Path,required=True)
    args=ap.parse_args()

    if sha(args.pairwise_discovery)!=PAIRWISE_SHA: raise RuntimeError("pairwise discovery hash drift")
    pair=json.loads(args.pairwise_discovery.read_text())
    candidates=[r for r in pair["transitions"] if r.get("harvested")]
    if len(candidates)!=7: raise RuntimeError("frozen candidate count drift")

    rows,by_id=load_geometry(args.geometry); mapping=load_mapping(args.mapping)
    row_ids=set(by_id)
    if any(oid not in mapping for oid in row_ids): raise RuntimeError("missing regime mapping")

    edges=[]
    for r in rows:
        pid=r["parentObservationId"]
        if pid is None: continue
        if pid not in by_id: raise RuntimeError("parent outside validation geometry")
        edges.append({
            "sourceGroupId":r["sourceGroupId"],
            "childScale":r["proposalScale"],
            "childRegime":mapping[r["observationId"]],
            "parentScale":r["parentScale"],
            "parentRegime":mapping[pid],
        })
    if len(edges)!=EXPECTED_EDGES: raise RuntimeError("validation edge count drift")

    scale_parent=Counter(); scale_total=Counter()
    for e in edges:
        scale_parent[(e["childScale"],e["parentScale"],e["parentRegime"])]+=1
        scale_total[(e["childScale"],e["parentScale"])]+=1

    adjudicated=[]
    for d in candidates:
        key=d["transitionKey"]; cs,crg,ps,prg=parse_key(key)
        ctx=[e for e in edges if e["childScale"]==cs and e["childRegime"]==crg and e["parentScale"]==ps]
        hits=[e for e in ctx if e["parentRegime"]==prg]
        total=len(ctx); hit_n=len(hits)
        hit_sources=len(set(e["sourceGroupId"] for e in hits))
        cond=hit_n/total if total else 0.0
        base=scale_parent[(cs,ps,prg)]/scale_total[(cs,ps)] if scale_total[(cs,ps)] else 0.0
        lift=cond/base if base else 0.0

        p_rule=float(d["conditionalProbability"])
        p_base=float(d["scalePairParentMarginal"])
        rule_loss=bernoulli_logloss(hit_n,total,p_rule)
        base_loss=bernoulli_logloss(hit_n,total,p_base)
        gain=base_loss-rule_loss

        insufficient=total<MIN_CONTEXT or hit_sources<MIN_TARGET_SOURCES
        if insufficient:
            status="INSUFFICIENT_CONTRAST"
            gates=None
        else:
            gates={
                "conditionalProbability":cond>=MIN_COND,
                "lift":lift>=MIN_LIFT,
                "frozenPredictiveGain":gain>0.0,
            }
            status="TRANSFERRED" if all(gates.values()) else "REJECTED_ON_VALIDATION"

        adjudicated.append({
            "transitionKey":key,
            "status":status,
            "validationContextOccurrences":total,
            "validationTargetOccurrences":hit_n,
            "validationTargetDistinctSources":hit_sources,
            "validationConditionalProbability":cond,
            "validationScalePairParentMarginal":base,
            "validationLift":lift,
            "discoveryFrozenConditionalProbability":p_rule,
            "discoveryFrozenScalePairParentMarginal":p_base,
            "frozenRuleLogLossBits":rule_loss,
            "frozenBaselineLogLossBits":base_loss,
            "frozenPredictiveGainBitsPerEdge":gain,
            "gates":gates,
        })

    transferred=sum(r["status"]=="TRANSFERRED" for r in adjudicated)
    rejected=sum(r["status"]=="REJECTED_ON_VALIDATION" for r in adjudicated)
    insufficient=sum(r["status"]=="INSUFFICIENT_CONTRAST" for r in adjudicated)
    supported=(rejected==0 and transferred>=5)

    out={
        "schema":"mark_regime_transition_pairwise_validation_v47_v1",
        "experimentId":"mark:regime-transition-grammar:v47",
        "geometrySha256":GEOMETRY_SHA,
        "mappingSha256":MAPPING_SHA,
        "pairwiseDiscoverySha256":PAIRWISE_SHA,
        "linkedEdges":len(edges),
        "criteria":{
            "minimumContextOccurrences":MIN_CONTEXT,
            "minimumTargetDistinctSources":MIN_TARGET_SOURCES,
            "minimumConditionalProbability":MIN_COND,
            "minimumLift":MIN_LIFT,
            "requirePositiveFrozenPredictiveGain":True,
            "overallRequireNoRejectedRules":True,
            "overallMinimumTransferredRules":5,
        },
        "rules":adjudicated,
        "counts":{"transferred":transferred,"rejected":rejected,"insufficientContrast":insufficient},
        "status":"VALIDATION_SUPPORTED" if supported else "VALIDATION_RESIDUAL",
        "validationSupported":supported,
        "refitPerformed":False,
        "confirmationOpened":False,
        "provenanceConsumed":False,
    }
    args.out.mkdir(parents=True,exist_ok=True)
    (args.out/"pairwise-validation.json").write_text(json.dumps(out,indent=2)+"\n")
    print(json.dumps({
        "status":out["status"],
        "transferred":transferred,
        "rejected":rejected,
        "insufficientContrast":insufficient,
        "rules":[{"key":r["transitionKey"],"status":r["status"]} for r in adjudicated],
    },indent=2))

if __name__=="__main__":
    main()
