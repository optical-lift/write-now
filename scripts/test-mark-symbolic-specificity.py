#!/usr/bin/env python3
import hashlib, json, math, os, random, statistics
from collections import Counter, defaultdict, deque
from pathlib import Path

PROTOCOL=Path(os.environ.get('MARK_SYMBOLIC_SPECIFICITY_PROTOCOL','research/mark/discovery-experiments/symbolic-specificity-v1.protocol.json'))
GLYPHS=Path(os.environ.get('MARK_SYMBOLIC_GRAPH_CORPUS','artifacts/mark-symbolic-specificity-v1/glyphs/symbolic-critical-graphs.json'))
V5=Path(os.environ.get('MARK_V5_EDGE_WORLD','artifact-staging/critical-edge-v5/mark-critical-edge-projector-v5/critical-edge-observations.jsonl'))
V5SUMMARY=Path(os.environ.get('MARK_V5_WORLD_SUMMARY','artifact-staging/critical-edge-v5/mark-critical-edge-world-v5/critical-edge-world.json'))
OUT=Path(os.environ.get('MARK_SYMBOLIC_SPECIFICITY_OUT','artifacts/mark-symbolic-specificity-v1/result'))
OUT.mkdir(parents=True,exist_ok=True)
P=json.loads(PROTOCOL.read_text())
SEED=int(P['null']['seed']); NULLS=int(P['null']['rewireWorldsPerGraph']); SIGN=int(P['null']['pairedSignFlipWorlds'])
BINS=P['matching']['edgeLengthBins']; MINV=P['eligibility']['minimumCriticalNodes']; MAXV=P['eligibility']['maximumCriticalNodes']; MINTRACE=P['eligibility']['minimumTraceResolution']

def canonical_sha(v): return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def mean(xs): return sum(xs)/len(xs) if xs else float('nan')
def stdev(xs):
    if len(xs)<2:return 0.0
    m=mean(xs);return math.sqrt(sum((x-m)**2 for x in xs)/(len(xs)-1))
def median(xs): return statistics.median(xs) if xs else float('nan')
def qbin(x):
    for i in range(len(BINS)-1):
        if BINS[i] <= x < BINS[i+1]: return i
    return len(BINS)-2

def prep_graph(raw, kind):
    nodes=[]; idmap={}
    for i,n in enumerate(raw['nodes'] if kind=='symbolic' else raw['centers']):
        oid=n['id'] if kind=='symbolic' else n['eventId'];idmap[oid]=i
        nodes.append({'id':i,'kind':n['kind'],'x':float(n['x']),'y':float(n['y'])})
    if kind=='symbolic': w=float(raw['width']);h=float(raw['height']); src=None; gid=raw['id']; trace=float(raw.get('traceResolution',1))
    else:
        w=float(raw['region']['width']);h=float(raw['region']['height']);src=raw['sourceGroupId'];gid=raw['observationId'];trace=float(raw['traceResolutionFraction'])
    diag=max(1.0,math.hypot(w,h));edges=[]
    for e in raw['edges']:
        a=idmap.get(e['a']);b=idmap.get(e['b'])
        if a is None or b is None: continue
        chord=float(e.get('chordPixels', math.hypot(nodes[a]['x']-nodes[b]['x'],nodes[a]['y']-nodes[b]['y'])))/diag
        edges.append({'a':a,'b':b,'selfLoop':bool(e.get('selfLoop',a==b)),'len':chord})
    return {'id':gid,'source':src,'kind':kind,'nodes':nodes,'edges':edges,'w':w,'h':h,'trace':trace}

def adjacency(g, edges=None):
    es=g['edges'] if edges is None else edges;n=len(g['nodes']);adj=[set() for _ in range(n)];mult=Counter()
    for e in es:
        a,b=e['a'],e['b']
        if a==b: continue
        p=(a,b) if a<b else (b,a);mult[p]+=1;adj[a].add(b);adj[b].add(a)
    return adj,mult

def components(g, edges=None):
    adj,_=adjacency(g,edges);seen=set();c=0
    for s in range(len(adj)):
        if s in seen: continue
        c+=1;q=[s];seen.add(s)
        for u in q:
            for v in adj[u]:
                if v not in seen:seen.add(v);q.append(v)
    return c

def degrees(g, edges=None):
    es=g['edges'] if edges is None else edges;d=[0]*len(g['nodes'])
    for e in es:
        a,b=e['a'],e['b']
        if a==b:d[a]+=2
        else:d[a]+=1;d[b]+=1
    return d

