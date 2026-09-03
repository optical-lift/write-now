#!/usr/bin/env python3
import hashlib, json, math, os
from collections import Counter, defaultdict
from pathlib import Path

protocol_path=Path(os.environ.get('MARK_SIBLING_ROLE_PROTOCOL','research/mark/discovery-experiments/sibling-role-substitution-v2.protocol.json'))
topology_dir=Path(os.environ.get('MARK_TOPOLOGY_ATLAS','artifact-staging/topology-cache/topology-atlas'))
parent_atlas_dir=Path(os.environ.get('MARK_PARENT_ATLAS','artifact-staging/parent-atlas'))
out_dir=Path(os.environ.get('MARK_SIBLING_ROLE_VOCAB_OUT','artifacts/mark-sibling-role-vocabulary-v2'))

def load_json(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def canonical_bytes(v): return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
def canonical_sha(v): return hashlib.sha256(canonical_bytes(v)).hexdigest()
def mean(xs): return sum(xs)/len(xs) if xs else 0.0
def stdev(xs):
    if not xs:return 0.0
    m=mean(xs); return math.sqrt(mean([(x-m)**2 for x in xs]))
def distance(a,b): return math.sqrt(sum((x-y)**2 for x,y in zip(a,b)))
def area(r): return max(1,int(r['width'])*int(r['height']))
def center(r): return (float(r['x'])+float(r['width'])/2,float(r['y'])+float(r['height'])/2)
def contains(p,c):
    return area(p)>area(c) and p['x']<=c['x'] and p['y']<=c['y'] and p['x']+p['width']>=c['x']+c['width'] and p['y']+p['height']>=c['y']+c['height']
def overlap_area(a,b):
    x0=max(a['x'],b['x']); y0=max(a['y'],b['y']); x1=min(a['x']+a['width'],b['x']+b['width']); y1=min(a['y']+a['height'],b['y']+b['height'])
    return max(0,x1-x0)*max(0,y1-y0)
def rank01(vals,target):
    less=sum(v<target for v in vals); equal=sum(v==target for v in vals)
    return (less+0.5*equal)/len(vals)
def normalized_topology(row):
    c=max(1,int(row['centerCount']))
    out={k:float(v)/c for k,v in row['countFeatures'].items()}
    out['derived:centerDensityPerMillionPixelsLog1p']=math.log1p(float(row['centerCount'])*1_000_000.0/area(row['region']))
    return out
def select_features(value_maps,min_support,max_features):
    support=Counter(); keys=set(); variability={}
    for values in value_maps.values():
        keys.update(values)
        for k,v in values.items():
            if abs(v)>1e-15:support[k]+=1
    for k in keys: variability[k]=stdev([values.get(k,0.0) for values in value_maps.values()])
    eligible=[k for k in keys if support[k]>=min_support and variability[k]>1e-12]
    eligible.sort(key=lambda k:(-support[k],-variability[k],k))
    return eligible[:max_features]
def fit_stats(ids,values_by_id,features):
    out={}
    for f in features:
        xs=[values_by_id[i].get(f,0.0) for i in ids]; sd=stdev(xs)
        out[f]={'mean':mean(xs),'sd':sd if sd>1e-12 else 1.0}
    return out
def vector(values,features,stats,clip):
    out=[]
    for f in features:
        z=(values.get(f,0.0)-stats[f]['mean'])/stats[f]['sd']
        out.append(max(-clip,min(clip,z)))
    return out
def kmeans(points,ids,k,max_iter=100):
    if k>=len(points):return None
    gm=[mean([p[d] for p in points]) for d in range(len(points[0]))]
    first=max(range(len(points)),key=lambda i:(distance(points[i],gm),ids[i])); chosen=[first]
    while len(chosen)<k:
        remain=[i for i in range(len(points)) if i not in chosen]
        chosen.append(max(remain,key=lambda i:(min(distance(points[i],points[j]) for j in chosen),ids[i])))
    cents=[list(points[i]) for i in chosen]; assignments=None
    for _ in range(max_iter):
        new=[min(range(k),key=lambda j:(distance(p,cents[j]),j)) for p in points]
        if new==assignments:break
        assignments=new; nextc=[]
        for j in range(k):
            members=[points[i] for i,a in enumerate(assignments) if a==j]
            if not members:return None
            nextc.append([mean([r[d] for r in members]) for d in range(len(points[0]))])
        cents=nextc
    return assignments,cents
def sampled_silhouette(points,assignments,k,ids,limit):
    order=sorted(range(len(ids)),key=lambda i:hashlib.sha256(ids[i].encode()).hexdigest())[:min(limit,len(ids))]
    clusters={c:[i for i in order if assignments[i]==c] for c in range(k)}
    if any(not clusters[c] for c in range(k)):return -1.0
    scores=[]
    for i in order:
        own=assignments[i]; same=[j for j in clusters[own] if j!=i]
        a=mean([distance(points[i],points[j]) for j in same]) if same else 0.0
        b=min(mean([distance(points[i],points[j]) for j in clusters[c]]) for c in range(k) if c!=own)
        scores.append((b-a)/max(a,b) if max(a,b) else 0.0)
    return mean(scores)
def stable_remap(cents):
    order=sorted(range(len(cents)),key=lambda j:(tuple(round(x,12) for x in cents[j]),j))
    return {old:new+1 for new,old in enumerate(order)}

def role_geometry(oid,rows,parent,peers):
    t=rows[oid]; p=rows[parent[oid]]; tr=t['region']; pr=p['region']; tc=center(tr)
    all_ids=[oid]+peers; centers=[center(rows[x]['region']) for x in all_ids]
    xs=[c[0] for c in centers]; ys=[c[1] for c in centers]
    areas=[area(rows[x]['region']) for x in all_ids]; aspects=[float(rows[x]['region']['width'])/max(1.0,float(rows[x]['region']['height'])) for x in all_ids]
    diag=max(1.0,math.hypot(pr['width'],pr['height']))
    peer_cent=(mean([center(rows[s]['region'])[0] for s in peers]),mean([center(rows[s]['region'])[1] for s in peers]))
    dx=(tc[0]-peer_cent[0])/diag; dy=(tc[1]-peer_cent[1])/diag; angle=math.atan2(dy,dx)
    dists=[math.hypot(tc[0]-center(rows[s]['region'])[0],tc[1]-center(rows[s]['region'])[1])/diag for s in peers]
    peer_areas=sorted(area(rows[s]['region']) for s in peers); median_peer=peer_areas[len(peer_areas)//2]
    target_aspect=float(tr['width'])/max(1.0,float(tr['height']))
    return {
      'role:xRankAmongPeers':rank01(xs,tc[0]), 'role:yRankAmongPeers':rank01(ys,tc[1]),
      'role:areaRankAmongPeers':rank01(areas,area(tr)), 'role:aspectRankAmongPeers':rank01(aspects,target_aspect),
      'role:nearestPeerDistanceParentDiag':min(dists), 'role:meanPeerDistanceParentDiag':mean(dists),
      'role:peerCentroidRadialDistanceParentDiag':math.hypot(dx,dy), 'role:peerCentroidAngleSin':math.sin(angle), 'role:peerCentroidAngleCos':math.cos(angle),
      'role:leftParentMargin':(tr['x']-pr['x'])/max(1.0,float(pr['width'])), 'role:rightParentMargin':(pr['x']+pr['width']-(tr['x']+tr['width']))/max(1.0,float(pr['width'])),
      'role:topParentMargin':(tr['y']-pr['y'])/max(1.0,float(pr['height'])), 'role:bottomParentMargin':(pr['y']+pr['height']-(tr['y']+tr['height']))/max(1.0,float(pr['height'])),
      'role:leftPeerFraction':sum(center(rows[s]['region'])[0]<tc[0] for s in peers)/len(peers), 'role:rightPeerFraction':sum(center(rows[s]['region'])[0]>tc[0] for s in peers)/len(peers),
      'role:abovePeerFraction':sum(center(rows[s]['region'])[1]<tc[1] for s in peers)/len(peers), 'role:belowPeerFraction':sum(center(rows[s]['region'])[1]>tc[1] for s in peers)/len(peers),
      'role:logAreaToPeerMedian':math.log(area(tr)/max(1.0,float(median_peer)))
    }

protocol=load_json(protocol_path)
if protocol.get('schema')!='mark_sibling_role_substitution_protocol_v2':raise RuntimeError('unexpected sibling-role protocol')
topo_summary=load_json(topology_dir/'summary.json'); custody=load_json(parent_atlas_dir/'compiler'/'custody.json')
if topo_summary.get('schema')!='mark_observation_topology_atlas_summary_v1':raise RuntimeError('unexpected topology atlas')
if topo_summary['physicalLedgerMerkleRoot']!=custody['physicalLedger']['merkleRoot']:raise RuntimeError('topology/custody Merkle mismatch')
if topo_summary['sourceBlindInputSha256']!=custody['sourceBlindInputSha256']:raise RuntimeError('topology/custody blind-input mismatch')
if not topo_summary.get('contract',{}).get('noProvenanceConsumed'):raise RuntimeError('topology atlas consumed provenance')
rows={}
with (topology_dir/'observation-topology-atlas.jsonl').open(encoding='utf-8') as h:
    for line in h:
        if line.strip():
            r=json.loads(line); rows[r['observationId']]=r
if len(rows)!=int(topo_summary['observations']):raise RuntimeError('topology row count mismatch')
by_source=defaultdict(list)
for r in rows.values():by_source[r['sourceGroupId']].append(r)
parent={}
for source,items in by_source.items():
    for child in items:
        candidates=[p for p in items if p['observationId']!=child['observationId'] and contains(p['region'],child['region'])]
        if candidates:parent[child['observationId']]=min(candidates,key=lambda r:(area(r['region']),r['observationId']))['observationId']
children=defaultdict(list)
for c,p in parent.items():children[p].append(c)
for p in children:children[p].sort()
peer_map={}
for oid,pid in parent.items():
    peers=[s for s in children[pid] if s!=oid and overlap_area(rows[oid]['region'],rows[s]['region'])==0]
    if len(peers)>=int(protocol['eligibility']['minimumDisjointSiblingPeers']):peer_map[oid]=peers
ids=sorted(peer_map); train=[i for i in ids if rows[i]['lane']=='train']
if len(train)<int(protocol['eligibility']['minimumTrainEligibleObservations']):raise RuntimeError(f'too few eligible train observations: {len(train)}')
norm={i:normalized_topology(rows[i]) for i in rows}
role_geo={i:role_geometry(i,rows,parent,peer_map[i]) for i in ids}
peer_mean={}; nearest={}
for oid in ids:
    peers=peer_map[oid]; tc=center(rows[oid]['region']); agg=defaultdict(list)
    for s in peers:
        for k,v in norm[s].items():agg[k].append(v)
    peer_mean[oid]={k:mean(vs) for k,vs in agg.items()}
    ns=min(peers,key=lambda s:(math.hypot(tc[0]-center(rows[s]['region'])[0],tc[1]-center(rows[s]['region'])[1]),s))
    nearest[oid]=norm[ns]
neighbor_cfg=protocol['maskedRoleContext']['neighborTopology']
selected_neighbor=select_features({i:peer_mean[i] for i in train},int(neighbor_cfg['minimumTrainTargetSupport']),int(neighbor_cfg['maximumBaseFeatures']))
role_aug={}
for oid in ids:
    v=dict(role_geo[oid])
    for f in selected_neighbor:
        v['peerMean:'+f]=peer_mean[oid].get(f,0.0); v['nearestPeer:'+f]=nearest[oid].get(f,0.0)
    role_aug[oid]=v
geo_features=sorted(role_geo[train[0]]); aug_features=geo_features+[x for f in selected_neighbor for x in ('peerMean:'+f,'nearestPeer:'+f)]
clip=float(protocol['robustStandardization']['zClip'])
geo_stats=fit_stats(train,role_geo,geo_features); aug_stats=fit_stats(train,role_aug,aug_features)
geo_vec={i:vector(role_geo[i],geo_features,geo_stats,clip) for i in ids}; aug_vec={i:vector(role_aug[i],aug_features,aug_stats,clip) for i ids}
occ_cfg=protocol['occupantDiscovery']; occ_features=select_features({i:norm[i] for i in train},int(occ_cfg['minimumTrainObservationSupport']),int(occ_cfg['maximumFeatures']))
occ_stats=fit_stats(train,norm,occ_features); occ_vec={i:vector(norm[i],occ_features,occ_stats,clip) for i in ids}
cl=protocol['occupantClustering']
all_train_points=[occ_vec[i] for i in train]
core_fraction=float(cl['coreTrainingFraction'])
norms=[math.sqrt(sum(x*x for x in v)) for v in all_train_points]
ordered=sorted(range(len(train)),key=lambda j:(norms[j],train[j]))
core_n=max(int(len(train)*core_fraction),int(cl['minimumCoreTrainingObservations']))
core_indices=ordered[:min(len(ordered),core_n)]
core_ids=[train[j] for j in core_indices]
points=[all_train_points[j] for j in core_indices]
candidates=[]
for k in cl['candidateK']:
    res=kmeans(points,core_ids,int(k))
    if res is None:continue
    assign,cents=res; sizes=[assign.count(j) for j in range(int(k))]; src=[len({rows[core_ids[x]]['sourceGroupId'] for x,a in enumerate(assign) if a==j}) for j in range(int(k))]
    if min(sizes)<int(cl['minimumClusterObservations']) or min(src)<int(cl['minimumClusterDistinctSources']):continue
    sil=sampled_silhouette(points,assign,int(k),core_ids,int(cl['silhouetteSampleLimit']))
    candidates.append({'k':int(k),'assignments':assign,'centroids':cents,'sizes':sizes,'sources':src,'silhouette':sil})
if not candidates:raise RuntimeError('no supported multi-family occupant clustering')
best=max(candidates,key=lambda r:(r['silhouette'],-r['k'])); remap=stable_remap(best['centroids']); cents={remap[j]:best['centroids'][j] for j in range(best['k'])}
def assign_centroid(vec):return min(cents,key=lambda f:(distance(vec,cents[f]),f))
occ_assign={i:assign_centroid(occ_vec[i]) for i ids}
out_dir.mkdir(parents=True,exist_ok=True)
role_path=out_dir/'masked-sibling-role-vectors.jsonl'; occ_path=out_dir/'occupant-assignments.jsonl'; rh=hashlib.sha256(); oh=hashlib.sha256()
with role_path.open('wb') as h:
    for i in ids:
        r=rows[i]; payload={'schema':'mark_masked_sibling_role_vector_v2','observationId':i,'sourceGroupId':r['sourceGroupId'],'lane':r['lane'],'parentObservationId':parent[i],'peerCount':len(peer_map[i]),'geometryVector':geo_vec[i],'augmentedVector':aug_vec[i],'region':r['region']}
        b=json.dumps(payload,separators=(',',':')).encode()+b'\n';h.write(b);rh.update(b)
with occ_path.open('wb') as h:
    for i in ids:
        r=rows[i];payload={'schema':'mark_sibling_role_occupant_assignment_v2','observationId':i,'sourceGroupId':r['sourceGroupId'],'lane':r['lane'],'occupantFamily':occ_assign[i]}
        b=json.dumps(payload,separators=(',',':')).encode()+b'\n';h.write(b);oh.update(b)
core={'schema':'mark_sibling_role_vocabulary_v2','experimentId':protocol['experimentId'],'physicalLedgerMerkleRoot':topo_summary['physicalLedgerMerkleRoot'],'sourceBlindInputSha256':topo_summary['sourceBlindInputSha256'],'topologyRowsSha256':topo_summary['rowsSha256'],'provenanceAvailableDuringDiscovery':False,'eligibleObservations':len(ids),'trainEligibleObservations':len(train),'maskedRoleContext':{'geometryFeatures':geo_features,'selectedNeighborTopologyBaseFeatures':selected_neighbor,'augmentedFeatures':aug_features,'trainGeometryStandardization':geo_stats,'trainAugmentedStandardization':aug_stats,'minimumDisjointSiblingPeers':protocol['eligibility']['minimumDisjointSiblingPeers']},'occupantVocabulary':{'features':occ_features,'trainStandardization':occ_stats,'zClip':clip,'chosenK':best['k'],'centroids':{str(k):v for k,v in sorted(cents.items())},'coreTrainingObservations':len(core_ids),'candidateSolutions':[{'k':r['k'],'sampledSilhouette':r['silhouette'],'sizes':r['sizes'],'distinctSources':r['sources']} for r in sorted(candidates,key=lambda x:x['k'])]},'assignmentFiles':{'maskedRoleVectorsSha256':rh.hexdigest(),'occupantAssignmentsSha256':oh.hexdigest()},'contract':{'targetTopologyUnavailableToMaskedRoleContext':True,'parentAndAncestorTopologyUnavailableToMaskedRoleContext':True,'overlappingSiblingTopologyUnavailableToMaskedRoleContext':True,'atLeastTwoDisjointSiblingPeersRequired':True,'peerMultiplicityNotIncludedAsRoleFeature':True,'continuousRoleVectorsFrozenBeforeSubstitutionPairEvaluation':True,'occupantFamiliesDiscoveredOnTrainOnly':True,'holdoutAndControlAssignedWithoutRefit':True,'noLocalStateIdsConsumed':True,'noTransitionGrammarConsumed':True,'noProvenanceConsumed':True}}
digest=canonical_sha(core); packet={**core,'siblingRoleVocabularySha256':digest}
(out_dir/'sibling-role-vocabulary.json').write_text(json.dumps(packet,indent=2)+'\n')
(out_dir/'summary.txt').write_text('\n'.join([f'sibling_role_vocabulary_sha256={digest}',f'eligible_observations={len(ids)}',f'train_eligible_observations={len(train)}',f'occupant_families={best["k"]}',f'occupant_silhouette={best["silhouette"]:.6f}',f'neighbor_topology_features={len(selected_neighbor)}','role_clusters_created=false','target_topology_available_to_role_context=false'])+'\n')
print(json.dumps(packet,indent=2))
