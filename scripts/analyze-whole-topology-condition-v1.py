#!/usr/bin/env python3
"""Analyze Whole-Topology Condition Test v1 under frozen blinded rules."""
from __future__ import annotations
import argparse, glob, hashlib, json, math, pathlib, random, statistics

ap=argparse.ArgumentParser()
ap.add_argument("--metrics-glob",required=True)
ap.add_argument("--protocol",required=True)
ap.add_argument("--out",required=True)
args=ap.parse_args()
protocol=json.loads(pathlib.Path(args.protocol).read_text())

rows=[]
for path in sorted(glob.glob(args.metrics_glob)):
    for line in pathlib.Path(path).read_text().splitlines():
        if line.strip():
            rows.append(json.loads(line))
ids=[r["sourceGroupId"] for r in rows]
if len(rows)!=705 or len(set(ids))!=705:
    raise SystemExit(f"expected 705 unique untouched source rows, got rows={len(rows)} unique={len(set(ids))}")
excluded=set(protocol["sealed_universe"]["excluded_discovery_sources"])
if excluded.intersection(ids):
    raise SystemExit("hypothesis-generating source leaked into untouched test")
if any(r.get("provenanceOpened") for r in rows):
    raise SystemExit("provenance contamination")

def rankdata(vals):
    order=sorted(range(len(vals)),key=lambda i:(vals[i],i))
    ranks=[0.0]*len(vals); k=0
    while k<len(order):
        j=k+1
        while j<len(order) and vals[order[j]]==vals[order[k]]:
            j+=1
        avg=(k+1+j)/2.0
        for z in range(k,j): ranks[order[z]]=avg
        k=j
    return ranks

def pearson(a,b):
    ma=statistics.fmean(a); mb=statistics.fmean(b)
    num=sum((x-ma)*(y-mb) for x,y in zip(a,b))
    da=sum((x-ma)**2 for x in a); db=sum((y-mb)**2 for y in b)
    return num/math.sqrt(da*db) if da>0 and db>0 else 0.0

def median(xs):
    return statistics.median(xs)

