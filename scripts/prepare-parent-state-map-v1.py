#!/usr/bin/env python3
"""Build frozen observation -> containing-parent local-state map."""
from __future__ import annotations
import argparse, hashlib, json, pathlib

ap=argparse.ArgumentParser()
ap.add_argument("--occurrences",required=True)
ap.add_argument("--observation-states",required=True)
ap.add_argument("--protocol",required=True)
ap.add_argument("--out",required=True)
args=ap.parse_args()

protocol=json.loads(pathlib.Path(args.protocol).read_text())
pinst=protocol["placementInstrument"]
sinst=protocol["parentStateInstrument"]

occ_path=pathlib.Path(args.occurrences)
occ_raw=occ_path.read_bytes()
occ_sha=hashlib.sha256(occ_raw).hexdigest()
if occ_sha!=pinst["occurrenceRowsSha256"]:
    raise SystemExit(f"occurrence SHA mismatch: {occ_sha}")
occ_lines=[x for x in occ_raw.decode().splitlines() if x.strip()]
if len(occ_lines)!=int(pinst["occurrenceRows"]):
    raise SystemExit(f"occurrence row count mismatch: {len(occ_lines)}")

state_path=pathlib.Path(args.observation_states)
state_raw=state_path.read_bytes()
state_sha=hashlib.sha256(state_raw).hexdigest()
if state_sha!=sinst["observationStateRowsSha256"]:
    raise SystemExit(f"observation-state SHA mismatch: {state_sha}")
state_lines=[x for x in state_raw.decode().splitlines() if x.strip()]
if len(state_lines)!=int(sinst["observationStateRows"]):
    raise SystemExit(f"observation-state row count mismatch: {len(state_lines)}")

states={}
for lineno,line in enumerate(state_lines,1):
    row=json.loads(line)
    if row.get("schema")!="mark_observation_local_state_v1":
        raise SystemExit(f"unexpected local-state schema at line {lineno}")
    oid=row["observationId"]
    if oid in states:
        raise SystemExit(f"duplicate local-state observation {oid}")
    state=int(row["stateId"])
    if state not in (1,2,3):
        raise SystemExit(f"invalid state {state} for {oid}")
    states[oid]={
      "sourceGroupId":row["sourceGroupId"],
      "lane":row["lane"],
      "stateId":state
    }

parent_states={}
counts={"S1":0,"S2":0,"S3":0,"UNPARENTED_STATE":0}
lane_counts={}
for lineno,line in enumerate(occ_lines,1):
    row=json.loads(line)
    if row.get("schema")!="mark_masked_slot_occurrence_v1":
        raise SystemExit(f"unexpected occurrence schema at line {lineno}")
    oid=row["observationId"]
    if oid in parent_states:
        raise SystemExit(f"duplicate occurrence observation {oid}")
    source=row["sourceGroupId"]; lane=row["lane"]
    pid=row.get("parentObservationId")
    parent=states.get(pid) if pid else None
    if parent is None:
        token="UNPARENTED_STATE"
    else:
        if parent["sourceGroupId"]!=source or parent["lane"]!=lane:
            raise SystemExit(
              f"parent-state custody mismatch for {oid}: target={source}/{lane} "
              f"parent={parent['sourceGroupId']}/{parent['lane']}"
            )
        token=f"S{parent['stateId']}"
    counts[token]+=1
    lane_counts.setdefault(lane,{}).setdefault(token,0)
    lane_counts[lane][token]+=1
    parent_states[oid]={
      "sourceGroupId":source,
      "lane":lane,
      "parentObservationId":pid,
      "parentStateToken":token
    }

core={
 "schema":"parent_state_map_v1",
 "status":"FROZEN_FROM_PRIOR_LOCAL_STATE_AND_MASKED_SLOT_ARTIFACTS",
 "occurrenceRowsSha256":occ_sha,
 "observationStateRowsSha256":state_sha,
 "localStateFieldDiscoverySha256":sinst["discoverySha256"],
 "targetStateUsed":False,
 "provenanceOpened":False,
 "parentRelation":"smallest strictly larger wholly-containing observation",
 "counts":counts,
 "laneCounts":lane_counts,
 "parentStates":parent_states
}
sha=hashlib.sha256(json.dumps(core,sort_keys=True,separators=(",",":")).encode()).hexdigest()
result={**core,"parentStateMapSha256":sha}
out=pathlib.Path(args.out); out.parent.mkdir(parents=True,exist_ok=True)
out.write_text(json.dumps(result,separators=(",",":"))+"\n")
print(json.dumps({
 "parentStateMapSha256":sha,
 "observations":len(parent_states),
 "counts":counts,
 "mappedFraction":1.0-(counts["UNPARENTED_STATE"]/len(parent_states))
},indent=2))
