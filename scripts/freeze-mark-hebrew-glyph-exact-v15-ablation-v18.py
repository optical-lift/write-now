#!/usr/bin/env python3
import os
from pathlib import Path
from mark_hebrew_glyph_exact_v15_ablation_v18_core import *
def find(root,name):
    xs=list(Path(root).rglob(name))
    if len(xs)!=1: raise RuntimeError(f"expected one {name}: {xs}")
    return xs[0]
def main():
    pp=os.environ.get("MARK_V18_PROTOCOL","research/mark/discovery-experiments/hebrew-glyph-exact-v15-ablation-v18.protocol.json"); p=read_json(pp)
    hr=Path(os.environ["MARK_V18_HEBREW_TRAIN"]); gr=Path(os.environ["MARK_V18_GLYPH_TRAIN"])
    for bad in ("holdout.jsonl","control.jsonl"):
        if list(hr.rglob(bad)) or list(gr.rglob(bad)): raise RuntimeError("evaluation visible during freeze")
    fz=freeze_all(read_jsonl(find(hr,"train.jsonl")),read_jsonl(find(gr,"train.jsonl")),p)
    fz["schema"]="mark_hebrew_glyph_exact_v15_ablation_freeze_v18"; fz["protocolSha256"]=sha256_file(pp); fz["evaluationOpenedDuringFreeze"]=False
    fz["freezeSha256"]=sha256_json({k:v for k,v in fz.items() if k!="freezeSha256"})
    out=Path(os.environ.get("MARK_V18_FREEZE_OUT","artifacts/mark-hebrew-glyph-exact-v15-ablation-v18/freeze")); out.mkdir(parents=True,exist_ok=True); write_json(out/"freeze.json",fz)
    lines=["# V18 pre-evaluation exact-V15 freeze","",f"- freeze SHA-256: `{fz['freezeSha256']}`","- evaluation opened: **false**","",
           "| variant | states | H ops | glyph ops | pairs | H events | glyph events |","|---|---:|---:|---:|---:|---:|---:|"]
    for v in p["variants"]:
        x=fz["variants"][v["id"]]; lines.append(f"| {v['id']} | {len(x['sharedStates'])} | {len(x['hebrewOperators'])} | {len(x['glyphOperators'])} | {len(x['pairs'])} | {x['trainEventCounts']['hebrew']} | {x['trainEventCounts']['glyph']} |")
    text="\n".join(lines)+"\n"; (out/"summary.md").write_text(text,encoding="utf-8"); print(text)
if __name__=="__main__": main()
