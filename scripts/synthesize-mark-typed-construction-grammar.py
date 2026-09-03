#!/usr/bin/env python3
import hashlib, json, os
from pathlib import Path

PROTOCOL=Path(os.environ.get('MARK_TYPED_PROTOCOL','research/mark/discovery-experiments/typed-construction-grammar-v1.protocol.json'))
ROOT=Path(os.environ.get('MARK_TYPED_INPUT','artifact-staging/typed-grammar'))
OUT=Path(os.environ.get('MARK_TYPED_OUT','artifacts/mark-typed-construction-grammar-v1'))

def load(p): return json.loads(Path(p).read_text())
def canon(x): return json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
def sha(x): return hashlib.sha256(canon(x)).hexdigest()
def find(name):
    xs=list(ROOT.rglob(name))
    if len(xs)!=1: raise RuntimeError(f'expected exactly one {name}, found {len(xs)}: {xs}')
    return xs[0]

p=load(PROTOCOL)
OUT.mkdir(parents=True,exist_ok=True)

topo=load(find('topology-edit-invariance.json'))
vertex=load(find('critical-center-edit-grammar.json'))
edge=load(find('matched-edge-geometry.json'))
gblind=load(find('white-paint-glyph-transfer-blind.json'))
gctx=load(find('white-paint-glyph-transfer-context.json'))
pblind=load(find('physical-witness-frozen.json'))
pctx=load(find('physical-witness-context-result.json'))
state=load(find('state-transition-grammar-discovery.json'))

checks=[
 ('topologyEditInvarianceSha256',topo,p['sourceLineages']['role_preservation']['inputs'][0]['expectedSha']),
 ('criticalCenterEditGrammarSha256',vertex,p['sourceLineages']['role_preservation']['inputs'][1]['expectedSha']),
 ('matchedEdgeGeometrySha256',edge,p['sourceLineages']['role_preservation']['inputs'][2]['expectedSha']),
 ('blindTransferSha256',gblind,p['sourceLineages']['white_paint_transfer']['inputs'][0]['expectedSha']),
 ('contextSha256',gctx,p['sourceLineages']['white_paint_transfer']['inputs'][1]['expectedSha']),
 ('blindFeatureSha256',pblind,p['sourceLineages']['white_paint_transfer']['inputs'][2]['expectedSha']),
 ('contextResultSha256',pctx,p['sourceLineages']['white_paint_transfer']['inputs'][3]['expectedSha']),
 ('stateTransitionGrammarDiscoverySha256',state,p['sourceLineages']['state_program']['inputs'][0]['expectedSha'])]
for field,obj,expected in checks:
    got=obj.get(field)
    if got!=expected: raise RuntimeError(f'custody mismatch {field}: {got} != {expected}')

# P2: structural scaffold / vertex vs residual path geometry
jtj=next(x for x in topo['crossLaneSummary'] if x['editId']=='arm:JUNCTION:PATH_TO_JUNCTION')
unmatched=next(x for x in vertex['selectedContinuousEditAtoms'] if x['id']=='unmatchedCenterFraction')
edge_train=edge['laneResults']['train']['features']; edge_hold=edge['laneResults']['holdout']['features']
residual={
 'trainTurn':edge_train['meanTurnRateMutation']['balancedEffect'],
 'trainTortuosity':edge_train['meanTortuosityMutation']['balancedEffect'],
 'holdoutTurn':edge_hold['meanTurnRateMutation']['balancedEffect'],
 'holdoutTortuosity':edge_hold['meanTortuosityMutation']['balancedEffect']}
p2=(jtj['sameDirectionAllLanes'] and unmatched['strongTransfer'] and unmatched['trainEffect']>0 and unmatched['holdoutEffect']>0 and unmatched['controlEffect']>0 and all(abs(v)<0.08 for v in residual.values()))

