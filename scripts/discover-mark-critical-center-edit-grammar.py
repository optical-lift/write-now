#!/usr/bin/env python3
import hashlib, json, math, os, statistics
from collections import Counter, defaultdict
from pathlib import Path

from scipy.spatial import cKDTree

protocol_path=Path(os.environ.get("MARK_VERTEX_PROTOCOL","research/mark/discovery-experiments/critical-center-correspondence-v4.protocol.json"))
manifest_dir=Path(os.environ.get("MARK_VERTEX_PAIR_MANIFEST","artifacts/mark-vertex-pair-manifest-v4"))
world_dir=Path(os.environ.get("MARK_VERTEX_WORLD","artifacts/mark-critical-center-world-v4"))
out_dir=Path(os.environ.get("MARK_VERTEX_GRAMMAR_OUT","artifacts/mark-critical-center-edit-grammar-v4"))

def load_json(p): return json.loads(Path(p).read_text(encoding="utf-8"))
def canonical_sha(v): return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
def transform_point(u,v,name):
    if name=="IDENTITY": return u,v
    if name=="ROT90": return 1.0-v,u
    if name=="ROT180": return 1.0-u,1.0-v
    if name=="ROT270": return v,1.0-u
    if name=="MIRROR_X": return 1.0-u,v
    if name=="MIRROR_Y": return u,1.0-v
    if name=="MIRROR_DIAGONAL": return v,u
    if name=="MIRROR_ANTIDIAGONAL": return 1.0-v,1.0-u
    raise RuntimeError(name)
def transformed_points(rows,transform):
    return [transform_point(float(x["u"]),float(x["v"]),transform) for x in rows]
def symmetric_nearest_distance(a,b,transform):
    if not a or not b:return None
    A=transformed_points(a,transform);B=[(float(x["u"]),float(x["v"])) for x in b]
    ta=cKDTree(A);tb=cKDTree(B)
    dab=tb.query(A,k=1,workers=1)[0];dba=ta.query(B,k=1,workers=1)[0]
    return (float(dab.sum())+float(dba.sum()))/(len(A)+len(B))
def sparse_greedy_match(a,b,transform,k_candidates):
    if not a or not b:return []
    A=transformed_points(a,transform);B=[(float(x["u"]),float(x["v"])) for x in b]
    swapped=False
    left,right=A,B
    if len(left)>len(right):left,right=right,left;swapped=True
    k=max(1,min(int(k_candidates),len(right)))
    tree=cKDTree(right);dists,idxs=tree.query(left,k=k,workers=1)
    if k==1:
        dists=[[float(x)] for x in dists];idxs=[[int(x)] for x in idxs]
    edges=[]
    for i in range(len(left)):
        for q in range(k):edges.append((float(dists[i][q]),i,int(idxs[i][q])))
    edges.sort(key=lambda x:(x[0],x[1],x[2]));used_left=set();used_right=set();pairs=[]
    for d,i,j in edges:
        if i in used_left or j in used_right:continue
        used_left.add(i);used_right.add(j)
        pairs.append((j,i,d) if swapped else (i,j,d))
    pairs.sort(key=lambda x:(x[0],x[1],x[2]));return pairs
def arm_norm(c):
    d=max(1,int(c["degree"]));return {k:float(v)/d for k,v in c.get("armHistogram",{}).items()}
def arm_l1(a,b):
    A=arm_norm(a);B=arm_norm(b);keys=set(A)|set(B);return sum(abs(A.get(k,0.0)-B.get(k,0.0)) for k in keys)
