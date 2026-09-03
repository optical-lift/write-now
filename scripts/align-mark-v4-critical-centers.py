#!/usr/bin/env python3
import hashlib, json, math, os, statistics
from collections import defaultdict
from pathlib import Path

protocol_path=Path(os.environ.get("MARK_V4_PROTOCOL","research/mark/discovery-experiments/critical-center-correspondence-v4.protocol.json"))
pair_dir=Path(os.environ.get("MARK_V4_UNLABELED","artifact-staging/v4-unlabeled"))
center_dir=Path(os.environ.get("MARK_V4_CENTERS","artifact-staging/v4-centers"))
out_dir=Path(os.environ.get("MARK_V4_ALIGNMENT_OUT","artifacts/mark-critical-center-alignment-v4"))

def load_json(p): return json.loads(Path(p).read_text())
def canonical_sha(v): return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
def locate(root,name):
    hits=list(root.rglob(name))
    if len(hits)!=1: raise RuntimeError(f"expected one {name}, found {len(hits)}")
    return hits[0]
def median(xs): return statistics.median(xs) if xs else 1.0
def percentile(xs,p):
    if not xs: return 1.0
    s=sorted(xs); idx=min(len(s)-1,max(0,int(math.ceil(p*len(s)))-1)); return s[idx]

protocol=load_json(protocol_path)
if protocol.get("schema")!="mark_critical_center_correspondence_protocol_v4": raise RuntimeError("unexpected v4 protocol")
freeze=load_json(locate(pair_dir,"pair-world-freeze.json"))
pair_bytes=locate(pair_dir,"unlabeled-pairs.jsonl").read_bytes()
if hashlib.sha256(pair_bytes).hexdigest()!=freeze["unlabeledPairsSha256"]: raise RuntimeError("unlabeled pair SHA mismatch")
pairs=[json.loads(x) for x in pair_bytes.splitlines() if x.strip()]
if any("label" in p for p in pairs): raise RuntimeError("alignment received a labeled pair manifest")
exact=load_json(locate(center_dir,"replay-exactness.json"))
if not exact.get("allSelectedObservationsExactlyMatchFrozenAggregateTopology"): raise RuntimeError("critical-center replay did not match parent topology")
center_path=locate(center_dir,"critical-centers.jsonl")
if hashlib.sha256(center_path.read_bytes()).hexdigest()!=exact["criticalCentersSha256"]: raise RuntimeError("critical-center file SHA mismatch")
region_path=locate(center_dir,"observation-regions.jsonl")
if hashlib.sha256(region_path.read_bytes()).hexdigest()!=exact["observationRegionsSha256"]: raise RuntimeError("region file SHA mismatch")
regions={json.loads(x)["observationId"]:json.loads(x) for x in region_path.read_bytes().splitlines() if x.strip()}

raw=defaultdict(list)
with center_path.open() as f:
    for line in f:
        if not line.strip(): continue
        r=json.loads(line)
        raw[r["observationId"]].append((float(r["x"]),float(r["y"]),0 if r["kind"]=="ENDPOINT" else 1,int(r["degree"]),int(r["endpointArms"]),int(r["junctionArms"]),int(r["unresolvedArms"]),int(r["otherArms"]),r.get("eventId") or ""))

required={p["observationA"] for p in pairs}|{p["observationB"] for p in pairs}
if required-set(raw): raise RuntimeError(f"missing center clouds for {len(required-set(raw))} pair observations")

def normalize(oid):
    reg=regions[oid]["region"]; pts=raw[oid]
    xy=[((p[0]-reg["x"])/max(1.0,float(reg["width"])),(p[1]-reg["y"])/max(1.0,float(reg["height"]))) for p in pts]
    mx=sum(x for x,y in xy)/len(xy); my=sum(y for x,y in xy)/len(xy)
    rms=math.sqrt(sum((x-mx)**2+(y-my)**2 for x,y in xy)/len(xy))
    scale=rms if rms>1e-9 else 1.0
    out=[]
    for (x,y),p in zip(xy,pts): out.append(((x-mx)/scale,(y-my)/scale,*p[2:]))
    return out
norm={oid:normalize(oid) for oid in required}

transforms={
 "identity":lambda x,y:(x,y),
 "rot90":lambda x,y:(-y,x),
 "rot180":lambda x,y:(-x,-y),
 "rot270":lambda x,y:(y,-x),
 "reflectX":lambda x,y:(x,-y),
 "reflectY":lambda x,y:(-x,y),
 "reflectDiag":lambda x,y:(y,x),
 "reflectAntiDiag":lambda x,y:(-y,-x)
}
transform_order={name:i for i,name in enumerate(protocol["alignment"]["candidateTransforms"])}
cell=float(protocol["alignment"]["spatialGridCell"])
radius=float(protocol["alignment"]["maximumSpatialRadius"])
cost_cfg=protocol["alignment"]["centerCost"]
max_shell=int(math.ceil(radius/cell))

