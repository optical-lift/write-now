#!/usr/bin/env python3
import os
from pathlib import Path
from mark_hebrew_glyph_exact_v15_ablation_v18_core import *

def main():
    pp=os.environ.get("MARK_V18_PROTOCOL","research/mark/discovery-experiments/hebrew-glyph-exact-v15-ablation-v18.protocol.json")
    p=read_json(pp); lanes,manifest=parse_hebrew_wlc(os.environ["MARK_V18_WLC"],p)
    out=Path(os.environ.get("MARK_V18_HEBREW_OUT","artifacts/mark-hebrew-glyph-exact-v15-ablation-v18/hebrew-custody")); out.mkdir(parents=True,exist_ok=True)
    for lane,rows in lanes.items():
        with open(out/f"{lane}.jsonl","w",encoding="utf-8") as f:
            for r in rows:f.write(canonical_json(r)+"\n")
    manifest["files"]={lane:sha256_file(out/f"{lane}.jsonl") for lane in lanes}; manifest["manifestSha256"]=sha256_json(manifest); write_json(out/"manifest.json",manifest)
    print(json.dumps(manifest,indent=2))
if __name__=="__main__": main()