def low_features(g):
    es=g['edges'];V=len(g['nodes']);E=len(es);d=degrees(g);C=components(g);cy=max(0,E-V+C)
    endpoints=sum(1 for n in g['nodes'] if n['kind']=='ENDPOINT');d3=sum(x==3 for x in d);d4=sum(x>=4 for x in d)
    non=[e for e in es if not e['selfLoop']];jj=sum(1 for e in non if g['nodes'][e['a']]['kind']=='JUNCTION' and g['nodes'][e['b']]['kind']=='JUNCTION')
    lengths=[e['len'] for e in non]
    return [math.log1p(V), endpoints/max(1,V), d3/max(1,V), d4/max(1,V), E/max(1,V), cy/max(1,V), jj/max(1,len(non)), sum(e['selfLoop'] for e in es)/max(1,E), median(lengths) if lengths else 0.0]

def assortativity(g, edges):
    d=degrees(g,edges);xs=[];ys=[]
    for e in edges:
        if e['a']==e['b']:continue
        a,b=e['a'],e['b'];xs.extend([d[a],d[b]]);ys.extend([d[b],d[a]])
    if len(xs)<3:return float('nan')
    mx,my=mean(xs),mean(ys);vx=sum((x-mx)**2 for x in xs);vy=sum((y-my)**2 for y in ys)
    if vx<=0 or vy<=0:return 0.0
    return sum((x-mx)*(y-my) for x,y in zip(xs,ys))/math.sqrt(vx*vy)