def analyze_endpoint(key,seed_tag):
    eligible=[r for r in rows if r["centers"]>0 and r[key]["eligible"] and r["pairDensity"] is not None and r[key]["matchingLift"] is not None]
    eligible.sort(key=lambda r:(r["pairDensity"],r["sourceGroupId"]))
    n=len(eligible)
    if n<20: raise SystemExit(f"too few eligible sources for {key}: {n}")
    low_n=math.ceil(n/10)
    low_ids={r["sourceGroupId"] for r in eligible[:low_n]}
    y=[r[key]["matchingLift"] for r in eligible]
    x=[r["pairDensity"] for r in eligible]
    lanes=[r["originalBlindLane"] for r in eligible]
    low=[r[key]["matchingLift"] for r in eligible if r["sourceGroupId"] in low_ids]
    rest=[r[key]["matchingLift"] for r in eligible if r["sourceGroupId"] not in low_ids]
    obs_tail=median(low)-median(rest)
    xr=rankdata(x); yr=rankdata(y)
    obs_rho=pearson(xr,yr)
    obs_rev=(sum(v<0 for v in low)/len(low))-(sum(v<0 for v in rest)/len(rest))

    lane_indices={}
    for i,lane in enumerate(lanes): lane_indices.setdefault(lane,[]).append(i)
    low_mask=[eligible[i]["sourceGroupId"] in low_ids for i in range(n)]
    seed=int(hashlib.sha256(seed_tag.encode()).hexdigest()[:16],16)
    rng=random.Random(seed)
    iters=int(protocol["primary_test"]["permutation"]["iterations"])
    tail_extreme=rho_extreme=rev_extreme=0
    for _ in range(iters):
        py=y[:]
        pyr=yr[:]
        for idxs in lane_indices.values():
            vals=[py[i] for i in idxs]; rng.shuffle(vals)
            rvals=[pyr[i] for i in idxs]; rng.shuffle(rvals)
            for i,v in zip(idxs,vals): py[i]=v
            for i,v in zip(idxs,rvals): pyr[i]=v
        plow=[py[i] for i,m in enumerate(low_mask) if m]
        prest=[py[i] for i,m in enumerate(low_mask) if not m]
        stat=median(plow)-median(prest)
        if stat<=obs_tail: tail_extreme+=1
        rho=pearson(xr,pyr)
        if rho>=obs_rho: rho_extreme+=1
        rev=(sum(v<0 for v in plow)/len(plow))-(sum(v<0 for v in prest)/len(prest))
        if rev>=obs_rev: rev_extreme+=1

    lane_diag={}
    for lane,idxs in lane_indices.items():
        sub=sorted((eligible[i] for i in idxs),key=lambda r:(r["pairDensity"],r["sourceGroupId"]))
        ln=math.ceil(len(sub)/10)
        l=[r[key]["matchingLift"] for r in sub[:ln]]
        rr=[r[key]["matchingLift"] for r in sub[ln:]]
        lane_diag[lane]={
          "n":len(sub),"lowDensityN":ln,
          "tailMedianDifference":median(l)-median(rr) if rr else None,
          "spearmanRho":pearson(rankdata([r["pairDensity"] for r in sub]),rankdata([r[key]["matchingLift"] for r in sub])) if len(sub)>2 else None,
          "negativeLiftRateLow":sum(v<0 for v in l)/len(l),
          "negativeLiftRateRest":sum(v<0 for v in rr)/len(rr) if rr else None
        }

    return {
      "eligibleSources":n,
      "lowDensityN":low_n,
      "lowDensitySourceIds":[r["sourceGroupId"] for r in eligible[:low_n]],
      "pairDensityBoundaryMax":eligible[low_n-1]["pairDensity"],
      "tailMedianDifference":obs_tail,
      "tailPermutationP":(1+tail_extreme)/(iters+1),
      "spearmanRho":obs_rho,
      "spearmanPermutationP":(1+rho_extreme)/(iters+1),
      "negativeLiftRateLow":sum(v<0 for v in low)/len(low),
      "negativeLiftRateRest":sum(v<0 for v in rest)/len(rest),
      "negativeLiftRateDifference":obs_rev,
      "reversalPermutationP":(1+rev_extreme)/(iters+1),
      "medianLiftLow":median(low),
      "medianLiftRest":median(rest),
      "laneDiagnostics":lane_diag
    }

junction=analyze_endpoint("junction","whole-topology-condition-v1|junction-tail|2026-09-19")
endpoint=analyze_endpoint("endpoint","whole-topology-condition-v1|endpoint-tail|2026-09-19")
tail_pass=junction["tailMedianDifference"]<0 and junction["tailPermutationP"]<=0.01
rho_pass=junction["spearmanRho"]>0 and junction["spearmanPermutationP"]<=0.05
if tail_pass and rho_pass:
    verdict="SUPPORTS_DENSITY_CONDITION"
elif tail_pass:
    verdict="LOW_DENSITY_EFFECT_NONMONOTONIC"
else:
    verdict="NO_DENSITY_SUPPORT"

lane_counts={}
for r in rows: lane_counts[r["originalBlindLane"]]=lane_counts.get(r["originalBlindLane"],0)+1
result={
 "schema":"whole_topology_condition_test_v1_result",
 "status":"BLIND_RESULT_FROZEN_READY_FOR_PROVENANCE_REJOIN",
 "sourceCount":len(rows),
 "laneCounts":lane_counts,
 "excludedHypothesisGeneratingSources":len(excluded),
 "primaryVerdict":verdict,
 "primary":junction,
 "secondaryEndpoint":endpoint,
 "guards":{
   "provenanceOpened":False,
   "objectTypesUsed":False,
   "institutionsUsed":False,
   "alternativeTopologyPredictorsOpened":False
 }
}
payload=json.dumps(result,sort_keys=True,separators=(",",":")).encode()
result["resultSha256"]=hashlib.sha256(payload).hexdigest()
out=pathlib.Path(args.out); out.parent.mkdir(parents=True,exist_ok=True)
out.write_text(json.dumps(result,indent=2)+"\n")
print(json.dumps({"verdict":verdict,"sourceCount":len(rows),"junction":junction,"endpoint":endpoint,"resultSha256":result["resultSha256"]},indent=2))
