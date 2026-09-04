#!/usr/bin/env python3
import json, math, os
from collections import Counter, defaultdict
from pathlib import Path
from mark_state_operator_separation_v12_core import *

PROTOCOL=Path(os.environ.get("MARK_V12_PROTOCOL","research/mark/discovery-experiments/state-operator-separation-v12.protocol.json"))
FREEZE=Path(os.environ.get("MARK_V12_FREEZE","artifacts/mark-state-operator-separation-v12-freeze/state-operator-freeze.json"))
EVAL_DIR=Path(os.environ.get("MARK_V10_EVAL","artifact-staging/v10-eval"))
OUT=Path(os.environ.get("MARK_V12_OUT","artifacts/mark-state-operator-separation-v12"))

def thaw(packet,protocol):
    sp=packet["space"]; max_order=max(protocol["probabilityModel"]["ngramOrders"]); tabs=[defaultdict(Counter) for _ in range(max_order+1)]; totals=[Counter() for _ in range(max_order+1)]
    for r in sp["ngramRows"]:
        o=int(r["order"]); ctx=tuple(r["context"]); tabs[o][ctx][r["outcome"]]+=int(r["count"]); totals[o][ctx]+=int(r["count"])
    exact={tuple(r["history"]):int(r["state"]) for r in sp["exactHistoryStates"]}; hc=Counter({tuple(r["history"]):int(r["count"]) for r in sp["exactHistoryStates"]})
    vocab=Counter()
    for y,n in tabs[0][()].items(): vocab[y]=n
    space={"tokens":sp["tokens"],"tabs":tabs,"totals":totals,"vocab":vocab,"fpOutcomes":sp["fingerprintOutcomes"],"centers":sp["centroids"],"exact":exact,"historyCounts":hc}; st=state_assigner(space,protocol); K=int(packet["selectedStateCount"])
    emit=[Counter() for _ in range(K)]; emitN=[0]*K
    for r in packet["machine"]["emissionRows"]: emit[int(r["state"])][r["outcome"]]+=int(r["count"]); emitN[int(r["state"])]+=int(r["count"])
    trans=defaultdict(Counter); transN=Counter()
    for r in packet["machine"]["transitionRows"]:
        key=(int(r["state"]),r["glyph"]); trans[key][int(r["nextState"])]+=int(r["count"]); transN[key]+=int(r["count"])
    trans0=[Counter() for _ in range(K)]; trans0N=[0]*K
    for r in packet["machine"]["stateOnlyTransitionRows"]: trans0[int(r["state"])][int(r["nextState"])]+=int(r["count"]); trans0N[int(r["state"])]+=int(r["count"])
    pair=defaultdict(Counter); pairN=Counter()
    for r in packet["machine"]["directPairRows"]:
        key=(int(r["state"]),r["firstGlyph"],r["secondGlyph"]); pair[key][r["outcome"]]+=int(r["count"]); pairN[key]+=int(r["count"])
    support=Counter({(int(r["state"]),r["glyph"]):int(r["count"]) for r in packet["machine"]["stateGlyphSupport"]})
    gc=Counter(); GN=0
    for c in emit: gc.update(c); GN+=sum(c.values())
    m={"K":K,"emit":emit,"emitN":emitN,"trans":trans,"transN":transN,"trans0":trans0,"trans0N":trans0N,"pair":pair,"pairN":pairN,"opSupport":support,"global":gc,"globalN":GN,"state":st}
    subs={(int(r["state"]),r["glyph"]):r for r in packet["machine"]["substitutions"]}
    return space,m,subs

