#!/usr/bin/env python3
"""Freeze train parent-state sublaws inside the 67 placement-MIXED targets."""
from __future__ import annotations
import argparse, glob, hashlib, json, pathlib

ap=argparse.ArgumentParser()
ap.add_argument("--metrics-glob",required=True)
ap.add_argument("--parent-state-map",required=True)
ap.add_argument("--target-set",required=True)
ap.add_argument("--protocol",required=True)
ap.add_argument("--out",required=True)
args=ap.parse_args()

protocol=json.loads(pathlib.Path(args.protocol).read_text())
pmap=json.loads(pathlib.Path(args.parent_state_map).read_text())
targets=json.loads(pathlib.Path(args.target_set).read_text())

if pmap.get("schema")!="parent_state_map_v1" or pmap.get("provenanceOpened") or pmap.get("targetStateUsed"):
    raise SystemExit("parent-state map custody failure")
if targets.get("schema")!="parent_state_conditioned_target_set_v1" or targets.get("parentStateJoined"):
    raise SystemExit("target set custody failure")
if len(targets["targets"])!=67:
    raise SystemExit("expected 67 frozen targets")

target_keys={(int(x["degree"]),x["placementToken"],x["contextArm"]) for x in targets["targets"]}

sources=[]
for path in sorted(glob.glob(args.metrics_glob)):
    for line in pathlib.Path(path).read_text().splitlines():
        if line.strip(): sources.append(json.loads(line))
ids=[x["sourceGroupId"] for x in sources]
if len(sources)!=237 or len(set(ids))!=237:
    raise SystemExit(f"expected 237 unique train sources, got {len(sources)} rows / {len(set(ids))} unique")
if any(x["originalBlindLane"]!="train" or x.get("provenanceOpened") for x in sources):
    raise SystemExit("train lane/provenance custody failure")
if any(x.get("parentStateMapSha256")!=pmap["parentStateMapSha256"] for x in sources):
    raise SystemExit("parent-state map SHA mismatch")
if any(x.get("targetSetSha256")!=targets["targetSetSha256"] for x in sources):
    raise SystemExit("target-set SHA mismatch")

by={}
for s in sources:
    for row in s["rows"]:
        base=(int(row["degree"]),row["placementToken"],row["contextArm"])
        if base not in target_keys:
            raise SystemExit(f"metric row escaped frozen target set: {base}")
        if row["parentStateToken"]=="UNPARENTED_STATE":
            continue
        key=(base[0],base[1],row["parentStateToken"],base[2])
        by.setdefault(key,[]).append(row)

catalogue=[]; diagnostics=[]
for (degree,placement,parent_state,arm),rows in sorted(by.items()):
    eligible=[r for r in rows if r["state"]!="INELIGIBLE"]
    counts={k:sum(r["state"]==k for r in eligible) for k in ["STRICT_MATCH","STRICT_REVERSE","UNRESOLVED"]}
    n=len(eligible)
    if n>=10:
        if counts["STRICT_MATCH"]>=5 and counts["STRICT_REVERSE"]==0: cls="MATCH_ONLY"
        elif counts["STRICT_REVERSE"]>=5 and counts["STRICT_MATCH"]==0: cls="REVERSE_ONLY"
        elif counts["STRICT_MATCH"]>=1 and counts["STRICT_REVERSE"]>=1: cls="MIXED"
        else: cls="UNRESOLVED"
    else:
        cls="INSUFFICIENT_SOURCES"
    entry={
      "degree":degree,"placementToken":placement,"parentStateToken":parent_state,"contextArm":arm,
      "eligibleSources":n,
      "strictMatchSources":counts["STRICT_MATCH"],
      "strictReverseSources":counts["STRICT_REVERSE"],
      "unresolvedSources":counts["UNRESOLVED"],
      "classification":cls
    }
    diagnostics.append(entry)
    if cls in {"MATCH_ONLY","REVERSE_ONLY"}:
        catalogue.append({**entry,"frozenDirection":"STRICT_MATCH" if cls=="MATCH_ONLY" else "STRICT_REVERSE"})

by_parent={}
for d in diagnostics:
    by_parent.setdefault((d["degree"],d["placementToken"],d["contextArm"]),[]).append(d)

resolutions=[]
for t in targets["targets"]:
    key=(int(t["degree"]),t["placementToken"],t["contextArm"])
    subs=[x for x in by_parent.get(key,[]) if x["eligibleSources"]>=10]
    classes=[x["classification"] for x in subs]
    has_match="MATCH_ONLY" in classes
    has_reverse="REVERSE_ONLY" in classes
    has_mixed="MIXED" in classes
    if has_mixed:
        status="STILL_MIXED"
    elif has_match and has_reverse:
        status="TWO_SIDED_RESOLVED"
    elif has_match or has_reverse:
        status="ONE_SIDED_DECONFOUNDED"
    else:
        status="INSUFFICIENT_PARENT_STATE_SUPPORT"
    resolutions.append({
      "degree":key[0],"placementToken":key[1],"contextArm":key[2],
      "resolutionStatus":status,
      "testableParentStates":[x["parentStateToken"] for x in subs],
      "parentStateClassifications":[
        {"parentStateToken":x["parentStateToken"],"classification":x["classification"],
         "eligibleSources":x["eligibleSources"],"strictMatchSources":x["strictMatchSources"],
         "strictReverseSources":x["strictReverseSources"],"unresolvedSources":x["unresolvedSources"]}
        for x in subs
      ]
    })

core={
 "schema":"parent_state_conditioned_junction_train_catalogue_v1",
 "status":"FROZEN_BEFORE_HOLDOUT_OR_CONTROL_PARENT_STATE_JOIN",
 "trainSourceCount":len(sources),
 "parentStateMapSha256":pmap["parentStateMapSha256"],
 "targetSetSha256":targets["targetSetSha256"],
 "targetCount":len(targets["targets"]),
 "catalogue":catalogue,
 "diagnostics":diagnostics,
 "targetResolutions":resolutions,
 "holdoutJoined":False,
 "controlJoined":False,
 "provenanceOpened":False
}
sha=hashlib.sha256(json.dumps(core,sort_keys=True,separators=(",",":")).encode()).hexdigest()
result={**core,"catalogueSha256":sha}
out=pathlib.Path(args.out); out.parent.mkdir(parents=True,exist_ok=True)
out.write_text(json.dumps(result,indent=2)+"\n")
counts={}
for r in resolutions: counts[r["resolutionStatus"]]=counts.get(r["resolutionStatus"],0)+1
print(json.dumps({
 "catalogueSha256":sha,
 "admittedCandidates":len(catalogue),
 "matchOnlyCandidates":sum(x["classification"]=="MATCH_ONLY" for x in catalogue),
 "reverseOnlyCandidates":sum(x["classification"]=="REVERSE_ONLY" for x in catalogue),
 "mixedParentStateSubcells":sum(x["classification"]=="MIXED" for x in diagnostics),
 "testedParentStateSubcells":sum(x["eligibleSources"]>=10 for x in diagnostics),
 "targetResolutionCounts":counts
},indent=2))
