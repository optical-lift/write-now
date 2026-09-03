#!/usr/bin/env python3
import hashlib, json, math, os, statistics
from collections import defaultdict
from pathlib import Path

protocol_path=Path(os.environ.get('MARK_EDIT_PROTOCOL','research/mark/discovery-experiments/topology-edit-invariance-v3.protocol.json'))
pair_dir=Path(os.environ.get('MARK_ROLE_PAIR_FREEZE','artifacts/mark-role-pair-freeze-v3'))
topology_dir=Path(os.environ.get('MARK_TOPOLOGY_ATLAS','artifact-staging/topology-cache/topology-atlas'))
parent_dir=Path(os.environ.get('MARK_PARENT_ATLAS','artifact-staging/parent-atlas'))
out_dir=Path(os.environ.get('MARK_EDIT_GRAMMAR_OUT','artifacts/mark-topology-edit-grammar-v3'))

def load_json(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def canonical_sha(v): return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
def area(r): return max(1,int(r['width'])*int(r['height']))
def profile(r):
    c=max(1,int(r['centerCount'])); out={k:float(v)/c for k,v in r['countFeatures'].items()}
    out['derived:centerDensityPerMillionPixelsLog1p']=math.log1p(float(r['centerCount'])*1_000_000.0/area(r['region']))
    out['derived:centerCountLog1p']=math.log1p(float(r['centerCount']))
    return out

def auc_smaller(pos,neg):
    if not pos or not neg: return None
    score=0.0; total=0
    for p in pos:
        for n in neg:
            total+=1
            if p<n: score+=1
            elif p==n: score+=0.5
    return 2.0*(score/total)-1.0

def balanced_effect(rows,feature):
    by_pair=defaultdict(lambda:{'preserved':[],'broken':[]})
    for r in rows: by_pair[(r['occupantFamilyA'],r['occupantFamilyB'])][r['label']].append(r['editMagnitudes'][feature])
    effects=[]; details=[]
    for (a,b),d in sorted(by_pair.items()):
        e=auc_smaller(d['preserved'],d['broken'])
        if e is None: continue
        effects.append(e); details.append({'occupantFamilyA':a,'occupantFamilyB':b,'effect':e,'preserved':len(d['preserved']),'broken':len(d['broken']),'preservedMedian':statistics.median(d['preserved']),'brokenMedian':statistics.median(d['broken'])})
    return (statistics.mean(effects) if effects else None, statistics.median(effects) if effects else None, details)

def locate_parent_custody():
    hits=list(parent_dir.rglob('custody.json'))
    hits=[p for p in hits if p.parent.name=='compiler'] or hits
    if len(hits)!=1: raise RuntimeError(f'expected one parent compiler custody, found {len(hits)}')
    return hits[0]

protocol=load_json(protocol_path)
if protocol.get('schema')!='mark_topology_edit_invariance_protocol_v3': raise RuntimeError('unexpected protocol')
pfreeze=load_json(pair_dir/'role-pair-freeze.json'); psha=pfreeze.get('rolePairFreezeSha256')
if canonical_sha({k:v for k,v in pfreeze.items() if k!='rolePairFreezeSha256'})!=psha: raise RuntimeError('role-pair freeze SHA mismatch')
pair_bytes=(pair_dir/'role-pair-labels.jsonl').read_bytes()
if hashlib.sha256(pair_bytes).hexdigest()!=pfreeze['rolePairRowsSha256']: raise RuntimeError('role-pair rows SHA mismatch')
pairs=[json.loads(x) for x in pair_bytes.splitlines() if x.strip()]
summary=load_json(topology_dir/'summary.json'); custody=load_json(locate_parent_custody())
if summary.get('schema')!='mark_observation_topology_atlas_summary_v1': raise RuntimeError('unexpected topology summary')
if summary['rowsSha256']!=pfreeze['topologyRowsSha256'] or summary['physicalLedgerMerkleRoot']!=pfreeze['physicalLedgerMerkleRoot'] or summary['sourceBlindInputSha256']!=pfreeze['sourceBlindInputSha256']: raise RuntimeError('topology differs from frozen role-pair parent')
if summary['physicalLedgerMerkleRoot']!=custody['physicalLedger']['merkleRoot'] or summary['sourceBlindInputSha256']!=custody['sourceBlindInputSha256']: raise RuntimeError('topology/parent custody mismatch')
if not summary.get('contract',{}).get('noProvenanceConsumed'): raise RuntimeError('topology consumed provenance')
topo={}
with (topology_dir/'observation-topology-atlas.jsonl').open(encoding='utf-8') as f:
    for line in f:
        if line.strip():
            r=json.loads(line); topo[r['observationId']]=r
if len(topo)!=int(summary['observations']): raise RuntimeError('topology row count mismatch')
labels={x['id']:x['label'] for x in protocol['editObservables']}; features=[x['id'] for x in protocol['editObservables']]
edit_rows=[]
for r in pairs:
    if r['lane']!='train': continue
    a=topo.get(r['observationA']); b=topo.get(r['observationB'])
    if not a or not b: raise RuntimeError('pair observation missing from topology')
    if a['sourceGroupId']!=r['sourceGroupA'] or b['sourceGroupId']!=r['sourceGroupB'] or a['lane']!='train' or b['lane']!='train': raise RuntimeError('pair/topology custody mismatch')
    pa,pb=profile(a),profile(b); mags={f:abs(pb.get(f,0.0)-pa.get(f,0.0)) for f in features}
    edit_rows.append({**r,'editMagnitudes':mags})
observed={}
for f in features:
    mean_effect,median_effect,details=balanced_effect(edit_rows,f)
    observed[f]={'editId':f,'label':labels[f],'balancedEffect':mean_effect,'medianFamilyPairEffect':median_effect,'familyPairEffects':details}
iterations=int(protocol['trainDiscovery']['nullIterations']); nulls={f:[] for f in features}; bypair=defaultdict(list)
for r in edit_rows: bypair[(r['occupantFamilyA'],r['occupantFamilyB'])].append(r)
for it in range(iterations):
    shuffled=[]
    for (a,b),rs in sorted(bypair.items()):
        npos=sum(r['label']=='preserved' for r in rs)
        ordered=sorted(rs,key=lambda r:(hashlib.sha256(f"edit-null|{it}|{a}|{b}|{r['observationA']}|{r['observationB']}".encode()).hexdigest(),r['observationA'],r['observationB']))
        for idx,r in enumerate(ordered): shuffled.append({**r,'label':'preserved' if idx<npos else 'broken'})
    for f in features:
        e,_,_=balanced_effect(shuffled,f); nulls[f].append(e if e is not None else 0.0)
for f in features:
    obs=observed[f]['balancedEffect']; vals=nulls[f]
    observed[f]['null']={'iterations':iterations,'mean':statistics.mean(vals),'min':min(vals),'max':max(vals),'absoluteNullAtLeastObserved':sum(abs(x)>=abs(obs) for x in vals),'beatsAllNullsByAbsoluteEffect':all(abs(obs)>abs(x) for x in vals)}
max_atoms=int(protocol['trainDiscovery']['maximumSelectedEditAtoms'])
selected=sorted(features,key=lambda f:(-abs(observed[f]['balancedEffect']),f))[:max_atoms]
core={'schema':'mark_topology_edit_grammar_v3','experimentId':protocol['experimentId'],'parentRolePairFreezeSha256':psha,'topologyRowsSha256':summary['rowsSha256'],'physicalLedgerMerkleRoot':summary['physicalLedgerMerkleRoot'],'sourceBlindInputSha256':summary['sourceBlindInputSha256'],'provenanceAvailableDuringDiscovery':False,'trainPairs':len(edit_rows),'effectSemantics':'positive balanced effect means role-preserving pairs exhibit a smaller physical edit magnitude than matched role-broken pairs','selectedEditAtoms':[observed[f] for f in selected],'allTrainEditAtomEffects':[observed[f] for f in features],'contract':{'selectionUsesTrainOnly':True,'roleLabelsFrozenBeforeTopologyAvailable':True,'nullShufflesLabelsWithinPhysicalFamilyPair':True,'holdoutAndControlUnavailableToEditAtomSelection':True,'aggregateTopologyCompositionOnly':True,'noLiteralAlignedGraphEditClaim':True,'noStateVocabularyConsumed':True,'noTransitionGrammarConsumed':True,'noProvenanceConsumed':True}}
digest=canonical_sha(core); packet={**core,'topologyEditGrammarSha256':digest}
out_dir.mkdir(parents=True,exist_ok=True); (out_dir/'topology-edit-grammar.json').write_text(json.dumps(packet,indent=2)+'\n')
lines=[f'topology_edit_grammar_sha256={digest}',f'train_pairs={len(edit_rows)}']
for i,f in enumerate(selected,1):
    o=observed[f]; lines.append(f"atom_{i}={f};effect={o['balancedEffect']:.6f};null_at_least_observed={o['null']['absoluteNullAtLeastObserved']};label={labels[f]}")
(out_dir/'summary.txt').write_text('\n'.join(lines)+'\n'); print(json.dumps(packet,indent=2))
