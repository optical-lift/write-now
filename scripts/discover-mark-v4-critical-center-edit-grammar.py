#!/usr/bin/env python3
import hashlib, json, os, statistics
from collections import defaultdict, Counter
from pathlib import Path

protocol_path=Path(os.environ.get("MARK_V4_PROTOCOL","research/mark/discovery-experiments/critical-center-correspondence-v4.protocol.json"))
align_dir=Path(os.environ.get("MARK_V4_ALIGNMENT","artifact-staging/v4-alignment"))
label_dir=Path(os.environ.get("MARK_V4_LABELS","artifact-staging/v4-labels"))
out_dir=Path(os.environ.get("MARK_V4_DISCOVERY_OUT","artifacts/mark-critical-center-edit-grammar-v4"))

def load_json(p): return json.loads(Path(p).read_text())
def canonical_sha(v): return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
def locate(root,name):
    hits=list(root.rglob(name))
    if len(hits)!=1: raise RuntimeError(f"expected one {name}, found {len(hits)}")
    return hits[0]
def auc_smaller(pos,neg):
    if not pos or not neg:return None
    score=0.0; total=0
    for p in pos:
        for n in neg:
            total+=1
            if p<n:score+=1
            elif p==n:score+=0.5
    return 2*(score/total)-1
def auc_larger(pos,neg):
    x=auc_smaller(pos,neg)
    return -x if x is not None else None
def balanced(rows,value_fn,larger=False):
    by=defaultdict(lambda:{"preserved":[],"broken":[]})
    for r in rows:
        by[(r["occupantFamilyA"],r["occupantFamilyB"])][r["label"]].append(value_fn(r))
    effects=[]; details=[]
    for (a,b),d in sorted(by.items()):
        e=(auc_larger if larger else auc_smaller)(d["preserved"],d["broken"])
        if e is None:continue
        effects.append(e)
        details.append({"occupantFamilyA":a,"occupantFamilyB":b,"effect":e,"preserved":len(d["preserved"]),"broken":len(d["broken"])})
    return (statistics.mean(effects) if effects else None,details)
def transfer_gate(train,holdout,control):
    if train is None or holdout is None or control is None or abs(train)<1e-12:return False
    same=(train>0 and holdout>0 and control>0) or (train<0 and holdout<0 and control<0)
    return same and abs(holdout)>=0.25*abs(train) and abs(control)>=0.25*abs(train)

protocol=load_json(protocol_path)
if protocol.get("schema")!="mark_critical_center_correspondence_protocol_v4":raise RuntimeError("unexpected protocol")
freeze=load_json(locate(align_dir,"correspondence-freeze.json"))
corr_path=locate(align_dir,"correspondence-pairs.jsonl"); corr_bytes=corr_path.read_bytes()
if hashlib.sha256(corr_bytes).hexdigest()!=freeze["correspondenceRowsSha256"]:raise RuntimeError("correspondence row SHA mismatch")
if freeze.get("labelsAvailableDuringAlignment"):raise RuntimeError("correspondence alignment was not blind to labels")
rows={r["pairId"]:r for r in (json.loads(x) for x in corr_bytes.splitlines() if x.strip())}
cust=load_json(locate(label_dir,"label-custody.json"))
lab_path=locate(label_dir,"pair-labels.jsonl"); lab_bytes=lab_path.read_bytes()
if hashlib.sha256(lab_bytes).hexdigest()!=cust["labelsSha256"]:raise RuntimeError("label file SHA mismatch")
labels={r["pairId"]:r["label"] for r in (json.loads(x) for x in lab_bytes.splitlines() if x.strip())}
if set(rows)!=set(labels):raise RuntimeError("correspondence/label pair mismatch")
all_rows=[]
for pid in sorted(rows):all_rows.append({**rows[pid],"label":labels[pid]})

atoms=[x["id"] for x in protocol["editAtoms"]]; atom_labels={x["id"]:x["label"] for x in protocol["editAtoms"]}
lanes={lane:[r for r in all_rows if r["lane"]==lane] for lane in ("train","holdout","control")}
train=lanes["train"]
observed_atoms={}
for atom in atoms:
    e,details=balanced(train,lambda r,a=atom:float(r["metrics"][a]),False)
    observed_atoms[atom]={"id":atom,"label":atom_labels[atom],"trainEffect":e,"familyPairEffects":details}

support=Counter()
for r in train:
    for motif,rate in r["metrics"].get("motifRates",{}).items():
        if rate>0:support[motif]+=1
min_support=int(protocol["motifDiscovery"]["minimumTrainPairsContainingMotif"])
motifs=sorted([m for m,c in support.items() if c>=min_support])
observed_motifs={}
for m in motifs:
    e,details=balanced(train,lambda r,m=m:float(r["metrics"].get("motifRates",{}).get(m,0.0)),True)
    observed_motifs[m]={"motif":m,"trainEffect":e,"trainPairsContaining":support[m],"familyPairEffects":details}

iters=int(protocol["trainDiscovery"]["nullIterations"])
byfam=defaultdict(list)
for r in train:byfam[(r["occupantFamilyA"],r["occupantFamilyB"])].append(r)
null_atoms={a:[] for a in atoms}; null_motifs={m:[] for m in motifs}
for it in range(iters):
    shuffled=[]
    for (a,b),rs in sorted(byfam.items()):
        npos=sum(r["label"]=="preserved" for r in rs)
        order=sorted(rs,key=lambda r:(hashlib.sha256(f"v4-null|{it}|{a}|{b}|{r['pairId']}".encode()).hexdigest(),r["pairId"]))
        for i,r in enumerate(order):shuffled.append({**r,"label":"preserved" if i<npos else "broken"})
    for a in atoms:
        e,_=balanced(shuffled,lambda r,a=a:float(r["metrics"][a]),False);null_atoms[a].append(e if e is not None else 0.0)
    for m in motifs:
        e,_=balanced(shuffled,lambda r,m=m:float(r["metrics"].get("motifRates",{}).get(m,0.0)),True);null_motifs[m].append(e if e is not None else 0.0)

