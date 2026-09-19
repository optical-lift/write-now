#!/usr/bin/env python3
"""Freeze train-lane degree-conditioned law catalogue."""
from __future__ import annotations
import argparse, glob, hashlib, json, pathlib

ap=argparse.ArgumentParser()
ap.add_argument("--metrics-glob",required=True)
ap.add_argument("--protocol",required=True)
ap.add_argument("--out",required=True)
args=ap.parse_args()
protocol=json.loads(pathlib.Path(args.protocol).read_text())

sources=[]
for path in sorted(glob.glob(args.metrics_glob)):
    for line in pathlib.Path(path).read_text().splitlines():
        if line.strip():
            sources.append(json.loads(line))
ids=[x["sourceGroupId"] for x in sources]
if len(sources)!=237 or len(set(ids))!=237:
    raise SystemExit(f"expected 237 unique train sources, got {len(sources)} rows / {len(set(ids))} unique")
if any(x["originalBlindLane"]!="train" or x.get("provenanceOpened") for x in sources):
    raise SystemExit("lane/provenance custody failure")

by={}
for s in sources:
    for row in s["rows"]:
        key=(row["degree"],row["contextArm"])
        by.setdefault(key,[]).append(row)

catalogue=[]
diagnostics=[]
for (degree,arm),rows in sorted(by.items()):
    eligible=[r for r in rows if r["state"]!="INELIGIBLE"]
    counts={k:sum(r["state"]==k for r in eligible) for k in ["STRICT_MATCH","STRICT_REVERSE","UNRESOLVED"]}
    n=len(eligible)
    if n>=10:
        if counts["STRICT_MATCH"]>=5 and counts["STRICT_REVERSE"]==0:
            cls="MATCH_ONLY"
        elif counts["STRICT_REVERSE"]>=5 and counts["STRICT_MATCH"]==0:
            cls="REVERSE_ONLY"
        elif counts["STRICT_MATCH"]>=1 and counts["STRICT_REVERSE"]>=1:
            cls="MIXED"
        else:
            cls="UNRESOLVED"
    else:
        cls="INSUFFICIENT_SOURCES"
    entry={
      "degree":degree,"contextArm":arm,"eligibleSources":n,
      "strictMatchSources":counts["STRICT_MATCH"],
      "strictReverseSources":counts["STRICT_REVERSE"],
      "unresolvedSources":counts["UNRESOLVED"],
      "classification":cls
    }
    diagnostics.append(entry)
    if cls in {"MATCH_ONLY","REVERSE_ONLY"}:
        catalogue.append({
          **entry,
          "frozenDirection":"STRICT_MATCH" if cls=="MATCH_ONLY" else "STRICT_REVERSE"
        })

core={
 "schema":"degree_conditioned_junction_train_catalogue_v1",
 "status":"FROZEN_BEFORE_HOLDOUT_OR_CONTROL_DEGREE_OUTCOMES",
 "trainSourceCount":len(sources),
 "catalogue":catalogue,
 "diagnostics":diagnostics,
 "holdoutOpened":False,
 "controlOpened":False,
 "provenanceOpened":False
}
sha=hashlib.sha256(json.dumps(core,sort_keys=True,separators=(",",":")).encode()).hexdigest()
result={**core,"catalogueSha256":sha}
out=pathlib.Path(args.out); out.parent.mkdir(parents=True,exist_ok=True)
out.write_text(json.dumps(result,indent=2)+"\n")
print(json.dumps({
 "catalogueSha256":sha,
 "admittedCandidates":len(catalogue),
 "mixedCandidates":sum(x["classification"]=="MIXED" for x in diagnostics),
 "diagnostics":diagnostics
},indent=2))