# P3 degree across representation
p3=bool(gctx['predictions']['P3_REPETITION_DEGREE']['pass'] and pctx['predictions']['P3_REPETITION_PHYSICAL']['pass'])

# P4 closure carrier-relative
opclasses=gblind['physicalClasses']['closure']; proxy_closed=opclasses.get('closed',0); proxy_open=opclasses.get('open',0); proxy_share=proxy_closed/max(1,proxy_closed+proxy_open)
physical_records=load(find('physical-witness-blind.json'))['records']
closed=sum(sum(1 for r in s['regions'] if r['closure']=='closed') for s in physical_records)
open_=sum(sum(1 for r in s['regions'] if r['closure']=='open') for s in physical_records)
phys_share=closed/max(1,closed+open_)
p4=(gctx['predictions']['P4_CLOSURE_PHASE']['pass'] and 0.10<=proxy_share<=0.70 and phys_share>0.95 and not pctx['predictions']['P4_CLOSURE_PHYSICAL']['pass'])

# P5 relation requires carrier segmentation
rel=gblind['physicalClasses']['relation']; near=rel.get('near_terminal',0); interior=rel.get('interior',0); reln=near+interior
proxy_interior_share=interior/max(1,reln)
proxy_rel=gctx['predictions']['P2_RELATION_PORTABILITY']
diag=pctx['unresolvedDiagnostics']['P2_RELATION_PORTABILITY']
phys_near=sum(x['nearTerminalRegions'] for x in diag['bySystem']); phys_int=sum(x['interiorRegions'] for x in diag['bySystem']); physn=phys_near+phys_int
p5=(proxy_rel['nearTerminalSystems']>=8 and proxy_rel['interiorSystems']>=8 and proxy_interior_share>=0.10 and phys_int/max(1,physn)<0.01 and phys_near/max(1,physn)>0.95)

# P6 state/program higher-order
edges=state['transitionEdges']; progs=state['transitionPrograms']
edge_both=sum(1 for x in edges if x['observedBeyondAllNulls'] and x['sameDirectionAcrossAllLanes'])
prog_both=sum(1 for x in progs if x['observedBeyondAllNulls'] and x['sameDirectionAcrossAllLanes'])
ch=state['commitmentHysteresis']; ratio_gain=ch['observedCommitmentToReturnRatio']/ch['nullMeanCommitmentToReturnRatio']
p6=(edge_both/len(edges)>=0.75 and prog_both/len(progs)>=0.75 and ratio_gain>=5.0)

# P7 style/structure division
pg=gctx['predictions']['P5_SUBSTRATE_BEATS_STYLE']; pp=pctx['predictions']['P5_SUBSTRATE_BEATS_STYLE_PHYSICAL']
p7=bool(pg['pass'] and pp['pass'] and pp['appearanceMinusWhitePaintAccuracy']>pg['appearanceMinusWhitePaintAccuracy'])

# P1 typed separation depends on the signatures above rather than pooled meta-significance
p1=bool(p2 and p3 and p6 and (p4 or p5))

