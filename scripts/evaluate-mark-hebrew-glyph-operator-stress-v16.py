#!/usr/bin/env python3
import os
from pathlib import Path
from mark_hebrew_glyph_operator_stress_v16_core import *

def find(root,name):
    xs=list(Path(root).rglob(name))
    if len(xs)!=1: raise RuntimeError(f"expected one {name} under {root}, got {xs}")
    return xs[0]

def main():
    pp=os.environ.get("MARK_V16_PROTOCOL","research/mark/discovery-experiments/hebrew-glyph-operator-stress-v16.protocol.json"); protocol=read_json(pp); freeze=read_json(find(Path(os.environ["MARK_V16_FREEZE"]),"freeze.json"))
    if freeze.get("evaluationOpenedDuringFreeze") is not False: raise RuntimeError("invalid freeze custody flag")
    hroot=Path(os.environ["MARK_V16_HEBREW_EVAL"]); groot=Path(os.environ["MARK_V16_GLYPH_EVAL"]); out=Path(os.environ.get("MARK_V16_RESULT_OUT","artifacts/mark-hebrew-glyph-operator-stress-v16/result")); out.mkdir(parents=True,exist_ok=True)
    if list(hroot.rglob("train.jsonl")) or list(groot.rglob("train.jsonl")): raise RuntimeError("train evidence visible during evaluation")
    results={lane:lane_score(read_jsonl(find(hroot,f"{lane}.jsonl")),read_jsonl(find(groot,f"{lane}.jsonl")),freeze,protocol,lane) for lane in ("holdout","control")}
    enough=len(freeze["pairs"])>=int(protocol["training"]["minimumFrozenPairCount"])
    if not enough: adjud="INSUFFICIENT_STRESS_TEST_PAIR_FEASIBILITY"
    elif results["holdout"]["gate"] and results["control"]["gate"]: adjud="CROSS_CORPUS_OPERATOR_MATCHES_SURVIVE_STRESS_CONTROLS"
    else: adjud="CROSS_CORPUS_OPERATOR_MATCHES_DO_NOT_SURVIVE_STRESS_CONTROLS"
    packet={"schema":"mark_hebrew_glyph_operator_stress_result_v16","adjudication":adjud,"freezeSha256":freeze["freezeSha256"],"results":results,"claimBoundary":protocol["claimBoundary"]}; packet["resultSha256"]=sha256_json(packet); write_json(out/"result.json",packet)
    lines=["# Mark Hebrew ↔ glyph operator stress test v16","",f"Adjudication: **{adjud}**","",f"Frozen train-only pairs: **{len(freeze['pairs'])}** across **{len(freeze['sharedStates'])}** internal anonymous states.",""]
    for lane in ("holdout","control"):
        r=results[lane]; lines += [f"## {lane}","",f"- evaluable frozen pairs: **{r['evaluablePairCount']} / {r['frozenPairCount']} ({r['evaluablePairFraction']:.3f})**",f"- mean similarity: **{r['meanSimilarity']:+.6f}**",f"- positive pair fraction: **{r['positivePairFraction']:.3f}**",f"- median retrieval percentile: **{r['medianRankPercentile']:.3f}**",f"- permutation p: **{r['unstratifiedPermutationP']:.6f}**",f"- frequency-stratified permutation p: **{r['frequencyStratifiedPermutationP']:.6f}**",f"- lane gate: **{r['gate']}**",""]
    lines += ["V16 scores only internal positions from 6–10 item segments, caps each segment at three events, removes START/END and whole-segment seen/new outcomes, excludes Hebrew operator identities with any train proper-noun-tagged occurrence, and permits train pair selection only within a 0.15 within-corpus frequency-percentile gap.","",f"Result SHA-256: `{packet['resultSha256']}`",""]
    (out/"summary.md").write_text("\n".join(lines),encoding="utf-8"); print("\n".join(lines))
if __name__=="__main__": main()
