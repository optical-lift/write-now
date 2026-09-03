#!/usr/bin/env python3
import hashlib,json,math,os,statistics
from collections import defaultdict
from pathlib import Path
from scipy.spatial import cKDTree
protocol_path=Path(os.environ.get('MARK_EDGE_PROTOCOL','research/mark/discovery-experiments/critical-edge-correspondence-v5.protocol.json'))
manifest_dir=Path(os.environ.get('MARK_EDGE_PAIR_MANIFEST','artifacts/mark-edge-pair-manifest-v5'))
world_dir=Path(os.environ.get('MARK_EDGE_WORLD_OUT','artifacts/mark-critical-edge-world-v5'))
projector_dir=Path(os.environ.get('MARK_EDGE_PROJECTOR_OUT','artifacts/mark-critical-edge-projector-v5'))
grammar_dir=Path(os.environ.get('MARK_EDGE_GRAMMAR_OUT','artifacts/mark-critical-edge-grammar-v5'))
out_dir=Path(os.environ.get('MARK_EDGE_TRANSFER_OUT','artifacts/mark-critical-edge-correspondence-v5'))

def load_json(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def canonical_sha(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
def tp(u,v,t):
 if t=='IDENTITY':return u,v
 if t=='ROT90':return 1-v,u
 if t=='ROT180':return 1-u,1-v
 if t=='ROT270':return v,1-u
 if t=='MIRROR_X':return 1-u,v
 if t=='MIRROR_Y':return u,1-v
 if t=='MIRROR_DIAGONAL':return v,u
 if t=='MIRROR_ANTIDIAGONAL':return 1-v,1-u
 raise RuntimeError(t)
TRANS=['IDENTITY','ROT90','ROT180','ROT270','MIRROR_X','MIRROR_Y','MIRROR_DIAGONAL','MIRROR_ANTIDIAGONAL']
def pts(rows,reg,t):
 w=max(1.,float(reg['width']));h=max(1.,float(reg['height']));x=float(reg['x']);y=float(reg['y']);return [tp((float(c['x'])-x)/w,(float(c['y'])-y)/h,t) for c in rows]
def sym(a,b,ra,rb,t):
 if not a or not b:return None
 A=pts(a,ra,t);B=pts(b,rb,'IDENTITY');ta=cKDTree(A);tb=cKDTree(B);da=tb.query(A,k=1,workers=1)[0];db=ta.query(B,k=1,workers=1)[0];return (float(da.sum())+float(db.sum()))/(len(A)+len(B))
def smatch(a,b,ra,rb,t,kc):
 if not a or not b:return []
 A=pts(a,ra,t);B=pts(b,rb,'IDENTITY');swap=False;left,right=A,B
 if len(left)>len(right):left,right=right,left;swap=True
 k=max(1,min(kc,len(right)));tree=cKDTree(right);ds,ix=tree.query(left,k=k,workers=1)
 if k==1:ds=[[float(x)] for x in ds];ix=[[int(x)] for x in ix]
 es=[]
 for i in range(len(left)):
  for q in range(k):es.append((float(ds[i][q]),i,int(ix[i][q])))
 es.sort(key=lambda x:(x[0],x[1],x[2]));ul=set();ur=set();out=[]
 for d,i,j in es:
  if i in ul or j in ur:continue
  ul.add(i);ur.add(j);out.append((j,i,d) if swap else (i,j,d))
 return out
def mapping(A,B,kc):
 aa=defaultdict(list);bb=defaultdict(list)
 for c in A['centers']:aa[c['kind']].append(c)
 for c in B['centers']:bb[c['kind']].append(c)
 score=[]
 for order,t in enumerate(TRANS):
  num=0.;den=0
  for k in ('ENDPOINT','JUNCTION'):
   d=sym(aa[k],bb[k],A['region'],B['region'],t)
   if d is not None:w=len(aa[k])+len(bb[k]);num+=d*w;den+=w
  score.append((float('inf') if den==0 else num/den,order,t))
 t=min(score)[2];m={}
 for k in ('ENDPOINT','JUNCTION'):
  for ia,ib,_ in smatch(aa[k],bb[k],A['region'],B['region'],t,kc):m[aa[k][ia]['eventId']]=bb[k][ib]['eventId']
 return m
def bucket(row,allowed=None,remap=None):
 d=defaultdict(list)
 for e in row['edges']:
  a,b=e['a'],e['b']
  if allowed is not None and (a not in allowed or b not in allowed):continue
  if remap is not None:a,b=remap[a],remap[b]
  d[tuple(sorted((a,b)))].append(e)
 return d
def adj(row,allowed):
 d=defaultdict(set)
 for e in row['edges']:
  a,b=e['a'],e['b']
  if a not in allowed or b not in allowed:continue
  d[a].add(b);d[b].add(a)
 return d
def jac(a,b):
 u=set(a)|set(b);return 0. if not u else 1-len(set(a)&set(b))/len(u)
def avg(x):return statistics.mean(x) if x else None
def metrics(A,B,kc):
 m=mapping(A,B,kc);ma=set(m);mb=set(m.values());ba=bucket(A,ma,m);bb=bucket(B,mb);keys=set(ba)|set(bb)
 ta=sum(map(len,ba.values()));tb=sum(map(len,bb.values()))
 dele=sum(max(0,len(ba.get(k,()))-len(bb.get(k,()))) for k in keys)
 ins=sum(max(0,len(bb.get(k,()))-len(ba.get(k,()))) for k in keys)
 mult=[abs(len(ba.get(k,()))-len(bb.get(k,())))/max(1,len(ba.get(k,()))+len(bb.get(k,()))) for k in keys]
 aa=adj(A,ma);ab=adj(B,mb);kinds={c['eventId']:c['kind'] for c in A['centers']};ep=[];ju=[]
 for a,b in m.items():
  ex={m[n] for n in aa.get(a,set()) if n in m};ac={n for n in ab.get(b,set()) if n in mb};(ep if kinds.get(a)=='ENDPOINT' else ju).append(jac(ex,ac))
 da=math.hypot(float(A['region']['width']),float(A['region']['height']));db=math.hypot(float(B['region']['width']),float(B['region']['height']));le=[];to=[];tu=[]
 for k in set(ba)&set(bb):
  xa=sorted(ba[k],key=lambda e:(e['pathSteps'],e['tortuosity'],e['turnRate'],e['pathSha256']));xb=sorted(bb[k],key=lambda e:(e['pathSteps'],e['tortuosity'],e['turnRate'],e['pathSha256']))
  for ea,eb in zip(xa,xb):le.append(abs(float(ea['pathSteps'])/max(1.,da)-float(eb['pathSteps'])/max(1.,db)));to.append(abs(float(ea['tortuosity'])-float(eb['tortuosity'])));tu.append(abs(float(ea['turnRate'])-float(eb['turnRate'])))
 return {'mappedEdgeDeletionFraction':dele/max(1,ta),'mappedEdgeInsertionFraction':ins/max(1,tb),'mappedEdgeSymmetricDifferenceFraction':(dele+ins)/max(1,ta+tb),'parallelPathMultiplicityMutation':avg(mult),'endpointAttachmentMutationFraction':avg(ep),'junctionAdjacencyMutationFraction':avg(ju),'preservedEdgeMeanNormalizedLengthMutation':avg(le),'preservedEdgeMeanTortuosityMutation':avg(to),'preservedEdgeMeanTurnRateMutation':avg(tu)}
def auc(pos,neg):
 if not pos or not neg:return None
 s=0.;n=0
 for p in pos:
  for q in neg:
   n+=1;s+=1 if p<q else .5 if p==q else 0
 return 2*s/n-1
def effect(rows,f):
 by=defaultdict(lambda:{'preserved':[],'broken':[]})
 for r in rows:
  x=r['editMagnitudes'].get(f)
  if x is not None:by[(r['occupantFamilyA'],r['occupantFamilyB'])][r['label']].append(float(x))
 es=[]
 for d in by.values():
  e=auc(d['preserved'],d['broken'])
  if e is not None:es.append(e)
 return statistics.mean(es) if es else None
protocol=load_json(protocol_path);manifest=load_json(manifest_dir/'edge-pair-manifest.json');world=load_json(world_dir/'critical-edge-world.json');grammar=load_json(grammar_dir/'critical-edge-grammar.json')
if canonical_sha({k:v for k,v in grammar.items() if k!='criticalEdgeGrammarSha256'})!=grammar.get('criticalEdgeGrammarSha256'):raise RuntimeError('grammar SHA mismatch')
if grammar['criticalEdgeWorldSha256']!=world['criticalEdgeWorldSha256']:raise RuntimeError('grammar/world mismatch')
selected=[x['editId'] for x in grammar['selectedEditAtoms']];train_effect={x['editId']:x['balancedEffect'] for x in grammar['selectedEditAtoms']};eligible=set(world['pairEligibleObservationIds'])
pairs=[]
for x in (manifest_dir/'role-pair-labels.jsonl').read_bytes().splitlines():
 if x.strip():
  r=json.loads(x)
  if r['lane'] in ('holdout','control'):pairs.append(r)
pairs=[r for r in pairs if r['observationA'] in eligible and r['observationB'] in eligible];needed={r['observationA'] for r in pairs}|{r['observationB'] for r in pairs};obs={}
with (projector_dir/'critical-edge-observations.jsonl').open(encoding='utf-8') as f:
 for line in f:
  if line.strip():
   r=json.loads(line)
   if r['observationId'] in needed:obs[r['observationId']]=r
if set(obs)!=needed:raise RuntimeError('missing transfer graph observations')
kc=int(protocol['centerCorrespondence']['greedyNearestCandidatesPerCenter']);rows=[]
for r in pairs:rows.append({**r,'editMagnitudes':metrics(obs[r['observationA']],obs[r['observationB']],kc)})
lane_effects={}
for lane in ('holdout','control'):
 rs=[r for r in rows if r['lane']==lane];lane_effects[lane]={'pairs':len(rs),'effects':{f:effect(rs,f) for f in selected}}
threshold=.08;results=[];passed=[]
for f in selected:
 tr=train_effect[f];ho=lane_effects['holdout']['effects'][f];co=lane_effects['control']['effects'][f];same=ho is not None and co is not None and tr*ho>0 and tr*co>0;ok=same and abs(ho)>=threshold and abs(co)>=threshold
 results.append({'editId':f,'trainEffect':tr,'holdoutEffect':ho,'controlEffect':co,'sameDirectionAllLanes':same,'passesTransferThreshold':ok})
 if ok:passed.append(f)
core={'schema':'mark_critical_edge_correspondence_v5','experimentId':protocol['experimentId'],'edgePairManifestSha256':manifest['edgePairManifestSha256'],'criticalEdgeWorldSha256':world['criticalEdgeWorldSha256'],'criticalEdgeGrammarSha256':grammar['criticalEdgeGrammarSha256'],'provenanceAvailableDuringTransfer':False,'selectedAtoms':results,'passedTransferAtoms':passed,'eligibleTransferPairs':len(rows),'laneEffects':lane_effects,'contract':{'selectedAtomsFrozenBeforeTransfer':True,'noTransferRefit':True,'noTransferReselection':True,'noProvenanceConsumed':True,'noStateVocabularyConsumed':True,'noTransitionGrammarConsumed':True}}
digest=canonical_sha(core);packet={**core,'criticalEdgeCorrespondenceSha256':digest};out_dir.mkdir(parents=True,exist_ok=True);(out_dir/'critical-edge-correspondence.json').write_text(json.dumps(packet,indent=2)+'\n');lines=[f'critical_edge_correspondence_sha256={digest}',f'critical_edge_grammar_sha256={grammar["criticalEdgeGrammarSha256"]}',f'eligible_transfer_pairs={len(rows)}',f'passed_transfer_atoms={len(passed)}']
for r in results:lines.append(f"{r['editId']}:train={r['trainEffect']:.6f};holdout={r['holdoutEffect'] if r['holdoutEffect'] is not None else 'null'};control={r['controlEffect'] if r['controlEffect'] is not None else 'null'};pass={str(r['passesTransferThreshold']).lower()}")
(out_dir/'summary.txt').write_text('\n'.join(lines)+'\n');print(json.dumps(packet,indent=2))
