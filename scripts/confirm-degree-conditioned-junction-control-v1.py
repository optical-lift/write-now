#!/usr/bin/env python3
"""Confirm holdout-validated degree-conditioned cells on untouched control."""
from __future__ import annotations
import argparse, glob, hashlib, json, pathlib

ap=argparse.ArgumentParser()
ap.add_argument("--metrics-glob",required=True)
ap.add_argument("--train-freeze",required=True)
ap.add_argument("--holdout-freeze",required=True)
ap.add_argument("--protocol",required=True)
ap.add_argument("--out",required=True)
args=ap.parse_args()

protocol=json.loads(pathlib.Path(args.protocol).read_text())
train=json.loads(pathlib.Path(args.train_freeze).read_text())
hold=json.loads(pathlib.Path(args.holdout_freeze).read_text())

TRAIN_SHA="eb1b7e8e825dd09b80bcc5a25135770b7e822c0244528f1f92e0ec065fd95223"
HOLDOUT_SHA="140e982e7b060076f1fed5036a4ba8bc46749a2cf93a658c312416d1421876e7"
if train.get("catalogueSha256")!=TRAIN_SHA:
    raise SystemExit("train catalogue SHA mismatch")
if hold.get("trainCatalogueSha256")!=TRAIN_SHA or hold.get("holdoutValidationSha256")!=HOLDOUT_SHA:
    raise SystemExit("holdout freeze custody mismatch")
if hold.get("status")!="FROZEN_BEFORE_CONTROL_DEGREE_OUTCOMES" or hold.get("controlOpened") or hold.get("provenanceOpened"):
    raise SystemExit("holdout freeze is not sealed before control")

sources=[]
for path in sorted(glob.glob(args.metrics_glob)):
    for line in pathlib.Path(path).read_text().splitlines():
        if line.strip():
            sources.append(json.loads(line))
ids=[x["sourceGroupId"] for x in sources]
if len(sources)!=232 or len(set(ids))!=232:
    raise SystemExit(f"expected 232 unique control sources, got {len(sources)} rows / {len(set(ids))} unique")
if any(x["originalBlindLane"]!="control" or x.get("provenanceOpened") for x in sources):
    raise SystemExit("control lane/provenance custody failure")

by={}
for s in sources:
    for row in s["rows"]:
        by.setdefault((row["degree"],row["contextArm"]),[]).append(row)

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
    c=counts_for(key); n=c["eligibleSources"]; m=c["strictMatchSources"]; r=c["strictReverseSources"]
    if n<10: cls="INSUFFICIENT_SOURCES"
    elif m and r: cls="MIXED"
    elif m: cls="MATCH_ONLY"
    elif r: cls="REVERSE_ONLY"
    else: cls="UNRESOLVED"
    diagnostics.append({"degree":degree,"contextArm":arm,**c,"classification":cls})

holdout_pass=[x for x in hold["candidateResults"] if x["validationVerdict"]=="PASS"]
control_results=[]
for cand in holdout_pass:
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
    control_results.append({
      "degree":cand["degree"],"contextArm":cand["contextArm"],"frozenDirection":direction,
      **c,"decidedSources":decided,"reproducedDirectionSources":reproduced,
      "oppositeStrictSources":opposite,"reproductionRateAmongDecided":ratio,
      "confirmationVerdict":verdict
    })

control_by={(x["degree"],x["contextArm"]):x for x in control_results}
final_candidates=[]
for h in hold["candidateResults"]:
    key=(h["degree"],h["contextArm"])
    if h["validationVerdict"]!="PASS":
        final="ELIMINATED_AT_HOLDOUT"
        c=None
    else:
        c=control_by[key]
        final="SURVIVES_TRAIN_HOLDOUT_CONTROL" if c["confirmationVerdict"]=="PASS" else "ELIMINATED_AT_CONTROL"
    final_candidates.append({
      "degree":h["degree"],"contextArm":h["contextArm"],
      "trainDirection":h["frozenDirection"],
      "holdoutVerdict":h["validationVerdict"],
      "controlVerdict":None if c is None else c["confirmationVerdict"],
      "finalStatus":final
    })

survivors=sum(x["finalStatus"]=="SURVIVES_TRAIN_HOLDOUT_CONTROL" for x in final_candidates)
mixed_control=[x for x in diagnostics if x["classification"]=="MIXED"]
core={
 "schema":"degree_conditioned_junction_control_confirmation_v1",
 "status":"FINAL_BLIND_DEGREE_TEST_COMPLETE",
 "trainCatalogueSha256":TRAIN_SHA,
 "holdoutValidationSha256":HOLDOUT_SHA,
 "controlSourceCount":len(sources),
 "controlResults":control_results,
 "finalCandidates":final_candidates,
 "diagnostics":diagnostics,
 "summary":{
   "trainCandidates":len(hold["candidateResults"]),
   "holdoutPassed":len(holdout_pass),
   "controlPassed":sum(x["confirmationVerdict"]=="PASS" for x in control_results),
   "controlFailed":sum(x["confirmationVerdict"]=="FAIL" for x in control_results),
   "controlInsufficient":sum(x["confirmationVerdict"]=="INSUFFICIENT_ELIGIBLE_SOURCES" for x in control_results),
   "survivedAllThreeLanes":survivors,
   "mixedControlCells":len(mixed_control),
   "mixedControlDegrees":len({x["degree"] for x in mixed_control}),
   "degreeAloneFalsifiedOnControl":bool(mixed_control),
   "broadHypothesisStatus":"FALSIFIED_DEGREE_ALONE" if (train["falsificationEvidence"]["mixedCells"]>0 or hold["summary"]["degreeAloneFalsifiedOnHoldout"] or mixed_control) else "NOT_FALSIFIED"
 },
 "interpretationGuard":{
   "degreeMayBeARealCondition":True,
   "degreeAloneSufficient":False,
   "reason":"The preregistered falsification condition was met before control: identical degree/context cells contained both strict matching and strict reversal across independent sources. Control characterizes surviving substructure; it cannot rescue the degree-alone hypothesis."
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
  "controlResults":control_results,
  "survivingCandidates":[x for x in final_candidates if x["finalStatus"]=="SURVIVES_TRAIN_HOLDOUT_CONTROL"]
},indent=2))
