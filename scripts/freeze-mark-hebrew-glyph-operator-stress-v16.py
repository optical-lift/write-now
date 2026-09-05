#!/usr/bin/env python3
import os
from pathlib import Path
from mark_hebrew_glyph_operator_stress_v16_core import *

def find(root,name):
    xs=list(Path(root).rglob(name))
    if len(xs)!=1: raise RuntimeError(f"expected one {name} under {root}, got {xs}")
    return xs[0]

def main():
    pp=os.environ.get("MARK_V16_PROTOCOL","research/mark/discovery-experiments/hebrew-glyph-operator-stress-v16.protocol.json"); protocol=read_json(pp)
    hroot=Path(os.environ["MARK_V16_HEBREW_TRAIN"]); groot=Path(os.environ["MARK_V16_GLYPH_TRAIN"]); out=Path(os.environ.get("MARK_V16_FREEZE_OUT","artifacts/mark-hebrew-glyph-operator-stress-v16/freeze")); out.mkdir(parents=True,exist_ok=True)
    for bad in ("holdout.jsonl","control.jsonl","sealed-evaluation.json","evaluation.jsonl"):
        if list(hroot.rglob(bad)) or list(groot.rglob(bad)): raise RuntimeError(f"evaluation evidence visible during freeze: {bad}")
    freeze=freeze_model(read_jsonl(find(hroot,"train.jsonl")),read_jsonl(find(groot,"train.jsonl")),protocol)
    freeze["schema"]="mark_hebrew_glyph_operator_stress_freeze_v16"; freeze["protocolSha256"]=sha256_file(pp); freeze["evaluationOpenedDuringFreeze"]=False
    freeze["freezeSha256"]=sha256_json({k:v for k,v in freeze.items() if k!="freezeSha256"}); write_json(out/"freeze.json",freeze)
    summary=f"""# V16 pre-evaluation freeze\n\n- internal shared anonymous states: **{len(freeze['sharedStates'])}**\n- Hebrew train events after stress filters: **{freeze['trainEventCounts']['hebrew']}**\n- glyph train events after stress filters: **{freeze['trainEventCounts']['glyph']}**\n- Hebrew candidate operators after proper-name exclusion: **{len(freeze['hebrewOperators'])}**\n- glyph candidate operators: **{len(freeze['glyphOperators'])}**\n- Hebrew operators excluded by proper-noun morphology: **{len(freeze['excludedHebrewProperOperators'])}**\n- frequency-matched mutual-nearest frozen pairs: **{len(freeze['pairs'])}**\n- evaluation opened: **false**\n- freeze SHA-256: `{freeze['freezeSha256']}`\n"""
    (out/"summary.md").write_text(summary,encoding="utf-8"); print(summary)
if __name__=="__main__": main()
