#!/usr/bin/env python3
"""Prepare one-source blind compiler packets for ISLD v1."""
from __future__ import annotations
import argparse, hashlib, json, pathlib, shutil

def compact_sha(value):
    payload=json.dumps(value,separators=(",",":"),ensure_ascii=False).encode()
    return hashlib.sha256(payload).hexdigest()

ap=argparse.ArgumentParser()
ap.add_argument("--sealed-input",required=True)
ap.add_argument("--captures-dir",required=True)
ap.add_argument("--selection",required=True)
ap.add_argument("--out",required=True)
args=ap.parse_args()

sealed=json.loads(pathlib.Path(args.sealed_input).read_text())
selection=json.loads(pathlib.Path(args.selection).read_text())
if sealed.get("blindInputSha256") != selection["sealed_input_sha256"]:
    raise SystemExit("sealed input SHA custody mismatch")

sources={s["sourceGroupId"]:s for s in sealed["sources"]}
obs_by={}
for o in sealed["observations"]:
    obs_by.setdefault(o["sourceGroupId"],[]).append(o)

out=pathlib.Path(args.out)
out.mkdir(parents=True,exist_ok=True)
written=[]
for picked in selection["selected"]:
    sid=picked["sourceGroupId"]
    source=dict(sources[sid])
    if len(obs_by.get(sid,[])) != picked["observation_count"]:
        raise SystemExit(f"observation count changed for {sid}")
    if source.get("captureToken") != picked["captureToken"] or source.get("continuityToken") != picked["continuityToken"]:
        raise SystemExit(f"capture/continuity custody changed for {sid}")

    dest=out/sid
    (dest/"captures").mkdir(parents=True,exist_ok=True)
    src_capture=pathlib.Path(args.captures_dir)/f"{sid}.jpg"
    dst_capture=dest/"captures"/f"{sid}.jpg"
    shutil.copyfile(src_capture,dst_capture)

    source["lane"]="train"
    local_obs=[]
    for original in sorted(obs_by[sid],key=lambda x:x["id"]):
        o=dict(original)
        o["lane"]="train"
        local_obs.append(o)

    core={
      "schema":sealed["schema"],
      "corpusKind":sealed.get("corpusKind"),
      "generatedAt":sealed.get("generatedAt"),
      "lanePolicy":{"isld_v1":"single isolated source; original lane retained only in sealed selection metadata"},
      "sourceHarvestSha256":sealed.get("sourceHarvestSha256"),
      "proposalBudget":sealed.get("proposalBudget"),
      "sources":[source],
      "observations":local_obs,
      "blindnessContract":sealed.get("blindnessContract"),
    }
    packet={**core,"blindInputSha256":compact_sha(core)}
    (dest/"input.json").write_text(json.dumps(packet,indent=2,ensure_ascii=False)+"\n")
    written.append({"sourceGroupId":sid,"localBlindInputSha256":packet["blindInputSha256"],"observations":len(local_obs)})

manifest={
 "schema":"independent_source_law_discovery_local_input_manifest_v1",
 "sealedParentBlindInputSha256":sealed["blindInputSha256"],
 "sources":written
}
(out/"manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")
print(json.dumps(manifest,indent=2))
