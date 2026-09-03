#!/usr/bin/env python3
import hashlib, json, math, os, statistics
from collections import Counter, defaultdict
from pathlib import Path

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
def euclid(a,b): return math.hypot(a[0]-b[0],a[1]-b[1])
def hungarian(cost):
    n=len(cost)
    if n==0:return []
    m=len(cost[0])
    if n>m:raise RuntimeError("hungarian requires rows<=columns")
    u=[0.0]*(n+1);v=[0.0]*(m+1);p=[0]*(m+1);way=[0]*(m+1)
    for i in range(1,n+1):
        p[0]=i;j0=0;minv=[float("inf")]*(m+1);used=[False]*(m+1)
        while True:
            used[j0]=True;i0=p[j0];delta=float("inf");j1=0
            for j in range(1,m+1):
                if used[j]:continue
                cur=cost[i0-1][j-1]-u[i0]-v[j]
                if cur<minv[j]-1e-15:minv[j]=cur;way[j]=j0
                if minv[j]<delta-1e-15 or (abs(minv[j]-delta)<=1e-15 and (j1==0 or j<j1)):delta=minv[j];j1=j
            for j in range(m+1):
                if used[j]:u[p[j]]+=delta;v[j]-=delta
                else:minv[j]-=delta
            j0=j1
            if p[j0]==0:break
        while True:
            j1=way[j0];p[j0]=p[j1];j0=j1
            if j0==0:break
    assignment=[None]*n
    for j in range(1,m+1):
        if p[j]!=0:assignment[p[j]-1]=j-1
    return [(i,j) for i,j in enumerate(assignment) if j is not None]
def match_kind(a,b,transform):
    if not a or not b:return []
    apos=[transform_point(x["u"],x["v"],transform) for x in a];bpos=[(x["u"],x["v"]) for x in b]
    if len(a)<=len(b):
        return hungarian([[euclid(apos[i],bpos[j]) for j in range(len(b))] for i in range(len(a))])
    rev=hungarian([[euclid(bpos[j],apos[i]) for i in range(len(a))] for j in range(len(b))])
    return [(ai,bj) for bj,ai in rev]
def arm_norm(c):
    d=max(1,int(c["degree"]));return {k:float(v)/d for k,v in c.get("armHistogram",{}).items()}
def arm_l1(a,b):
    A=arm_norm(a);B=arm_norm(b);keys=set(A)|set(B);return sum(abs(A.get(k,0.0)-B.get(k,0.0)) for k in keys)
def mean_or_none(xs):return statistics.mean(xs) if xs else None
TRANSFORMS=["IDENTITY","ROT90","ROT180","ROT270","MIRROR_X","MIRROR_Y","MIRROR_DIAGONAL","MIRROR_ANTIDIAGONAL"]
REFLECTIONS={"MIRROR_X","MIRROR_Y","MIRROR_DIAGONAL","MIRROR_ANTIDIAGONAL"}
def alignment(A,B,transform):
    byA=defaultdict(list);byB=defaultdict(list)
    for c in A:byA[c["kind"]].append(c)
    for c in B:byB[c["kind"]].append(c)
    pairs=[]
    for kind in ("ENDPOINT","JUNCTION"):
        aa=byA[kind];bb=byB[kind]
        for ia,ib in match_kind(aa,bb,transform):
            pa=transform_point(aa[ia]["u"],aa[ia]["v"],transform);pb=(bb[ib]["u"],bb[ib]["v"])
            pairs.append((kind,aa[ia],bb[ib],euclid(pa,pb)))
    return pairs
