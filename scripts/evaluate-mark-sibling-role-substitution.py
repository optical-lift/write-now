#!/usr/bin/env python3
import hashlib, json, math, os, statistics
from collections import defaultdict
from pathlib import Path

protocol_path=Path(os.environ.get('MARK_SIBLING_ROLE_PROTOCOL','research/mark/discovery-experiments/sibling-role-substitution-v2.protocol.json'))
vocab_dir=Path(os.environ.get('MARK_SIBLING_ROLE_VOCAB','artifacts/mark-sibling-role-vocabulary-v2'))
out_dir=Path(os.environ.get('MARK_SIBLING_ROLE_OUT','artifacts/mark-sibling-role-substitution-v2'))

def load_json(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def canonical_sha(v): return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
def distance(a,b): return math.sqrt(sum((x-y)**2 for x,y in zip(a,b)))
def median(xs): return statistics.median(xs) if xs else None
def mean(xs): return sum(xs)/len(xs) if xs else None

def source_balanced(rows,family,lane):
    by_source=defaultdict(list)
    for r in rows:
        if r['occupantFamily']==family and r['lane']==lane: by_source[r['sourceGroupId']].append(r)
    out=[]
    for source,items in sorted(by_source.items()):
        out.append(min(items,key=lambda r:(hashlib.sha256(f"sibling-role-representative|{lane}|{family}|{source}|{r['observationId']}".encode()).hexdigest(),r['observationId'])))
    return out

def nearest_summary(left,right,key,forbid_same_source=True):
    if not left or not right:return None
    ds=[]; matches=[]
    for a in left:
        eligible=[b for b in right if not forbid_same_source or b['sourceGroupId']!=a['sourceGroupId']]
        if not eligible:continue
        b=min(eligible,key=lambda x:(distance(a[key],x[key]),x['sourceGroupId'],x['observationId']))
        d=distance(a[key],b[key]); ds.append(d); matches.append((a,b,d))
    if not ds:return None
    return {'medianNearestDistance':median(ds),'meanNearestDistance':mean(ds),'directedMatches':len(ds),'matches':matches}

def symmetric_cross(a_rows,b_rows,key):
    ab=nearest_summary(a_rows,b_rows,key,True); ba=nearest_summary(b_rows,a_rows,key,True)
    if not ab or not ba:return None
    distances=[m[2] for m in ab['matches']]+[m[2] for m in ba['matches']]
    # Reciprocal pairs are particularly strong because both physical families choose one another's contexts.
    amap={(m[0]['observationId'],m[1]['observationId']) for m in ab['matches']}
    bmap={(m[1]['observationId'],m[0]['observationId']) for m in ba['matches']}
    reciprocal=sorted(amap & bmap)
    return {'symmetricMedianNearestDistance':median(distances),'symmetricMeanNearestDistance':mean(distances),'directedMatches':len(distances),'reciprocalNearestMatches':len(reciprocal),'reciprocalObservationPairs':[list(x) for x in reciprocal[:24]]}

def within_family(family_rows,key):
    x=nearest_summary(family_rows,family_rows,key,True)
    return x['medianNearestDistance'] if x else None

def lane_pair_stats(rows,a,b,lane):
    A=source_balanced(rows,a,lane); B=source_balanced(rows,b,lane)
    out={'occupantASources':len(A),'occupantBSources':len(B)}
    for label,key in [('geometry','geometryVector'),('augmented','augmentedVector')]:
        cross=symmetric_cross(A,B,key); wa=within_family(A,key); wb=within_family(B,key)
        baseline=mean([x for x in (wa,wb) if x is not None])
        if cross and baseline is not None and baseline>0:
            out[label]={k:v for k,v in cross.items() if k!='reciprocalObservationPairs'}
            out[label]['withinFamilyMedianA']=wa; out[label]['withinFamilyMedianB']=wb; out[label]['pooledWithinFamilyMedian']=baseline
            out[label]['crossToWithinDistanceRatio']=cross['symmetricMedianNearestDistance']/baseline
            out[label]['reciprocalObservationPairs']=cross['reciprocalObservationPairs']
        else: out[label]=None
    return out

protocol=load_json(protocol_path)
if protocol.get('schema')!='mark_sibling_role_substitution_protocol_v2':raise RuntimeError('unexpected sibling-role protocol')
vocab=load_json(vocab_dir/'sibling-role-vocabulary.json'); sha=vocab.get('siblingRoleVocabularySha256')
if vocab.get('schema')!='mark_sibling_role_vocabulary_v2' or canonical_sha({k:v for k,v in vocab.items() if k!='siblingRoleVocabularySha256'})!=sha:raise RuntimeError('sibling-role vocabulary SHA mismatch')
if vocab.get('provenanceAvailableDuringDiscovery'):raise RuntimeError('vocabulary consumed provenance')
role_bytes=(vocab_dir/'masked-sibling-role-vectors.jsonl').read_bytes(); occ_bytes=(vocab_dir/'occupant-assignments.jsonl').read_bytes()
if hashlib.sha256(role_bytes).hexdigest()!=vocab['assignmentFiles']['maskedRoleVectorsSha256']:raise RuntimeError('role vector SHA mismatch')
if hashlib.sha256(occ_bytes).hexdigest()!=vocab['assignmentFiles']['occupantAssignmentsSha256']:raise RuntimeError('occupant assignment SHA mismatch')
roles={json.loads(l)['observationId']:json.loads(l) for l in role_bytes.splitlines() if l.strip()}
occs={json.loads(l)['observationId']:json.loads(l) for l in occ_bytes.splitlines() if l.strip()}
if set(roles)!=set(occs):raise RuntimeError('role/occupant observation mismatch')
rows=[]
for oid in sorted(roles):
    r=roles[oid]; o=occs[oid]
    if r['sourceGroupId']!=o['sourceGroupId'] or r['lane']!=o['lane']:raise RuntimeError(f'custody mismatch {oid}')
    rows.append({**r,'occupantFamily':int(o['occupantFamily'])})
families=sorted(map(int,vocab['occupantVocabulary']['centroids'].keys())); cents={int(k):v for k,v in vocab['occupantVocabulary']['centroids'].items()}
pairs=[]
for i,a in enumerate(families):
    for b in families[i+1:]:pairs.append((a,b,distance(cents[a],cents[b])))
distance_gate=median([p[2] for p in pairs])
min_sources=int(protocol['substitutionTest']['minimumTrainDistinctSourcesPerOccupant'])
train_candidates=[]
for a,b,pdist in pairs:
    t=lane_pair_stats(rows,a,b,'train')
    if pdist<distance_gate or t['occupantASources']<min_sources or t['occupantBSources']<min_sources or not t['geometry'] or not t['augmented']:continue
    train_candidates.append({'occupantFamilyA':a,'occupantFamilyB':b,'physicalCentroidDistance':pdist,'train':t})
train_candidates.sort(key=lambda r:(r['train']['geometry']['crossToWithinDistanceRatio'],r['train']['augmented']['crossToWithinDistanceRatio'],-r['physicalCentroidDistance'],r['occupantFamilyA'],r['occupantFamilyB']))
frozen=train_candidates[:int(protocol['substitutionTest']['maximumFrozenCandidatePairs'])]
# Evaluate all family pairs in each lane for percentile context, without changing frozen train selection.
all_lane={}
for lane in ('train','holdout','control'):
    arr=[]
    for a,b,pdist in pairs:
        s=lane_pair_stats(rows,a,b,lane)
        if s['geometry'] and s['augmented']:
            arr.append({'a':a,'b':b,'geometryRatio':s['geometry']['crossToWithinDistanceRatio'],'augmentedRatio':s['augmented']['crossToWithinDistanceRatio']})
    all_lane[lane]=arr

def percentile_low(values,x):
    return sum(v>=x for v in values)/len(values) if values else None  # 1.0 = among closest / best substitution
for pair in frozen:
    for lane in ('holdout','control'):
        pair[lane]=lane_pair_stats(rows,pair['occupantFamilyA'],pair['occupantFamilyB'],lane)
    for lane in ('train','holdout','control'):
        s=pair[lane]; gs=[r['geometryRatio'] for r in all_lane[lane]]; aus=[r['augmentedRatio'] for r in all_lane[lane]]
        if s['geometry']:s['geometry']['closenessPercentileAmongAllPhysicalPairs']=percentile_low(gs,s['geometry']['crossToWithinDistanceRatio'])
        if s['augmented']:s['augmented']['closenessPercentileAmongAllPhysicalPairs']=percentile_low(aus,s['augmented']['crossToWithinDistanceRatio'])
    pair['strongTransfer']=(
      pair['train']['geometry']['crossToWithinDistanceRatio']<=1.25 and pair['train']['augmented']['crossToWithinDistanceRatio']<=1.25 and
      pair['holdout']['geometry'] is not None and pair['control']['geometry'] is not None and
      pair['holdout']['geometry']['closenessPercentileAmongAllPhysicalPairs']>=0.75 and pair['control']['geometry']['closenessPercentileAmongAllPhysicalPairs']>=0.75 and
      pair['holdout']['augmented']['closenessPercentileAmongAllPhysicalPairs']>=0.75 and pair['control']['augmented']['closenessPercentileAmongAllPhysicalPairs']>=0.75
    )
core={'schema':'mark_sibling_role_substitution_discovery_v2','experimentId':protocol['experimentId'],'parentSiblingRoleVocabularySha256':sha,'provenanceAvailableDuringDiscovery':False,'eligibleObservations':len(rows),'occupantFamilies':len(families),'physicalDifferenceGateMedianCentroidDistance':distance_gate,'frozenCandidatePairs':frozen,'allPairContextRatiosByLane':all_lane,'contract':{'pairSelectionTrainOnly':True,'allNearestContextMatchesCrossSourceGroupId':True,'oneDeterministicRepresentativePerSourcePerFamily':True,'holdoutAndControlCannotAlterFamilyDefinitionsOrPairSelection':True,'geometryOnlyAndNeighborTopologyAugmentedContextsBothReported':True,'noStateVocabularyConsumed':True,'noTransitionGrammarConsumed':True,'noProvenanceConsumed':True}}
digest=canonical_sha(core); packet={**core,'siblingRoleSubstitutionDiscoverySha256':digest}
out_dir.mkdir(parents=True,exist_ok=True); (out_dir/'sibling-role-substitution.json').write_text(json.dumps(packet,indent=2)+'\n'); (out_dir/'candidate-pairs.json').write_text(json.dumps(frozen,indent=2)+'\n')
lines=[f'sibling_role_vocabulary_sha256={sha}',f'sibling_role_substitution_sha256={digest}',f'eligible_observations={len(rows)}',f'occupant_families={len(families)}',f'frozen_candidate_pairs={len(frozen)}']
for n,p in enumerate(frozen,1):
    lines.append(f"pair_{n}=O{p['occupantFamilyA']}~O{p['occupantFamilyB']};physical_distance={p['physicalCentroidDistance']:.6f};train_geometry_ratio={p['train']['geometry']['crossToWithinDistanceRatio']:.6f};train_augmented_ratio={p['train']['augmented']['crossToWithinDistanceRatio']:.6f};holdout_geometry_pct={p['holdout']['geometry']['closenessPercentileAmongAllPhysicalPairs'] if p['holdout']['geometry'] else -1:.6f};control_geometry_pct={p['control']['geometry']['closenessPercentileAmongAllPhysicalPairs'] if p['control']['geometry'] else -1:.6f};strong_transfer={str(p['strongTransfer']).lower()}")
(out_dir/'summary.txt').write_text('\n'.join(lines)+'\n'); print(json.dumps(packet,indent=2))