def mean_or_none(xs):return statistics.mean(xs) if xs else None
TRANSFORMS=["IDENTITY","ROT90","ROT180","ROT270","MIRROR_X","MIRROR_Y","MIRROR_DIAGONAL","MIRROR_ANTIDIAGONAL"]
REFLECTIONS={"MIRROR_X","MIRROR_Y","MIRROR_DIAGONAL","MIRROR_ANTIDIAGONAL"}
def pair_metrics(A,B,k_candidates):
    byA=defaultdict(list);byB=defaultdict(list)
    for c in A:byA[c["kind"]].append(c)
    for c in B:byB[c["kind"]].append(c)
    scores=[]
    for order,t in enumerate(TRANSFORMS):
        numer=0.0;denom=0
        for kind in ("ENDPOINT","JUNCTION"):
            aa=byA[kind];bb=byB[kind]
            d=symmetric_nearest_distance(aa,bb,t)
            if d is not None:
                w=len(aa)+len(bb);numer+=d*w;denom+=w
        scores.append((float("inf") if denom==0 else numer/denom,order,t))
    best=min(scores)[2]
    identity_distance=next(x[0] for x in scores if x[2]=="IDENTITY");best_distance=min(scores)[0]
    matched=defaultdict(list);matched_total=0
    for kind in ("ENDPOINT","JUNCTION"):
        aa=byA[kind];bb=byB[kind]
        for ia,ib,d in sparse_greedy_match(aa,bb,best,k_candidates):
            matched[kind].append((aa[ia],bb[ib],d));matched_total+=1
    countsA=Counter(c["kind"] for c in A);countsB=Counter(c["kind"] for c in B)
    def degree_mut(kind):return mean_or_none([abs(int(a["degree"])-int(b["degree"])) for a,b,_ in matched[kind]])
    def arm_mut(kind):return mean_or_none([arm_l1(a,b) for a,b,_ in matched[kind]])
    endpoint_total=max(1,countsA["ENDPOINT"]+countsB["ENDPOINT"]);junction_total=max(1,countsA["JUNCTION"]+countsB["JUNCTION"]);total=max(1,len(A)+len(B))
    return {
      "criticalCenterBirthDeathFraction":(abs(countsA["ENDPOINT"]-countsB["ENDPOINT"])+abs(countsA["JUNCTION"]-countsB["JUNCTION"]))/total,
      "endpointBirthDeathFraction":abs(countsA["ENDPOINT"]-countsB["ENDPOINT"])/endpoint_total,
      "junctionBirthDeathFraction":abs(countsA["JUNCTION"]-countsB["JUNCTION"])/junction_total,
      "identitySymmetricNearestDisplacement":None if math.isinf(identity_distance) else identity_distance,
      "bestD4SymmetricNearestDisplacement":None if math.isinf(best_distance) else best_distance,
      "orientationNormalizationGain":None if math.isinf(identity_distance) or math.isinf(best_distance) else identity_distance-best_distance,
      "nonIdentityTransform":0.0 if best=="IDENTITY" else 1.0,
      "reflectionTransform":1.0 if best in REFLECTIONS else 0.0,
      "endpointMeanDegreeMutation":degree_mut("ENDPOINT"),
      "junctionMeanDegreeMutation":degree_mut("JUNCTION"),
      "endpointMeanArmMutation":arm_mut("ENDPOINT"),
      "junctionMeanArmMutation":arm_mut("JUNCTION"),
      "allMatchedMeanArmMutation":mean_or_none([arm_l1(a,b) for kind in ("ENDPOINT","JUNCTION") for a,b,_ in matched[kind]]),
      "_bestTransform":best,"_matchedCenters":matched_total,"_centersA":len(A),"_centersB":len(B)
    }
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
    return (statistics.mean(effects) if effects else None,statistics.median(effects) if effects else None,details)
protocol=load_json(protocol_path)
if protocol.get("schema")!="mark_critical_center_correspondence_protocol_v4":raise RuntimeError("unexpected v4 protocol")
manifest=load_json(manifest_dir/"vertex-pair-manifest.json");msha=manifest.get("vertexPairManifestSha256")
if canonical_sha({k:v for k,v in manifest.items() if k!="vertexPairManifestSha256"})!=msha:raise RuntimeError("manifest SHA mismatch")
world=load_json(world_dir/"critical-center-world.json");wsha=world.get("criticalCenterWorldSha256")
if canonical_sha({k:v for k,v in world.items() if k!="criticalCenterWorldSha256"})!=wsha:raise RuntimeError("critical-center world SHA mismatch")
if world["vertexPairManifestSha256"]!=msha or not world["replayEquivalence"]["exactAggregateEquivalence"]:raise RuntimeError("critical-center world failed replay gate")
row_bytes=(world_dir/"critical-center-world.jsonl").read_bytes()
if hashlib.sha256(row_bytes).hexdigest()!=world["criticalCenterRowsSha256"]:raise RuntimeError("critical-center row SHA mismatch")
obs={}
for raw in row_bytes.splitlines():
    if raw.strip():
        r=json.loads(raw);obs[r["observationId"]]=r
pair_bytes=(manifest_dir/"role-pair-labels.jsonl").read_bytes()
if hashlib.sha256(pair_bytes).hexdigest()!=manifest["parentRolePairRowsSha256"]:raise RuntimeError("pair row SHA mismatch")
pairs=[json.loads(x) for x in pair_bytes.splitlines() if x.strip()]
features=[x["id"] for x in protocol["editObservables"]];labels={x["id"]:x["label"] for x in protocol["editObservables"]};k_candidates=int(protocol["correspondence"]["greedyNearestCandidatesPerCenter"])
edit_rows=[];transform_counts=defaultdict(lambda:defaultdict(Counter))
for r in pairs:
    metrics=pair_metrics(obs[r["observationA"]]["centers"],obs[r["observationB"]]["centers"],k_candidates);best=metrics.pop("_bestTransform")
    transform_counts[r["lane"]][r["label"]][best]+=1;edit_rows.append({**r,"editMagnitudes":metrics,"bestD4Transform":best})
