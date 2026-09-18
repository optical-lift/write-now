#!/usr/bin/env python3
"""V47 discovery-only higher-order regime-program harvest.

Tests whether length-3 and length-4 cross-scale regime histories improve
prediction of the next regime beyond the frozen first-order transition model.
Uses the same 100 deterministic source x scale preserving label permutations.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy as np

EXPERIMENT_ID="mark:regime-transition-grammar:v47"
GEOMETRY_SHA256="480c174ff503ad877f5d08cdf0dae78007750334873045bd0d8e91a9e8513f55"
MAPPING_SHA256="633918a3bad435adfdef9859a33743b9fa88bfcf59a79a4ed8a59b71141d9d90"
PAIRWISE_RESULT_SHA256="e0623f374b3d065288ded3c9c4a1ff636835632b8675ba081045bedfabe564ff"
EXPECTED_ROWS=5305
EXPECTED_SOURCES=171
REGIMES=["RG-001","RG-002","RG-003","RG-004","RG-005"]
ALPHA=0.5
NULL_ITERATIONS=100
NULL_Q=0.99
MIN_OCC=20
MIN_SOURCES=10
MIN_DOMINANT_PROB=0.50
MAX_PER_LENGTH=15


def sha(path:Path)->str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for c in iter(lambda:f.read(1024*1024),b""):
            h.update(c)
    return h.hexdigest()


def null_seed(iteration:int)->int:
    material=f"{EXPERIMENT_ID}|higher-order-null|{iteration}".encode()
    return int.from_bytes(hashlib.sha256(material).digest()[:8],"big",signed=False)


def load_geometry(path:Path):
    if sha(path)!=GEOMETRY_SHA256: raise RuntimeError("geometry hash drift")
    rows=[]; by_id={}
    with path.open() as f:
        for line in f:
            r=json.loads(line)
            if r.get("schema")!="mark_regime_transition_geometry_row_v47_v1": raise RuntimeError("schema drift")
            if "regimeId" in r: raise RuntimeError("regime leaked into geometry")
            rows.append(r); by_id[r["observationId"]]=r
    if len(rows)!=EXPECTED_ROWS or len(set(r["sourceGroupId"] for r in rows))!=EXPECTED_SOURCES: raise RuntimeError("inventory drift")
    return rows,by_id


def load_mapping(path:Path):
    if sha(path)!=MAPPING_SHA256: raise RuntimeError("mapping hash drift")
    arr=json.loads(path.read_text()); out={}
    for r in arr:
        if r["regimeId"] not in REGIMES: raise RuntimeError("bad regime")
        out[r["observationId"]]=r["regimeId"]
    return out


def chain_ids(rows,by_id,length:int):
    chains=[]
    for r in rows:
        ids=[r["observationId"]]; cur=r
        while len(ids)<length and cur["parentObservationId"] is not None:
            pid=cur["parentObservationId"]
            if pid not in by_id: break
            ids.append(pid); cur=by_id[pid]
        if len(ids)==length:
            chains.append((r["sourceGroupId"],ids))
    return chains


def strata_permutation(rows,base,iteration):
    strata=defaultdict(list)
    for r in rows: strata[(r["sourceGroupId"],r["proposalScale"])].append(r["observationId"])
    rng=np.random.default_rng(null_seed(iteration)); out={}
    for key in sorted(strata):
        ids=sorted(strata[key]); vals=np.asarray([base[i] for i in ids],dtype=object)
        perm=rng.permutation(len(vals))
        for oid,j in zip(ids,perm): out[oid]=str(vals[int(j)])
    return out


def smoothed_probs(counts:Counter,total:int):
    denom=total+ALPHA*len(REGIMES)
    return {rg:(counts[rg]+ALPHA)/denom for rg in REGIMES}


def first_order_tables(rows,by_id,labels):
    counts=defaultdict(Counter); totals=Counter(); scale_counts=defaultdict(Counter); scale_totals=Counter()
    for r in rows:
        pid=r["parentObservationId"]
        if pid is None: continue
        p=by_id[pid]
        ctx=(r["proposalScale"],labels[r["observationId"]],p["proposalScale"])
        rg=labels[pid]
        counts[ctx][rg]+=1; totals[ctx]+=1
        sctx=(r["proposalScale"],p["proposalScale"])
        scale_counts[sctx][rg]+=1; scale_totals[sctx]+=1
    first={ctx:smoothed_probs(counts[ctx],totals[ctx]) for ctx in counts}
    scale={ctx:smoothed_probs(scale_counts[ctx],scale_totals[ctx]) for ctx in scale_counts}
    return first,scale


def context_key(ids,by_id,labels):
    prefix=[]
    for oid in ids[:-1]:
        r=by_id[oid]; prefix.append(f'{r["proposalScale"]}|{labels[oid]}')
    next_scale=by_id[ids[-1]]["proposalScale"]
    return ">".join(prefix)+f"->{next_scale}"


def program_key(ids,by_id,labels):
    parts=[f'{by_id[oid]["proposalScale"]}|{labels[oid]}' for oid in ids]
    return ">".join(parts)


def evaluate(rows,by_id,labels,length:int,chains):
    first,scale=first_order_tables(rows,by_id,labels)
    ctx_counts=defaultdict(Counter); ctx_total=Counter(); ctx_sources=defaultdict(lambda:defaultdict(set))
    examples=defaultdict(list)
    for src,ids in chains:
        ck=context_key(ids,by_id,labels); next_rg=labels[ids[-1]]
        ctx_counts[ck][next_rg]+=1; ctx_total[ck]+=1; ctx_sources[ck][next_rg].add(src)
        examples[ck].append((src,ids,next_rg))
    out={}
    for ck,total in sorted(ctx_total.items()):
        hp=smoothed_probs(ctx_counts[ck],total)
        higher_loss=0.0; first_loss=0.0; scale_loss=0.0
        for src,ids,next_rg in examples[ck]:
            prev=by_id[ids[-2]]; last=by_id[ids[-1]]
            fctx=(prev["proposalScale"],labels[ids[-2]],last["proposalScale"])
            sctx=(prev["proposalScale"],last["proposalScale"])
            higher_loss += -math.log2(hp[next_rg])
            first_loss += -math.log2(first[fctx][next_rg])
            scale_loss += -math.log2(scale[sctx][next_rg])
        higher_loss/=total; first_loss/=total; scale_loss/=total
        dominant=max(REGIMES,key=lambda rg:(ctx_counts[ck][rg],-REGIMES.index(rg)))
        dom_n=ctx_counts[ck][dominant]
        # Full program key = context prefix plus dominant final state.
        prefix=ck.rsplit("->",1)[0]; next_scale=ck.rsplit("->",1)[1]
        pk=prefix+f">{next_scale}|{dominant}"
        out[ck]={
            "contextKey":ck,
            "programKey":pk,
            "length":length,
            "contextOccurrences":int(total),
            "dominantNextRegime":dominant,
            "dominantOccurrences":int(dom_n),
            "dominantDistinctSources":len(ctx_sources[ck][dominant]),
            "dominantProbability":float(dom_n/total),
            "higherOrderLogLossBits":float(higher_loss),
            "firstOrderLogLossBits":float(first_loss),
            "scaleOnlyLogLossBits":float(scale_loss),
            "gainOverFirstOrderBits":float(first_loss-higher_loss),
            "gainOverScaleOnlyBits":float(scale_loss-higher_loss),
        }
    return out


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--geometry",type=Path,required=True)
    ap.add_argument("--mapping",type=Path,required=True)
    ap.add_argument("--pairwise-result",type=Path,required=True)
    ap.add_argument("--out",type=Path,required=True)
    args=ap.parse_args()

    if sha(args.pairwise_result)!=PAIRWISE_RESULT_SHA256: raise RuntimeError("pairwise result hash drift")
    pair=json.loads(args.pairwise_result.read_text())
    if pair.get("harvestedCount",0)<1: raise RuntimeError("Phase B not authorized")

    rows,by_id=load_geometry(args.geometry); mapping=load_mapping(args.mapping)
    if any(r["observationId"] not in mapping for r in rows): raise RuntimeError("missing regime mapping")

    results={}
    for length in (3,4):
        chains=chain_ids(rows,by_id,length)
        observed=evaluate(rows,by_id,mapping,length,chains)
        null_gain={k:[] for k in observed}
        for i in range(NULL_ITERATIONS):
            labels=strata_permutation(rows,mapping,i)
            scored=evaluate(rows,by_id,labels,length,chains)
            for k in observed:
                null_gain[k].append(float(scored.get(k,{}).get("gainOverFirstOrderBits",0.0)))
        adjudicated=[]
        for k,r in observed.items():
            arr=np.asarray(null_gain[k],dtype=float)
            q99=float(np.quantile(arr,NULL_Q))
            gates={
                "dominantOccurrences":r["dominantOccurrences"]>=MIN_OCC,
                "dominantDistinctSources":r["dominantDistinctSources"]>=MIN_SOURCES,
                "dominantProbability":r["dominantProbability"]>=MIN_DOMINANT_PROB,
                "improvesFirstOrder":r["gainOverFirstOrderBits"]>0.0,
                "aboveNullQ99":r["gainOverFirstOrderBits"]>q99,
            }
            adjudicated.append({
                **r,
                "nullMeanGainOverFirstOrderBits":float(arr.mean()),
                "nullQ99GainOverFirstOrderBits":q99,
                "nullExcessGainBits":float(r["gainOverFirstOrderBits"]-q99),
                "gates":gates,
                "allGatesPass":all(gates.values()),
            })
        eligible=[r for r in adjudicated if r["allGatesPass"]]
        eligible.sort(key=lambda r:(-r["dominantDistinctSources"],-r["nullExcessGainBits"],-r["dominantOccurrences"],r["programKey"]))
        harvested=eligible[:MAX_PER_LENGTH]
        hkeys={r["programKey"] for r in harvested}
        for r in adjudicated: r["harvested"]=r["programKey"] in hkeys
        results[str(length)]={
            "chainCount":len(chains),
            "observedContexts":len(adjudicated),
            "eligibleBeforeCap":len(eligible),
            "harvested":[r["programKey"] for r in harvested],
            "contexts":adjudicated,
        }

    out={
        "schema":"mark_regime_transition_higher_order_discovery_v47_v1",
        "experimentId":EXPERIMENT_ID,
        "geometrySha256":GEOMETRY_SHA256,
        "mappingSha256":MAPPING_SHA256,
        "pairwiseResultSha256":PAIRWISE_RESULT_SHA256,
        "smoothing":{"method":"symmetric additive","alpha":ALPHA,"regimeCount":len(REGIMES)},
        "prediction":{
            "higherOrder":"P(next RG | complete prior scale+RG history and next scale)",
            "firstOrder":"P(next RG | immediate prior scale+RG and next scale)",
            "scaleOnly":"P(next RG | immediate prior scale and next scale)",
            "metric":"mean negative log2 likelihood over chains sharing an observed context",
        },
        "null":{
            "iterations":NULL_ITERATIONS,
            "seedFormula":"first 64 bits of SHA256('mark:regime-transition-grammar:v47|higher-order-null|ITERATION') unsigned big-endian",
            "shuffle":"within each sourceGroupId x proposalScale stratum",
            "quantile":NULL_Q,
        },
        "candidateThresholds":{
            "minimumDominantOccurrences":MIN_OCC,
            "minimumDominantDistinctSources":MIN_SOURCES,
            "minimumDominantProbability":MIN_DOMINANT_PROB,
            "requirePositiveHeldInGainOverFirstOrder":True,
            "requireGainStrictlyAboveMatchedNullQ99":True,
            "maximumHarvestedPerLength":MAX_PER_LENGTH,
        },
        "lengths":results,
        "validationOpened":False,
        "confirmationOpened":False,
        "provenanceConsumed":False,
    }
    args.out.mkdir(parents=True,exist_ok=True)
    (args.out/"higher-order-discovery.json").write_text(json.dumps(out,indent=2)+"\n")
    print(json.dumps({
        "length3Chains":results["3"]["chainCount"],
        "length3Eligible":results["3"]["eligibleBeforeCap"],
        "length3Harvested":results["3"]["harvested"],
        "length4Chains":results["4"]["chainCount"],
        "length4Eligible":results["4"]["eligibleBeforeCap"],
        "length4Harvested":results["4"]["harvested"],
    },indent=2))

if __name__=="__main__":
    main()
