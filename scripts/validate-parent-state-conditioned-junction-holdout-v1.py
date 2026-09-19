#!/usr/bin/env python3
"""Validate frozen parent-state-conditioned sublaws on untouched holdout."""
from __future__ import annotations
import argparse, glob, hashlib, json, pathlib

ap=argparse.ArgumentParser()
ap.add_argument("--metrics-glob",required=True)
ap.add_argument("--train-catalogue",required=True)
ap.add_argument("--train-freeze",required=True)
ap.add_argument("--parent-state-map",required=True)
ap.add_argument("--target-set",required=True)
ap.add_argument("--protocol",required=True)
ap.add_argument("--out",required=True)
args=ap.parse_args()

protocol=json.loads(pathlib.Path(args.protocol).read_text())
freeze=json.loads(pathlib.Path(args.train_freeze).read_text())
train_path=pathlib.Path(args.train_catalogue)
train_bytes=train_path.read_bytes()
train=json.loads(train_bytes)
pmap=json.loads(pathlib.Path(args.parent_state_map).read_text())
targets=json.loads(pathlib.Path(args.target_set).read_text())

EXPECTED_CATALOGUE_SHA="a53c6023739e3a449ba8577fea2085c1469e6a4b4c48641c1576caf6254f2576"
EXPECTED_CATALOGUE_FILE_SHA="c592bcc71c8f0cebb3c48052a8e17eb5dd26483bc4ba9ab7ff5bf88d8efd708c"
EXPECTED_PARENT_STATE_SHA="15daa540f2f1219c12c001c1ed7a42936b7db6b9119156f0fda5dd0ae5109ee6"
EXPECTED_TARGET_SHA="92efb66137f1803c0cb74784ed20d5ec840ab72b4df12e5c5168482ab5811c55"

if freeze.get("status")!="FROZEN_BEFORE_HOLDOUT_OR_CONTROL_PARENT_STATE_JOIN":
    raise SystemExit("train freeze status mismatch")
if freeze.get("holdoutJoined") or freeze.get("controlJoined") or freeze.get("provenanceOpened"):
    raise SystemExit("train freeze custody already opened")
if freeze.get("catalogueSha256")!=EXPECTED_CATALOGUE_SHA:
    raise SystemExit("train freeze catalogue SHA mismatch")
if freeze.get("parentStateMapSha256")!=EXPECTED_PARENT_STATE_SHA:
    raise SystemExit("train freeze parent-state SHA mismatch")
if freeze.get("targetSetSha256")!=EXPECTED_TARGET_SHA:
    raise SystemExit("train freeze target-set SHA mismatch")
if hashlib.sha256(train_bytes).hexdigest()!=EXPECTED_CATALOGUE_FILE_SHA:
    raise SystemExit("train catalogue file SHA mismatch")
if train.get("catalogueSha256")!=EXPECTED_CATALOGUE_SHA:
    raise SystemExit("train embedded catalogue SHA mismatch")
core={k:v for k,v in train.items() if k!="catalogueSha256"}
calc=hashlib.sha256(json.dumps(core,sort_keys=True,separators=(",",":")).encode()).hexdigest()
if calc!=EXPECTED_CATALOGUE_SHA:
    raise SystemExit("train catalogue canonical SHA mismatch")
if pmap.get("parentStateMapSha256")!=EXPECTED_PARENT_STATE_SHA:
    raise SystemExit("parent-state map SHA mismatch")
if pmap.get("provenanceOpened") or pmap.get("targetStateUsed"):
    raise SystemExit("parent-state contamination guard failed")
if targets.get("targetSetSha256")!=EXPECTED_TARGET_SHA or targets.get("parentStateJoined"):
    raise SystemExit("target-set custody mismatch")

sources=[]
for path in sorted(glob.glob(args.metrics_glob)):
    for line in pathlib.Path(path).read_text().splitlines():
        if line.strip(): sources.append(json.loads(line))
ids=[x["sourceGroupId"] for x in sources]
if len(sources)!=236 or len(set(ids))!=236:
    raise SystemExit(f"expected 236 unique holdout sources, got {len(sources)} rows / {len(set(ids))} unique")
if any(x["originalBlindLane"]!="holdout" or x.get("provenanceOpened") for x in sources):
    raise SystemExit("holdout lane/provenance custody failure")
if any(x.get("parentStateMapSha256")!=EXPECTED_PARENT_STATE_SHA for x in sources):
    raise SystemExit("parent-state map SHA mismatch across metrics")
if any(x.get("targetSetSha256")!=EXPECTED_TARGET_SHA for x in sources):
    raise SystemExit("target-set SHA mismatch across metrics")

by={}
for s in sources:
    for row in s["rows"]:
        if row["parentStateToken"]=="UNPARENTED_STATE":
            continue
        key=(int(row["degree"]),row["placementToken"],row["parentStateToken"],row["contextArm"])
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
    degree,placement,parent_state,arm=key
    c=counts_for(key); n=c["eligibleSources"]; m=c["strictMatchSources"]; r=c["strictReverseSources"]
    if n<10: cls="INSUFFICIENT_SOURCES"
    elif m>=5 and r==0: cls="MATCH_ONLY"
    elif r>=5 and m==0: cls="REVERSE_ONLY"
    elif m>=1 and r>=1: cls="MIXED"
    else: cls="UNRESOLVED"
    diagnostics.append({
      "degree":degree,"placementToken":placement,"parentStateToken":parent_state,"contextArm":arm,
      **c,"classification":cls
    })

