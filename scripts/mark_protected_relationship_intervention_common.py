#!/usr/bin/env python3
import hashlib, json, math, statistics
from collections import Counter, defaultdict, deque
from pathlib import Path
from scipy.spatial import cKDTree

TRANSFORMS=("IDENTITY","ROT90","ROT180","ROT270","MIRROR_X","MIRROR_Y","MIRROR_DIAGONAL","MIRROR_ANTIDIAGONAL")

def load_json(path): return json.loads(Path(path).read_text(encoding="utf-8"))
def canonical_sha(v): return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
def locate(root,name):
    hits=list(Path(root).rglob(name))
    if len(hits)!=1: raise RuntimeError(f"expected one {name}, found {len(hits)}")
    return hits[0]

def tp(u,v,t):
    if t=="IDENTITY": return u,v
    if t=="ROT90": return 1-v,u
    if t=="ROT180": return 1-u,1-v
    if t=="ROT270": return v,1-u
    if t=="MIRROR_X": return 1-u,v
    if t=="MIRROR_Y": return u,1-v
    if t=="MIRROR_DIAGONAL": return v,u
    if t=="MIRROR_ANTIDIAGONAL": return 1-v,1-u
    raise RuntimeError(t)

def points(ids,g,t):
    r=g["region"]; w=max(1.,float(r["width"])); h=max(1.,float(r["height"])); x0=float(r["x"]); y0=float(r["y"])
    return [tp((g["centers"][i]["x"]-x0)/w,(g["centers"][i]["y"]-y0)/h,t) for i in ids]

def symmetric_distance(a,b,ga,gb,t):
    if not a or not b: return None
    A=points(a,ga,t); B=points(b,gb,"IDENTITY"); ta=cKDTree(A); tb=cKDTree(B)
    da=tb.query(A,k=1,workers=1)[0]; db=ta.query(B,k=1,workers=1)[0]
    return (float(da.sum())+float(db.sum()))/(len(A)+len(B))

def sparse_match(a,b,ga,gb,t,kcand=8):
    if not a or not b: return []
    A=points(a,ga,t); B=points(b,gb,"IDENTITY"); swapped=False; left,right=A,B; li,ri=a,b
    if len(left)>len(right): left,right=right,left; li,ri=ri,li; swapped=True
    k=max(1,min(kcand,len(right))); tree=cKDTree(right); ds,ix=tree.query(left,k=k,workers=1)
    if k==1: ds=[[float(x)] for x in ds]; ix=[[int(x)] for x in ix]
    candidates=[]
    for i in range(len(left)):
        for q in range(k): candidates.append((float(ds[i][q]),i,int(ix[i][q])))
    candidates.sort(key=lambda z:(z[0],z[1],z[2])); used_l=set(); used_r=set(); out=[]
    for d,i,j in candidates:
        if i in used_l or j in used_r: continue
        used_l.add(i); used_r.add(j); out.append((ri[j],li[i],d) if swapped else (li[i],ri[j],d))
    return out

def center_mapping(ga,gb,kcand=8):
    aa=defaultdict(list); bb=defaultdict(list)
    for i,c in ga["centers"].items(): aa[c["kind"]].append(i)
    for i,c in gb["centers"].items(): bb[c["kind"]].append(i)
    scored=[]
    for order,t in enumerate(TRANSFORMS):
        num=0.; den=0
        for kind in ("ENDPOINT","JUNCTION"):
            d=symmetric_distance(aa[kind],bb[kind],ga,gb,t)
            if d is not None:
                weight=len(aa[kind])+len(bb[kind]); num+=d*weight; den+=weight
        scored.append((float("inf") if den==0 else num/den,order,t))
    best=min(scored)[2]; mapping={}
    for kind in ("ENDPOINT","JUNCTION"):
        for a,b,_ in sparse_match(aa[kind],bb[kind],ga,gb,best,kcand): mapping[a]=b
    return mapping,best

