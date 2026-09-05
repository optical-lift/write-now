#!/usr/bin/env python3
import os
from pathlib import Path
from mark_hebrew_glyph_operator_stress_v16_core import *

def main():
    protocol=read_json(os.environ.get("MARK_V16_PROTOCOL","research/mark/discovery-experiments/hebrew-glyph-operator-stress-v16.protocol.json")); wlc=os.environ["MARK_V16_WLC"]
    lanes,manifest=parse_hebrew_wlc(wlc,protocol); out=Path(os.environ.get("MARK_V16_HEBREW_OUT","artifacts/mark-hebrew-glyph-operator-stress-v16/hebrew-custody")); out.mkdir(parents=True,exist_ok=True)
    for lane,rows in lanes.items():
        with open(out/f"{lane}.jsonl","w",encoding="utf-8") as f:
            for r in rows: f.write(canonical_json(r)+"\n")
    manifest["files"]={lane:sha256_file(out/f"{lane}.jsonl") for lane in lanes}; manifest["manifestSha256"]=sha256_json(manifest); write_json(out/"manifest.json",manifest); print(json.dumps(manifest,indent=2))
if __name__=="__main__": main()
