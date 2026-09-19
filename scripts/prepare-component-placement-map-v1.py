#!/usr/bin/env python3
"""Build frozen observation -> masked structural placement token map."""
from __future__ import annotations
import argparse, hashlib, json, pathlib

ap=argparse.ArgumentParser()
ap.add_argument("--occurrences",required=True)
ap.add_argument("--protocol",required=True)
ap.add_argument("--out",required=True)
args=ap.parse_args()

protocol=json.loads(pathlib.Path(args.protocol).read_text())
inst=protocol["placementInstrument"]
path=pathlib.Path(args.occurrences)
raw=path.read_bytes()
sha=hashlib.sha256(raw).hexdigest()
if sha!=inst["occurrenceRowsSha256"]:
    raise SystemExit(f"masked-slot occurrence SHA mismatch: {sha}")
lines=[x for x in raw.decode().splitlines() if x.strip()]
if len(lines)!=int(inst["occurrenceRows"]):
    raise SystemExit(f"masked-slot occurrence row count mismatch: {len(lines)}")

placements={}
token_keys={}
lane_counts={}
source_ids=set()
for lineno,line in enumerate(lines,1):
    row=json.loads(line)
    if row.get("schema")!="mark_masked_slot_occurrence_v1":
        raise SystemExit(f"unexpected occurrence schema at line {lineno}")
    oid=row["observationId"]
    if oid in placements:
        raise SystemExit(f"duplicate placement observation {oid}")
    key=row.get("maskedContextKey")
    if not key:
        raise SystemExit(f"missing maskedContextKey at line {lineno}")
    token="P"+hashlib.sha256(key.encode()).hexdigest()[:16]
    old=token_keys.setdefault(token,key)
    if old!=key:
        raise SystemExit("placement-token hash collision")
    placements[oid]={
      "sourceGroupId":row["sourceGroupId"],
      "lane":row["lane"],
      "placementToken":token
    }
    lane_counts[row["lane"]]=lane_counts.get(row["lane"],0)+1
    source_ids.add(row["sourceGroupId"])

core={
 "schema":"component_placement_map_v1",
 "status":"FROZEN_FROM_PRIOR_MASKED_SLOT_ARTIFACT",
 "occurrenceRowsSha256":sha,
 "occurrenceRows":len(lines),
 "placementField":"maskedContextKey",
 "targetTopologyExcluded":True,
 "occupantTokenUsed":False,
 "familyIdUsed":False,
 "provenanceOpened":False,
 "laneOccurrenceCounts":lane_counts,
 "sourceCount":len(source_ids),
 "placements":placements,
 "tokenKeys":token_keys
}
core_sha=hashlib.sha256(json.dumps(core,sort_keys=True,separators=(",",":")).encode()).hexdigest()
result={**core,"placementMapSha256":core_sha}
out=pathlib.Path(args.out); out.parent.mkdir(parents=True,exist_ok=True)
out.write_text(json.dumps(result,separators=(",",":"))+"\n")
print(json.dumps({
 "placementMapSha256":core_sha,
 "occurrenceRows":len(lines),
 "placementTokens":len(token_keys),
 "laneOccurrenceCounts":lane_counts,
 "sourceCount":len(source_ids)
},indent=2))
