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
    freeze=read_json(find(Path(os.environ["MARK_V17_FREEZE"]),"freeze.json"))
    if freeze.get("evaluationOpenedDuringFreeze") is not False:
        raise RuntimeError("invalid freeze custody flag")
    if freeze.get("protocolSha256")!=sha256_file(protocol_path):
        raise RuntimeError("protocol changed after V17 freeze")

    hroot=Path(os.environ["MARK_V17_HEBREW_EVAL"])
    groot=Path(os.environ["MARK_V17_GLYPH_EVAL"])
    if list(hroot.rglob("train.jsonl")) or list(groot.rglob("train.jsonl")):
        raise RuntimeError("train evidence visible during evaluation")

    hebrew_lanes={
        lane:read_jsonl(find(hroot,f"{lane}.jsonl"))
        for lane in ("holdout","control")
    }
    glyph_lanes={
        lane:read_jsonl(find(groot,f"{lane}.jsonl"))
        for lane in ("holdout","control")
    }

    results={}
    for variant in protocol["variants"]:
        vid=variant["id"]
        results[vid]=variant_result(
            hebrew_lanes,
            glyph_lanes,
            freeze["variants"][vid],
            protocol
        )

    interpretation=adjudicate(results,protocol)
    packet={
        "schema":"mark_hebrew_glyph_ablation_ladder_result_v17",
        "adjudication":interpretation["adjudication"],
        "interpretation":interpretation,
        "freezeSha256":freeze["freezeSha256"],
        "results":results,
        "claimBoundary":protocol["claimBoundary"]
    }
    packet["resultSha256"]=sha256_json(packet)

    out=Path(os.environ.get(
        "MARK_V17_RESULT_OUT",
        "artifacts/mark-hebrew-glyph-ablation-ladder-v17/result"
    ))
    out.mkdir(parents=True,exist_ok=True)
    write_json(out/"result.json",packet)

    lines=[
        "# Mark Hebrew ↔ glyph ablation ladder v17",
        "",
        f"Adjudication: **{packet['adjudication']}**",
        "",
        f"Baseline status: **{interpretation['baselineStatus']}**",
        f"Isolated sufficient breakers: **{canonical_json(interpretation['isolatedSufficientBreakers'])}**",
        f"Cumulative first break: **{canonical_json(interpretation['cumulativeFirstBreak'])}**",
        "",
        "| variant | status | pairs | holdout eval | holdout mean | holdout p | holdout freq-p | holdout rank | control eval | control mean | control p | control freq-p | control rank |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"
    ]
    for variant in protocol["variants"]:
        vid=variant["id"]
        r=results[vid]
        h=r["lanes"]["holdout"]
        c=r["lanes"]["control"]
        lines.append(
            f"| {vid} | {r['status']} | {r['frozenPairCount']} | "
            f"{h['evaluablePairCount']}/{h['frozenPairCount']} | {h['meanSimilarity']:+.4f} | "
            f"{h['unstratifiedPermutationP']:.4f} | {h['frequencyStratifiedPermutationP']:.4f} | {h['medianRankPercentile']:.3f} | "
            f"{c['evaluablePairCount']}/{c['frozenPairCount']} | {c['meanSimilarity']:+.4f} | "
            f"{c['unstratifiedPermutationP']:.4f} | {c['frequencyStratifiedPermutationP']:.4f} | {c['medianRankPercentile']:.3f} |"
        )
    lines += [
        "",
        "Every variant and its pair panel was frozen from train only before either evaluation packet was downloaded.",
        "",
        f"Result SHA-256: `{packet['resultSha256']}`",
        ""
    ]
    text="\n".join(lines)
    (out/"summary.md").write_text(text,encoding="utf-8")
    print(text)

if __name__=="__main__":
    main()