def lane_eval(rows,lane,packet,protocol,space,m,subs):
    common=set(packet["commonStates"]); eligible=set(packet["eligibleGlyphs"]); L=int(packet["historyLength"]); orders=list(protocol["probabilityModel"]["ngramOrders"]); cfg=protocol["probabilityModel"]
    one={"events":0,"lossMachine":0.0,"lossState":0.0,"ngramLoss":{str(o):0.0 for o in orders},"docs":set()}; one_doc=defaultdict(lambda:{"machine":0.0,"n":0,"ng":{o:0.0 for o in orders}})
    cf_doc=defaultdict(list); cf_events=0
    comp={"events":0,"factorized":0.0,"stateOnly":0.0,"firstOnly":0.0,"secondOnly":0.0,"direct":0.0,"docs":set()}; comp_doc=defaultdict(lambda:[0.0,0.0,0])
    for row in rows:
        doc=row["anonymousInscriptionId"]; raw,s=mapped_stream(row["words"],common)
        for i in range(1,len(s)-1):
            g=raw[i]
            if g not in eligible: continue
            S=m["state"](history_before(s,i,L)); y=s[i+1]; qm=max(consequence_kernel(m,S,g,protocol).get(y,1e-300),1e-300); qs=max(emit_prob(m,y,S,protocol),1e-300)
            lm=-math.log2(qm); one["events"]+=1; one["lossMachine"]+=lm; one["lossState"]+=-math.log2(qs); one["docs"].add(doc); one_doc[doc]["machine"]+=lm; one_doc[doc]["n"]+=1
            for o in orders:
                p=ngram_distribution(tuple(s[max(0,i+1-o):i+1]),space["tokens"],space["tabs"],space["totals"],float(cfg["globalAdditiveAlpha"]),float(cfg["hierarchicalBackoffPseudoCount"])); q=max(p[space["tokens"].index(y)] if y in space["tokens"] else 1e-300,1e-300); l=-math.log2(q); one["ngramLoss"][str(o)]+=l; one_doc[doc]["ng"][o]+=l
            sub=subs.get((S,g))
            if sub:
                b=sub["substitute"]; qb=max(consequence_kernel(m,S,b,protocol).get(y,1e-300),1e-300); cf_doc[doc].append(math.log2(qm)-math.log2(qb)); cf_events+=1
            if i+2<len(s) and raw[i+1] in eligible:
                b=raw[i+1]; z=s[i+2]; qf=max(compose_kernel(m,S,g,b,protocol,"factorized").get(z,1e-300),1e-300); q0=max(compose_kernel(m,S,g,b,protocol,"stateOnly").get(z,1e-300),1e-300); qa=max(compose_kernel(m,S,g,b,protocol,"firstOnly").get(z,1e-300),1e-300); qb=max(compose_kernel(m,S,g,b,protocol,"secondOnly").get(z,1e-300),1e-300); qd=max(direct_pair_prob(m,S,g,b,z,protocol),1e-300)
                lf,l0,la,lb,ld=[-math.log2(q) for q in (qf,q0,qa,qb,qd)]; comp["events"]+=1; comp["factorized"]+=lf; comp["stateOnly"]+=l0; comp["firstOnly"]+=la; comp["secondOnly"]+=lb; comp["direct"]+=ld; comp["docs"].add(doc); comp_doc[doc][0]+=lf; comp_doc[doc][1]+=l0; comp_doc[doc][2]+=1
    n=max(1,one["events"]); machine=one["lossMachine"]/n; state=one["lossState"]/n; ng={o:one["ngramLoss"][str(o)]/n for o in orders}; best_o=min(orders,key=lambda o:(ng[o],o)); best_ng=ng[best_o]
    ngvals=[]
    for doc in sorted(one_doc):
        d=one_doc[doc];
        if d["n"]: ngvals.append((d["ng"][best_o]-d["machine"])/d["n"])
    ngcfg=protocol["ngramChallenge"]; ngp=signflip_p(ngvals,int(ngcfg["signFlipIterations"]),ngcfg["signFlipSalt"]+"|"+lane); ngmean=sum(ngvals)/max(1,len(ngvals)); ngpos=sum(v>0 for v in ngvals)/max(1,len(ngvals))
    cfvals=[sum(cf_doc[d])/len(cf_doc[d]) for d in sorted(cf_doc) if cf_doc[d]]; cfcfg=protocol["counterfactualSubstitution"]; cfp=signflip_p(cfvals,int(cfcfg["signFlipIterations"]),cfcfg["signFlipSalt"]+"|"+lane); cfmean=sum(cfvals)/max(1,len(cfvals)); cfpos=sum(v>0 for v in cfvals)/max(1,len(cfvals))
    cn=max(1,comp["events"]); cb={k:comp[k]/cn for k in ("factorized","stateOnly","firstOnly","secondOnly","direct")}; compwins=sum(1 for d in comp_doc.values() if d[2] and d[0]<d[1])/max(1,len(comp_doc))
    ocfg=protocol["operatorMachine"]; operatorGate=one["events"]>=int(ocfg["minimumEvaluationEvents"][lane]) and len(one["docs"])>=int(ocfg["minimumDistinctEvaluationInscriptions"][lane]) and (state-machine)>=float(ocfg["minimumGainOverStateOnlyBitsPerEvent"])
    cfGate=len(cfvals)>=int(cfcfg["minimumEligibleInscriptions"][lane]) and cfmean>0 and cfpos>=float(cfcfg["minimumPositiveInscriptionFraction"]) and cfp<=float(cfcfg["maximumOneSidedSignFlipP"])
    ccfg=protocol["composition"]; compositionGate=comp["events"]>=int(ccfg["minimumEvaluationEvents"][lane]) and (cb["stateOnly"]-cb["factorized"])>=float(ccfg["minimumGainOverStateOnlyBitsPerEvent"]) and (cb["firstOnly"]-cb["factorized"])>=float(ccfg["minimumGainOverEachOneSidedBitsPerEvent"]) and (cb["secondOnly"]-cb["factorized"])>=float(ccfg["minimumGainOverEachOneSidedBitsPerEvent"]) and (cb["factorized"]-cb["direct"])<=float(ccfg["maximumDirectPairAdvantageBitsPerEvent"]) and compwins>=float(ccfg["minimumInscriptionFractionCompositionBeatsStateOnly"])
    ngramGate=ngmean>0 and ngp<=0.05
    return {"lane":lane,"oneStep":{"events":one["events"],"inscriptions":len(one["docs"]),"machineBitsPerEvent":machine,"stateOnlyBitsPerEvent":state,"gainOverStateOnlyBitsPerEvent":state-machine,"ngramBitsPerEvent":{str(o):ng[o] for o in orders},"bestNgramOrder":best_o,"bestNgramBitsPerEvent":best_ng,"machineGainOverBestNgramBitsPerEvent":best_ng-machine,"operatorGate":operatorGate},"ngramChallenge":{"inscriptions":len(ngvals),"meanInscriptionAdvantageBits":ngmean,"positiveFraction":ngpos,"signFlipP":ngp,"gate":ngramGate},"counterfactual":{"events":cf_events,"inscriptions":len(cfvals),"meanInscriptionAdvantageBits":cfmean,"medianInscriptionAdvantageBits":sorted(cfvals)[len(cfvals)//2] if cfvals else None,"positiveFraction":cfpos,"signFlipP":cfp,"gate":cfGate},"composition":{"events":comp["events"],"inscriptions":len(comp_doc),"factorizedBitsPerEvent":cb["factorized"],"stateOnlyBitsPerEvent":cb["stateOnly"],"firstOnlyBitsPerEvent":cb["firstOnly"],"secondOnlyBitsPerEvent":cb["secondOnly"],"directPairBitsPerEvent":cb["direct"],"gainOverStateOnly":cb["stateOnly"]-cb["factorized"],"gainOverFirstOnly":cb["firstOnly"]-cb["factorized"],"gainOverSecondOnly":cb["secondOnly"]-cb["factorized"],"directPairAdvantage":cb["factorized"]-cb["direct"],"inscriptionWinFractionVsStateOnly":compwins,"gate":compositionGate}}

def main():
    protocol=json.loads(PROTOCOL.read_text(encoding="utf-8")); packet=json.loads(FREEZE.read_text(encoding="utf-8"))
    if packet.get("schema")!="mark_state_operator_separation_freeze_v12" or packet.get("protocolSha256")!=canonical_sha(protocol): raise RuntimeError("V12 freeze/protocol mismatch")
    check=dict(packet); expected=check.pop("freezeSha256");
    if canonical_sha(check)!=expected: raise RuntimeError("V12 freeze hash mismatch")
    space,m,subs=thaw(packet,protocol); results={}
    for lane in ("holdout","control"): results[lane]=lane_eval(read_jsonl(EVAL_DIR/f"{lane}.jsonl",lane),lane,packet,protocol,space,m,subs)
    op=all(results[x]["oneStep"]["operatorGate"] and results[x]["counterfactual"]["gate"] for x in ("holdout","control")); comp=all(results[x]["composition"]["gate"] for x in ("holdout","control")); ng=all(results[x]["ngramChallenge"]["gate"] for x in ("holdout","control"))
    if op and comp and ng: adjud="LATENT_STATE_OPERATOR_MACHINE_BEATS_NGRAM_AND_COMPOSES"
    elif op and comp: adjud="LATENT_OPERATOR_MACHINE_BUT_NGRAM_SUFFICIENT"
    elif op: adjud="LATENT_OPERATOR_CONSEQUENCE_WITHOUT_COMPOSITION"
    else: adjud="NO_STATE_OPERATOR_SEPARATION_UNDER_V12"
    result={"schema":"mark_state_operator_separation_result_v12","experimentId":protocol["experimentId"],"protocolSha256":packet["protocolSha256"],"freezeSha256":packet["freezeSha256"],"selectedStateCount":packet["selectedStateCount"],"trainUniqueHistories":packet["trainUniqueHistories"],"stateCompressionRatio":packet["stateCompressionRatio"],"adjudication":adjud,"freshIndependentHoldout":False,"evaluationLanesReused":True,"lanes":results}; result["resultSha256"]=canonical_sha(result)
    OUT.mkdir(parents=True,exist_ok=True); (OUT/"result.json").write_text(json.dumps(result,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    lines=["# Mark state-operator separation v12","",f"Adjudication: **{adjud}**","",f"Frozen predictive states: **{packet['selectedStateCount']}** from **{packet['trainUniqueHistories']}** train histories (compression {packet['stateCompressionRatio']:.2f}x).","",f"Current glyph excluded from incoming state: **true**.",""]
    for lane in ("holdout","control"):
        r=results[lane]; o=r["oneStep"]; c=r["counterfactual"]; q=r["composition"]; n=r["ngramChallenge"]
        lines += [f"## {lane}","",f"- one-step: events={o['events']}; machine={o['machineBitsPerEvent']:.6f}; stateOnly={o['stateOnlyBitsPerEvent']:.6f}; gain={o['gainOverStateOnlyBitsPerEvent']:+.6f}; bestNgram={o['bestNgramOrder']} @ {o['bestNgramBitsPerEvent']:.6f}; machine-vs-ngram={o['machineGainOverBestNgramBitsPerEvent']:+.6f}; operatorGate={o['operatorGate']}",f"- n-gram challenge: inscriptions={n['inscriptions']}; mean={n['meanInscriptionAdvantageBits']:+.6f}; positiveFraction={n['positiveFraction']:.3f}; signFlipP={n['signFlipP']:.6f}; gate={n['gate']}",f"- counterfactual: events={c['events']}; inscriptions={c['inscriptions']}; mean={c['meanInscriptionAdvantageBits']:+.6f}; positiveFraction={c['positiveFraction']:.3f}; signFlipP={c['signFlipP']:.6f}; gate={c['gate']}",f"- composition: events={q['events']}; factorized={q['factorizedBitsPerEvent']:.6f}; gainState={q['gainOverStateOnly']:+.6f}; gainA={q['gainOverFirstOnly']:+.6f}; gainB={q['gainOverSecondOnly']:+.6f}; directAdvantage={q['directPairAdvantage']:+.6f}; winFraction={q['inscriptionWinFractionVsStateOnly']:.3f}; gate={q['gate']}",""]
    lines += ["The V10/V11 evaluation inscriptions were already opened before V12 was designed. This is a frozen mechanistic follow-up, not fresh independent confirmation.","",f"Result SHA-256: `{result['resultSha256']}`"]
    (OUT/"summary.md").write_text("\n".join(lines)+"\n",encoding="utf-8"); print("\n".join(lines))
if __name__=="__main__": main()
