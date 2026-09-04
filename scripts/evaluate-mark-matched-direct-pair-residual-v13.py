#!/usr/bin/env python3
import json, math, os
from collections import defaultdict
from pathlib import Path
from mark_state_operator_separation_v12_core import canonical_sha, history_before, mapped_stream, read_jsonl, compose_kernel, direct_pair_prob
from mark_matched_direct_pair_residual_v13_core import thaw_v12, decode_history, history_pair_prob, ngram_prob, panel_lookup, summarize_docs

PROTOCOL=Path(os.environ.get("MARK_V13_PROTOCOL","research/mark/discovery-experiments/matched-direct-pair-residual-v13.protocol.json"))
FREEZE=Path(os.environ.get("MARK_V13_FREEZE","artifacts/mark-matched-direct-pair-residual-v13-freeze/matched-pair-freeze.json"))
V12_FREEZE=Path(os.environ.get("MARK_V12_FREEZE","artifacts/v12-freeze/state-operator-freeze.json"))
EVAL_DIR=Path(os.environ.get("MARK_V10_EVAL","artifact-staging/v10-eval"))
OUT=Path(os.environ.get("MARK_V13_OUT","artifacts/mark-matched-direct-pair-residual-v13"))


def safe(q): return max(float(q),1e-300)
def logratio(a,b): return math.log2(safe(a))-math.log2(safe(b))