def load_graphs(v5_root,needed):
    path=locate(v5_root,"critical-edge-observations.jsonl"); out={}
    with path.open(encoding="utf-8") as f:
        for line in f:
            if not line.strip(): continue
            r=json.loads(line); oid=r["observationId"]
            if oid not in needed: continue
            centers={c["eventId"]:{"kind":c["kind"],"degree":int(c["degree"]),"x":float(c["x"]),"y":float(c["y"])} for c in r["centers"]}
            grouped=defaultdict(list)
            for e in r["edges"]: grouped[tuple(sorted((e["a"],e["b"])))].append(e)
            diag=max(1.,math.hypot(float(r["region"]["width"]),float(r["region"]["height"]))); edges={}; adjacency=defaultdict(set)
            for key,es in grouped.items():
                a,b=key
                edges[key]={"mult":len(es),"length":statistics.mean(float(e["pathSteps"]) for e in es)/diag,"turn":statistics.mean(float(e["turnRate"]) for e in es),"tort":statistics.mean(float(e["tortuosity"]) for e in es)}
                if a!=b: adjacency[a].add(b); adjacency[b].add(a)
            out[oid]={"observationId":oid,"region":r["region"],"centers":centers,"edges":edges,"adjacency":adjacency}
    missing=set(needed)-set(out)
    if missing: raise RuntimeError(f"missing graphs: {len(missing)}")
    return out

def degree_class(d,cap=6): return min(int(d),cap)
def multiplicity_class(m,cap=3): return min(int(m),cap)
def length_bin(x,width=.05): return int(math.floor(max(0.,float(x))/float(width)+1e-12))

def orient_edge(key,g):
    a,b=key; ca,cb=g["centers"][a],g["centers"][b]; sa=(ca["kind"],degree_class(ca["degree"])); sb=(cb["kind"],degree_class(cb["degree"]))
    if sb<sa or (sb==sa and b<a): a,b=b,a; sa,sb=sb,sa
    return a,b,sa,sb

def graph_distance_roots(g,edited,mapping,radius=2,include_edited=False):
    dist={n:0 for n in edited}; q=deque(edited)
    while q:
        cur=q.popleft()
        if dist[cur]>=radius: continue
        for nb in g["adjacency"].get(cur,()):
            if nb not in dist: dist[nb]=dist[cur]+1; q.append(nb)
    return sorted(n for n,d in dist.items() if n in mapping and d<=radius and (include_edited or n not in edited))

def select_intervention(g,mapping,cfg):
    width=float(cfg["normalizedPathLengthBinWidth"]); min_geom=float(cfg["minimumResidualGeometrySeparation"]); chord_tol=int(cfg["maximumNewChordBinShift"]); min_roots=int(cfg["minimumAffectedMappedNonEndpointRoots"]); mapped=set(mapping); buckets=defaultdict(list)
    for key,attr in g["edges"].items():
        a,b=key
        if a==b or a not in mapped or b not in mapped: continue
        a,b,sa,sb=orient_edge(key,g); buckets[(sa,sb,int(attr["mult"]),length_bin(attr["length"],width))].append((a,b,key,attr))
    reg=g["region"]; diag=max(1.,math.hypot(float(reg["width"]),float(reg["height"])))
    def chord(u,v):
        a,b=g["centers"][u],g["centers"][v]; return math.hypot(a["x"]-b["x"],a["y"]-b["y"])/diag
    for bucket in sorted(buckets,key=str):
        es=sorted(buckets[bucket],key=lambda z:(z[0],z[1]))
        for i in range(len(es)):
            a,b,k1,e1=es[i]
            for j in range(i+1,min(len(es),i+120)):
                x,y,k2,e2=es[j]
                if len({a,b,x,y})<4: continue
                n1=tuple(sorted((a,y))); n2=tuple(sorted((x,b)))
                if n1 in g["edges"] or n2 in g["edges"]: continue
                geom=abs(e1["turn"]-e2["turn"])+abs(e1["tort"]-e2["tort"])
                if geom<min_geom: continue
                old1,old2,new1,new2=chord(a,b),chord(x,y),chord(a,y),chord(x,b)
                if abs(length_bin(old1,width)-length_bin(new1,width))>chord_tol or abs(length_bin(old2,width)-length_bin(new2,width))>chord_tol: continue
                edited={a,b,x,y}; roots=graph_distance_roots(g,edited,mapping,2,False)
                if len(roots)<min_roots: continue
                return {"edge1":[a,b],"edge2":[x,y],"rewiredEdge1":list(n1),"rewiredEdge2":list(n2),"edgeStratum":[list(bucket[0]),list(bucket[1]),bucket[2],bucket[3]],"residualGeometrySeparation":geom,"oldChord":[old1,old2],"newChord":[new1,new2],"affectedRootCount":len(roots)}
    return None

def relation_overlay(g,intervention):
    a,b=intervention["edge1"]; x,y=intervention["edge2"]; k1=tuple(sorted((a,b))); k2=tuple(sorted((x,y))); n1=tuple(intervention["rewiredEdge1"]); n2=tuple(intervention["rewiredEdge2"])
    return {"removed":{k1,k2},"added":{n1:g["edges"][k1],n2:g["edges"][k2]}}