preds={
 'P1_TYPED_SEPARATION':{'pass':p1},
 'P2_SCAFFOLD_OVER_RESIDUAL_GEOMETRY':{'pass':p2,'junctionToJunctionArm':jtj,'criticalCenterInsertionDeletion':{k:unmatched[k] for k in ['trainEffect','holdoutEffect','controlEffect','strongTransfer']},'matchedResidualGeometry':residual,'v6Conclusion':edge['conclusion']},
 'P3_DEGREE_CROSS_REPRESENTATION':{'pass':p3,'proxy':gctx['predictions']['P3_REPETITION_DEGREE'],'physical':pctx['predictions']['P3_REPETITION_PHYSICAL']},
 'P4_BOUNDARY_IS_CARRIER_RELATIVE':{'pass':p4,'proxyClosedShare':proxy_share,'physicalPatchClosedShare':phys_share,'proxyClosurePass':gctx['predictions']['P4_CLOSURE_PHASE']['pass'],'physicalClosurePass':pctx['predictions']['P4_CLOSURE_PHYSICAL']['pass']},
 'P5_RELATION_REQUIRES_CARRIER_SEGMENTATION':{'pass':p5,'proxyInteriorShare':proxy_interior_share,'proxyNearTerminalSystems':proxy_rel['nearTerminalSystems'],'proxyInteriorSystems':proxy_rel['interiorSystems'],'physicalInteriorShare':phys_int/max(1,physn),'physicalNearTerminalShare':phys_near/max(1,physn)},
 'P6_STATE_PROGRAM_IS_HIGHER_ORDER':{'pass':p6,'edgeBothCount':edge_both,'edgeCount':len(edges),'programBothCount':prog_both,'programCount':len(progs),'commitmentToReturnRatio':ch['observedCommitmentToReturnRatio'],'nullCommitmentToReturnRatio':ch['nullMeanCommitmentToReturnRatio'],'ratioGain':ratio_gain,'sourceRegimeRecovery':state['sourceTransitionDynamics']['sourceRegimeRecovery']},
 'P7_STYLE_AND_STRUCTURE_DIVIDE_LABOR':{'pass':p7,'proxy':pg,'physical':pp}
}

# Type statuses are architecture outputs, not semantic assignments.
types={
 'EDGE_SCAFFOLD':{'status':'SUPPORTED','basis':'junction-to-junction arm-rate constraint transfers across role-preservation lanes; residual geometry comparison is separately demoted','sourceLineage':'role_preservation'},
 'JUNCTION_VERTEX':{'status':'STRONG_SUPPORTED','basis':'critical-center insertion/deletion and multiple vertex/junction composition constraints transfer across lanes','sourceLineage':'role_preservation'},
 'BOUNDARY_CYCLE':{'status':'CANDIDATE_CARRIER_RELATIVE' if p4 else 'UNRESOLVED','basis':'isolated proxy closure is diverse but physical patch extraction collapses to closure, indicating unit dependence','sourceLineage':'white_paint_transfer'},
 'RELATION':{'status':'CANDIDATE_REQUIRES_SEGMENTATION' if p5 else 'UNRESOLVED','basis':'attachment relation is present in isolated proxies but collapses under coarse physical patches','sourceLineage':'white_paint_transfer'},
 'DEGREE':{'status':'STRONG_SUPPORTED' if p3 else 'UNRESOLVED','basis':'repetition/degree passes both standardized-proxy and physical-witness gates','sourceLineage':'white_paint_transfer'},
 'STATE_PROGRAM':{'status':'STRONG_SUPPORTED' if p6 else 'UNRESOLVED','basis':'directed transitions and ordered programs exceed nulls with lane-stable direction and strong commitment hysteresis','sourceLineage':'state_program'},
 'REALIZATION_GEOMETRY':{'status':'DEMOTED_NOT_PROTECTED','basis':'matched turn-rate and tortuosity effects collapse below practical magnitude after scaffold conditioning','sourceLineage':'role_preservation'},
 'STYLE_REALIZATION':{'status':'SUPPORTED_AS_IDENTITY_LAYER' if p7 else 'UNRESOLVED','basis':'appearance predicts writing-system identity better than structural white-paint features in proxy and physical lanes','sourceLineage':'white_paint_transfer'}
}

