#!/usr/bin/env python3
import json, math, os
from collections import Counter
from pathlib import Path
from mark_state_operator_separation_v12_core import *

PROTOCOL=Path(os.environ.get("MARK_V12_PROTOCOL","research/mark/discovery-experiments/state-operator-separation-v12.protocol.json"))
V10_FREEZE=Path(os.environ.get("MARK_V10_FREEZE","artifacts/v10-freeze/glyph-transition-code-freeze.json"))
TRAIN=Path(os.environ.get("MARK_V10_TRAIN","artifact-staging/v10-train/train.jsonl"))
OUT=Path(os.environ.get("MARK_V12_FREEZE","artifacts/mark-state-operator-separation-v12-freeze"))

def rows_from_counter_dict(counter,names): return serialize_counter(counter,names)

def encode_space(space):
    tabs=[]
    for order,tab in enumerate(space["tabs"]):
        for ctx,c in tab.items():
            for y,n in c.items(): tabs.append({"order":order,"context":list(ctx),"outcome":y,"count":int(n)})
    tabs.sort(key=lambda r:(r["order"],r["context"],r["outcome"]))
    exact=[{"history":list(h),"state":int(s),"count":int(space["historyCounts"][h])} for h,s in space["exact"].items()]
    exact.sort(key=lambda r:r["history"])
    return {"tokens":space["tokens"],"fingerprintOutcomes":space["fpOutcomes"],"centroids":space["centers"],"ngramRows":tabs,"exactHistoryStates":exact}

def encode_machine(m,subs):
    emit=[]
    for s,c in enumerate(m["emit"]):
        for y,n in c.items(): emit.append({"state":s,"outcome":y,"count":int(n)})
    emit.sort(key=lambda r:(r["state"],r["outcome"]))
    trans=[]
    for (s,g),c in m["trans"].items():
        for s2,n in c.items(): trans.append({"state":s,"glyph":g,"nextState":s2,"count":int(n)})
    trans.sort(key=lambda r:(r["state"],r["glyph"],r["nextState"]))
    trans0=[]
    for s,c in enumerate(m["trans0"]):
        for s2,n in c.items(): trans0.append({"state":s,"nextState":s2,"count":int(n)})
    trans0.sort(key=lambda r:(r["state"],r["nextState"]))
    pair=[]
    for (s,a,b),c in m["pair"].items():
        for z,n in c.items(): pair.append({"state":s,"firstGlyph":a,"secondGlyph":b,"outcome":z,"count":int(n)})
    pair.sort(key=lambda r:(r["state"],r["firstGlyph"],r["secondGlyph"],r["outcome"]))
    support=[{"state":s,"glyph":g,"count":int(n)} for (s,g),n in m["opSupport"].items()]; support.sort(key=lambda r:(r["state"],r["glyph"]))
    sub=[{"state":s,"glyph":g,**v} for (s,g),v in subs.items()]; sub.sort(key=lambda r:(r["state"],r["glyph"]))
    return {"emissionRows":emit,"transitionRows":trans,"stateOnlyTransitionRows":trans0,"directPairRows":pair,"stateGlyphSupport":support,"substitutions":sub}

def main():
    protocol=json.loads(PROTOCOL.read_text(encoding="utf-8")); v10=json.loads(V10_FREEZE.read_text(encoding="utf-8"))
    if protocol.get("schema")!="mark_state_operator_separation_protocol_v12": raise RuntimeError("bad V12 protocol")
    if v10.get("freezeSha256")!=protocol["parent"]["expectedV10FreezeSha256"]: raise RuntimeError("V10 freeze drift")
    rows=read_jsonl(TRAIN,"train"); v=v10["variants"]["lineOnly"]; common=set(v["commonStates"]); eligible=set(v["eligibleGlyphs"])
    scfg=protocol["stateInduction"]; folds=int(scfg["cvFolds"]); candidates=list(scfg["candidateStateCounts"]); cv={k:{"loss":0.0,"events":0} for k in candidates}
    for f in range(folds):
        fit=[r for r in rows if fold_for_doc(r["anonymousInscriptionId"],folds)!=f]; val=[r for r in rows if fold_for_doc(r["anonymousInscriptionId"],folds)==f]
        for k in candidates:
            space=induce_state_space(fit,common,protocol,k); m=learn_machine(fit,common,eligible,space,protocol); L=int(protocol["representation"]["historyLength"]); loss=0.0; n=0
            for row in val:
                raw,s=mapped_stream(row["words"],common)
                for i in range(1,len(s)-1):
                    g=raw[i]
                    if g not in eligible: continue
                    S=m["state"](history_before(s,i,L)); y=s[i+1]; q=max(consequence_kernel(m,S,g,protocol).get(y,1e-300),1e-300); loss+=-math.log2(q); n+=1
            cv[k]["loss"]+=loss; cv[k]["events"]+=n
    cvrows=[{"stateCount":k,"bitsPerEvent":cv[k]["loss"]/max(1,cv[k]["events"]),"events":cv[k]["events"]} for k in candidates]
    best=min(r["bitsPerEvent"] for r in cvrows); tol=float(scfg["selectionToleranceBitsPerEvent"]); selected=min(r["stateCount"] for r in cvrows if r["bitsPerEvent"]<=best+tol)
    space=induce_state_space(rows,common,protocol,selected); m=learn_machine(rows,common,eligible,space,protocol); subs=select_substitutes(m,eligible,protocol)
    packet={"schema":"mark_state_operator_separation_freeze_v12","experimentId":protocol["experimentId"],"protocolSha256":canonical_sha(protocol),"parentV10FreezeSha256":v10["freezeSha256"],"trainInscriptionCount":len(rows),"currentGlyphExcludedFromIncomingState":True,"historyLength":int(protocol["representation"]["historyLength"]),"commonStates":sorted(common),"eligibleGlyphs":sorted(eligible),"selectedStateCount":selected,"crossValidation":cvrows,"trainUniqueHistories":len(space["exact"]),"stateCompressionRatio":len(space["exact"])/selected,"space":encode_space(space),"machine":encode_machine(m,subs)}
    packet["freezeSha256"]=canonical_sha(packet)
    OUT.mkdir(parents=True,exist_ok=True); (OUT/"state-operator-freeze.json").write_text(json.dumps(packet,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    summary=["Mark state-operator separation v12 — pre-evaluation freeze",f"protocolSha256={packet['protocolSha256']}",f"freezeSha256={packet['freezeSha256']}",f"selectedStates={selected}",f"trainUniqueHistories={packet['trainUniqueHistories']}",f"stateCompressionRatio={packet['stateCompressionRatio']:.6f}",f"substitutionMappings={len(subs)}","currentGlyphExcludedFromIncomingState=true","evaluationOpenedByThisJob=false"]
    for r in cvrows: summary.append(f"cv_states={r['stateCount']};bits={r['bitsPerEvent']:.6f};events={r['events']}")
    (OUT/"summary.txt").write_text("\n".join(summary)+"\n",encoding="utf-8"); print("\n".join(summary))
if __name__=="__main__": main()