def neighbors(g,node,overlay=None):
    n=set(g["adjacency"].get(node,set()))
    if overlay:
        for a,b in overlay["removed"]:
            if a==node: n.discard(b)
            elif b==node: n.discard(a)
        for a,b in overlay["added"]:
            if a==node: n.add(b)
            elif b==node: n.add(a)
    return n

def get_edge(g,key,overlay=None):
    key=tuple(sorted(key))
    if overlay:
        if key in overlay["removed"]: return None
        if key in overlay["added"]: return overlay["added"][key]
    return g["edges"].get(key)

def motif_tokens(g,root,radius,variant,overlay=None):
    depths={root:0}; q=deque([root])
    while q:
        cur=q.popleft(); depth=depths[cur]
        if depth>=radius: continue
        for nb in sorted(neighbors(g,cur,overlay)):
            if nb not in depths: depths[nb]=depth+1; q.append(nb)
    nodes=set(depths); tokens=Counter()
    for node in nodes:
        c=g["centers"][node]; tokens[f"N|Z{depths[node]}|{'R' if node==root else 'N'}|{c['kind']}|D{degree_class(c['degree'])}"]+=1
    keys=set()
    for node in nodes:
        for nb in neighbors(g,node,overlay):
            if nb in nodes: keys.add(tuple(sorted((node,nb))))
    for key in g["edges"]:
        if key[0]==key[1] and key[0] in nodes and get_edge(g,key,overlay) is not None: keys.add(key)
    if overlay:
        for key in overlay["added"]:
            if key[0]==key[1] and key[0] in nodes: keys.add(key)
    for a,b in sorted(keys):
        e=get_edge(g,(a,b),overlay)
        if e is None: continue
        ca,cb=g["centers"][a],g["centers"][b]; left=f"Z{depths[a]}|{ca['kind']}|D{degree_class(ca['degree'])}"; right=f"Z{depths[b]}|{cb['kind']}|D{degree_class(cb['degree'])}"
        if right<left: left,right=right,left
        tok=f"E|{'LOOP' if a==b else 'EDGE'}|{left}|M{multiplicity_class(e['mult'])}"
        if variant=="lengthAware": tok+=f"|L{length_bin(e['length'],.05)}"
        tokens[tok+f"|{right}"]+=1
    return tokens

def multiset_jaccard_distance(a,b):
    keys=set(a)|set(b)
    if not keys: return 0.
    inter=sum(min(a.get(k,0),b.get(k,0)) for k in keys); union=sum(max(a.get(k,0),b.get(k,0)) for k in keys)
    return 0. if union==0 else 1-inter/union

def score_intervention(gA,gB,mapping,intervention,variant="lengthAware",include_edited=False):
    edited=set(intervention["edge1"]+intervention["edge2"]); roots=graph_distance_roots(gA,edited,mapping,2,include_edited)
    if not roots: return None
    overlay=relation_overlay(gA,intervention); deltas=[]; base=[]; rew=[]
    for root in roots:
        target=mapping[root]; tb=motif_tokens(gB,target,2,variant,None); render=motif_tokens(gA,root,2,variant,None); relation=motif_tokens(gA,root,2,variant,overlay)
        d0=multiset_jaccard_distance(render,tb); d1=multiset_jaccard_distance(relation,tb); base.append(d0); rew.append(d1); deltas.append(d1-d0)
    return {"delta":statistics.mean(deltas),"roots":len(roots),"renderDistance":statistics.mean(base),"relationshipDistance":statistics.mean(rew)}

def auc_larger(pos,neg):
    if not pos or not neg: return None
    score=0.; total=0
    for p in pos:
        for n in neg:
            total+=1; score+=1 if p>n else .5 if p==n else 0
    return 2*score/total-1

def balanced_effect(scored,feature,label_override=None):
    by=defaultdict(lambda:{"preserved":[],"broken":[]})
    for r in scored:
        label=label_override.get(r["pairId"],r["label"]) if label_override else r["label"]; by[(r["occupantFamilyA"],r["occupantFamilyB"])][label].append(float(r[feature]))
    effects=[]; details=[]
    for (a,b),d in sorted(by.items()):
        e=auc_larger(d["preserved"],d["broken"])
        if e is None: continue
        effects.append(e); details.append({"occupantFamilyA":a,"occupantFamilyB":b,"effect":e,"preserved":len(d["preserved"]),"broken":len(d["broken"])})
    return {"balancedEffect":statistics.mean(effects) if effects else None,"supportedFamilies":len(effects),"familyEffects":details}