def transitivity(g, edges):
    adj,_=adjacency(g,edges);wedges=sum(len(a)*(len(a)-1)//2 for a in adj)
    if wedges==0:return 0.0
    tri=0
    for u in range(len(adj)):
        for v in adj[u]:
            if v<=u:continue
            tri+=sum(1 for w in adj[u].intersection(adj[v]) if w>v)
    return 3.0*tri/wedges

def bridge_fraction(g, edges):
    adj,mult=adjacency(g,edges);n=len(adj);disc=[-1]*n;low=[0]*n;t=0;bridges=0
    def dfs(u,p):
        nonlocal t,bridges
        disc[u]=low[u]=t;t+=1
        for v in adj[u]:
            if disc[v]<0:
                dfs(v,u);low[u]=min(low[u],low[v]);pair=(u,v) if u<v else (v,u)
                if low[v]>disc[u] and mult[pair]==1:bridges+=1
            elif v!=p:low[u]=min(low[u],disc[v])
    for i in range(n):
        if disc[i]<0:dfs(i,-1)
    nonloop=sum(1 for e in edges if e['a']!=e['b'])
    return bridges/max(1,nonloop)

def core2_fraction(g, edges):
    adj,_=adjacency(g,edges);deg=[len(a) for a in adj];q=deque(i for i,x in enumerate(deg) if x<2);alive=[True]*len(adj)
    while q:
        u=q.popleft()
        if not alive[u]:continue
        alive[u]=False
        for v in adj[u]:
            if alive[v]:deg[v]-=1
            if alive[v] and deg[v]<2:q.append(v)
    return sum(alive)/max(1,len(alive))

def endpoint_junction_distance(g, edges):
    adj,_=adjacency(g,edges);junctions=[i for i,n in enumerate(g['nodes']) if n['kind']=='JUNCTION'];endpoints=[i for i,n in enumerate(g['nodes']) if n['kind']=='ENDPOINT']
    if not junctions or not endpoints:return float('nan')
    dist=[-1]*len(adj);q=deque(junctions)
    for j in junctions:dist[j]=0
    while q:
        u=q.popleft()
        for v in adj[u]:
            if dist[v]<0:dist[v]=dist[u]+1;q.append(v)
    vals=[dist[e] for e in endpoints if dist[e]>=0]
    return mean(vals) if vals else float('nan')

def metrics(g, edges=None):
    es=g['edges'] if edges is None else edges
    return {'assortativity':assortativity(g,es),'transitivity':transitivity(g,es),'bridgeFraction':bridge_fraction(g,es),'core2Fraction':core2_fraction(g,es),'endpointJunctionDistance':endpoint_junction_distance(g,es)}

def pair_surplus(edges):
    c=Counter((min(e['a'],e['b']),max(e['a'],e['b'])) for e in edges if e['a']!=e['b'])
    return sum(max(0,x-1) for x in c.values())

def edge_class(g,e):
    ka=g['nodes'][e['a']]['kind'][0];kb=g['nodes'][e['b']]['kind'][0];tp=''.join(sorted([ka,kb]));return (tp,qbin(e['len']),bool(e['selfLoop']))

def rewire(g, rng, target):
    edges=[dict(e) for e in g['edges']];baseC=components(g,edges);baseSur=pair_surplus(edges);groups=defaultdict(list)
    for i,e in enumerate(edges):
        if not e['selfLoop']:groups[edge_class(g,e)].append(i)
    classes=[a for a in groups.values() if len(a)>=2];accepted=0;attempts=0;limit=max(1000,target*250)
    while accepted<target and attempts<limit and classes:
        attempts+=1;pool=rng.choice(classes);i,j=rng.sample(pool,2);e1,e2=edges[i],edges[j];a,b,c,d=e1['a'],e1['b'],e2['a'],e2['b']
        if len({a,b,c,d})<4:continue
        opts=[((a,d),(c,b)),((a,c),(b,d))];rng.shuffle(opts);done=False
        for (x1,y1),(x2,y2) in opts:
            if x1==y1 or x2==y2:continue
            n1=dict(e1,a=x1,b=y1,len=math.hypot(g['nodes'][x1]['x']-g['nodes'][y1]['x'],g['nodes'][x1]['y']-g['nodes'][y1]['y'])/max(1.0,math.hypot(g['w'],g['h'])))
            n2=dict(e2,a=x2,b=y2,len=math.hypot(g['nodes'][x2]['x']-g['nodes'][y2]['x'],g['nodes'][x2]['y']-g['nodes'][y2]['y'])/max(1.0,math.hypot(g['w'],g['h'])))
            if edge_class(g,n1)!=edge_class(g,e1) or edge_class(g,n2)!=edge_class(g,e2):continue
            old1,old2=edges[i],edges[j];edges[i],edges[j]=n1,n2
            if pair_surplus(edges)!=baseSur or components(g,edges)!=baseC:edges[i],edges[j]=old1,old2;continue
            accepted+=1;done=True;break
        if done:continue
    return edges,accepted

def score_graph(g):
    obs=metrics(g);nulls=defaultdict(list);acc=[];target=max(P['null']['minimumAcceptedSwaps'], int(P['null']['acceptedSwapsPerEdge']*len(g['edges'])))
    for k in range(NULLS):
        rng=random.Random(int(hashlib.sha256(f'{SEED}|{g["kind"]}|{g["id"]}|{k}'.encode()).hexdigest()[:16],16));es,a=rewire(g,rng,target);acc.append(a);m=metrics(g,es)
        for key,v in m.items():
            if math.isfinite(v):nulls[key].append(v)
    z={}
    for key,v in obs.items():
        vals=nulls[key]
        if not math.isfinite(v) or len(vals)<max(16,NULLS//2):continue
        sd=stdev(vals)
        if sd<=1e-8:continue
        z[key]=max(-8.0,min(8.0,(v-mean(vals))/sd))
    org=math.sqrt(mean([v*v for v in z.values()])) if len(z)>=P['eligibility']['minimumActiveHigherOrderMetrics'] else float('nan')
    return {'id':g['id'],'source':g['source'],'kind':g['kind'],'low':low_features(g),'organizationScore':org,'z':z,'activeMetrics':len(z),'medianAcceptedSwaps':median(acc),'nodes':len(g['nodes']),'edges':len(g['edges'])}

v5summary=json.loads(V5SUMMARY.read_text())
if v5summary.get('criticalEdgeWorldSha256') != P['parentEvidence']['criticalEdgeWorldSha256']:
    raise RuntimeError('v5 critical-edge world SHA mismatch')
glyph=json.loads(GLYPHS.read_text());symbolic=[]
for r in glyph['records']:
    g=prep_graph(r,'symbolic')
    if MINV<=len(g['nodes'])<=MAXV and g['trace']>=MINTRACE:symbolic.append(g)

photos_by_source=defaultdict(list)
with V5.open() as f:
    for line in f:
        r=json.loads(line)
        if r.get('lane')!='control':continue
        if r.get('traceResolutionFraction',0)<MINTRACE:continue
        if not (MINV<=r.get('centerCount',0)<=MAXV):continue
        g=prep_graph(r,'photo');photos_by_source[g['source']].append(g)
photos=[sorted(gs,key=lambda g:(len(g['nodes']),g['id']))[0] for gs in photos_by_source.values()]

symbolic_scores=[score_graph(g) for g in symbolic];photo_scores=[score_graph(g) for g in photos]
symbolic_scores=[x for x in symbolic_scores if math.isfinite(x['organizationScore']) and x['medianAcceptedSwaps']>=P['null']['minimumAcceptedSwaps']]
photo_scores=[x for x in photo_scores if math.isfinite(x['organizationScore']) and x['medianAcceptedSwaps']>=P['null']['minimumAcceptedSwaps']]

allscore=symbolic_scores+photo_scores;cols=len(allscore[0]['low']) if allscore else 0;med=[];scale=[]
for j in range(cols):
    xs=[x['low'][j] for x in allscore];m=median(xs);mad=median([abs(v-m) for v in xs]);med.append(m);scale.append(max(1e-6,1.4826*mad))
def dist(a,b):return math.sqrt(sum(((a['low'][j]-b['low'][j])/scale[j])**2 for j in range(cols)))
cands=[]
for pi,p in enumerate(photo_scores):
    for gi,g in enumerate(symbolic_scores):
        d=dist(p,g)
        if d<=P['matching']['maximumRobustDistance']:cands.append((d,p['id'],g['id'],pi,gi))
cands.sort();usedp=set();usedg=set();pairs=[]
for d,_,__,pi,gi in cands:
    if pi in usedp or gi in usedg:continue
    usedp.add(pi);usedg.add(gi);p=photo_scores[pi];g=symbolic_scores[gi];pairs.append({'photo':p,'symbolic':g,'matchDistance':d,'difference':g['organizationScore']-p['organizationScore']})

status='INFEASIBLE';stats={}
if len(pairs)>=P['matching']['minimumMatchedPairs']:
    diffs=[x['difference'] for x in pairs];obs=mean(diffs);pos=sum(d>0 for d in diffs)/len(diffs);rng=random.Random(SEED+991);null=[]
    for _ in range(SIGN):null.append(mean([d*(1 if rng.random()<.5 else -1) for d in diffs]))
    ppos=(1+sum(x>=obs for x in null))/(1+len(null));pneg=(1+sum(x<=obs for x in null))/(1+len(null))
    if obs>=P['adjudication']['symbolicSpecificity']['minimumMeanPairedDifference'] and pos>=P['adjudication']['symbolicSpecificity']['minimumPositivePairFraction'] and ppos<=P['adjudication']['symbolicSpecificity']['maximumOneSidedP']:
        status='SYMBOLIC_SPECIFICITY'
    elif obs<=P['adjudication']['nonSymbolicMoreOrganized']['maximumMeanPairedDifference'] and pos<=P['adjudication']['nonSymbolicMoreOrganized']['maximumPositivePairFraction'] and pneg<=P['adjudication']['nonSymbolicMoreOrganized']['maximumOneSidedP']:
        status='NON_SYMBOLIC_MORE_ORGANIZED'
    else:status='GENERIC_STRUCTURE_COMPATIBLE'
    stats={'matchedPairs':len(pairs),'meanPairedDifference':obs,'medianPairedDifference':median(diffs),'positivePairFraction':pos,'pSymbolicGreater':ppos,'pPhotoGreater':pneg,'meanSymbolicOrganization':mean([x['symbolic']['organizationScore'] for x in pairs]),'meanPhotoOrganization':mean([x['photo']['organizationScore'] for x in pairs]),'medianMatchDistance':median([x['matchDistance'] for x in pairs])}

result={'schema':'mark_symbolic_specificity_result_v1','question':P['question'],'adjudication':status,'glyphCorpusSha256':glyph['corpusSha256'],'v5ExpectedEdgeWorldSha256':P['parentEvidence']['criticalEdgeWorldSha256'],'eligibleSymbolicGraphs':len(symbolic_scores),'eligiblePhotoSourceGraphs':len(photo_scores),'stats':stats,'matchedPairs':[{'symbolicId':x['symbolic']['id'],'photoObservationId':x['photo']['id'],'photoSourceGroupId':x['photo']['source'],'matchDistance':x['matchDistance'],'symbolicOrganization':x['symbolic']['organizationScore'],'photoOrganization':x['photo']['organizationScore'],'difference':x['difference']} for x in pairs]}
result['resultSha256']=canonical_sha(result)
(OUT/'symbolic-specificity-result.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
lines=['# Mark symbolic specificity v1','',f'Adjudication: **{status}**',f'Eligible symbolic graphs: {len(symbolic_scores)}',f'Eligible photo-source graphs: {len(photo_scores)}']
if stats:
    lines += [f"Matched pairs: {stats['matchedPairs']}",f"Mean symbolic-minus-photo organization: {stats['meanPairedDifference']:+.3f}",f"Positive-pair fraction: {stats['positivePairFraction']:.3f}",f"One-sided p (symbolic > photo): {stats['pSymbolicGreater']:.4f}",f"Mean organization: symbolic {stats['meanSymbolicOrganization']:.3f} vs photo {stats['meanPhotoOrganization']:.3f}",f"Median low-order match distance: {stats['medianMatchDistance']:.3f}"]
lines += ['','Interpretation boundary: this test asks whether standardized symbolic glyph graphs show excess higher-order organization beyond their own degree/type/cycle/length-preserving rewiring nulls compared with low-order-matched ordinary-photography graphs. It does not establish historical semantics or cognitive universals.', '', f"Result SHA-256: `{result['resultSha256']}`"]
(OUT/'summary.md').write_text('\n'.join(lines)+'\n')
print('\n'.join(lines))
