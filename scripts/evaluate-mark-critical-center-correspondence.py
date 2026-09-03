#!/usr/bin/env python3
import hashlib, json, os, statistics
from collections import defaultdict
from pathlib import Path

protocol_path=Path(os.environ.get("MARK_VERTEX_PROTOCOL","research/mark/discovery-experiments/critical-center-correspondence-v4.protocol.json"))
grammar_dir=Path(os.environ.get("MARK_VERTEX_GRAMMAR","artifacts/mark-critical-center-edit-grammar-v4"))
out_dir=Path(os.environ.get("MARK_VERTEX_TRANSFER_OUT","artifacts/mark-critical-center-correspondence-v4"))

def load_json(p): return json.loads(Path(p).read_text(encoding="utf-8"))
def canonical_sha(v): return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
def auc_smaller(pos,neg):
    if not pos or not neg:return None
    score=0.0;total=0
    for p in pos:
        for n in neg:
            total+=1
            if p<n:score+=1
            elif p==n:score+=0.5
    return 2.0*(score/total)-1.0
def balanced_effect(rows,feature):
    bypair=defaultdict(lambda:{"preserved":[],"broken":[]})
    for r in rows:
        x=r["editMagnitudes"].get(feature)
        if x is not None:bypair[(r["occupantFamilyA"],r["occupantFamilyB"])][r["label"]].append(float(x))
    effects=[];details=[]
    for (a,b),d in sorted(bypair.items()):
        e=auc_smaller(d["preserved"],d["broken"])
        if e is None:continue
        effects.append(e);details.append({"occupantFamilyA":a,"occupantFamilyB":b,"effect":e,"preserved":len(d["preserved"]),"broken":len(d["broken"]),"preservedMedian":statistics.median(d["preserved"]),"brokenMedian":statistics.median(d["broken"])})
    return (statistics.mean(effects) if effects else None,details)

protocol=load_json(protocol_path)
grammar=load_json(grammar_dir/"critical-center-edit-grammar.json")
gsha=grammar.get("criticalCenterEditGrammarSha256")
if canonical_sha({k:v for k,v in grammar.items() if k!="criticalCenterEditGrammarSha256"})!=gsha:raise RuntimeError("critical-center edit grammar SHA mismatch")
rows=[json.loads(x) for x in (grammar_dir/"critical-center-pair-edits.jsonl").read_text().splitlines() if x.strip()]
selected=[x["editId"] for x in grammar["selectedEditAtoms"]];threshold=0.08;results=[]
for f in selected:
    lanes={}
    for lane in ("train","holdout","control"):
        e,details=balanced_effect([r for r in rows if r["lane"]==lane],f);lanes[lane]={"balancedEffect":e,"familyPairEffects":details}
    te=lanes["train"]["balancedEffect"];he=lanes["holdout"]["balancedEffect"];ce=lanes["control"]["balancedEffect"]
    same=(te is not None and he is not None and ce is not None and te!=0 and he*te>0 and ce*te>0);passed=bool(same and abs(he)>=threshold and abs(ce)>=threshold)
    results.append({"editId":f,"label":next(x["label"] for x in grammar["selectedEditAtoms"] if x["editId"]==f),"train":lanes["train"],"holdout":lanes["holdout"],"control":lanes["control"],"sameDirectionAllLanes":same,"transferPass":passed})
core={"schema":"mark_critical_center_correspondence_result_v4","experimentId":protocol["experimentId"],"criticalCenterEditGrammarSha256":gsha,"criticalCenterWorldSha256":grammar["criticalCenterWorldSha256"],"vertexPairManifestSha256":grammar["vertexPairManifestSha256"],"selectedAtoms":results,"transferPassCount":sum(x["transferPass"] for x in results),"selectedAtomCount":len(results),"allSelectedSameDirectionCount":sum(x["sameDirectionAllLanes"] for x in results),"conclusionClass":"TRANSFERABLE_LITERAL_VERTEX_EDIT_CONSTRAINTS" if any(x["transferPass"] for x in results) else "NO_TRANSFERABLE_LITERAL_VERTEX_EDIT_CONSTRAINTS_AT_THIS_RESOLUTION","contract":{"editAtomsFrozenInTrain":True,"holdoutAndControlReselectNothing":True,"alignmentFrozenBeforeRoleLabelComparison":True,"selectedReplayExactToFrozenFullWorldAggregates":True,"claimsCriticalCenterCorrespondenceNotExplicitGraphEdgeCorrespondence":True,"noStateVocabularyConsumed":True,"noTransitionGrammarConsumed":True,"noProvenanceConsumed":True}}
digest=canonical_sha(core);packet={**core,"criticalCenterCorrespondenceSha256":digest}
out_dir.mkdir(parents=True,exist_ok=True);(out_dir/"critical-center-correspondence.json").write_text(json.dumps(packet,indent=2)+"\n")
lines=[f"critical_center_correspondence_sha256={digest}",f"critical_center_edit_grammar_sha256={gsha}",f"selected_atoms={len(results)}",f"transfer_pass={packet['transferPassCount']}",f"all_selected_same_direction={packet['allSelectedSameDirectionCount']}",f"conclusion={packet['conclusionClass']}"]
for i,r in enumerate(results,1):lines.append(f"atom_{i}={r['editId']};train={r['train']['balancedEffect']:.6f};holdout={r['holdout']['balancedEffect']:.6f};control={r['control']['balancedEffect']:.6f};pass={str(r['transferPass']).lower()};label={r['label']}")
(out_dir/"summary.txt").write_text("\n".join(lines)+"\n");print(json.dumps(packet,indent=2))