required=int(protocol["validation"]["perCandidateRequiredEligibleSources"])
candidate_results=[]
for cand in train["catalogue"]:
    key=(int(cand["degree"]),cand["placementToken"],cand["parentStateToken"],cand["contextArm"])
    c=counts_for(key)
    decided=c["strictMatchSources"]+c["strictReverseSources"]
    direction=cand["frozenDirection"]
    reproduced=c["strictMatchSources"] if direction=="STRICT_MATCH" else c["strictReverseSources"]
    opposite=c["strictReverseSources"] if direction=="STRICT_MATCH" else c["strictMatchSources"]
    ratio=(reproduced/decided) if decided else None
    if c["eligibleSources"]<required:
        verdict="INSUFFICIENT_ELIGIBLE_SOURCES"
    elif reproduced>=5 and ratio is not None and ratio>=0.90:
        verdict="PASS"
    else:
        verdict="FAIL"
    candidate_results.append({
      "degree":cand["degree"],"placementToken":cand["placementToken"],
      "parentStateToken":cand["parentStateToken"],"contextArm":cand["contextArm"],
      "frozenDirection":direction,**c,"decidedSources":decided,
      "reproducedDirectionSources":reproduced,"oppositeStrictSources":opposite,
      "reproductionRateAmongDecided":ratio,"validationVerdict":verdict
    })

by_target={}
for x in diagnostics:
    by_target.setdefault((x["degree"],x["placementToken"],x["contextArm"]),[]).append(x)

lane_resolutions=[]
for t in targets["targets"]:
    key=(int(t["degree"]),t["placementToken"],t["contextArm"])
    subs=[x for x in by_target.get(key,[]) if x["eligibleSources"]>=10]
    classes=[x["classification"] for x in subs]
    has_match="MATCH_ONLY" in classes
    has_reverse="REVERSE_ONLY" in classes
    has_mixed="MIXED" in classes
    if has_mixed: status="STILL_MIXED"
    elif has_match and has_reverse: status="TWO_SIDED_RESOLVED"
    elif has_match or has_reverse: status="ONE_SIDED_DECONFOUNDED"
    else: status="INSUFFICIENT_PARENT_STATE_SUPPORT"
    lane_resolutions.append({
      "degree":key[0],"placementToken":key[1],"contextArm":key[2],
      "resolutionStatus":status,
      "testableParentStates":[x["parentStateToken"] for x in subs]
    })

candidate_by_key={(int(x["degree"]),x["placementToken"],x["parentStateToken"],x["contextArm"]):x for x in candidate_results}
lane_resolution_by={(int(x["degree"]),x["placementToken"],x["contextArm"]):x for x in lane_resolutions}
one_sided_transfer=[]
for tr in train["targetResolutions"]:
    if tr["resolutionStatus"]!="ONE_SIDED_DECONFOUNDED":
        continue
    base=(int(tr["degree"]),tr["placementToken"],tr["contextArm"])
    frozen_candidates=[
      c for c in train["catalogue"]
      if (int(c["degree"]),c["placementToken"],c["contextArm"])==base
    ]
    results=[
      candidate_by_key[(int(c["degree"]),c["placementToken"],c["parentStateToken"],c["contextArm"])]
      for c in frozen_candidates
    ]
    lane_res=lane_resolution_by[base]
    reproduced=bool(results) and any(x["validationVerdict"]=="PASS" for x in results) and lane_res["resolutionStatus"]!="STILL_MIXED"
    one_sided_transfer.append({
      "degree":base[0],"placementToken":base[1],"contextArm":base[2],
      "holdoutResolutionStatus":lane_res["resolutionStatus"],
      "frozenCandidateVerdicts":[
        {"parentStateToken":x["parentStateToken"],"direction":x["frozenDirection"],"verdict":x["validationVerdict"]}
        for x in results
      ],
      "oneSidedDeconfoundingReproduced":reproduced
    })

core={
 "schema":"parent_state_conditioned_junction_holdout_validation_v1",
 "status":"FROZEN_BEFORE_CONTROL_PARENT_STATE_JOIN",
 "trainCatalogueSha256":EXPECTED_CATALOGUE_SHA,
 "parentStateMapSha256":EXPECTED_PARENT_STATE_SHA,
 "targetSetSha256":EXPECTED_TARGET_SHA,
 "holdoutSourceCount":len(sources),
 "candidateResults":candidate_results,
 "diagnostics":diagnostics,
 "targetResolutions":lane_resolutions,
 "oneSidedTransfer":one_sided_transfer,
 "summary":{
   "trainCandidates":len(train["catalogue"]),
   "passed":sum(x["validationVerdict"]=="PASS" for x in candidate_results),
   "failed":sum(x["validationVerdict"]=="FAIL" for x in candidate_results),
   "insufficient":sum(x["validationVerdict"]=="INSUFFICIENT_ELIGIBLE_SOURCES" for x in candidate_results),
   "mixedTestedParentStateSubcells":sum(x["classification"]=="MIXED" for x in diagnostics),
   "oneSidedTrainTargets":len(one_sided_transfer),
   "oneSidedReproduced":sum(x["oneSidedDeconfoundingReproduced"] for x in one_sided_transfer),
   "strongBranchSelectorAlreadyFalsifiedOnTrain":True
 },
 "controlJoined":False,
 "provenanceOpened":False
}
sha=hashlib.sha256(json.dumps(core,sort_keys=True,separators=(",",":")).encode()).hexdigest()
result={**core,"holdoutValidationSha256":sha}
out=pathlib.Path(args.out); out.parent.mkdir(parents=True,exist_ok=True)
out.write_text(json.dumps(result,indent=2)+"\n")
print(json.dumps({
 "holdoutValidationSha256":sha,
 "summary":core["summary"],
 "oneSidedTransfer":one_sided_transfer
},indent=2))
