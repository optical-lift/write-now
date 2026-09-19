#!/usr/bin/env python3
"""Validate the frozen degree-conditioned train catalogue on untouched holdout."""
from __future__ import annotations
import argparse, glob, hashlib, json, pathlib

ap=argparse.ArgumentParser()
ap.add_argument("--metrics-glob",required=True)
ap.add_argument("--train-freeze",required=True)
ap.add_argument("--protocol",required=True)
ap.add_argument("--out",required=True)
args=ap.parse_args()

protocol=json.loads(pathlib.Path(args.protocol).read_text())
freeze=json.loads(pathlib.Path(args.train_freeze).read_text())

EXPECTED_TRAIN_SHA="eb1b7e8e825dd09b80bcc5a25135770b7e822c0244528f1f92e0ec065fd95223"
if freeze.get("catalogueSha256")!=EXPECTED_TRAIN_SHA:
    raise SystemExit("train catalogue SHA does not match frozen preregistration")
if freeze.get("status")!="FROZEN_BEFORE_HOLDOUT_OR_CONTROL_DEGREE_OUTCOMES":
    raise SystemExit("train freeze status invalid")
if freeze.get("holdoutOpened") or freeze.get("controlOpened") or freeze.get("provenanceOpened"):
    raise SystemExit("train freeze custody already opened")
if freeze.get("hypothesisStatus")!="DEGREE_ALONE_FALSIFIED_ON_TRAIN":
    raise SystemExit("train falsification status missing")

sources=[]
for path in sorted(glob.glob(args.metrics_glob)):
    for line in pathlib.Path(path).read_text().splitlines():
        if line.strip():
            sources.append(json.loads(line))
ids=[x["sourceGroupId"] for x in sources]
if len(sources)!=236 or len(set(ids))!=236:
    raise SystemExit(f"expected 236 unique holdout sources, got {len(sources)} rows / {len(set(ids))} unique")
if any(x["originalBlindLane"]!="holdout" or x.get("provenanceOpened") for x in sources):
    raise SystemExit("holdout lane/provenance custody failure")

by={}
for s in sources:
    for row in s["rows"]:
        key=(row["degree"],row["contextArm"])
        by.setdefault(key,[]).append(row)

def counts_for(key):
    rows=[r for r in by.get(key,[]) if r["state"]!="INELIGIBLE"]
    return {
      "eligibleSources":len(rows),
      "strictMatchSources":sum(r["state"]=="STRICT_MATCH" for r in rows),
      "strictReverseSources":sum(r["state"]=="STRICT_REVERSE" for r in rows),
      "unresolvedSources":sum(r["state"]=="UNRESOLVED" for r in rows),
    }

diagnostics=[]
for key in sorted(by):
    degree,arm=key
    c=counts_for(key)
    n=c["eligibleSources"]; m=c["strictMatchSources"]; r=c["strictReverseSources"]
    if n<10:
        cls="INSUFFICIENT_SOURCES"
    elif m and r:
        cls="MIXED"
    elif m:
        cls="MATCH_ONLY"
    elif r:
        cls="REVERSE_ONLY"
    else:
        cls="UNRESOLVED"
    diagnostics.append({"degree":degree,"contextArm":arm,**c,"classification":cls})

candidate_results=[]
for cand in freeze["catalogue"]:
    key=(cand["degree"],cand["contextArm"])
    c=counts_for(key)
    decided=c["strictMatchSources"]+c["strictReverseSources"]
    direction=cand["frozenDirection"]
    reproduced=c["strictMatchSources"] if direction=="STRICT_MATCH" else c["strictReverseSources"]
    opposite=c["strictReverseSources"] if direction=="STRICT_MATCH" else c["strictMatchSources"]
    ratio=(reproduced/decided) if decided else None
    if c["eligibleSources"]<int(protocol["validation"]["per_candidate_required_eligible_sources"]):
        verdict="INSUFFICIENT_ELIGIBLE_SOURCES"
    elif reproduced>=5 and ratio is not None and ratio>=0.90:
        verdict="PASS"
    else:
        verdict="FAIL"
    candidate_results.append({
      "degree":cand["degree"],"contextArm":cand["contextArm"],
      "frozenDirection":direction,**c,
      "decidedSources":decided,"reproducedDirectionSources":reproduced,
      "oppositeStrictSources":opposite,"reproductionRateAmongDecided":ratio,
      "validationVerdict":verdict
    })

core={
 "schema":"degree_conditioned_junction_holdout_validation_v1",
 "status":"FROZEN_BEFORE_CONTROL_DEGREE_OUTCOMES",
 "trainCatalogueSha256":EXPECTED_TRAIN_SHA,
 "holdoutSourceCount":len(sources),
 "candidateResults":candidate_results,
 "diagnostics":diagnostics,
 "summary":{
   "trainCandidates":len(candidate_results),
   "passed":sum(x["validationVerdict"]=="PASS" for x in candidate_results),
   "failed":sum(x["validationVerdict"]=="FAIL" for x in candidate_results),
   "insufficient":sum(x["validationVerdict"]=="INSUFFICIENT_ELIGIBLE_SOURCES" for x in candidate_results),
   "mixedTestedCells":sum(x["classification"]=="MIXED" for x in diagnostics),
   "mixedTestedDegrees":len({x["degree"] for x in diagnostics if x["classification"]=="MIXED"}),
   "degreeAloneFalsifiedOnHoldout":any(x["classification"]=="MIXED" for x in diagnostics)
 },
 "controlOpened":False,
 "provenanceOpened":False
}
sha=hashlib.sha256(json.dumps(core,sort_keys=True,separators=(",",":")).encode()).hexdigest()
result={**core,"holdoutValidationSha256":sha}
out=pathlib.Path(args.out); out.parent.mkdir(parents=True,exist_ok=True)
out.write_text(json.dumps(result,indent=2)+"\n")
print(json.dumps({
  "holdoutValidationSha256":sha,
  "summary":core["summary"],
  "candidateResults":candidate_results
},indent=2))