train=[r for r in edit_rows if r["lane"]=="train"];min_cov=float(protocol["trainDiscovery"]["minimumPairCoveragePerEditAtom"])
observed={};eligible=[]
for f in features:
    available=sum(r["editMagnitudes"].get(f) is not None for r in train);coverage=available/max(1,len(train));mean_effect,median_effect,details=balanced_effect(train,f)
    observed[f]={"editId":f,"label":labels[f],"balancedEffect":mean_effect,"medianFamilyPairEffect":median_effect,"familyPairEffects":details,"trainPairCoverage":coverage,"trainPairsWithValue":available}
    if mean_effect is not None and coverage>=min_cov:eligible.append(f)
iterations=int(protocol["trainDiscovery"]["nullIterations"]);nulls={f:[] for f in eligible};bypair=defaultdict(list)
for r in train:bypair[(r["occupantFamilyA"],r["occupantFamilyB"])].append(r)
for it in range(iterations):
    shuffled=[]
    for (a,b),rs in sorted(bypair.items()):
        npos=sum(r["label"]=="preserved" for r in rs);ordered=sorted(rs,key=lambda r:(hashlib.sha256(f"vertex-edit-null|{it}|{a}|{b}|{r['observationA']}|{r['observationB']}".encode()).hexdigest(),r["observationA"],r["observationB"]))
        for idx,r in enumerate(ordered):shuffled.append({**r,"label":"preserved" if idx<npos else "broken"})
    for f in eligible:
        e,_,_=balanced_effect(shuffled,f);nulls[f].append(0.0 if e is None else e)
for f in eligible:
    obs_effect=observed[f]["balancedEffect"];vals=nulls[f];observed[f]["null"]={"iterations":iterations,"mean":statistics.mean(vals),"min":min(vals),"max":max(vals),"absoluteNullAtLeastObserved":sum(abs(x)>=abs(obs_effect) for x in vals),"beatsAllNullsByAbsoluteEffect":all(abs(obs_effect)>abs(x) for x in vals)}
max_atoms=int(protocol["trainDiscovery"]["maximumSelectedEditAtoms"]);selected=sorted(eligible,key=lambda f:(-abs(observed[f]["balancedEffect"]),f))[:max_atoms]
core={"schema":"mark_critical_center_edit_grammar_v4","experimentId":protocol["experimentId"],"vertexPairManifestSha256":msha,"criticalCenterWorldSha256":wsha,"parentRolePairFreezeSha256":manifest["parentRolePairFreezeSha256"],"provenanceAvailableDuringDiscovery":False,"trainPairs":len(train),"editRows":len(edit_rows),"effectSemantics":"positive = edit value is smaller in role-preserving pairs; negative = edit value is larger/enriched in role-preserving pairs","selectedEditAtoms":[observed[f] for f in selected],"allTrainEditAtomEffects":[observed[f] for f in features],"transformCountsByLaneAndLabel":{lane:{label:dict(sorted(c.items())) for label,c in labels2.items()} for lane,labels2 in transform_counts.items()},"contract":{"alignmentUsesNoRoleLabel":True,"transformSelectionUsesSymmetricNearestDistance":True,"oneToOneMutationCorrespondenceUsesSparseGreedyNearestCandidates":True,"matchingWithinCriticalCenterKindOnly":True,"editSelectionTrainOnly":True,"nullShufflesRoleLabelsWithinPhysicalFamilyPair":True,"holdoutAndControlUnavailableToSelection":True,"selectedReplayExactToFrozenFullWorldAggregates":True,"explicitEdgeCorrespondenceClaim":False,"noStateVocabularyConsumed":True,"noTransitionGrammarConsumed":True,"noProvenanceConsumed":True}}
digest=canonical_sha(core);packet={**core,"criticalCenterEditGrammarSha256":digest}
out_dir.mkdir(parents=True,exist_ok=True);(out_dir/"critical-center-edit-grammar.json").write_text(json.dumps(packet,indent=2)+"\n")
with (out_dir/"critical-center-pair-edits.jsonl").open("w",encoding="utf-8") as h:
    for r in edit_rows:h.write(json.dumps(r,separators=(",",":"),ensure_ascii=False)+"\n")
lines=[f"critical_center_edit_grammar_sha256={digest}",f"critical_center_world_sha256={wsha}",f"train_pairs={len(train)}",f"selected_atoms={len(selected)}"]
for i,f in enumerate(selected,1):
    o=observed[f];n=o.get("null",{});lines.append(f"atom_{i}={f};effect={o['balancedEffect']:.6f};coverage={o['trainPairCoverage']:.6f};null_at_least_observed={n.get('absoluteNullAtLeastObserved',-1)};label={labels[f]}")
(out_dir/"summary.txt").write_text("\n".join(lines)+"\n");print(json.dumps(packet,indent=2))
