#!/usr/bin/env python3
import hashlib,json,math,os,statistics
from collections import defaultdict
from pathlib import Path
from scipy.spatial import cKDTree
protocol_path=Path(os.environ.get('MARK_EDGE_PROTOCOL','research/mark/discovery-experiments/critical-edge-correspondence-v5.protocol.json'))
manifest_dir=Path(os.environ.get('MARK_EDGE_PAIR_MANIFEST','artifacts/mark-edge-pair-manifest-v5'))
world_dir=Path(os.environ.get('MARK_EDGE_WORLD_OUT','artifacts/mark-critical-edge-world-v5'))
projector_dir=Path(os.environ.get('MARK_EDGE_PROJECTOR_OUT','artifacts/mark-critical-edge-projector-v5'))
out_dir=Path(os.environ.get('MARK_EDGE_GRAMMAR_OUT','artifacts/mark-critical-edge-grammar-v5'))

def load_json(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def canonical_sha(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
def transform_point(u,v,name):
 if name=='IDENTITY':return u,v
 if name=='ROT90':return 1-v,u
 if name=='ROT180':return 1-u,1-v
 if name=='ROT270':return v,1-u
 if name=='MIRROR_X':return 1-u,v
 if name=='MIRROR_Y':return u,1-v
 if name=='MIRROR_DIAGONAL':return v,u
 if name=='MIRROR_ANTIDIAGONAL':return 1-v,1-u
 raise RuntimeError(name)
TRANSFORMS=['IDENTITY','ROT90','ROT180','ROT270','MIRROR_X','MIRROR_Y','MIRROR_DIAGONAL','MIRROR_ANTIDIAGONAL']
def normalized_points(rows,region,transform):
 w=max(1,float(region['width']));h=max(1,float(region['height']));x0=float(region['x']);y0=float(region['y'])
 return [transform_point((float(c['x'])-x0)/w,(float(c['y'])-y0)/h,transform) for c in rows]
def symmetric_distance(a,b,ra,rb,transform):
 if not a or not b:return None
 A=normalized_points(a,ra,transform);B=normalized_points(b,rb,'IDENTITY');ta=cKDTree(A);tb=cKDTree(B)
 dab=tb.query(A,k=1,workers=1)[0];dba=ta.query(B,k=1,workers=1)[0]
 return (float(dab.sum())+float(dba.sum()))/(len(A)+len(B))
def sparse_match(a,b,ra,rb,transform,kcand):
 if not a or not b:return []
 A=normalized_points(a,ra,transform);B=normalized_points(b,rb,'IDENTITY');swapped=False;left,right=A,B
 if len(left)>len(right):left,right=right,left;swapped=True
 k=max(1,min(int(kcand),len(right)));tree=cKDTree(right);dists,idxs=tree.query(left,k=k,workers=1)
 if k==1:dists=[[float(x)] for x in dists];idxs=[[int(x)] for x in idxs]
 cand=[]
 for i in range(len(left)):
  for q in range(k):cand.append((float(dists[i][q]),i,int(idxs[i][q])))
 cand.sort(key=lambda x:(x[0],x[1],x[2]));ul=set();ur=set();pairs=[]
 for d,i,j in cand:
  if i in ul or j in ur:continue
  ul.add(i);ur.add(j);pairs.append((j,i,d) if swapped else (i,j,d))
 return pairs
def center_mapping(A,B,kcand):
 byA=defaultdict(list);byB=defaultdict(list)
 for c in A['centers']:byA[c['kind']].append(c)
 for c in B['centers']:byB[c['kind']].append(c)
 scored=[]
 for order,t in enumerate(TRANSFORMS):
  num=0.;den=0
  for kind in ('ENDPOINT','JUNCTION'):
   d=symmetric_distance(byA[kind],byB[kind],A['region'],B['region'],t)
   if d is not None:w=len(byA[kind])+len(byB[kind]);num+=d*w;den+=w
  scored.append((float('inf') if den==0 else num/den,order,t))
 best=min(scored)[2];mapping={}
 for kind in ('ENDPOINT','JUNCTION'):
  aa,bb=byA[kind],byB[kind]
  for ia,ib,_ in sparse_match(aa,bb,A['region'],B['region'],best,kcand):mapping[aa[ia]['eventId']]=bb[ib]['eventId']
 return mapping,best
def buckets(row,allowed=None,remap=None):
 out=defaultdict(list)
 for e in row['edges']:
  a,b=e['a'],e['b']
  if allowed is not None and (a not in allowed or b not in allowed):continue
  if remap is not None:a,b=remap[a],remap[b]
  out[tuple(sorted((a,b)))].append(e)
 return out
def adjacency(row,allowed=None):
 out=defaultdict(set)
 for e in row['edges']:
  a,b=e['a'],e['b']
  if allowed is not None and (a not in allowed or b not in allowed):continue
  out[a].add(b);out[b].add(a)
 return out
def jaccard_distance(a,b):
 u=set(a)|set(b)
 return 0.0 if not u else 1.0-len(set(a)&set(b))/len(u)
def mean(xs):return statistics.mean(xs) if xs else None
def edge_metrics(A,B,kcand):
 mapping,best=center_mapping(A,B,kcand);matchedA=set(mapping);matchedB=set(mapping.values())
 ba=buckets(A,matchedA,mapping);bb=buckets(B,matchedB,None);keys=set(ba)|set(bb)
 totalA=sum(len(v) for v in ba.values());totalB=sum(len(v) for v in bb.values())
 deletions=sum(max(0,len(ba.get(k,()))-len(bb.get(k,()))) for k in keys);insertions=sum(max(0,len(bb.get(k,()))-len(ba.get(k,()))) for k in keys)
 multiplicity=[abs(len(ba.get(k,()))-len(bb.get(k,())))/max(1,len(ba.get(k,()))+len(bb.get(k,()))) for k in keys]
 adjA=adjacency(A,matchedA);adjB=adjacency(B,matchedB);kindA={c['eventId']:c['kind'] for c in A['centers']}
 endpoint=[];junction=[]
 for aid,bid in mapping.items():
  expected={mapping[n] for n in adjA.get(aid,set()) if n in mapping};actual={n for n in adjB.get(bid,set()) if n in matchedB};d=jaccard_distance(expected,actual)
  (endpoint if kindA.get(aid)=='ENDPOINT' else junction).append(d)
 diagA=math.hypot(float(A['region']['width']),float(A['region']['height']));diagB=math.hypot(float(B['region']['width']),float(B['region']['height']))
 length=[];tort=[];turn=[];preserved=0
 for k in sorted(set(ba)&set(bb)):
  xa=sorted(ba[k],key=lambda e:(e['pathSteps'],e['tortuosity'],e['turnRate'],e['pathSha256']));xb=sorted(bb[k],key=lambda e:(e['pathSteps'],e['tortuosity'],e['turnRate'],e['pathSha256']))
  for ea,eb in zip(xa,xb):
   preserved+=1;length.append(abs(float(ea['pathSteps'])/max(1.,diagA)-float(eb['pathSteps'])/max(1.,diagB)));tort.append(abs(float(ea['tortuosity'])-float(eb['tortuosity'])));turn.append(abs(float(ea['turnRate'])-float(eb['turnRate'])))
 return {
  'mappedEdgeDeletionFraction':deletions/max(1,totalA),'mappedEdgeInsertionFraction':insertions/max(1,totalB),
  'mappedEdgeSymmetricDifferenceFraction':(deletions+insertions)/max(1,totalA+totalB),'parallelPathMultiplicityMutation':mean(multiplicity),
  'endpointAttachmentMutationFraction':mean(endpoint),'junctionAdjacencyMutationFraction':mean(junction),
  'preservedEdgeMeanNormalizedLengthMutation':mean(length),'preservedEdgeMeanTortuosityMutation':mean(tort),'preservedEdgeMeanTurnRateMutation':mean(turn),
  '_matchedCenters':len(mapping),'_mappedEdgesA':totalA,'_mappedEdgesB':totalB,'_preservedMappedEdges':preserved,'_bestTransform':best
 }
def auc_smaller(pos,neg):
 if not pos or not neg:return None
 score=0.;total=0
 for p in pos:
  for n in neg:
   total+=1
   if p<n:score+=1
   elif p==n:score+=.5
 return 2*(score/total)-1
def balanced_effect(rows,feature):
 by=defaultdict(lambda:{'preserved':[],'broken':[]})
 for r in rows:
  x=r['editMagnitudes'].get(feature)
  if x is not None:by[(r['occupantFamilyA'],r['occupantFamilyB'])][r['label']].append(float(x))
 effects=[];details=[]
 for (a,b),d in sorted(by.items()):
  e=auc_smaller(d['preserved'],d['broken'])
  if e is None:continue
  effects.append(e);details.append({'occupantFamilyA':a,'occupantFamilyB':b,'effect':e,'preserved':len(d['preserved']),'broken':len(d['broken']),'preservedMedian':statistics.median(d['preserved']),'brokenMedian':statistics.median(d['broken'])})
 return (statistics.mean(effects) if effects else None,statistics.median(effects) if effects else None,details)
protocol=load_json(protocol_path);manifest=load_json(manifest_dir/'edge-pair-manifest.json');world=load_json(world_dir/'critical-edge-world.json')
if protocol.get('schema')!='mark_critical_edge_correspondence_protocol_v5':raise RuntimeError('unexpected protocol')
if canonical_sha({k:v for k,v in world.items() if k!='criticalEdgeWorldSha256'})!=world.get('criticalEdgeWorldSha256'):raise RuntimeError('edge world SHA mismatch')
if world['edgePairManifestSha256']!=manifest['edgePairManifestSha256'] or not world['exactCenterEqualityToV4']:raise RuntimeError('edge world parent mismatch')
pairs=[json.loads(x) for x in (manifest_dir/'role-pair-labels.jsonl').read_bytes().splitlines() if x.strip()];train_pairs=[r for r in pairs if r['lane']=='train']
eligible_obs=set(world['pairEligibleObservationIds']);train_pairs=[r for r in train_pairs if r['observationA'] in eligible_obs and r['observationB'] in eligible_obs]
if len(train_pairs)<int(protocol['physicalProjection']['minimumEligibleTrainPairs']):raise RuntimeError(f'insufficient eligible train pairs {len(train_pairs)}')
needed={r['observationA'] for r in train_pairs}|{r['observationB'] for r in train_pairs};obs={}
with (projector_dir/'critical-edge-observations.jsonl').open(encoding='utf-8') as f:
 for line in f:
  if line.strip():
   r=json.loads(line)
   if r['observationId'] in needed:obs[r['observationId']]=r
if set(obs)!=needed:raise RuntimeError('missing train graph observations')
kcand=int(protocol['centerCorrespondence']['greedyNearestCandidatesPerCenter']);edit_rows=[]
for r in train_pairs:
 m=edge_metrics(obs[r['observationA']],obs[r['observationB']],kcand);best=m.pop('_bestTransform');edit_rows.append({**r,'editMagnitudes':m,'bestD4Transform':best})
features=[x['id'] for x in protocol['editObservables']];labels={x['id']:x['label'] for x in protocol['editObservables']};mincov=float(protocol['trainDiscovery']['minimumPairCoveragePerEditAtom']);observed={};eligible=[]
for f in features:
 avail=sum(r['editMagnitudes'].get(f) is not None for r in edit_rows);coverage=avail/max(1,len(edit_rows));e,med,details=balanced_effect(edit_rows,f);observed[f]={'editId':f,'label':labels[f],'balancedEffect':e,'medianFamilyPairEffect':med,'familyPairEffects':details,'trainPairCoverage':coverage,'trainPairsWithValue':avail}
 if e is not None and coverage>=mincov:eligible.append(f)
iterations=int(protocol['trainDiscovery']['nullIterations']);nulls={f:[] for f in eligible};bypair=defaultdict(list)
for r in edit_rows:bypair[(r['occupantFamilyA'],r['occupantFamilyB'])].append(r)
for it in range(iterations):
 shuffled=[]
 for (a,b),rs in sorted(bypair.items()):
  npos=sum(r['label']=='preserved' for r in rs);ordered=sorted(rs,key=lambda r:(hashlib.sha256(f"edge-null|{it}|{a}|{b}|{r['observationA']}|{r['observationB']}".encode()).hexdigest(),r['observationA'],r['observationB']))
  for i,r in enumerate(ordered):shuffled.append({**r,'label':'preserved' if i<npos else 'broken'})
 for f in eligible:
  e,_,_=balanced_effect(shuffled,f);nulls[f].append(0. if e is None else e)
for f in eligible:
 e=observed[f]['balancedEffect'];vals=nulls[f];observed[f]['null']={'iterations':iterations,'mean':statistics.mean(vals),'min':min(vals),'max':max(vals),'absoluteNullAtLeastObserved':sum(abs(x)>=abs(e) for x in vals),'beatsAllNullsByAbsoluteEffect':all(abs(e)>abs(x) for x in vals)}
selected=sorted(eligible,key=lambda f:(-abs(observed[f]['balancedEffect']),f))[:int(protocol['trainDiscovery']['maximumSelectedEditAtoms'])]
core={'schema':'mark_critical_edge_grammar_v5','experimentId':protocol['experimentId'],'edgePairManifestSha256':manifest['edgePairManifestSha256'],'criticalEdgeWorldSha256':world['criticalEdgeWorldSha256'],'parentCriticalCenterWorldSha256':world['parentCriticalCenterWorldSha256'],'provenanceAvailableDuringDiscovery':False,'eligibleTrainPairs':len(edit_rows),'effectSemantics':'positive = connection/path edit is smaller in role-preserving pairs; negative = edit is larger in role-preserving pairs','selectedEditAtoms':[observed[f] for f in selected],'allTrainEditAtomEffects':[observed[f] for f in features],'contract':{'centerAlignmentUsesNoRoleLabel':True,'edgeWorldFrozenBeforeRoleLabelsOpenedForScoring':True,'editSelectionTrainOnly':True,'nullShufflesLabelsWithinPhysicalFamilyPair':True,'holdoutAndControlUnavailableToSelection':True,'parallelPathMultiplicityPreserved':True,'noProvenanceConsumed':True,'noStateVocabularyConsumed':True,'noTransitionGrammarConsumed':True}}
digest=canonical_sha(core);packet={**core,'criticalEdgeGrammarSha256':digest};out_dir.mkdir(parents=True,exist_ok=True);(out_dir/'critical-edge-grammar.json').write_text(json.dumps(packet,indent=2)+'\n')
with (out_dir/'train-edge-pair-edits.jsonl').open('w',encoding='utf-8') as h:
 for r in edit_rows:h.write(json.dumps(r,separators=(',',':'),ensure_ascii=False)+'\n')
lines=[f'critical_edge_grammar_sha256={digest}',f'critical_edge_world_sha256={world["criticalEdgeWorldSha256"]}',f'eligible_train_pairs={len(edit_rows)}',f'selected_atoms={len(selected)}']
for i,f in enumerate(selected,1):
 o=observed[f];lines.append(f"atom_{i}={f};effect={o['balancedEffect']:.6f};coverage={o['trainPairCoverage']:.6f};null_at_least_observed={o.get('null',{}).get('absoluteNullAtLeastObserved',-1)};label={labels[f]}")
(out_dir/'summary.txt').write_text('\n'.join(lines)+'\n');print(json.dumps(packet,indent=2))
