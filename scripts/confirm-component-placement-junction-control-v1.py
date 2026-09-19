#!/usr/bin/env python3
"""Confirm holdout-validated component-placement junction laws on untouched control.

This file may be committed before the holdout result exists. It cannot execute
without an exact frozen holdout validation plus a holdout freeze that binds that
validation by file SHA and canonical result SHA.
"""
from __future__ import annotations
import argparse, glob, hashlib, json, pathlib

ap=argparse.ArgumentParser()
ap.add_argument("--metrics-glob",required=True)
ap.add_argument("--train-catalogue",required=True)
ap.add_argument("--train-freeze",required=True)
ap.add_argument("--holdout-validation",required=True)
ap.add_argument("--holdout-freeze",required=True)
ap.add_argument("--placement-map",required=True)
ap.add_argument("--protocol",required=True)
ap.add_argument("--out",required=True)
args=ap.parse_args()

TRAIN_SHA="6e1d0b4a9d093e38423108a3711cc3bd32ee2a68668b078fd332401f24bf7543"
PLACEMENT_SHA="0e4663fa5595df96f09800472458c86258b348fba64325bea1f102200fa0b1ba"

protocol=json.loads(pathlib.Path(args.protocol).read_text())
train=json.loads(pathlib.Path(args.train_catalogue).read_text())
train_freeze=json.loads(pathlib.Path(args.train_freeze).read_text())
hold_path=pathlib.Path(args.holdout_validation)
hold_bytes=hold_path.read_bytes()
hold=json.loads(hold_bytes)
hold_freeze=json.loads(pathlib.Path(args.holdout_freeze).read_text())
pmap=json.loads(pathlib.Path(args.placement_map).read_text())

if train.get("catalogueSha256")!=TRAIN_SHA or train_freeze.get("catalogueSha256")!=TRAIN_SHA:
    raise SystemExit("train catalogue custody mismatch")
if train_freeze.get("placementMapSha256")!=PLACEMENT_SHA or pmap.get("placementMapSha256")!=PLACEMENT_SHA:
    raise SystemExit("placement map custody mismatch")
if hold_freeze.get("status")!="FROZEN_BEFORE_CONTROL_PLACEMENT_LAW_JOIN":
    raise SystemExit("holdout freeze status mismatch")
if hold_freeze.get("controlJoined") or hold_freeze.get("provenanceOpened"):
    raise SystemExit("holdout freeze is not sealed before control")
if hold_freeze.get("trainCatalogueSha256")!=TRAIN_SHA or hold_freeze.get("placementMapSha256")!=PLACEMENT_SHA:
    raise SystemExit("holdout freeze parent custody mismatch")
if hashlib.sha256(hold_bytes).hexdigest()!=hold_freeze.get("holdoutValidationFileSha256"):
    raise SystemExit("holdout validation file SHA mismatch")
hold_core={k:v for k,v in hold.items() if k!="holdoutValidationSha256"}
hold_sha=hashlib.sha256(json.dumps(hold_core,sort_keys=True,separators=(",",":")).encode()).hexdigest()
if hold_sha!=hold.get("holdoutValidationSha256") or hold_sha!=hold_freeze.get("holdoutValidationSha256"):
    raise SystemExit("holdout validation canonical SHA mismatch")
if hold.get("status")!="FROZEN_BEFORE_CONTROL_PLACEMENT_LAW_JOIN" or hold.get("controlJoined") or hold.get("provenanceOpened"):
    raise SystemExit("holdout validation custody mismatch")
if hold.get("trainCatalogueSha256")!=TRAIN_SHA or hold.get("placementMapSha256")!=PLACEMENT_SHA:
    raise SystemExit("holdout validation parent mismatch")
if pmap.get("provenanceOpened") or pmap.get("occupantTokenUsed") or pmap.get("familyIdUsed"):
    raise SystemExit("placement map contamination guard failed")

sources=[]
for path in sorted(glob.glob(args.metrics_glob)):
    for line in pathlib.Path(path).read_text().splitlines():
        if line.strip(): sources.append(json.loads(line))
ids=[x["sourceGroupId"] for x in sources]
if len(sources)!=232 or len(set(ids))!=232:
    raise SystemExit(f"expected 232 unique control sources, got {len(sources)} rows / {len(set(ids))} unique")
if any(x["originalBlindLane"]!="control" or x.get("provenanceOpened") for x in sources):
    raise SystemExit("control lane/provenance custody failure")
if any(x.get("placementMapSha256")!=PLACEMENT_SHA for x in sources):
    raise SystemExit("control metric placement-map mismatch")