def pair_metrics(A,B):
    alignments={t:alignment(A,B,t) for t in TRANSFORMS}
    def disp(ps):return statistics.mean([x[3] for x in ps]) if ps else None
    scored=[]
    for order,t in enumerate(TRANSFORMS):
        d=disp(alignments[t]);scored.append((float("inf") if d is None else d,order,t))
    best=min(scored)[2];id_pairs=alignments["IDENTITY"];best_pairs=alignments[best]
    countsA=Counter(c["kind"] for c in A);countsB=Counter(c["kind"] for c in B)
    matched=defaultdict(list)
    for kind,a,b,d in best_pairs:matched[kind].append((a,b,d))
    def degree_mut(kind):return mean_or_none([abs(int(a["degree"])-int(b["degree"])) for a,b,_ in matched[kind]])
    def arm_mut(kind):return mean_or_none([arm_l1(a,b) for a,b,_ in matched[kind]])
    identity_disp=disp(id_pairs);best_disp=disp(best_pairs)
    endpoint_total=max(1,countsA["ENDPOINT"]+countsB["ENDPOINT"]);junction_total=max(1,countsA["JUNCTION"]+countsB["JUNCTION"]);total=max(1,len(A)+len(B))
    return {
      "criticalCenterBirthDeathFraction":(abs(countsA["ENDPOINT"]-countsB["ENDPOINT"])+abs(countsA["JUNCTION"]-countsB["JUNCTION"]))/total,
      "endpointBirthDeathFraction":abs(countsA["ENDPOINT"]-countsB["ENDPOINT"])/endpoint_total,
      "junctionBirthDeathFraction":abs(countsA["JUNCTION"]-countsB["JUNCTION"])/junction_total,
      "identityMeanMatchedDisplacement":identity_disp,
      "bestD4MeanMatchedDisplacement":best_disp,
      "orientationNormalizationGain":None if identity_disp is None or best_disp is None else identity_disp-best_disp,
      "nonIdentityTransform":0.0 if best=="IDENTITY" else 1.0,
      "reflectionTransform":1.0 if best in REFLECTIONS else 0.0,
      "endpointMeanDegreeMutation":degree_mut("ENDPOINT"),
      "junctionMeanDegreeMutation":degree_mut("JUNCTION"),
      "endpointMeanArmMutation":arm_mut("ENDPOINT"),
      "junctionMeanArmMutation":arm_mut("JUNCTION"),
      "allMatchedMeanArmMutation":mean_or_none([arm_l1(a,b) for _,a,b,_ in best_pairs]),
      "_bestTransform":best,"_matchedCenters":len(best_pairs),"_centersA":len(A),"_centersB":len(B)
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
features=[x["id"] for x in protocol["editObservables"]];labels={x["id"]:x["label"] for x in protocol["editObservables"]}
edit_rows=[];transform_counts=defaultdict(lambda:defaultdict(Counter))
for r in pairs:
    metrics=pair_metrics(obs[r["observationA"]]["centers"],obs[r["observationB"]]["centers"]);best=metrics.pop("_bestTransform")
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
core={"schema":"mark_critical_center_edit_grammar_v4","experimentId":protocol["experimentId"],"vertexPairManifestSha256":msha,"criticalCenterWorldSha256":wsha,"parentRolePairFreezeSha256":manifest["parentRolePairFreezeSha256"],"provenanceAvailableDuringDiscovery":False,"trainPairs":len(train),"editRows":len(edit_rows),"effectSemantics":"positive = edit value is smaller in role-preserving pairs; negative = edit value is larger/enriched in role-preserving pairs","selectedEditAtoms":[observed[f] for f in selected],"allTrainEditAtomEffects":[observed[f] for f in features],"transformCountsByLaneAndLabel":{lane:{label:dict(sorted(c.items())) for label,c in labels2.items()} for lane,labels2 in transform_counts.items()},"contract":{"alignmentUsesNoRoleLabel":True,"matchingWithinCriticalCenterKindOnly":True,"editSelectionTrainOnly":True,"nullShufflesRoleLabelsWithinPhysicalFamilyPair":True,"holdoutAndControlUnavailableToSelection":True,"selectedReplayExactToFrozenFullWorldAggregates":True,"explicitEdgeCorrespondenceClaim":False,"noStateVocabularyConsumed":True,"noTransitionGrammarConsumed":True,"noProvenanceConsumed":True}}
digest=canonical_sha(core);packet={**core,"criticalCenterEditGrammarSha256":digest}
out_dir.mkdir(parents=True,exist_ok=True);(out_dir/"critical-center-edit-grammar.json").write_text(json.dumps(packet,indent=2)+"\n")
with (out_dir/"critical-center-pair-edits.jsonl").open("w",encoding="utf-8") as h:
    for r in edit_rows:h.write(json.dumps(r,separators=(",",":"),ensure_ascii=False)+"\n")
lines=[f"critical_center_edit_grammar_sha256={digest}",f"critical_center_world_sha256={wsha}",f"train_pairs={len(train)}",f"selected_atoms={len(selected)}"]
for i,f in enumerate(selected,1):
    o=observed[f];n=o.get("null",{});lines.append(f"atom_{i}={f};effect={o['balancedEffect']:.6f};coverage={o['trainPairCoverage']:.6f};null_at_least_observed={n.get('absoluteNullAtLeastObserved',-1)};label={labels[f]}")
(out_dir/"summary.txt").write_text("\n".join(lines)+"\n");print(json.dumps(packet,indent=2))
