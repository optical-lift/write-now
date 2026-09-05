#!/usr/bin/env python3
import os
from pathlib import Path
from mark_hebrew_glyph_operator_fingerprint_v15_core import *

def find(root,name):
    xs=list(Path(root).rglob(name))
    if len(xs)!=1: raise RuntimeError(f"expected one {name} under {root}, got {xs}")
    return xs[0]

def main():
    protocol=read_json(os.environ.get("MARK_V15_PROTOCOL","research/mark/discovery-experiments/hebrew-glyph-operator-fingerprint-v15.protocol.json"))
    hroot=Path(os.environ["MARK_V15_HEBREW_TRAIN"]); groot=Path(os.environ["MARK_V15_GLYPH_TRAIN"]); out=Path(os.environ.get("MARK_V15_FREEZE_OUT","artifacts/mark-hebrew-glyph-operator-fingerprint-v15/freeze")); out.mkdir(parents=True,exist_ok=True)
    for bad in ("holdout.jsonl","control.jsonl","sealed-evaluation.json","evaluation.jsonl"):
        if list(hroot.rglob(bad)) or list(groot.rglob(bad)): raise RuntimeError(f"evaluation evidence visible during freeze: {bad}")
    hrows=read_jsonl(find(hroot,"train.jsonl")); grows=read_jsonl(find(groot,"train.jsonl"))
    freeze=freeze_model(hrows,grows,protocol)
    freeze["schema"]="mark_hebrew_glyph_operator_fingerprint_freeze_v15"; freeze["protocolSha256"]=sha256_file(os.environ.get("MARK_V15_PROTOCOL","research/mark/discovery-experiments/hebrew-glyph-operator-fingerprint-v15.protocol.json")); freeze["evaluationOpenedDuringFreeze"]=False
    core={k:v for k,v in freeze.items() if k!="freezeSha256"}; freeze["freezeSha256"]=sha256_json(core)
    write_json(out/"freeze.json",freeze)
    summary=f"""# V15 pre-evaluation freeze\n\n- shared anonymous states: **{len(freeze['sharedStates'])}**\n- Hebrew train operators: **{len(freeze['hebrewOperators'])}**\n- glyph train operators: **{len(freeze['glyphOperators'])}**\n- mutual-nearest frozen pairs: **{len(freeze['pairs'])}**\n- Hebrew train events: **{freeze['trainEventCounts']['hebrew']}**\n- glyph train events: **{freeze['trainEventCounts']['glyph']}**\n- evaluation opened: **false**\n- freeze SHA-256: `{freeze['freezeSha256']}`\n"""
    (out/"summary.md").write_text(summary,encoding="utf-8"); print(summary)
if __name__=="__main__": main()