by={}
for s in sources:
    for row in s["rows"]:
        if row["placementToken"]=="UNPLACED":
            continue
        by.setdefault((row["degree"],row["placementToken"],row["contextArm"]),[]).append(row)

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
    degree,placement,arm=key
    c=counts_for(key); n=c["eligibleSources"]; m=c["strictMatchSources"]; r=c["strictReverseSources"]
    if n<10: cls="INSUFFICIENT_SOURCES"
    elif m and r: cls="MIXED"
    elif m: cls="MATCH_ONLY"
    elif r: cls="REVERSE_ONLY"
    else: cls="UNRESOLVED"
    diagnostics.append({"degree":degree,"placementToken":placement,"contextArm":arm,**c,"classification":cls})

required=int(protocol["validation"]["perCandidateRequiredEligibleSources"])
holdout_pass=[x for x in hold["candidateResults"] if x["validationVerdict"]=="PASS"]
control_results=[]
for cand in holdout_pass:
    key=(cand["degree"],cand["placementToken"],cand["contextArm"])
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
    control_results.append({
      "degree":cand["degree"],"placementToken":cand["placementToken"],"contextArm":cand["contextArm"],
      "frozenDirection":direction,**c,"decidedSources":decided,
      "reproducedDirectionSources":reproduced,"oppositeStrictSources":opposite,
      "reproductionRateAmongDecided":ratio,"confirmationVerdict":verdict
    })

control_by={(x["degree"],x["placementToken"],x["contextArm"]):x for x in control_results}
final_candidates=[]
for h in hold["candidateResults"]:
    key=(h["degree"],h["placementToken"],h["contextArm"])
    if h["validationVerdict"]!="PASS":
        final="ELIMINATED_AT_HOLDOUT"
        c=None
    else:
        c=control_by[key]
        final="SURVIVES_TRAIN_HOLDOUT_CONTROL" if c["confirmationVerdict"]=="PASS" else "ELIMINATED_AT_CONTROL"
    final_candidates.append({
      "degree":h["degree"],"placementToken":h["placementToken"],"contextArm":h["contextArm"],
      "trainDirection":h["frozenDirection"],"holdoutVerdict":h["validationVerdict"],
      "controlVerdict":None if c is None else c["confirmationVerdict"],"finalStatus":final
    })

mixed=[x for x in diagnostics if x["classification"]=="MIXED"]
core={
 "schema":"component_placement_junction_control_confirmation_v1",
 "status":"FINAL_BLIND_COMPONENT_PLACEMENT_TEST_COMPLETE",
 "trainCatalogueSha256":TRAIN_SHA,
 "holdoutValidationSha256":hold["holdoutValidationSha256"],
 "placementMapSha256":PLACEMENT_SHA,
 "controlSourceCount":len(sources),
 "controlResults":control_results,
 "finalCandidates":final_candidates,
 "diagnostics":diagnostics,
 "summary":{
   "trainCandidates":len(train["catalogue"]),
   "holdoutPassed":len(holdout_pass),
   "controlPassed":sum(x["confirmationVerdict"]=="PASS" for x in control_results),
   "controlFailed":sum(x["confirmationVerdict"]=="FAIL" for x in control_results),
   "controlInsufficient":sum(x["confirmationVerdict"]=="INSUFFICIENT_ELIGIBLE_SOURCES" for x in control_results),
   "survivedAllThreeLanes":sum(x["finalStatus"]=="SURVIVES_TRAIN_HOLDOUT_CONTROL" for x in final_candidates),
   "mixedControlCells":len(mixed),
   "placementStillInsufficientOnControl":bool(mixed)
 },
 "interpretationGuard":{
   "placementMayBeARealStateCoordinate":True,
   "placementSufficient":False,
   "reason":"Train already met the preregistered falsifier: some identical degree + frozen masked placement + arm cells contain both strict matching and strict reversal. Holdout/control measure transfer and surviving substructure; they cannot retroactively make the placement coordinate sufficient."
 },
 "provenanceOpened":False
}
sha=hashlib.sha256(json.dumps(core,sort_keys=True,separators=(",",":")).encode()).hexdigest()
result={**core,"controlConfirmationSha256":sha}
out=pathlib.Path(args.out); out.parent.mkdir(parents=True,exist_ok=True)
out.write_text(json.dumps(result,indent=2)+"\n")
print(json.dumps({
  "controlConfirmationSha256":sha,
  "summary":core["summary"],
  "survivingCandidates":[x for x in final_candidates if x["finalStatus"]=="SURVIVES_TRAIN_HOLDOUT_CONTROL"]
},indent=2))