def eval_lane(rows,lane,packet,v12,protocol,space,m,hcounts,htotals,panel):
    common=set(v12["commonStates"]); eligible=set(v12["eligibleGlyphs"]); L=int(packet["historyLength"])
    losses={k:0.0 for k in ("factorized","directPair","historyPair","ngram2","ngram4")}; full_events=0; full_docs=set()
    full_doc={"directOverFactorized":defaultdict(list),"historyOverDirect":defaultdict(list),"ngram4OverDirect":defaultdict(list)}
    matched_events=0; matched_docs=set(); matched_doc={"factorizedResidual":defaultdict(list),"directResidualOverNgram4":defaultdict(list),"directContrast":defaultdict(list),"factorizedContrast":defaultdict(list),"ngram4Contrast":defaultdict(list)}
    for row in rows:
        doc=row["anonymousInscriptionId"]; raw,s=mapped_stream(row["words"],common)
        for i in range(1,len(s)-2):
            a,b=raw[i],raw[i+1]
            if a not in eligible or b not in eligible: continue
            H=history_before(s,i,L); S=m["state"](H); z=s[i+2]; j=i+2
            qf=safe(compose_kernel(m,S,a,b,protocol,"factorized").get(z,1e-300)); qd=safe(direct_pair_prob(m,S,a,b,z,protocol)); qh=safe(history_pair_prob(hcounts,htotals,m,H,S,a,b,z,protocol)); q2=safe(ngram_prob(space,s[max(0,j-2):j],2,z,protocol)); q4=safe(ngram_prob(space,s[max(0,j-4):j],4,z,protocol))
            for k,q in (("factorized",qf),("directPair",qd),("historyPair",qh),("ngram2",q2),("ngram4",q4)): losses[k]+=-math.log2(q)
            full_events+=1; full_docs.add(doc); full_doc["directOverFactorized"][doc].append(logratio(qd,qf)); full_doc["historyOverDirect"][doc].append(logratio(qh,qd)); full_doc["ngram4OverDirect"][doc].append(logratio(q4,qd))
            key=(S,a,b); match=panel.get(key)
            if not match: continue
            bp=match["substituteSecondGlyph"]; qfs=safe(compose_kernel(m,S,a,bp,protocol,"factorized").get(z,1e-300)); qds=safe(direct_pair_prob(m,S,a,bp,z,protocol))
            ctx4=list(s[max(0,j-4):j]); ctx2=list(s[max(0,j-2):j]); bpm=bp if bp in common else "OTHER"
            if ctx4: ctx4[-1]=bpm
            if ctx2: ctx2[-1]=bpm
            q4s=safe(ngram_prob(space,ctx4,4,z,protocol)); q2s=safe(ngram_prob(space,ctx2,2,z,protocol))
            dc=logratio(qd,qds); fc=logratio(qf,qfs); nc4=logratio(q4,q4s); _nc2=logratio(q2,q2s)
            matched_events+=1; matched_docs.add(doc); matched_doc["directContrast"][doc].append(dc); matched_doc["factorizedContrast"][doc].append(fc); matched_doc["ngram4Contrast"][doc].append(nc4); matched_doc["factorizedResidual"][doc].append(dc-fc); matched_doc["directResidualOverNgram4"][doc].append(dc-nc4)
    n=max(1,full_events); bits={k:losses[k]/n for k in losses}
    mc=protocol["matchedResidualPanel"]; it=int(mc["signFlipIterations"]); salt=mc["signFlipSalt"]+"|"+lane
    msum={k:summarize_docs(v,it,salt+"|"+k) for k,v in matched_doc.items()}
    def matched_gate(name):
        r=msum[name]; p=r["signFlipP"]
        return matched_events>=int(mc["minimumEvaluationEvents"][lane]) and r["inscriptions"]>=int(mc["minimumEligibleInscriptions"][lane]) and r["meanBits"]>0 and r["positiveFraction"]>=float(mc["minimumPositiveInscriptionFraction"]) and p is not None and p<=float(mc["maximumOneSidedSignFlipP"])
    sc=protocol["stateCompressionDiagnostic"]; ssum=summarize_docs(full_doc["historyOverDirect"],int(sc["signFlipIterations"]),sc["signFlipSalt"]+"|"+lane); sp=ssum["signFlipP"]
    compression_gate=full_events>=int(sc["minimumEvaluationEvents"][lane]) and ssum["inscriptions"]>=int(sc["minimumEligibleInscriptions"][lane]) and ssum["meanBits"]>=float(sc["minimumMeanGainBitsPerEvent"]) and sp is not None and sp<=float(sc["maximumOneSidedSignFlipP"])
    lc=protocol["localSequenceDiagnostic"]; lsum=summarize_docs(full_doc["ngram4OverDirect"],int(lc["signFlipIterations"]),lc["signFlipSalt"]+"|"+lane); lp=lsum["signFlipP"]; ngram4_better=lsum["meanBits"]>0 and lp is not None and lp<=float(lc["maximumOneSidedSignFlipP"])
    directsum=summarize_docs(full_doc["directOverFactorized"],int(lc["signFlipIterations"]),lc["signFlipSalt"]+"|direct|"+lane)
    return {"lane":lane,"fullPair":{"events":full_events,"inscriptions":len(full_docs),"bitsPerEvent":bits,"directPairAdvantageOverFactorizedBitsPerEvent":bits["factorized"]-bits["directPair"],"historyPairAdvantageOverDirectBitsPerEvent":bits["directPair"]-bits["historyPair"],"ngram4AdvantageOverDirectBitsPerEvent":bits["directPair"]-bits["ngram4"],"directOverFactorized":directsum,"historyOverDirect":ssum,"ngram4OverDirect":lsum,"stateCompressionGate":compression_gate,"ngram4BetterGate":ngram4_better},"matchedPanel":{"events":matched_events,"inscriptions":len(matched_docs),"summaries":msum,"factorizedResidualGate":matched_gate("factorizedResidual"),"beyondNgram4Gate":matched_gate("directResidualOverNgram4")}}


