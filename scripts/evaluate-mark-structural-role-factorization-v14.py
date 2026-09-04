#!/usr/bin/env python3
import json, math, os
from collections import defaultdict
from pathlib import Path
from mark_structural_role_factorization_v14_core import *

PROTOCOL=Path(os.environ.get("MARK_V14_PROTOCOL","research/mark/discovery-experiments/structural-role-factorization-v14.protocol.json"))
FREEZE=Path(os.environ.get("MARK_V14_FREEZE","artifacts/mark-structural-role-factorization-v14-freeze/structural-role-freeze.json"))
V12_FREEZE=Path(os.environ.get("MARK_V12_FREEZE","artifacts/v12-freeze/state-operator-freeze.json"))
EVAL_DIR=Path(os.environ.get("MARK_V10_EVAL","artifact-staging/v10-eval"))
OUT=Path(os.environ.get("MARK_V14_OUT","artifacts/mark-structural-role-factorization-v14"))

def safe(x): return max(float(x),1e-300)
def advantage(a,b): return math.log2(safe(a))-math.log2(safe(b))

def gate(summary,events,lane,cfg):
    p=summary["signFlipP"]
    return events>=int(cfg["minimumEvaluationEvents"][lane]) and summary["inscriptions"]>=int(cfg["minimumEligibleInscriptions"][lane]) and summary["meanBits"]>0 and summary["positiveFraction"]>=float(cfg["minimumPositiveInscriptionFraction"]) and p is not None and p<=float(cfg["maximumOneSidedSignFlipP"])

def evaluate_lane(rows,lane,packet,v12,protocol):
    roles=set(packet["eligibleRoles"]); masked={(r["glyph"],r["role"]) for r in packet["maskedGlyphRoleCells"]}; switches={(int(r["state"]),r["glyph"],r["actualRole"]):r for r in packet["roleSwitches"]}
    model=decode_model(packet["model"]); ntokens,ntabs,ntotals=decode_ngram(packet["ngram"],max(protocol["models"]["ngramOrders"])); order=int(packet["selectedNgramOrder"])
    events=build_prediction_events(rows,v12,protocol)
    general=defaultdict(list); matrix={"vsGlyph":defaultdict(list),"vsRole":defaultdict(list),"vsNgram":defaultdict(list)}; switch=defaultdict(list)
    general_events=matrix_events=switch_events=0; general_docs=set(); matrix_docs=set(); switch_docs=set()
    diagnostics={"factorizedLoss":0.0,"glyphLoss":0.0,"roleLoss":0.0,"ngramLoss":0.0,"eligibleEvents":0}
    for e in events:
        R=e["role"]
        if R not in roles: continue
        S=int(e["state"]); g=e["glyph"]; y=e["outcome"]; doc=e["doc"]
        pf=safe(factorized_dist(model,S,g,R,protocol).get(y,1e-300)); pg=safe(glyph_dist(model,S,g,protocol).get(y,1e-300)); pr=safe(role_state_loo_dist(model,S,R,g,protocol).get(y,1e-300)); pn=safe(ngram_prob(ntokens,ntabs,ntotals,e["context8"],y,order,protocol))
        general[doc].append(advantage(pf,pg)); general_events+=1; general_docs.add(doc)
        diagnostics["factorizedLoss"]+=-math.log2(pf); diagnostics["glyphLoss"]+=-math.log2(pg); diagnostics["roleLoss"]+=-math.log2(pr); diagnostics["ngramLoss"]+=-math.log2(pn); diagnostics["eligibleEvents"]+=1
        if (g,R) in masked:
            matrix["vsGlyph"][doc].append(advantage(pf,pg)); matrix["vsRole"][doc].append(advantage(pf,pr)); matrix["vsNgram"][doc].append(advantage(pf,pn)); matrix_events+=1; matrix_docs.add(doc)
        sw=switches.get((S,g,R))
        if sw:
            ps=safe(factorized_dist(model,S,g,sw["substituteRole"],protocol).get(y,1e-300)); switch[doc].append(advantage(pf,ps)); switch_events+=1; switch_docs.add(doc)
    gc=protocol["generalRoleTransfer"]; gs=summarize_docs(general,int(gc["signFlipIterations"]),gc["signFlipSalt"]+"|"+lane); general_gate=gate(gs,general_events,lane,gc)
    mc=protocol["matrixCompletion"]; ms={k:summarize_docs(v,int(mc["signFlipIterations"]),mc["signFlipSalt"]+"|"+lane+"|"+k) for k,v in matrix.items()}; mgates={k:gate(s,matrix_events,lane,mc) for k,s in ms.items()}
    sc=protocol["roleSwitchCounterfactual"]; ss=summarize_docs(switch,int(sc["signFlipIterations"]),sc["signFlipSalt"]+"|"+lane); switch_gate=gate(ss,switch_events,lane,sc)
    n=max(1,diagnostics["eligibleEvents"]); bits={k.replace("Loss",""):diagnostics[k]/n for k in ("factorizedLoss","glyphLoss","roleLoss","ngramLoss")}
    return {"lane":lane,"selectedNgramOrder":order,"eligibleRolePrediction":{"events":general_events,"inscriptions":len(general_docs),"bitsPerEvent":bits,"factorizedGainOverGlyphBitsPerEvent":bits["glyph"]-bits["factorized"],"factorizedGainOverNgramBitsPerEvent":bits["ngram"]-bits["factorized"],"summary":gs,"gate":general_gate},"maskedMatrix":{"events":matrix_events,"inscriptions":len(matrix_docs),"summaries":ms,"gates":mgates},"roleSwitch":{"events":switch_events,"inscriptions":len(switch_docs),"summary":ss,"gate":switch_gate}}

