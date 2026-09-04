#!/usr/bin/env python3
import json, math, os, statistics, hashlib, itertools
from collections import defaultdict
from pathlib import Path

PROTO=Path(os.environ.get('MARK_REWRITE_PROTOCOL','research/mark/discovery-experiments/legal-rewrite-identity-v1.protocol.json'))
CORR=Path(os.environ.get('MARK_REWRITE_CORR','artifact-staging/legal-rewrite/correspondence'))
LABELS=Path(os.environ.get('MARK_REWRITE_LABELS','artifact-staging/legal-rewrite/labels'))
TOPO=Path(os.environ.get('MARK_REWRITE_TOPO','artifact-staging/legal-rewrite/topology'))
OUT=Path(os.environ.get('MARK_REWRITE_OUT','artifacts/mark-legal-rewrite-identity-v1'))
OUT.mkdir(parents=True,exist_ok=True)
p=json.loads(PROTO.read_text())
freeze=json.loads((CORR/'correspondence-freeze.json').read_text()); label_custody=json.loads((LABELS/'label-custody.json').read_text()); topo_summary=json.loads((TOPO/'topology-atlas'/'summary.json').read_text())
assert freeze['criticalCenterCorrespondenceSha256']==p['inputs']['expectedCorrespondenceSha256']
assert label_custody['labelsSha256']==p['inputs']['expectedLabelsSha256']
assert topo_summary['rowsSha256']==p['inputs']['expectedTopologyRowsSha256']
labels={r['pairId']:r['label'] for r in map(json.loads,(LABELS/'pair-labels.jsonl').read_text().splitlines())}
pairs=list(map(json.loads,(CORR/'correspondence-pairs.jsonl').read_text().splitlines()))
needed=set(); family={}
for r in pairs:
    needed|={r['observationA'],r['observationB']}
    family.setdefault(r['observationA'],r['occupantFamilyA']); family.setdefault(r['observationB'],r['occupantFamilyB'])
atlas={}
with (TOPO/'topology-atlas'/'observation-topology-atlas.jsonl').open() as fh:
    for line in fh:
        r=json.loads(line)
        if r['observationId'] in needed: atlas[r['observationId']]=r
if len(atlas)!=len(needed): raise RuntimeError(f'topology coverage {len(atlas)}/{len(needed)}')
featids=['center:ENDPOINT','center:JUNCTION','degree:ENDPOINT:0','degree:ENDPOINT:1','degree:JUNCTION:2','degree:JUNCTION:3','degree:JUNCTION:4','degree:JUNCTION:5plus','arm:ENDPOINT:PATH_TO_ENDPOINT','arm:ENDPOINT:PATH_TO_JUNCTION','arm:ENDPOINT:UNRESOLVED','arm:JUNCTION:PATH_TO_ENDPOINT','arm:JUNCTION:PATH_TO_JUNCTION','arm:JUNCTION:UNRESOLVED']
def vec(o):
    cc=max(1,o['centerCount']); cf=o['countFeatures']; return [math.log1p(cc)]+[cf.get(f,0)/cc for f in featids]
train_obs=set()
for r in pairs:
    if r['lane']=='train': train_obs|={r['observationA'],r['observationB']}
vs=[vec(atlas[o]) for o in train_obs]; means=[statistics.mean(v[i] for v in vs) for i in range(len(vs[0]))]; sds=[statistics.pstdev(v[i] for v in vs) or 1.0 for i in range(len(vs[0]))]
def dist(a,b):
    va,vb=vec(atlas[a]),vec(atlas[b]); return math.sqrt(sum(((va[i]-vb[i])/sds[i])**2 for i in range(len(means))))
def balanced_effect(pos,neg):
    if not pos or not neg:return None
    auc=sum((a<b)+0.5*(a==b) for a in pos for b in neg)/(len(pos)*len(neg))
    return 2*auc-1