def transformed(points,name):
    fn=transforms[name]; out=[]
    for p in points:
        x,y=fn(p[0],p[1]); out.append((x,y,*p[2:]))
    return out
def grid(points):
    g=defaultdict(list)
    for i,p in enumerate(points): g[(math.floor(p[0]/cell),math.floor(p[1]/cell))].append(i)
    return g
def sig_cost(a,b):
    return (float(cost_cfg["kindMismatchPenalty"])*(a[2]!=b[2])
        +float(cost_cfg["degreeDifferenceWeight"])*abs(a[3]-b[3])
        +float(cost_cfg["armL1Weight"])*(abs(a[4]-b[4])+abs(a[5]-b[5])+abs(a[6]-b[6])+abs(a[7]-b[7])))
def nearest_one(q,target,g):
    cx=math.floor(q[0]/cell); cy=math.floor(q[1]/cell)
    best=None
    for shell in range(max_shell+1):
        cells=[]
        if shell==0: cells=[(cx,cy)]
        else:
            for dx in range(-shell,shell+1):
                cells.append((cx+dx,cy-shell)); cells.append((cx+dx,cy+shell))
            for dy in range(-shell+1,shell):
                cells.append((cx-shell,cy+dy)); cells.append((cx+shell,cy+dy))
        for c in cells:
            for j in g.get(c,()):
                b=target[j]; dx=q[0]-b[0]; dy=q[1]-b[1]; spatial=math.hypot(dx,dy)
                if spatial>radius: continue
                cost=float(cost_cfg["spatialWeight"])*spatial+sig_cost(q,b)
                cand=(cost,spatial,j)
                if best is None or cand<best: best=cand
        if best is not None:
            lower=max(0.0,(shell+1)*cell-math.sqrt(2.0)*cell)
            if float(cost_cfg["spatialWeight"])*lower>best[0]: break
    return best
def mutual_matches(A,B):
    gb=grid(B); ga=grid(A)
    ab={}
    for i,a in enumerate(A):
        n=nearest_one(a,B,gb)
        if n is not None: ab[i]=n
    ba={}
    for j,b in enumerate(B):
        n=nearest_one(b,A,ga)
        if n is not None: ba[j]=n
    out=[]
    for i,(cost,spatial,j) in ab.items():
        back=ba.get(j)
        if back is not None and back[2]==i: out.append((i,j,cost,spatial))
    return out
def deterministic_sketch(points,limit):
    if len(points)<=limit: return points
    idx=sorted(range(len(points)),key=lambda i:(hashlib.sha256((points[i][8]+f"|{i}").encode()).hexdigest(),i))[:limit]
    return [points[i] for i in idx]
def score_transform(A,B,name,sketch_limit):
    As=deterministic_sketch(A,sketch_limit); Bs=deterministic_sketch(transformed(B,name),sketch_limit)
    m=mutual_matches(As,Bs)
    frac=2*len(m)/max(1,len(As)+len(Bs))
    disp=median([x[3] for x in m])
    sig=statistics.mean([sig_cost(As[i],Bs[j]) for i,j,_,_ in m]) if m else 999.0
    return (-frac,disp,sig,transform_order[name]), frac, disp, sig

def delta_bucket(v):
    if v<=-2:return "-2+"
    if v==-1:return "-1"
    if v==0:return "0"
    if v==1:return "+1"
    return "+2+"
move_bins=protocol["motifDiscovery"]["movementBins"]
def move_bucket(d):
    if d<=move_bins[0]: return "S"
    if d<=move_bins[1]: return "M"
    return "L"
def motif(a,b,d):
    ka="E" if a[2]==0 else "J"; kb="E" if b[2]==0 else "J"
    return f"{ka}>{kb}|D{delta_bucket(b[3]-a[3])}|E{delta_bucket(b[4]-a[4])}|J{delta_bucket(b[5]-a[5])}|U{delta_bucket(b[6]-a[6])}|M{move_bucket(d)}"