for a,o in observed_atoms.items():
    vals=null_atoms[a]; obs=o["trainEffect"] if o["trainEffect"] is not None else 0.0
    o["null"]={"iterations":iters,"mean":statistics.mean(vals),"min":min(vals),"max":max(vals),"absoluteNullAtLeastObserved":sum(abs(x)>=abs(obs) for x in vals)}
for m,o in observed_motifs.items():
    vals=null_motifs[m]; obs=o["trainEffect"] if o["trainEffect"] is not None else 0.0
    o["null"]={"iterations":iters,"mean":statistics.mean(vals),"min":min(vals),"max":max(vals),"absoluteNullAtLeastObserved":sum(abs(x)>=abs(obs) for x in vals)}

selected_atoms=sorted(observed_atoms.values(),key=lambda o:(-abs(o["trainEffect"] or 0.0),o["id"]))[:int(protocol["trainDiscovery"]["maximumSelectedContinuousAtoms"])]
selected_motifs=sorted(observed_motifs.values(),key=lambda o:(-abs(o["trainEffect"] or 0.0),o["motif"]))[:int(protocol["motifDiscovery"]["maximumSelectedMotifs"])]

def lane_effect(rows,atom=None,motif=None):
    if atom is not None:return balanced(rows,lambda r:float(r["metrics"][atom]),False)[0]
    return balanced(rows,lambda r:float(r["metrics"].get("motifRates",{}).get(motif,0.0)),True)[0]

for o in selected_atoms:
    h=lane_effect(lanes["holdout"],atom=o["id"]); c=lane_effect(lanes["control"],atom=o["id"])
    o["holdoutEffect"]=h;o["controlEffect"]=c;o["strongTransfer"]=transfer_gate(o["trainEffect"],h,c)
for o in selected_motifs:
    h=lane_effect(lanes["holdout"],motif=o["motif"]); c=lane_effect(lanes["control"],motif=o["motif"])
    o["holdoutEffect"]=h;o["controlEffect"]=c;o["strongTransfer"]=transfer_gate(o["trainEffect"],h,c)

core={
 "schema":"mark_critical_center_edit_grammar_v4",
 "experimentId":protocol["experimentId"],
 "parentCriticalCenterCorrespondenceSha256":freeze["criticalCenterCorrespondenceSha256"],
 "labelsOpenedOnlyAfterCorrespondenceFreeze":True,
 "pairCounts":{lane:{"total":len(rs),"preserved":sum(r["label"]=="preserved" for r in rs),"broken":sum(r["label"]=="broken" for r in rs)} for lane,rs in lanes.items()},
 "selectedContinuousEditAtoms":selected_atoms,
 "selectedLocalEditMotifs":selected_motifs,
 "allTrainContinuousEffects":[observed_atoms[a] for a in atoms],
 "trainMotifCandidates":len(motifs),
 "strongTransferContinuousAtoms":sum(bool(x["strongTransfer"]) for x in selected_atoms),
 "strongTransferLocalMotifs":sum(bool(x["strongTransfer"]) for x in selected_motifs),
 "effectSemantics":{
   "continuous":"positive means role-preserving pairs change less than matched role-broken pairs",
   "motif":"positive means the local correspondence motif is more frequent in role-preserving pairs"
 },
 "provenanceAvailableDuringDiscovery":False,
 "contract":{
   "correspondenceFrozenBeforeLabelsOpened":True,
   "continuousAtomsDefinedBeforeLabelsOpened":True,
   "localMotifVocabularyDiscoveredInTrainOnly":True,
   "holdoutAndControlCannotReselectAtomsOrMotifs":True,
   "nullShufflesLabelsWithinPhysicalFamilyPair":True,
   "noStateVocabularyConsumed":True,
   "noTransitionGrammarConsumed":True,
   "noProvenanceConsumed":True
 }
}
digest=canonical_sha(core);packet={**core,"criticalCenterEditGrammarSha256":digest}
out_dir.mkdir(parents=True,exist_ok=True)
(out_dir/"critical-center-edit-grammar.json").write_text(json.dumps(packet,indent=2)+"\n")
lines=[
 f"critical_center_edit_grammar_sha256={digest}",
 f"train_pairs={len(train)}",
 f"selected_continuous_atoms={len(selected_atoms)}",
 f"selected_local_motifs={len(selected_motifs)}",
 f"strong_transfer_continuous_atoms={core['strongTransferContinuousAtoms']}",
 f"strong_transfer_local_motifs={core['strongTransferLocalMotifs']}"
]
for i,o in enumerate(selected_atoms,1):
    lines.append(f"atom_{i}={o['id']};train={o['trainEffect']:.6f};holdout={o['holdoutEffect']:.6f};control={o['controlEffect']:.6f};null_at_least={o['null']['absoluteNullAtLeastObserved']};strong={str(o['strongTransfer']).lower()};label={o['label']}")
for i,o in enumerate(selected_motifs,1):
    lines.append(f"motif_{i}={o['motif']};train={o['trainEffect']:.6f};holdout={o['holdoutEffect']:.6f};control={o['controlEffect']:.6f};null_at_least={o['null']['absoluteNullAtLeastObserved']};strong={str(o['strongTransfer']).lower()}")
(out_dir/"summary.txt").write_text("\n".join(lines)+"\n")
print(json.dumps(packet,indent=2))
