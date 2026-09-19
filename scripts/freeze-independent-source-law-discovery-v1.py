#!/usr/bin/env python3
"""Freeze nine source-local catalogues without comparing their contents."""
from __future__ import annotations
import argparse, hashlib, json, pathlib

ap=argparse.ArgumentParser()
ap.add_argument("--selection",required=True)
ap.add_argument("--catalogues-root",required=True)
ap.add_argument("--out",required=True)
args=ap.parse_args()
selection=json.loads(pathlib.Path(args.selection).read_text())
root=pathlib.Path(args.catalogues_root)
entries=[]
for s in selection["selected"]:
    sid=s["sourceGroupId"]
    cat=json.loads((root/sid/"catalogue.json").read_text())
    if cat["sourceGroupId"]!=sid or cat["independenceClass"]!="INDEPENDENT_LOCAL_DISCOVERY":
        raise SystemExit(f"catalogue custody mismatch {sid}")
    if cat["crossSourceMatchingPerformed"] or cat["globalLawLabelsAssigned"] or cat["provenanceOpened"]:
        raise SystemExit(f"contamination flag in {sid}")
    entries.append({
      "sourceGroupId":sid,
      "selectionLane":s["selection_lane"],
      "observationCount":s["observation_count"],
      "catalogueSha256":cat["catalogueSha256"],
      "admittedLocalLaws":cat["admittedLocalLaws"],
      "candidatePairsEvaluated":cat["candidatePairsEvaluated"]
    })
core={
 "schema":"independent_source_law_discovery_freeze_manifest_v1",
 "sourceSelectionBlindInputSha256":selection["sealed_input_sha256"],
 "catalogueCount":len(entries),
 "catalogues":entries,
 "crossSourceMatchingPerformed":False,
 "provenanceOpened":False,
 "globalLawLabelsAssigned":False,
 "readyForPostFreezeEquivalenceAdjudication":len(entries)==9
}
sha=hashlib.sha256(json.dumps(core,sort_keys=True,separators=(",",":")).encode()).hexdigest()
manifest={**core,"freezeManifestSha256":sha}
out=pathlib.Path(args.out); out.parent.mkdir(parents=True,exist_ok=True)
out.write_text(json.dumps(manifest,indent=2)+"\n")
print(json.dumps(manifest,indent=2))
