#!/usr/bin/env python3
import os
from pathlib import Path
from mark_hebrew_glyph_ablation_ladder_v17_core import *

def find(root,name):
    xs=list(Path(root).rglob(name))
    if len(xs)!=1:
        raise RuntimeError(f"expected one {name} under {root}, got {xs}")
    return xs[0]

def main():
    protocol_path=os.environ.get(
        "MARK_V17_PROTOCOL",
        "research/mark/discovery-experiments/hebrew-glyph-ablation-ladder-v17.protocol.json"
    )
    protocol=read_json(protocol_path)
    hroot=Path(os.environ["MARK_V17_HEBREW_TRAIN"])
    groot=Path(os.environ["MARK_V17_GLYPH_TRAIN"])
    out=Path(os.environ.get(
        "MARK_V17_FREEZE_OUT",
        "artifacts/mark-hebrew-glyph-ablation-ladder-v17/freeze"
    ))
    out.mkdir(parents=True,exist_ok=True)

    for bad in ("holdout.jsonl","control.jsonl","sealed-evaluation.json","evaluation.jsonl"):
        if list(hroot.rglob(bad)) or list(groot.rglob(bad)):
            raise RuntimeError(f"evaluation evidence visible during freeze: {bad}")

    hrows=read_jsonl(find(hroot,"train.jsonl"))
    grows=read_jsonl(find(groot,"train.jsonl"))
    frozen=freeze_all_variants(hrows,grows,protocol)
    frozen["schema"]="mark_hebrew_glyph_ablation_ladder_freeze_v17"
    frozen["protocolSha256"]=sha256_file(protocol_path)
    frozen["evaluationOpenedDuringFreeze"]=False
    core={k:v for k,v in frozen.items() if k!="freezeSha256"}
    frozen["freezeSha256"]=sha256_json(core)
    write_json(out/"freeze.json",frozen)

    lines=[
        "# V17 pre-evaluation ablation freeze",
        "",
        f"- variants frozen: **{len(frozen['variants'])}**",
        f"- train proper-name operator universe: **{frozen['properOperatorUniverseCount']}**",
        "- evaluation opened: **false**",
        f"- freeze SHA-256: `{frozen['freezeSha256']}`",
        "",
        "| variant | shared states | Hebrew events | glyph events | Hebrew ops | glyph ops | frozen pairs |",
        "|---|---:|---:|---:|---:|---:|---:|"
    ]
    for variant in protocol["variants"]:
        v=frozen["variants"][variant["id"]]
        lines.append(
            f"| {variant['id']} | {len(v['sharedStates'])} | "
            f"{v['trainEventCounts']['hebrew']} | {v['trainEventCounts']['glyph']} | "
            f"{len(v['hebrewOperators'])} | {len(v['glyphOperators'])} | {len(v['pairs'])} |"
        )
    lines.append("")
    text="\n".join(lines)
    (out/"summary.md").write_text(text,encoding="utf-8")
    print(text)

if __name__=="__main__":
    main()
