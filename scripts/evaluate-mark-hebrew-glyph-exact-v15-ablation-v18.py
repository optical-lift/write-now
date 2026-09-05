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
    fz=read_json(find(Path(os.environ["MARK_V18_FREEZE"]),"freeze.json"))
    if fz.get("evaluationOpenedDuringFreeze") is not False or fz.get("protocolSha256")!=sha256_file(pp): raise RuntimeError("invalid freeze")
    hr=Path(os.environ["MARK_V18_HEBREW_EVAL"]); gr=Path(os.environ["MARK_V18_GLYPH_EVAL"])
    if list(hr.rglob("train.jsonl")) or list(gr.rglob("train.jsonl")): raise RuntimeError("train visible during evaluation")
    H={l:read_jsonl(find(hr,f"{l}.jsonl")) for l in ("holdout","control")}; G={l:read_jsonl(find(gr,f"{l}.jsonl")) for l in ("holdout","control")}
    results=evaluate_all(H,G,fz,p); interp=adjudicate(results,p)
    packet={"schema":"mark_hebrew_glyph_exact_v15_ablation_result_v18","adjudication":interp["adjudication"],"interpretation":interp,"freezeSha256":fz["freezeSha256"],"results":results,"claimBoundary":p["claimBoundary"]}; packet["resultSha256"]=sha256_json(packet)
    out=Path(os.environ.get("MARK_V18_RESULT_OUT","artifacts/mark-hebrew-glyph-exact-v15-ablation-v18/result")); out.mkdir(parents=True,exist_ok=True); write_json(out/"result.json",packet)
    lines=["# Mark Hebrew ↔ glyph exact-V15 ablation v18","",f"Adjudication: **{packet['adjudication']}**","",f"Interpretation: `{canonical_json(interp)}`","",
           "| variant | status | pairs | holdout mean | holdout p | holdout support-p | holdout rank | control mean | control p | control support-p | control rank |",
           "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for v in p["variants"]:
        r=results[v["id"]]; h=r["lanes"]["holdout"]; c=r["lanes"]["control"]
        lines.append(f"| {v['id']} | {r['status']} | {r['frozenPairCount']} | {h['meanSimilarity']:+.4f} | {h['unstratifiedPermutationP']:.4f} | {h['supportStratifiedPermutationP']:.4f} | {h['medianRankPercentile']:.3f} | {c['meanSimilarity']:+.4f} | {c['unstratifiedPermutationP']:.4f} | {c['supportStratifiedPermutationP']:.4f} | {c['medianRankPercentile']:.3f} |")
    lines += ["",f"Result SHA-256: `{packet['resultSha256']}`",""]; text="\n".join(lines); (out/"summary.md").write_text(text,encoding="utf-8"); print(text)
if __name__=="__main__": main()
