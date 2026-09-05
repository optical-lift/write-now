#!/usr/bin/env python3
import os
from pathlib import Path
from mark_hebrew_glyph_operator_fingerprint_v15_core import *

def find(root,name):
    xs=list(Path(root).rglob(name))
    if len(xs)!=1: raise RuntimeError(f"expected one {name} under {root}, got {xs}")
    return xs[0]

def main():
    protocol=read_json(os.environ.get("MARK_V15_PROTOCOL","research/mark/discovery-experiments/hebrew-glyph-operator-fingerprint-v15.protocol.json")); freeze=read_json(find(Path(os.environ["MARK_V15_FREEZE"]),"freeze.json"))
    if freeze.get("evaluationOpenedDuringFreeze") is not False: raise RuntimeError("invalid freeze custody flag")
    hroot=Path(os.environ["MARK_V15_HEBREW_EVAL"]); groot=Path(os.environ["MARK_V15_GLYPH_EVAL"]); out=Path(os.environ.get("MARK_V15_RESULT_OUT","artifacts/mark-hebrew-glyph-operator-fingerprint-v15/result")); out.mkdir(parents=True,exist_ok=True)
    if list(hroot.rglob("train.jsonl")) or list(groot.rglob("train.jsonl")): raise RuntimeError("train evidence visible during evaluation")
    results={}
    for lane in ("holdout","control"):
        h=read_jsonl(find(hroot,f"{lane}.jsonl")); g=read_jsonl(find(groot,f"{lane}.jsonl")); results[lane]=lane_score(h,g,freeze,protocol,lane)
    enough=len(freeze["pairs"])>=int(protocol["training"]["minimumFrozenPairCount"])
    if not enough: adjud="INSUFFICIENT_FROZEN_PAIR_FEASIBILITY"
    elif results["holdout"]["gate"] and results["control"]["gate"]: adjud="TRANSFERABLE_CROSS_CORPUS_OPERATOR_FINGERPRINT_MATCHES"
    else: adjud="NO_TRANSFERABLE_CROSS_CORPUS_OPERATOR_FINGERPRINT_MATCHES"
    packet={"schema":"mark_hebrew_glyph_operator_fingerprint_result_v15","adjudication":adjud,"freezeSha256":freeze["freezeSha256"],"results":results,"claimBoundary":protocol["claimBoundary"]}
    packet["resultSha256"]=sha256_json(packet); write_json(out/"result.json",packet)
    lines=["# Mark Hebrew ↔ glyph operator fingerprint v15","",f"Adjudication: **{adjud}**","",f"Frozen pairs: **{len(freeze['pairs'])}** across **{len(freeze['sharedStates'])}** shared anonymous states.",""]
    for lane in ("holdout","control"):
        r=results[lane]; lines += [f"## {lane}","",f"- mean frozen-pair similarity: **{r['meanSimilarity']:+.6f}**",f"- median retrieval percentile: **{r['medianRankPercentile']:.3f}**",f"- permutation p: **{r['unstratifiedPermutationP']:.6f}**",f"- support-stratified permutation p: **{r['supportStratifiedPermutationP']:.6f}**",f"- lane gate: **{r['gate']}**",""]
    lines += ["The shared projector contains no Hebrew glosses, morphology, translation, verse/book identity, or proposed glyph readings. It uses only equality/repetition topology of preceding items and the anonymous structural relation of the next item.","",f"Result SHA-256: `{packet['resultSha256']}`",""]
    (out/"summary.md").write_text("\n".join(lines),encoding="utf-8"); print("\n".join(lines))
if __name__=="__main__": main()