def match_metrics(A,B,name):
    Bt=transformed(B,name); matches=mutual_matches(A,Bt); m=len(matches)
    denom=max(1,len(A)+len(Bt))
    ds=[x[3] for x in matches]
    endpoint_ds=[]; junction_ds=[]; kind_switch=degree_change=exact_sig=0
    degree_abs=[]; e_abs=[]; j_abs=[]; u_abs=[]; motifs=defaultdict(int)
    for i,j,_,d in matches:
        a=A[i]; b=Bt[j]
        if a[2]!=b[2]: kind_switch+=1
        if a[3]!=b[3]: degree_change+=1
        if (a[2],a[3],a[4],a[5],a[6],a[7])==(b[2],b[3],b[4],b[5],b[6],b[7]): exact_sig+=1
        degree_abs.append(abs(a[3]-b[3])); e_abs.append(abs(a[4]-b[4])); j_abs.append(abs(a[5]-b[5])); u_abs.append(abs(a[6]-b[6]))
        if a[2]==0 and b[2]==0: endpoint_ds.append(d)
        if a[2]==1 and b[2]==1: junction_ds.append(d)
        motifs[motif(a,b,d)]+=1
    reflection=name in ("reflectX","reflectY","reflectDiag","reflectAntiDiag")
    quarter=name in ("rot90","rot270")
    return {
      "nodesA":len(A),"nodesB":len(Bt),"matchedCenters":m,
      "matchedFraction":2*m/denom,
      "unmatchedCenterFraction":1-(2*m/denom),
      "medianMatchedDisplacement":median(ds),
      "p90MatchedDisplacement":percentile(ds,0.90),
      "endpointMedianDisplacement":median(endpoint_ds),
      "junctionMedianDisplacement":median(junction_ds),
      "kindSwitchFraction":kind_switch/max(1,m),
      "degreeChangeFraction":degree_change/max(1,m),
      "meanAbsDegreeChange":statistics.mean(degree_abs) if degree_abs else 1.0,
      "endpointArmChangeMean":statistics.mean(e_abs) if e_abs else 1.0,
      "junctionArmChangeMean":statistics.mean(j_abs) if j_abs else 1.0,
      "unresolvedArmChangeMean":statistics.mean(u_abs) if u_abs else 1.0,
      "signatureChangeFraction":1-(exact_sig/max(1,m)),
      "nonIdentityTransform":0.0 if name=="identity" else 1.0,
      "reflectionTransform":1.0 if reflection else 0.0,
      "quarterTurnTransform":1.0 if quarter else 0.0,
      "motifCounts":dict(sorted(motifs.items())),
      "motifRates":{k:v/max(1,m) for k,v in sorted(motifs.items())}
    }

sketch_limit=int(protocol["alignment"]["transformSelectionSketchLimit"])
alignment_rows=[]
for idx,p in enumerate(pairs,1):
    A=norm[p["observationA"]]; B=norm[p["observationB"]]
    scored=[]
    for name in protocol["alignment"]["candidateTransforms"]:
        key,frac,disp,sig=score_transform(A,B,name,sketch_limit); scored.append((key,name,frac,disp,sig))
    scored.sort(key=lambda x:x[0]); _,name,skfrac,skdisp,sksig=scored[0]
    metrics=match_metrics(A,B,name)
    alignment_rows.append({
      "schema":"mark_critical_center_correspondence_pair_v4",
      **p,
      "selectedTransform":name,
      "transformSketchMatchedFraction":skfrac,
      "transformSketchMedianDisplacement":skdisp,
      "transformSketchMeanSignatureEdit":sksig,
      "metrics":metrics
    })
    if idx%25==0: print(f"aligned {idx}/{len(pairs)} pairs",flush=True)

out_dir.mkdir(parents=True,exist_ok=True); out_path=out_dir/"correspondence-pairs.jsonl"; h=hashlib.sha256()
with out_path.open("wb") as f:
    for r in alignment_rows:
        b=json.dumps(r,separators=(",",":")).encode()+b"\n"; f.write(b); h.update(b)
core={
 "schema":"mark_critical_center_correspondence_freeze_v4",
 "experimentId":protocol["experimentId"],
 "parentPairWorldFreezeSha256":freeze["pairWorldFreezeSha256"],
 "criticalCenterReplaySha256":exact["criticalCentersSha256"],
 "pairs":len(alignment_rows),
 "correspondenceRowsSha256":h.hexdigest(),
 "provenanceAvailableDuringAlignment":False,
 "labelsAvailableDuringAlignment":False,
 "contract":{
   "actualCriticalCenterCoordinatesUsed":True,
   "transformSelectedWithoutLabels":True,
   "fullCenterCloudUsedForFinalCorrespondence":True,
   "mutualNearestOnly":True,
   "sameAlgorithmForAllPairs":True,
   "noStateVocabularyConsumed":True,
   "noTransitionGrammarConsumed":True,
   "noProvenanceConsumed":True
 }
}
digest=canonical_sha(core); packet={**core,"criticalCenterCorrespondenceSha256":digest}
(out_dir/"correspondence-freeze.json").write_text(json.dumps(packet,indent=2)+"\n")
(out_dir/"summary.txt").write_text(f"critical_center_correspondence_sha256={digest}\npairs={len(alignment_rows)}\nlabels_available_during_alignment=false\n")
print(json.dumps(packet,indent=2))
