#!/usr/bin/env python3
import hashlib, json, math, os, statistics
from collections import defaultdict
from pathlib import Path

protocol_path=Path(os.environ.get('MARK_EDIT_PROTOCOL','research/mark/discovery-experiments/topology-edit-invariance-v3.protocol.json'))
pair_dir=Path(os.environ.get('MARK_ROLE_PAIR_FREEZE','artifacts/mark-role-pair-freeze-v3'))
grammar_dir=Path(os.environ.get('MARK_EDIT_GRAMMAR','artifacts/mark-topology-edit-grammar-v3'))
topology_dir=Path(os.environ.get('MARK_TOPOLOGY_ATLAS','artifact-staging/topology-cache/topology-atlas'))
out_dir=Path(os.environ.get('MARK_EDIT_TRANSFER_OUT','artifacts/mark-topology-edit-invariance-v3'))

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
    bypair=defaultdict(lambda:{'preserved':[],'broken':[]})
    for r in rows: bypair[(r['occupantFamilyA'],r['occupantFamilyB'])][r['label']].append(r['editMagnitudes'][feature])
    effects=[]; details=[]
    for (a,b),d in sorted(bypair.items()):
        e=auc_smaller(d['preserved'],d['broken'])
        if e is None: continue
        effects.append(e); details.append({'occupantFamilyA':a,'occupantFamilyB':b,'effect':e,'preserved':len(d['preserved']),'broken':len(d['broken']),'preservedMedian':statistics.median(d['preserved']),'brokenMedian':statistics.median(d['broken'])})
    return (statistics.mean(effects) if effects else None,statistics.median(effects) if effects else None,details)

protocol=load_json(protocol_path); pfreeze=load_json(pair_dir/'role-pair-freeze.json'); grammar=load_json(grammar_dir/'topology-edit-grammar.json')
psha=pfreeze['rolePairFreezeSha256']; gsha=grammar['topologyEditGrammarSha256']
if canonical_sha({k:v for k,v in pfreeze.items() if k!='rolePairFreezeSha256'})!=psha: raise RuntimeError('role-pair freeze SHA mismatch')
if canonical_sha({k:v for k,v in grammar.items() if k!='topologyEditGrammarSha256'})!=gsha: raise RuntimeError('edit grammar SHA mismatch')
if grammar['parentRolePairFreezeSha256']!=psha: raise RuntimeError('grammar/pair-freeze mismatch')
pair_bytes=(pair_dir/'role-pair-labels.jsonl').read_bytes()
if hashlib.sha256(pair_bytes).hexdigest()!=pfreeze['rolePairRowsSha256']: raise RuntimeError('role-pair rows SHA mismatch')
pairs=[json.loads(x) for x in pair_bytes.splitlines() if x.strip()]
summary=load_json(topology_dir/'summary.json')
if summary['rowsSha256']!=grammar['topologyRowsSha256']: raise RuntimeError('topology rows differ from train grammar')
topo={}
with (topology_dir/'observation-topology-atlas.jsonl').open(encoding='utf-8') as f:
    for line in f:
        if line.strip():
            r=json.loads(line); topo[r['observationId']]=r
selected=[r['editId'] for r in grammar['selectedEditAtoms']]; train_effect={r['editId']:r['balancedEffect'] for r in grammar['selectedEditAtoms']}; labels={x['id']:x['label'] for x in protocol['editObservables']}
transfer={}
for lane in ('holdout','control'):
    rows=[]
    for r in pairs:
        if r['lane']!=lane: continue
        a,b=topo[r['observationA']],topo[r['observationB']]
        if a['sourceGroupId']!=r['sourceGroupA'] or b['sourceGroupId']!=r['sourceGroupB'] or a['lane']!=lane or b['lane']!=lane: raise RuntimeError('transfer pair/topology custody mismatch')
        pa,pb=profile(a),profile(b); rows.append({**r,'editMagnitudes':{f:abs(pb.get(f,0.0)-pa.get(f,0.0)) for f in selected}})
    atoms=[]
    for f in selected:
        effect,median_effect,details=balanced_effect(rows,f); te=train_effect[f]
        same_sign=(effect==0 or te==0 or (effect>0)==(te>0)); retained=(abs(effect)/abs(te)) if te else None
        strong=same_sign and retained is not None and retained>=0.25
        atoms.append({'editId':f,'label':labels[f],'trainBalancedEffect':te,'transferBalancedEffect':effect,'medianFamilyPairEffect':median_effect,'sameEffectDirection':same_sign,'retainedEffectFraction':retained,'strongTransferDescriptiveGate':strong,'familyPairEffects':details})
    transfer[lane]={'pairs':len(rows),'selectedEditAtomEffects':atoms}
core={'schema':'mark_topology_edit_invariance_discovery_v3','experimentId':protocol['experimentId'],'parentTopologyEditGrammarSha256':gsha,'parentRolePairFreezeSha256':psha,'provenanceAvailableDuringDiscovery':False,'selectedEditAtoms':[r['editId'] for r in grammar['selectedEditAtoms']],'transfer':transfer,'crossLaneSummary':[],'contract':{'selectedAtomsFrozenFromTrainOnly':True,'sameRolePairDefinitionUsedInAllLanes':True,'holdoutAndControlCannotReselectAtoms':True,'aggregateTopologyCompositionOnly':True,'noLiteralAlignedGraphEditClaim':True,'noStateVocabularyConsumed':True,'noTransitionGrammarConsumed':True,'noProvenanceConsumed':True}}
for f in selected:
    h=next(r for r in transfer['holdout']['selectedEditAtomEffects'] if r['editId']==f); c=next(r for r in transfer['control']['selectedEditAtomEffects'] if r['editId']==f)
    core['crossLaneSummary'].append({'editId':f,'label':labels[f],'trainBalancedEffect':train_effect[f],'holdoutBalancedEffect':h['transferBalancedEffect'],'controlBalancedEffect':c['transferBalancedEffect'],'sameDirectionAllLanes':h['sameEffectDirection'] and c['sameEffectDirection'],'strongTransferBothLanes':h['strongTransferDescriptiveGate'] and c['strongTransferDescriptiveGate']})
digest=canonical_sha(core); packet={**core,'topologyEditInvarianceSha256':digest}
out_dir.mkdir(parents=True,exist_ok=True); (out_dir/'topology-edit-invariance.json').write_text(json.dumps(packet,indent=2)+'\n')
lines=[f'topology_edit_grammar_sha256={gsha}',f'topology_edit_invariance_sha256={digest}']
for i,r in enumerate(core['crossLaneSummary'],1): lines.append(f"atom_{i}={r['editId']};train={r['trainBalancedEffect']:.6f};holdout={r['holdoutBalancedEffect']:.6f};control={r['controlBalancedEffect']:.6f};same_direction_all_lanes={str(r['sameDirectionAllLanes']).lower()};strong_transfer_both={str(r['strongTransferBothLanes']).lower()};label={r['label']}")
(out_dir/'summary.txt').write_text('\n'.join(lines)+'\n'); print(json.dumps(packet,indent=2))
