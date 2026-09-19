#!/usr/bin/env python3
"""Prepare untouched one-source compiler packets for Whole-Topology Condition Test v1."""
from __future__ import annotations
import argparse, hashlib, json, pathlib, shutil

def compact_sha(value):
    payload=json.dumps(value,separators=(",",":"),ensure_ascii=False).encode()
    return hashlib.sha256(payload).hexdigest()

ap=argparse.ArgumentParser()
ap.add_argument("--sealed-input",required=True)
ap.add_argument("--captures-dir",required=True)
ap.add_argument("--excluded-selection",required=True)
ap.add_argument("--lane",choices=["train","holdout","control"],required=True)
ap.add_argument("--out",required=True)
args=ap.parse_args()

sealed=json.loads(pathlib.Path(args.sealed_input).read_text())
selection=json.loads(pathlib.Path(args.excluded_selection).read_text())
if sealed.get("blindInputSha256") != selection["sealed_input_sha256"]:
    raise SystemExit("sealed input SHA custody mismatch")

excluded={x["sourceGroupId"] for x in selection["selected"]}
sources={s["sourceGroupId"]:s for s in sealed["sources"]}
obs_by={}
for o in sealed["observations"]:
    obs_by.setdefault(o["sourceGroupId"],[]).append(o)

picked=[s for s in sealed["sources"] if s["lane"]==args.lane and s["sourceGroupId"] not in excluded]
picked.sort(key=lambda s:s["sourceGroupId"])

out=pathlib.Path(args.out)
out.mkdir(parents=True,exist_ok=True)
written=[]
for original_source in picked:
    sid=original_source["sourceGroupId"]
    source=dict(original_source)
    original_obs=sorted(obs_by.get(sid,[]),key=lambda x:x["id"])
    if not original_obs:
        raise SystemExit(f"source has no frozen observations: {sid}")

    dest=out/sid
    (dest/"captures").mkdir(parents=True,exist_ok=True)
    src_capture=pathlib.Path(args.captures_dir)/f"{sid}.jpg"
    if not src_capture.exists():
        raise SystemExit(f"missing sealed capture: {src_capture}")
    shutil.copyfile(src_capture,dest/"captures"/f"{sid}.jpg")

    source["lane"]="train"
    local_obs=[]
    for original in original_obs:
        o=dict(original)
        o["lane"]="train"
        local_obs.append(o)

    core={
      "schema":sealed["schema"],
      "corpusKind":sealed.get("corpusKind"),
      "generatedAt":sealed.get("generatedAt"),
      "lanePolicy":{"whole_topology_condition_v1":"single untouched source; original blind lane retained only in shard manifest"},
      "sourceHarvestSha256":sealed.get("sourceHarvestSha256"),
      "proposalBudget":sealed.get("proposalBudget"),
      "sources":[source],
      "observations":local_obs,
      "blindnessContract":sealed.get("blindnessContract"),
    }
    packet={**core,"blindInputSha256":compact_sha(core)}
    (dest/"input.json").write_text(json.dumps(packet,indent=2,ensure_ascii=False)+"\n")
    written.append({
      "sourceGroupId":sid,
      "originalBlindLane":args.lane,
      "localBlindInputSha256":packet["blindInputSha256"],
      "observations":len(local_obs),
      "captureToken":source.get("captureToken"),
      "continuityToken":source.get("continuityToken")
    })

manifest={
 "schema":"whole_topology_condition_v1_lane_input_manifest",
 "lane":args.lane,
 "sealedParentBlindInputSha256":sealed["blindInputSha256"],
 "excludedDiscoverySourceCount":len(excluded),
 "sourceCount":len(written),
 "sources":written
}
(out/"manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")
print(json.dumps({"lane":args.lane,"sourceCount":len(written)}))