typed_supported=bool(p1 and p2 and p3 and p6 and p7)
flat_rejected=bool(p2)
result={
 'schema':'mark_typed_construction_grammar_synthesis_v1',
 'experimentId':p['experimentId'],
 'synthesisKind':'retrospective frozen-artifact architecture audit; no source-data refit',
 'lineagesCountedAsIndependentUnits':3,
 'predictions':preds,
 'typeStatuses':types,
 'typedGrammarSupportedAsWorkingArchitecture':typed_supported,
 'flatShapeModelRejectedByStructuralConditioningContrast':flat_rejected,
 'instructionSetHypothesis':[
  {'type':'EDGE_SCAFFOLD','operation':'connect / preserve adjacency / multiplicity'},
  {'type':'JUNCTION_VERTEX','operation':'branch / join / insert-delete critical node / mutate local arm class'},
  {'type':'BOUNDARY_CYCLE','operation':'open / close / contain, relative to an identified carrier'},
  {'type':'RELATION','operation':'attach / place / scope, relative to identified carrier and modifier'},
  {'type':'DEGREE','operation':'repeat / count / intensify as ordered multiplicity'},
  {'type':'STATE_PROGRAM','operation':'transition / persist / commit / suppress return'},
  {'type':'REALIZATION_GEOMETRY','operation':'drawn path shape; currently not protected syntax after scaffold matching'},
  {'type':'STYLE_REALIZATION','operation':'surface realization / system identity rather than substrate instruction'}],
 'claimBoundary':p['claimBoundary']
}
result['typedConstructionGrammarSynthesisSha256']=sha(result)
(OUT/'typed-construction-grammar-synthesis.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')

lines=['# Mark typed construction grammar v1','',f"Working architecture supported: **{str(typed_supported).lower()}**",f"Flat shape-feature model rejected by matched scaffold/geometry contrast: **{str(flat_rejected).lower()}**",'', '## Frozen synthesis predictions','']
for k,v in preds.items(): lines.append(f"- {k}: **{'PASS' if v['pass'] else 'FAIL'}**")
lines += ['', '## Type status','']
for k,v in types.items(): lines.append(f"- {k}: **{v['status']}** — {v['basis']}")
lines += ['', '## Key quantitative reread','',f"- Role-preserving junction-to-junction arm constraint: train {jtj['trainBalancedEffect']:.3f}, holdout {jtj['holdoutBalancedEffect']:.3f}, control {jtj['controlBalancedEffect']:.3f}.",f"- Critical-center insertion/deletion: train {unmatched['trainEffect']:.3f}, holdout {unmatched['holdoutEffect']:.3f}, control {unmatched['controlEffect']:.3f}.",f"- Residual matched path geometry: turn {residual['trainTurn']:.3f}/{residual['holdoutTurn']:.3f} train/holdout; tortuosity {residual['trainTortuosity']:.3f}/{residual['holdoutTortuosity']:.3f}.",f"- Closure share changes from {proxy_share:.3f} in isolated proxies to {phys_share:.3f} in physical patches.",f"- Interior relation share changes from {proxy_interior_share:.3f} in isolated proxies to {phys_int/max(1,physn):.4f} in physical patches.",f"- State constraints: {edge_both}/{len(edges)} edges and {prog_both}/{len(progs)} programs are beyond all nulls with same direction across all lanes; commitment:return is {ch['observedCommitmentToReturnRatio']:.2f}:1 vs null {ch['nullMeanCommitmentToReturnRatio']:.2f}:1.",f"- Appearance advantage over structure grows from {pg['appearanceMinusWhitePaintAccuracy']:.3f} in proxies to {pp['appearanceMinusWhitePaintAccuracy']:.3f} in physical witnesses.",'', '## Interpretation','', 'The accumulated frozen evidence is more coherent as a typed instruction-set architecture than as a flat inventory of equally meaningful shape features. Critical vertices/junction scaffold, ordered multiplicity, and state/program dynamics currently carry the strongest support. Boundary and attachment relations remain plausible grammar types but require carrier-aware segmentation. Detailed turn/tortuosity is demoted from protected syntax at the tested resolution; appearance behaves more like a realization/identity layer.', '', 'This is a retrospective synthesis, not proof of universal semantics or independent replication across all contributing experiments.', '', f"Synthesis SHA-256: `{result['typedConstructionGrammarSynthesisSha256']}`"]
(OUT/'summary.md').write_text('\n'.join(lines)+'\n')
print('\n'.join(lines))