lane_results={}
for lane in ['train','holdout','control']:
    ps=[r for r in pairs if r['lane']==lane]
    adj=defaultdict(set); direct=set(); pair_labels={}
    for r in ps:
        a,b=r['observationA'],r['observationB']; key=tuple(sorted((a,b))); pair_labels[key]=labels[r['pairId']]
        if labels[r['pairId']]=='preserved': adj[a].add(b); adj[b].add(a); direct.add(key)
    comp={}; cid=0
    for node in list(adj):
        if node in comp: continue
        cid+=1; stack=[node]; comp[node]=cid
        while stack:
            x=stack.pop()
            for y in adj[x]:
                if y not in comp: comp[y]=cid; stack.append(y)
    conflicts=0
    for key,label in pair_labels.items():
        a,b=key
        if a in comp and b in comp and comp[a]==comp[b] and label=='broken': conflicts+=1
    nodes=list(comp); by_family=defaultdict(list)
    for a,b in itertools.combinations(nodes,2):
        key=tuple(sorted((a,b)))
        if comp[a]==comp[b] and key not in direct:
            by_family[tuple(sorted((family[a],family[b])))].append(dist(a,b))
    controls=defaultdict(list)
    wanted=set(by_family)
    for a,b in itertools.combinations(nodes,2):
        fp=tuple(sorted((family[a],family[b])))
        if comp[a]!=comp[b] and fp in wanted: controls[fp].append(dist(a,b))
    effects=[]; multihop=sum(len(x) for x in by_family.values())
    strata={}
    for fp,pos in sorted(by_family.items()):
        neg=controls.get(fp,[]); e=balanced_effect(pos,neg)
        if e is not None: effects.append(e); strata[str(fp)]={'multiHopPairs':len(pos),'controls':len(neg),'effect':e}
    lane_results[lane]={'legalComponents':len(set(comp.values())),'multiHopPairs':multihop,'brokenWithinLegalComponent':conflicts,'supportedFamilyStrata':len(effects),'balancedTopologyCoherenceEffect':statistics.mean(effects) if effects else None,'strata':strata}
g=p['gates']; passed=True
for lane in ['train','holdout','control']:
    r=lane_results[lane]
    passed &= r['multiHopPairs']>=g['minimumMultiHopPairsPerLane'] and r['brokenWithinLegalComponent']<=g['maximumBrokenWithinLegalComponent']
passed &= lane_results['train']['balancedTopologyCoherenceEffect'] is not None and lane_results['train']['balancedTopologyCoherenceEffect']>=g['trainBalancedEffectMinimum']
passed &= lane_results['holdout']['balancedTopologyCoherenceEffect'] is not None and lane_results['holdout']['balancedTopologyCoherenceEffect']>=g['holdoutBalancedEffectMinimum']
passed &= lane_results['control']['balancedTopologyCoherenceEffect'] is not None and lane_results['control']['balancedTopologyCoherenceEffect']>=g['controlBalancedEffectMinimum']
result={'schema':'mark_legal_rewrite_identity_result_v1','experimentId':p['experimentId'],'passed':bool(passed),'lanes':lane_results,'scientificFailureIsGreen':True}
raw=json.dumps(result,sort_keys=True,separators=(',',':')).encode(); result['resultSha256']=hashlib.sha256(raw).hexdigest()
(OUT/'result.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
summary=['# Mark legal rewrite / functional identity v1','',f"Result: **{'PASS' if passed else 'FAIL'}**",'']
for lane in ['train','holdout','control']:
    r=lane_results[lane]; summary.append(f"- {lane}: {r['multiHopPairs']} multi-hop identity pairs; {r['supportedFamilyStrata']} family strata; topology-coherence effect {r['balancedTopologyCoherenceEffect']:+.3f}; broken-inside-component conflicts {r['brokenWithinLegalComponent']}")
summary += ['', 'Interpretation: a positive effect means members connected only through two or more role-preserving rewrites remain more topology-coherent than physical-family-matched pairs from different legal components. A negative independent-lane effect falsifies transitive equivalence under this representation.', '', f"Result SHA-256: `{result['resultSha256']}`"]
(OUT/'summary.md').write_text('\n'.join(summary)+'\n'); print('\n'.join(summary))
