#!/usr/bin/env python3
"""Validate frozen component-placement junction laws on untouched holdout."""
from __future__ import annotations
import argparse, glob, hashlib, json, pathlib

ap=argparse.ArgumentParser()
ap.add_argument("--metrics-glob",required=True)
ap.add_argument("--train-catalogue",required=True)
ap.add_argument("--train-freeze",required=True)
ap.add_argument("--placement-map",required=True)
ap.add_argument("--protocol",required=True)
ap.add_argument("--out",required=True)
args=ap.parse_args()

protocol=json.loads(pathlib.Path(args.protocol).read_text())
freeze=json.loads(pathlib.Path(args.train_freeze).read_text())
train_path=pathlib.Path(args.train_catalogue)
train_bytes=train_path.read_bytes()
train=json.loads(train_bytes)
pmap=json.loads(pathlib.Path(args.placement_map).read_text())

EXPECTED_CATALOGUE_SHA="6e1d0b4a9d093e38423108a3711cc3bd32ee2a68668b078fd332401f24bf7543"
EXPECTED_PLACEMENT_SHA="0e4663fa5595df96f09800472458c86258b348fba64325bea1f102200fa0b1ba"
EXPECTED_FILE_SHA="282137a1ff9789c86f0fb41155c29a1070cceb8877c2dd988ea986462dbfada1"

if freeze.get("status")!="FROZEN_BEFORE_HOLDOUT_OR_CONTROL_PLACEMENT_LAW_JOIN":
    raise SystemExit("train freeze status mismatch")
if freeze.get("holdoutJoined") or freeze.get("controlJoined") or freeze.get("provenanceOpened"):
    raise SystemExit("train freeze custody already opened")
if freeze.get("catalogueSha256")!=EXPECTED_CATALOGUE_SHA or freeze.get("placementMapSha256")!=EXPECTED_PLACEMENT_SHA:
    raise SystemExit("train freeze hash mismatch")
if hashlib.sha256(train_bytes).hexdigest()!=EXPECTED_FILE_SHA:
    raise SystemExit("train catalogue file SHA mismatch")
if train.get("catalogueSha256")!=EXPECTED_CATALOGUE_SHA:
    raise SystemExit("train embedded catalogue SHA mismatch")
core={k:v for k,v in train.items() if k!="catalogueSha256"}
calc=hashlib.sha256(json.dumps(core,sort_keys=True,separators=(",",":")).encode()).hexdigest()
if calc!=EXPECTED_CATALOGUE_SHA:
    raise SystemExit("train catalogue canonical hash mismatch")
if pmap.get("placementMapSha256")!=EXPECTED_PLACEMENT_SHA:
    raise SystemExit("placement map SHA mismatch")
if pmap.get("provenanceOpened") or pmap.get("occupantTokenUsed") or pmap.get("familyIdUsed"):
    raise SystemExit("placement map contamination guard failed")

sources=[]
for path in sorted(glob.glob(args.metrics_glob)):
    for line in pathlib.Path(path).read_text().splitlines():
        if line.strip(): sources.append(json.loads(line))
ids=[x["sourceGroupId"] for x in sources]
if len(sources)!=236 or len(set(ids))!=236:
    raise SystemExit(f"expected 236 unique holdout sources, got {len(sources)} rows / {len(set(ids))} unique")
if any(x["originalBlindLane"]!="holdout" or x.get("provenanceOpened") for x in sources):
    raise SystemExit("holdout lane/provenance custody failure")
if any(x.get("placementMapSha256")!=EXPECTED_PLACEMENT_SHA for x in sources):
    raise SystemExit("holdout metric placement-map mismatch")

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
candidate_results=[]
for cand in train["catalogue"]:
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
    candidate_results.append({
      "degree":cand["degree"],"placementToken":cand["placementToken"],"contextArm":cand["contextArm"],
      "frozenDirection":direction,**c,"decidedSources":decided,
      "reproducedDirectionSources":reproduced,"oppositeStrictSources":opposite,
      "reproductionRateAmongDecided":ratio,"validationVerdict":verdict
    })

mixed=[x for x in diagnostics if x["classification"]=="MIXED"]
core={
 "schema":"component_placement_junction_holdout_validation_v1",
 "status":"FROZEN_BEFORE_CONTROL_PLACEMENT_LAW_JOIN",
 "trainCatalogueSha256":EXPECTED_CATALOGUE_SHA,
 "placementMapSha256":EXPECTED_PLACEMENT_SHA,
 "holdoutSourceCount":len(sources),
 "candidateResults":candidate_results,
 "diagnostics":diagnostics,
 "summary":{
   "trainCandidates":len(train["catalogue"]),
   "passed":sum(x["validationVerdict"]=="PASS" for x in candidate_results),
   "failed":sum(x["validationVerdict"]=="FAIL" for x in candidate_results),
   "insufficient":sum(x["validationVerdict"]=="INSUFFICIENT_ELIGIBLE_SOURCES" for x in candidate_results),
   "mixedTestedCells":len(mixed),
   "mixedDegreePlacementArmCells":len(mixed),
   "placementStillInsufficientOnHoldout":bool(mixed)
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
 "topPasses":sorted([x for x in candidate_results if x["validationVerdict"]=="PASS"],key=lambda x:-x["eligibleSources"])[:20],
 "topMixed":sorted(mixed,key=lambda x:-x["eligibleSources"])[:20]
},indent=2))