def main():
    protocol=json.loads(PROTOCOL.read_text(encoding="utf-8")); packet=json.loads(FREEZE.read_text(encoding="utf-8")); v12=json.loads(V12_FREEZE.read_text(encoding="utf-8"))
    if packet.get("schema")!="mark_matched_direct_pair_residual_freeze_v13": raise RuntimeError("bad V13 freeze schema")
    if packet.get("protocolSha256")!=canonical_sha(protocol): raise RuntimeError("V13 protocol drift")
    check=dict(packet); expected=check.pop("freezeSha256")
    if canonical_sha(check)!=expected: raise RuntimeError("V13 freeze hash mismatch")
    if v12.get("freezeSha256")!=packet.get("parentV12FreezeSha256") or v12.get("freezeSha256")!=protocol["parent"]["expectedV12FreezeSha256"]: raise RuntimeError("V12 parent drift")
    vcheck=dict(v12); vexpected=vcheck.pop("freezeSha256")
    if canonical_sha(vcheck)!=vexpected: raise RuntimeError("V12 freeze hash mismatch")
    space,m=thaw_v12(v12,protocol); hcounts,htotals=decode_history(packet["historyPairRows"]); panel=panel_lookup(packet["matchedPanel"]); lanes={}
    for lane in ("holdout","control"): lanes[lane]=eval_lane(read_jsonl(EVAL_DIR/f"{lane}.jsonl",lane),lane,packet,v12,protocol,space,m,hcounts,htotals,panel)
    pair_all=all(lanes[x]["matchedPanel"]["factorizedResidualGate"] for x in lanes); ngram_all=all(lanes[x]["matchedPanel"]["beyondNgram4Gate"] for x in lanes); compression_all=all(lanes[x]["fullPair"]["stateCompressionGate"] for x in lanes); ngram_better_all=all(lanes[x]["fullPair"]["ngram4BetterGate"] for x in lanes)
    if pair_all and ngram_all: adjud="PAIR_INTERACTION_BEYOND_FIRST_ORDER_COMPOSITION_AND_LOCAL_CONTEXT"
    elif pair_all: adjud="PAIR_RESIDUAL_BUT_LOCAL_SEQUENCE_SUFFICIENT"
    elif compression_all or ngram_better_all: adjud="DIRECT_PAIR_ADVANTAGE_EXPLAINED_BY_CONTEXT_OR_STATE_COMPRESSION"
    else: adjud="NO_TRANSFERABLE_MATCHED_PAIR_RESIDUAL"
    result={"schema":"mark_matched_direct_pair_residual_result_v13","experimentId":protocol["experimentId"],"protocolSha256":packet["protocolSha256"],"freezeSha256":packet["freezeSha256"],"parentV12FreezeSha256":packet["parentV12FreezeSha256"],"parentV12ResultSha256":packet["parentV12ResultSha256"],"freshIndependentHoldout":False,"evaluationLanesReused":True,"adjudication":adjud,"lanes":lanes}; result["resultSha256"]=canonical_sha(result)
    OUT.mkdir(parents=True,exist_ok=True); (OUT/"result.json").write_text(json.dumps(result,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    lines=["# Mark matched direct-pair residual v13","",f"Adjudication: **{adjud}**","",f"Frozen matched mappings: **{len(packet['matchedPanel'])}**; train coverage: **{packet['matchedTrainEvents']} events / {packet['matchedTrainInscriptions']} inscriptions**.",""]
    for lane in ("holdout","control"):
        r=lanes[lane]; f=r["fullPair"]; p=r["matchedPanel"]; a=p["summaries"]["factorizedResidual"]; n=p["summaries"]["directResidualOverNgram4"]
        lines += [f"## {lane}","",f"- full pair: events={f['events']}; direct-vs-factorized={f['directPairAdvantageOverFactorizedBitsPerEvent']:+.6f} bits/event; history-vs-direct={f['historyPairAdvantageOverDirectBitsPerEvent']:+.6f}; ngram4-vs-direct={f['ngram4AdvantageOverDirectBitsPerEvent']:+.6f}",f"- matched residual: events={p['events']}; inscriptions={a['inscriptions']}; mean={a['meanBits']:+.6f}; positiveFraction={a['positiveFraction']:.3f}; signFlipP={a['signFlipP']}; gate={p['factorizedResidualGate']}",f"- residual beyond ngram4: mean={n['meanBits']:+.6f}; positiveFraction={n['positiveFraction']:.3f}; signFlipP={n['signFlipP']}; gate={p['beyondNgram4Gate']}",f"- state compression: mean history gain={f['historyOverDirect']['meanBits']:+.6f}; p={f['historyOverDirect']['signFlipP']}; gate={f['stateCompressionGate']}",""]
    lines += ["The V10/V12 evaluation inscriptions were already opened before V13 was designed. This is a frozen mechanistic decomposition, not fresh independent confirmation.","",f"Result SHA-256: `{result['resultSha256']}`"," "]
    (OUT/"summary.md").write_text("\n".join(lines)+"\n",encoding="utf-8"); print("\n".join(lines))

if __name__=="__main__": main()
