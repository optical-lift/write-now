#!/usr/bin/env python3
import hashlib, json, math, os, random, statistics
from collections import Counter, deque
from pathlib import Path

PROTOCOL = Path(os.environ.get("MARK_WHITE_PAINT_PROTOCOL", "research/mark/discovery-experiments/white-paint-grammar-v1.protocol.json"))
OUT = Path(os.environ.get("MARK_WHITE_PAINT_OUT", "artifacts/mark-white-paint-grammar-v1"))
V5_OBS = os.environ.get("MARK_WHITE_PAINT_V5_OBSERVATIONS")

def canonical_sha(v):
    return hashlib.sha256(json.dumps(v, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()

class Graph:
    def __init__(self):
        self.nodes = {}
        self.edges = set()
    def add_node(self, name, x, y):
        self.nodes[name] = (float(x), float(y)); return name
    def add_edge(self, a, b):
        if a == b: raise ValueError("self edge")
        if a not in self.nodes or b not in self.nodes: raise KeyError((a,b))
        self.edges.add(tuple(sorted((a,b))))
    def copy(self):
        g=Graph(); g.nodes=dict(self.nodes); g.edges=set(self.edges); return g

STYLES = {
    "identity": lambda x,y:(x,y),
    "rot90": lambda x,y:(-y,x),
    "rot180": lambda x,y:(-x,-y),
    "mirror_x": lambda x,y:(-x,y),
    "stretch_x": lambda x,y:(1.7*x,y),
    "stretch_y": lambda x,y:(x,1.6*y),
}

def styled(g, style):
    f=STYLES[style]; h=g.copy(); h.nodes={k:f(*v) for k,v in g.nodes.items()}; return h

def adjacency(g):
    a={n:set() for n in g.nodes}
    for u,v in g.edges: a[u].add(v); a[v].add(u)
    return a

def components(g):
    a=adjacency(g); unseen=set(g.nodes); out=[]
    while unseen:
        s=unseen.pop(); comp={s}; q=[s]
        for u in q:
            for v in a[u]:
                if v in unseen: unseen.remove(v); comp.add(v); q.append(v)
        out.append(comp)
    return out

def shortest_distances(a, s):
    q=deque([s]); d={s:0}; prev={s:None}
    while q:
        u=q.popleft()
        for v in a[u]:
            if v not in d: d[v]=d[u]+1; prev[v]=u; q.append(v)
    return d,prev

def diameter_path(g):
    a=adjacency(g); best=(-1, [])
    for comp in components(g):
        for s in comp:
            d,prev=shortest_distances(a,s)
            for t,dt in d.items():
                if t not in comp or dt <= best[0]: continue
                path=[]; cur=t
                while cur is not None:
                    path.append(cur)
                    if cur==s: break
                    cur=prev[cur]
                if path[-1]==s: best=(dt,list(reversed(path)))
    return best[1]

def is_collinear(p, q, r, eps=1e-8):
    return abs((q[0]-p[0])*(r[1]-q[1])-(q[1]-p[1])*(r[0]-q[0])) < eps

def extract(g):
    a=adjacency(g); deg={n:len(v) for n,v in a.items()}; comps=components(g)
    cycle_rank=max(0, len(g.edges)-len(g.nodes)+len(comps))
    endpoints=[n for n,d in deg.items() if d==1]
    turn_nodes=[]
    for n,d in deg.items():
        if d==2:
            u,v=tuple(a[n])
            if not is_collinear(g.nodes[u], g.nodes[n], g.nodes[v]): turn_nodes.append(n)
    path=diameter_path(g); diameter=max(1,len(path)-1)
    names=list(g.nodes); best_carrier=[]; best_span=-1.0
    for i,u in enumerate(names):
        x1,y1=g.nodes[u]
        for v in names[i+1:]:
            x2,y2=g.nodes[v]; dx=x2-x1; dy=y2-y1; norm=math.hypot(dx,dy)
            if norm==0: continue
            cand=[n for n,(x,y) in g.nodes.items() if abs(dx*(y-y1)-dy*(x-x1)) <= 1e-8*max(1.0,norm)]
            if len(cand)<2: continue
            ux,uy=dx/norm,dy/norm
            proj=[((g.nodes[n][0]-x1)*ux+(g.nodes[n][1]-y1)*uy,n) for n in cand]
            span=max(t for t,_ in proj)-min(t for t,_ in proj)
            if len(cand)>len(best_carrier) or (len(cand)==len(best_carrier) and span>best_span):
                best_carrier=cand; best_span=span
    carrier=set(best_carrier); locus=[]
    if carrier:
        eu,ev=max(((u,v) for u in carrier for v in carrier if u!=v), key=lambda p:math.dist(g.nodes[p[0]],g.nodes[p[1]]))
        x1,y1=g.nodes[eu]; x2,y2=g.nodes[ev]; dx=x2-x1; dy=y2-y1; den=dx*dx+dy*dy
        roots=[n for n in carrier if any(m not in carrier for m in a[n])]
        for n in roots:
            x,y=g.nodes[n]; t=((x-x1)*dx+(y-y1)*dy)/den if den else 0.0; locus.append(min(abs(t),abs(1-t)))
    off=[n for n in g.nodes if n not in carrier]
    off_edges=[e for e in g.edges if e[0] in off and e[1] in off]
    return {
        "components":len(comps), "cycleRank":cycle_rank, "endpoints":len(endpoints),
        "degree3":sum(d==3 for d in deg.values()), "degree4plus":sum(d>=4 for d in deg.values()),
        "turnNodes":len(turn_nodes), "diameterEdges":diameter,
        "minJunctionEndpointRatio":min(locus) if locus else 1.0,
        "meanJunctionEndpointRatio":statistics.mean(locus) if locus else 1.0,
        "offCarrierNodes":len(off), "offCarrierEdges":len(off_edges), "maxDegree":max(deg.values(), default=0),
    }

def carrier(n=11):
    g=Graph()
    for i in range(n):
        g.add_node(f"c{i}", i, 0)
        if i: g.add_edge(f"c{i-1}",f"c{i}")
    return g

def attach_modifier(g, idx, shape):
    root=f"c{idx}"
    if shape=="tick":
        g.add_node("m0",idx,1); g.add_node("m1",idx,2); g.add_edge(root,"m0"); g.add_edge("m0","m1")
    elif shape=="zigzag":
        g.add_node("m0",idx,1); g.add_node("m1",idx+1,1); g.add_node("m2",idx+1,2)
        g.add_edge(root,"m0"); g.add_edge("m0","m1"); g.add_edge("m1","m2")
    elif shape=="fork":
        g.add_node("m0",idx,1); g.add_node("m1",idx-1,2); g.add_node("m2",idx+1,2)
        g.add_edge(root,"m0"); g.add_edge("m0","m1"); g.add_edge("m0","m2")
    else: raise ValueError(shape)

def relation_rows():
    rows=[]
    for relation,idx in (("near_terminal",1),("interior",5)):
        for shape in ("tick","zigzag","fork"):
            base=carrier(); attach_modifier(base,idx,shape)
            for style in STYLES: rows.append({"label":relation,"shape":shape,"style":style,"features":extract(styled(base,style))})
    return rows

def repeated_graph(k):
    g=carrier(13)
    for j,idx in enumerate(range(2,2+k*2,2)):
        g.add_node(f"r{j}a",idx,1); g.add_node(f"r{j}b",idx,2)
        g.add_edge(f"c{idx}",f"r{j}a"); g.add_edge(f"r{j}a",f"r{j}b")
    return g

def degree_rows():
    return [{"degree":k,"style":style,"features":extract(styled(repeated_graph(k),style))} for k in range(1,6) for style in STYLES]

def closure_graph(closed, tail):
    g=Graph()
    for n,x,y in (("a",0,0),("b",4,0),("c",4,4),("d",0,4)): g.add_node(n,x,y)
    for e in (("a","b"),("b","c"),("c","d")): g.add_edge(*e)
    if closed: g.add_edge("d","a")
    if tail:
        g.add_node("t1",6,4); g.add_node("t2",8,4); g.add_edge("c","t1"); g.add_edge("t1","t2")
    return g

def closure_rows():
    return [{"label":"closed" if closed else "open","tail":tail,"style":style,"features":extract(styled(closure_graph(closed,tail),style))} for closed in (False,True) for tail in (False,True) for style in STYLES]

def operation_graph(op):
    g=Graph()
    if op=="persist":
        for i in range(5): g.add_node(f"n{i}",i,0)
        for i in range(4): g.add_edge(f"n{i}",f"n{i+1}")
    elif op=="turn":
        for n,x,y in (("a",0,0),("b",2,0),("c",2,2),("d",2,4)): g.add_node(n,x,y)
        for e in (("a","b"),("b","c"),("c","d")): g.add_edge(*e)
    elif op=="branch":
        for n,x,y in (("a",0,0),("b",2,0),("c",4,0),("d",2,2)): g.add_node(n,x,y)
        for e in (("a","b"),("b","c"),("b","d")): g.add_edge(*e)
    elif op=="cross":
        for n,x,y in (("a",0,2),("b",2,2),("c",4,2),("d",2,0),("e",2,4)): g.add_node(n,x,y)
        for e in (("a","b"),("b","c"),("d","b"),("b","e")): g.add_edge(*e)
    elif op=="close": g=closure_graph(True,False)
    elif op=="loop_continue": g=closure_graph(True,True)
    else: raise ValueError(op)
    return g

def operation_rows():
    return [{"label":op,"style":style,"features":extract(styled(operation_graph(op),style))} for op in ("persist","turn","branch","cross","close","loop_continue") for style in STYLES]

def zstats(rows, fs):
    means={f:statistics.mean(float(r["features"][f]) for r in rows) for f in fs}
    stds={f:statistics.pstdev(float(r["features"][f]) for r in rows) or 1.0 for f in fs}
    return means,stds

def vec(r, fs, means, stds): return [(float(r["features"][f])-means[f])/stds[f] for f in fs]

def nearest_centroid(train, test, fs, label_key="label"):
    means,stds=zstats(train,fs); labels=sorted({r[label_key] for r in train},key=str); cent={}
    for lab in labels:
        vs=[vec(r,fs,means,stds) for r in train if r[label_key]==lab]; cent[lab]=[statistics.mean(x) for x in zip(*vs)]
    good=0
    for r in test:
        v=vec(r,fs,means,stds); pred=min(labels,key=lambda lab:sum((a-b)**2 for a,b in zip(v,cent[lab]))); good+=pred==r[label_key]
    return good/max(1,len(test))

def leave_one_style_out(rows, fs, label_key="label"):
    return statistics.mean(nearest_centroid([r for r in rows if r["style"]!=s],[r for r in rows if r["style"]==s],fs,label_key) for s in STYLES)

def heldout_shape_relation(rows, fs):
    return statistics.mean(nearest_centroid([r for r in rows if r["shape"]!=shape],[r for r in rows if r["shape"]==shape],fs,"label") for shape in ("tick","zigzag","fork"))

def rankdata(xs):
    order=sorted(range(len(xs)),key=lambda i:xs[i]); ranks=[0.0]*len(xs); i=0
    while i<len(order):
        j=i+1
        while j<len(order) and xs[order[j]]==xs[order[i]]: j+=1
        rank=(i+j-1)/2+1
        for k in range(i,j): ranks[order[k]]=rank
        i=j
    return ranks

def pearson(a,b):
    ma=statistics.mean(a); mb=statistics.mean(b); da=[x-ma for x in a]; db=[x-mb for x in b]
    den=math.sqrt(sum(x*x for x in da)*sum(y*y for y in db)); return 0.0 if den==0 else sum(x*y for x,y in zip(da,db))/den

def spearman(a,b): return pearson(rankdata(a),rankdata(b))

def null_classification(rows, fs, rng, iterations=128):
    vals=[]; labels=[r["label"] for r in rows]
    for _ in range(iterations):
        shuffled=labels[:]; rng.shuffle(shuffled); rr=[{**r,"label":shuffled[i]} for i,r in enumerate(rows)]; vals.append(leave_one_style_out(rr,fs))
    return vals

def physical_screen(path):
    if not path or not Path(path).exists(): return {"available":False}
    counts=Counter(); n=0; cycle_values=[]; repeat_values=[]; turn_values=[]
    with Path(path).open(encoding="utf-8") as f:
        for line in f:
            if not line.strip(): continue
            row=json.loads(line); n+=1; centers=row.get("centers",[]); edges=row.get("edges",[])
            ids=[c.get("eventId") for c in centers if c.get("eventId") is not None]; adj={i:set() for i in ids}; multiplicity=Counter()
            for e in edges:
                a,b=e.get("a"),e.get("b")
                if a in adj and b in adj: adj[a].add(b); adj[b].add(a); multiplicity[tuple(sorted((a,b)))]+=1
                turn_values.append(float(e.get("turnRate",0) or 0))
            unseen=set(ids); cnum=0
            while unseen:
                cnum+=1; s=unseen.pop(); q=[s]
                for u in q:
                    for v in adj.get(u,()):
                        if v in unseen: unseen.remove(v); q.append(v)
            multigraph_cycle=max(0,len(edges)-len(ids)+cnum) if ids else 0; cycle_values.append(multigraph_cycle)
            mx=max(multiplicity.values(),default=1); repeat_values.append(mx)
            if edges: counts["operation"]+=1
            if any(c.get("kind")=="JUNCTION" for c in centers): counts["relation"]+=1
            if mx>1: counts["degree"]+=1
            if multigraph_cycle>0: counts["closure"]+=1
            if any(float(e.get("turnRate",0) or 0)>0 for e in edges): counts["turn"]+=1
    return {
        "available":True, "observations":n, "supportCounts":dict(counts),
        "supportRates":{k:counts[k]/max(1,n) for k in ("operation","relation","degree","closure","turn")},
        "criticalGraphCycleRank":{"median":statistics.median(cycle_values) if cycle_values else 0,"max":max(cycle_values,default=0)},
        "parallelPathMultiplicity":{"median":statistics.median(repeat_values) if repeat_values else 0,"max":max(repeat_values,default=0)},
        "edgeTurnRate":{"median":statistics.median(turn_values) if turn_values else 0,"mean":statistics.mean(turn_values) if turn_values else 0},
        "caveat":"closure is cycle rank of the v5 critical-center multigraph; degree-2-only pixel loops can be absent from this projection"
    }

protocol=json.loads(PROTOCOL.read_text(encoding="utf-8")); rng=random.Random(int(protocol.get("seed",240903))); iters=int(protocol.get("nullIterations",128))
rel=relation_rows(); deg=degree_rows(); clo=closure_rows(); ops=operation_rows()
operation_fs=["components","cycleRank","endpoints","degree3","degree4plus","turnNodes"]; operation_acc=leave_one_style_out(ops,operation_fs)
relation_locus_fs=["components","maxDegree","minJunctionEndpointRatio","meanJunctionEndpointRatio"]
relation_shape_fs=["offCarrierNodes","offCarrierEdges","turnNodes"]
relation_acc=heldout_shape_relation(rel,relation_locus_fs); relation_shape_acc=heldout_shape_relation(rel,relation_shape_fs)
degree_true=[r["degree"] for r in deg]; degree_pred=[r["features"]["degree3"] for r in deg]
degree_rho=spearman(degree_true,degree_pred); degree_mae=statistics.mean(abs(a-b) for a,b in zip(degree_true,degree_pred))
closure_fs=["cycleRank","endpoints","components","degree3"]; closure_acc=leave_one_style_out(clo,closure_fs)
op_null=null_classification(ops,operation_fs,rng,iters); cl_null=null_classification(clo,closure_fs,rng,iters)
rel_null=[]; labels=[r["label"] for r in rel]
for _ in range(iters):
    sh=labels[:]; rng.shuffle(sh); rr=[{**r,"label":sh[i]} for i,r in enumerate(rel)]; rel_null.append(heldout_shape_relation(rr,relation_locus_fs))
degree_null=[]
for _ in range(iters):
    sh=degree_true[:]; rng.shuffle(sh); degree_null.append(spearman(sh,degree_pred))
p=lambda null,obs:(1+sum(x>=obs for x in null))/(1+len(null)); g=protocol["successGates"]
gates={
    "operation":operation_acc>=float(g["operationAccuracy"]) and p(op_null,operation_acc)<=0.05,
    "relation":relation_acc>=float(g["relationAccuracy"]) and relation_acc-relation_shape_acc>=float(g["relationAdvantageOverShape"]) and p(rel_null,relation_acc)<=0.05,
    "degree":degree_rho>=float(g["degreeSpearman"]) and degree_mae<=float(g["degreeMae"]) and p(degree_null,degree_rho)<=0.05,
    "closure":closure_acc>=float(g["closureAccuracy"]) and p(cl_null,closure_acc)<=0.05,
}
physical=physical_screen(V5_OBS)
core={
    "schema":"mark_white_paint_grammar_v1", "experimentId":protocol["experimentId"], "protocolSha256":canonical_sha(protocol),
    "calibration":{
        "operation":{"accuracy":operation_acc,"nullP":p(op_null,operation_acc),"features":operation_fs},
        "relation":{"heldOutModifierAccuracy":relation_acc,"shapeOnlyAccuracy":relation_shape_acc,"advantage":relation_acc-relation_shape_acc,"nullP":p(rel_null,relation_acc),"features":relation_locus_fs},
        "degree":{"spearman":degree_rho,"mae":degree_mae,"nullP":p(degree_null,degree_rho),"estimator":"degree-3 attachment count"},
        "closure":{"accuracy":closure_acc,"nullP":p(cl_null,closure_acc),"features":closure_fs},
        "gates":gates,"allGatesPass":all(gates.values())
    },
    "physicalObservabilityScreen":physical,
    "claims":{
        "allowed":"calibrates whether the proposed white-paint grammar is recoverable from known graph constructions and measures whether corresponding observables exist in the frozen v5 physical graph world",
        "forbidden":"does not assign historical semantics, prove universality, or promote a physical observable to an Atlas meaning"
    }
}
digest=canonical_sha(core); packet={**core,"whitePaintGrammarSha256":digest}; OUT.mkdir(parents=True,exist_ok=True)
(OUT/"white-paint-grammar.json").write_text(json.dumps(packet,indent=2)+"\n",encoding="utf-8")
lines=[
    f"white_paint_grammar_sha256={digest}",
    f"operation_accuracy={operation_acc:.6f};null_p={p(op_null,operation_acc):.6f};pass={str(gates['operation']).lower()}",
    f"relation_heldout_modifier_accuracy={relation_acc:.6f};shape_only_accuracy={relation_shape_acc:.6f};advantage={relation_acc-relation_shape_acc:.6f};null_p={p(rel_null,relation_acc):.6f};pass={str(gates['relation']).lower()}",
    f"degree_spearman={degree_rho:.6f};mae={degree_mae:.6f};null_p={p(degree_null,degree_rho):.6f};pass={str(gates['degree']).lower()}",
    f"closure_accuracy={closure_acc:.6f};null_p={p(cl_null,closure_acc):.6f};pass={str(gates['closure']).lower()}",
    f"all_calibration_gates_pass={str(all(gates.values())).lower()}",
]
if physical.get("available"):
    lines.append(f"physical_observations={physical['observations']}")
    for k,v in physical["supportCounts"].items(): lines.append(f"physical_support_{k}={v}")
else: lines.append("physical_observations=unavailable")
(OUT/"summary.txt").write_text("\n".join(lines)+"\n",encoding="utf-8"); print(json.dumps(packet,indent=2))
if not all(gates.values()): raise SystemExit("white-paint calibration gate failed")
