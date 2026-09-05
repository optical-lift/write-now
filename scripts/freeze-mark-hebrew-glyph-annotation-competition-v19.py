#!/usr/bin/env python3
import os
from pathlib import Path
from mark_hebrew_glyph_annotation_competition_v19_core import read_json,read_jsonl,freeze_model,write_json,sha256_json
protocol=read_json(os.environ["MARK_V19_PROTOCOL"]); song=read_json(os.environ["MARK_V19_SONG_MAP"]); hd=Path(os.environ["MARK_V19_HEBREW_TRAIN"]); gd=Path(os.environ["MARK_V19_GLYPH_TRAIN"]); out=Path(os.environ["MARK_V19_FREEZE_OUT"])
h=read_jsonl(hd/"train.jsonl"); g=read_jsonl(gd/"train.jsonl"); conv=read_json(hd/"conventional-train-map.json"); model=freeze_model(h,g,conv,song,protocol)
model["schema"]="mark_hebrew_glyph_annotation_competition_freeze_v19"; model["evaluationOpenedDuringFreeze"]=False; model["protocolSha256"]=sha256_json(protocol); model["songManifestSha256"]=sha256_json(song)
if len(model["panelOperators"])<int(protocol["commonPanel"]["minimumPanelOperators"]): model["freezeAdjudication"]="INSUFFICIENT_SONG_COVERED_PANEL"
else: model["freezeAdjudication"]="FEASIBLE"
model["freezeSha256"]=sha256_json({k:v for k,v in model.items() if k!="freezeSha256"}); write_json(out/"freeze.json",model)
lines=["# V19 pre-evaluation annotation competition freeze","",f'- Song-covered panel operators: **{len(model["panelOperators"])}**',f'- label-blind frozen pairs: **{len(model["pairs"])}**',f'- shared states: **{len(model["sharedStates"])}**',f'- blind K: **{model["blindMetadata"]["k"]}**',f'- evaluation opened: **false**',f'- freeze SHA-256: `{model["freezeSha256"]}`',"","| map | related pairs | unrelated pairs |","|---|---:|---:|"]
for m in ("song","conventional","blind"): lines.append(f'| {m} | {model["relationCounts"][m]["relatedPairs"]} | {model["relationCounts"][m]["unrelatedPairs"]} |')
lines += ["","| Hebrew | glyph | train similarity |","|---|---|---:|"]+[f'| {r["hebrew"]} | {r["glyph"]} | {r["trainSimilarity"]:+.4f} |' for r in model["pairs"]]
(out/"summary.md").write_text("\n".join(lines)+"\n",encoding="utf-8"); print("\n".join(lines))
