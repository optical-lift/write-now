#!/usr/bin/env python3
"""Freeze exact placement-MIXED train cells before parent-state join."""
from __future__ import annotations
import argparse, hashlib, json, pathlib

ap=argparse.ArgumentParser()
ap.add_argument("--train-catalogue",required=True)
ap.add_argument("--protocol",required=True)
ap.add_argument("--out",required=True)
args=ap.parse_args()

protocol=json.loads(pathlib.Path(args.protocol).read_text())
expected=protocol["targetSet"]
train=json.loads(pathlib.Path(args.train_catalogue).read_text())
if train.get("schema")!="component_placement_junction_train_catalogue_v1":
    raise SystemExit("unexpected parent train catalogue schema")
if train.get("catalogueSha256")!="6e1d0b4a9d093e38423108a3711cc3bd32ee2a68668b078fd332401f24bf7543":
    raise SystemExit("parent train catalogue SHA mismatch")
core={k:v for k,v in train.items() if k!="catalogueSha256"}
calc=hashlib.sha256(json.dumps(core,sort_keys=True,separators=(",",":")).encode()).hexdigest()
if calc!=train["catalogueSha256"]:
    raise SystemExit("parent train catalogue canonical SHA mismatch")

items=[]
for x in train["diagnostics"]:
    if x["classification"]=="MIXED":
        items.append({
          "degree":int(x["degree"]),
          "placementToken":x["placementToken"],
          "contextArm":x["contextArm"],
          "parentEligibleSources":int(x["eligibleSources"]),
          "parentStrictMatchSources":int(x["strictMatchSources"]),
          "parentStrictReverseSources":int(x["strictReverseSources"]),
          "parentUnresolvedSources":int(x["unresolvedSources"])
        })
items.sort(key=lambda x:(x["degree"],x["placementToken"],x["contextArm"]))
if len(items)!=int(expected["expectedCount"]):
    raise SystemExit(f"expected {expected['expectedCount']} mixed targets, got {len(items)}")

core={
 "schema":"parent_state_conditioned_target_set_v1",
 "status":"FROZEN_BEFORE_PARENT_STATE_JOIN",
 "parentTrainCatalogueSha256":train["catalogueSha256"],
 "targetCount":len(items),
 "targets":items,
 "parentStateJoined":False,
 "provenanceOpened":False
}
sha=hashlib.sha256(json.dumps(core,sort_keys=True,separators=(",",":")).encode()).hexdigest()
result={**core,"targetSetSha256":sha}
out=pathlib.Path(args.out); out.parent.mkdir(parents=True,exist_ok=True)
out.write_text(json.dumps(result,indent=2)+"\n")
print(json.dumps({"targetSetSha256":sha,"targetCount":len(items)},indent=2))