def main():
    protocol=json.loads(PROTOCOL.read_text(encoding="utf-8")); packet=json.loads(FREEZE.read_text(encoding="utf-8")); v12=json.loads(V12_FREEZE.read_text(encoding="utf-8"))
    if packet.get("schema")!="mark_structural_role_factorization_freeze_v14": raise RuntimeError("bad V14 freeze schema")
    if packet.get("protocolSha256")!=canonical_sha(protocol): raise RuntimeError("V14 protocol drift")
    check=dict(packet); expected=check.pop("freezeSha256")
    if canonical_sha(check)!=expected: raise RuntimeError("V14 freeze hash mismatch")
    if v12.get("freezeSha256")!=packet.get("parentV12FreezeSha256") or v12.get("freezeSha256")!=protocol["lineage"]["v12StateParent"]["expectedFreezeSha256"]: raise RuntimeError("V12 parent drift")
    vcheck=dict(v12); vexpected=vcheck.pop("freezeSha256")
    if canonical_sha(vcheck)!=vexpected: raise RuntimeError("V12 freeze hash mismatch")
    lanes={lane:evaluate_lane(read_jsonl(EVAL_DIR/f"{lane}.jsonl",lane),lane,packet,v12,protocol) for lane in ("holdout","control")}
    general_all=all(lanes[x]["eligibleRolePrediction"]["gate"] for x in lanes)
    matrix_one_all=all(lanes[x]["maskedMatrix"]["gates"]["vsGlyph"] and lanes[x]["maskedMatrix"]["gates"]["vsRole"] for x in lanes)
    matrix_ng_all=all(lanes[x]["maskedMatrix"]["gates"]["vsNgram"] for x in lanes)
    switch_all=all(lanes[x]["roleSwitch"]["gate"] for x in lanes)
    if general_all and matrix_one_all and matrix_ng_all and switch_all: adjud="STRUCTURAL_ROLE_CONDITIONS_GLYPH_OPERATION_AND_COMPOSES_UNSEEN_COMBINATIONS"
    elif general_all and matrix_one_all and matrix_ng_all: adjud="UNSEEN_ROLE_FACTOR_COMPOSITION_WITHOUT_COUNTERFACTUAL_SWITCH"
    elif general_all and matrix_one_all: adjud="ROLE_FACTOR_TRANSFERS_BUT_LOCAL_SEQUENCE_SUFFICIENT"
    elif general_all: adjud="ROLE_SIGNAL_WITHOUT_COMPOSITIONAL_MATRIX_TRANSFER"
    else: adjud="NO_TRANSFERABLE_STRUCTURAL_ROLE_CONDITIONING"
    result={"schema":"mark_structural_role_factorization_result_v14","experimentId":protocol["experimentId"],"protocolSha256":packet["protocolSha256"],"freezeSha256":packet["freezeSha256"],"parentV12FreezeSha256":packet["parentV12FreezeSha256"],"v13RationaleResultSha256":protocol["lineage"]["v13RationaleOnly"]["expectedResultSha256"],"freshIndependentHoldout":False,"evaluationLanesReused":True,"adjudication":adjud,"lanes":lanes}; result["resultSha256"]=canonical_sha(result)
    OUT.mkdir(parents=True,exist_ok=True); (OUT/"result.json").write_text(json.dumps(result,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    lines=["# Mark structural role factorization v14","",f"Adjudication: **{adjud}**","",f"Frozen anonymous roles: **{packet['eligibleRoleCount']}**; masked glyph-role cells: **{len(packet['maskedGlyphRoleCells'])}** covering **{packet['maskedTrainEvents']}** removed train targets.",f"Role-switch mappings: **{len(packet['roleSwitches'])}**. Frozen local-sequence comparator: **order {packet['selectedNgramOrder']} n-gram**, selected by train-only CV.",""]
    for lane in ("holdout","control"):
        r=lanes[lane]; g=r["eligibleRolePrediction"]; m=r["maskedMatrix"]; s=r["roleSwitch"]
        lines += [f"## {lane}","",f"- leave-glyph-out role transfer: events={g['events']}; inscriptions={g['summary']['inscriptions']}; mean={g['summary']['meanBits']:+.6f}; positiveFraction={g['summary']['positiveFraction']:.3f}; p={g['summary']['signFlipP']}; gate={g['gate']}",f"- masked matrix: events={m['events']}; inscriptions={m['inscriptions']}; vsGlyph mean={m['summaries']['vsGlyph']['meanBits']:+.6f}, p={m['summaries']['vsGlyph']['signFlipP']}, gate={m['gates']['vsGlyph']}; vsRole mean={m['summaries']['vsRole']['meanBits']:+.6f}, p={m['summaries']['vsRole']['signFlipP']}, gate={m['gates']['vsRole']}; vsNgram mean={m['summaries']['vsNgram']['meanBits']:+.6f}, p={m['summaries']['vsNgram']['signFlipP']}, gate={m['gates']['vsNgram']}",f"- role switch: events={s['events']}; inscriptions={s['summary']['inscriptions']}; mean={s['summary']['meanBits']:+.6f}; positiveFraction={s['summary']['positiveFraction']:.3f}; p={s['summary']['signFlipP']}; gate={s['gate']}",f"- aggregate eligible-role bits/event: factorized={g['bitsPerEvent']['factorized']:.6f}; glyph={g['bitsPerEvent']['glyph']:.6f}; ngram={g['bitsPerEvent']['ngram']:.6f}",""]
    lines += ["Role keys contain only first-occurrence equality indices, typed boundaries, line-distance, recurrence depth, and prior-same-glyph-count buckets. The predicted next token is excluded from role construction.","","The V10/V12 evaluation inscriptions were already opened before V14 was designed. This is a frozen mechanistic follow-up, not fresh independent confirmation.","",f"Result SHA-256: `{result['resultSha256']}`"]
    (OUT/"summary.md").write_text("\n".join(lines)+"\n",encoding="utf-8"); print("\n".join(lines))
if __name__=="__main__": main()
