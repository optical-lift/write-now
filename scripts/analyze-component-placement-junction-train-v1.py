#!/usr/bin/env python3
"""Freeze train degree + component-placement law catalogue."""
from __future__ import annotations
import argparse, glob, hashlib, json, pathlib

ap=argparse.ArgumentParser()
ap.add_argument("--metrics-glob",required=True)
ap.add_argument("--placement-map",required=True)
ap.add_argument("--protocol",required=True)
ap.add_argument("--out",required=True)
args=ap.parse_args()
protocol=json.loads(pathlib.Path(args.protocol).read_text())
pmap=json.loads(pathlib.Path(args.placement_map).read_text())
if pmap.get("schema")!="component_placement_map_v1":
    raise SystemExit("invalid placement map")
if pmap.get("provenanceOpened") or pmap.get("occupantTokenUsed") or pmap.get("familyIdUsed"):
    raise SystemExit("placement map contamination guard failed")

sources=[]
for path in sorted(glob.glob(args.metrics_glob)):
    for line in pathlib.Path(path).read_text().splitlines():
        if line.strip(): sources.append(json.loads(line))
ids=[x["sourceGroupId"] for x in sources]
if len(sources)!=237 or len(set(ids))!=237:
    raise SystemExit(f"expected 237 unique train sources, got {len(sources)} rows / {len(set(ids))} unique")
if any(x["originalBlindLane"]!="train" or x.get("provenanceOpened") for x in sources):
    raise SystemExit("train lane/provenance custody failure")
if any(x.get("placementMapSha256")!=pmap["placementMapSha256"] for x in sources):
    raise SystemExit("placement map SHA mismatch across source metrics")

by={}
for s in sources:
    for row in s["rows"]:
        if row["placementToken"]=="UNPLACED":
            continue
        key=(row["degree"],row["placementToken"],row["contextArm"])
        by.setdefault(key,[]).append(row)

catalogue=[]; diagnostics=[]
for (degree,placement,arm),rows in sorted(by.items()):
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
      "degree":degree,"placementToken":placement,"contextArm":arm,
      "eligibleSources":n,
      "strictMatchSources":counts["STRICT_MATCH"],
      "strictReverseSources":counts["STRICT_REVERSE"],
      "unresolvedSources":counts["UNRESOLVED"],
      "classification":cls
    }
    diagnostics.append(entry)
    if cls in {"MATCH_ONLY","REVERSE_ONLY"}:
        catalogue.append({**entry,"frozenDirection":"STRICT_MATCH" if cls=="MATCH_ONLY" else "STRICT_REVERSE"})

core={
 "schema":"component_placement_junction_train_catalogue_v1",
 "status":"FROZEN_BEFORE_HOLDOUT_OR_CONTROL_PLACEMENT_LAW_JOIN",
 "trainSourceCount":len(sources),
 "placementMapSha256":pmap["placementMapSha256"],
 "placementTokenCount":len(pmap["tokenKeys"]),
 "catalogue":catalogue,
 "diagnostics":diagnostics,
 "holdoutJoined":False,
 "controlJoined":False,
 "provenanceOpened":False
}
sha=hashlib.sha256(json.dumps(core,sort_keys=True,separators=(",",":")).encode()).hexdigest()
result={**core,"catalogueSha256":sha}
out=pathlib.Path(args.out); out.parent.mkdir(parents=True,exist_ok=True)
out.write_text(json.dumps(result,indent=2)+"\n")
print(json.dumps({
 "catalogueSha256":sha,
 "admittedCandidates":len(catalogue),
 "matchOnlyCandidates":sum(x["classification"]=="MATCH_ONLY" for x in catalogue),
 "reverseOnlyCandidates":sum(x["classification"]=="REVERSE_ONLY" for x in catalogue),
 "mixedCells":sum(x["classification"]=="MIXED" for x in diagnostics),
 "testedCells":sum(x["eligibleSources"]>=10 for x in diagnostics),
 "placementTokens":len(pmap["tokenKeys"])
},indent=2))
