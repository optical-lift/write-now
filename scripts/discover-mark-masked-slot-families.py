#!/usr/bin/env python3
import hashlib, json, math, os, random
from collections import Counter, defaultdict
from pathlib import Path

protocol_path=Path(os.environ.get('MARK_MASKED_SLOT_PROTOCOL','research/mark/discovery-experiments/masked-slot-substitutability-v1.protocol.json'))
topology_dir=Path(os.environ.get('MARK_TOPOLOGY_ATLAS','artifacts/mark-observation-topology-atlas-v1'))
out_dir=Path(os.environ.get('MARK_MASKED_SLOT_OUT','artifacts/mark-masked-slot-substitutability-v1'))

def load_json(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def canonical_bytes(v): return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
def canonical_sha(v): return hashlib.sha256(canonical_bytes(v)).hexdigest()
def mean(xs): return sum(xs)/len(xs) if xs else 0.0
def stdev(xs):
    if not xs: return 0.0
    m=mean(xs); return math.sqrt(mean([(x-m)**2 for x in xs]))
def area(r): return max(1,int(r['width'])*int(r['height']))
def center(r): return (r['x']+r['width']/2.0,r['y']+r['height']/2.0)
def contains(p,c):
    return area(p)>area(c) and p['x']<=c['x'] and p['y']<=c['y'] and p['x']+p['width']>=c['x']+c['width'] and p['y']+p['height']>=c['y']+c['height']
def euclid(a,b): return math.sqrt(sum((x-y)**2 for x,y in zip(a,b)))
def cosine_counter(a,b):
    if not a or not b: return 0.0
    dot=sum(v*b.get(k,0.0) for k,v in a.items())
    na=math.sqrt(sum(v*v for v in a.values())); nb=math.sqrt(sum(v*v for v in b.values()))
    return dot/(na*nb) if na and nb else 0.0

def qbin(value,cuts):
    for i,c in enumerate(cuts):
        if value<=c: return i
    return len(cuts)
def quantile_cuts(values,parts):
    xs=sorted(values)
    if not xs: return []
    cuts=[]
    for p in range(1,parts):
        idx=min(len(xs)-1,max(0,math.ceil(len(xs)*p/parts)-1))
        cuts.append(xs[idx])
    return cuts

def normalized_features(row):
    centers=max(1,int(row['centerCount'])); out={}
    for k,v in row['countFeatures'].items(): out[k]=float(v)/centers
    out['derived:centerDensityPerMillionPixelsLog1p']=math.log1p(float(row['centerCount'])*1_000_000.0/area(row['region']))
    return out

def stable_token(code):
    return 'T'+hashlib.sha256(('|'.join(map(str,code))).encode()).hexdigest()[:10]

def information_entropy(counter):
    total=sum(counter.values())
    if total<=0: return 0.0
    h=0.0
    for n in counter.values():
        if n:
            p=n/total; h-=p*math.log(p)
    return h

protocol=load_json(protocol_path)
if protocol.get('schema')!='mark_masked_slot_substitutability_protocol_v1': raise RuntimeError('unexpected masked-slot protocol')
summary=load_json(topology_dir/'summary.json')
if summary.get('schema')!='mark_observation_topology_atlas_summary_v1': raise RuntimeError('unexpected topology atlas')
if not summary.get('contract',{}).get('noProvenanceConsumed'): raise RuntimeError('topology atlas consumed provenance')
pe=protocol['parentEvidence']
if summary.get('sourceBlindInputSha256')!=pe['sourceBlindInputSha256']: raise RuntimeError('topology atlas blind-input hash mismatch')
if summary.get('physicalLedgerMerkleRoot')!=pe['physicalLedgerMerkleRoot']: raise RuntimeError('topology atlas physical-ledger Merkle mismatch')
if int(summary.get('observations',-1))!=int(pe['observations']): raise RuntimeError('topology atlas observation-universe mismatch')

rows={}; full_row_count=0
with (topology_dir/'observation-topology-atlas.jsonl').open(encoding='utf-8') as h:
    for line in h:
        if not line.strip(): continue
        full_row_count+=1
        r=json.loads(line)
        if r['lane']!='train': continue
        oid=r['observationId']
        if oid in rows: raise RuntimeError(f'duplicate train observation {oid}')
        rows[oid]=r
if full_row_count!=int(summary['observations']): raise RuntimeError('topology row count does not match summary')

by_source=defaultdict(list)
for r in rows.values(): by_source[r['sourceGroupId']].append(r)
parent={}; children=defaultdict(list)
for source,items in by_source.items():
    for child in items:
        candidates=[p for p in items if p['observationId']!=child['observationId'] and contains(p['region'],child['region'])]
        if candidates:
            p=min(candidates,key=lambda x:(area(x['region']),x['observationId']))
            parent[child['observationId']]=p['observationId']; children[p['observationId']].append(child['observationId'])
for k in children: children[k].sort()

train_ids=sorted(oid for oid,r in rows.items() if r['lane']=='train')
if not train_ids: raise RuntimeError('no train observations')
norm={oid:normalized_features(r) for oid,r in rows.items()}
min_support=int(protocol['occupantFingerprint']['minimumTrainObservationSupport'])
feature_support=Counter(); feature_vals=defaultdict(list)
for oid in train_ids:
    for k,v in norm[oid].items():
        if abs(v)>1e-15: feature_support[k]+=1
        feature_vals[k].append(v)
feature_sd={k:stdev([norm[oid].get(k,0.0) for oid in train_ids]) for k,n in feature_support.items() if n>=min_support}
eligible=[k for k,sd in feature_sd.items() if sd>1e-12]
eligible.sort(key=lambda k:(-feature_sd[k],k))
selected=eligible[:int(protocol['occupantFingerprint']['maximumFeatures'])]
if not selected: raise RuntimeError('no physical occupant features selected')
means={k:mean([norm[oid].get(k,0.0) for oid in train_ids]) for k in selected}
sds={k:(stdev([norm[oid].get(k,0.0) for oid in train_ids]) or 1.0) for k in selected}
z={oid:[(norm[oid].get(k,0.0)-means[k])/sds[k] for k in selected] for oid in rows}
parts=int(protocol['occupantFingerprint']['quantileBins'])
cuts=[]
for d in range(len(selected)): cuts.append(quantile_cuts([z[oid][d] for oid in train_ids],parts))
codes={oid:tuple(qbin(z[oid][d],cuts[d]) for d in range(len(selected))) for oid in rows}
train_code_counts=Counter(codes[oid] for oid in train_ids)
train_code_sources=defaultdict(set)
for oid in train_ids: train_code_sources[codes[oid]].add(rows[oid]['sourceGroupId'])
min_occ=int(protocol['occupantFingerprint']['minimumArchetypeOccurrences'])
min_src=int(protocol['occupantFingerprint']['minimumArchetypeSources'])
common_codes=sorted([c for c,n in train_code_counts.items() if n>=min_occ and len(train_code_sources[c])>=min_src])
if len(common_codes)<2: raise RuntimeError('fewer than two recurring physical occupant archetypes')
centroid_sums={c:[0.0]*len(selected) for c in common_codes}
centroid_ns=Counter()
for oid in train_ids:
    c=codes[oid]
    if c in centroid_sums:
        centroid_ns[c]+=1
        for d,v in enumerate(z[oid]): centroid_sums[c][d]+=v
centroids={c:[v/centroid_ns[c] for v in centroid_sums[c]] for c in common_codes}
token_for_code={c:stable_token(c) for c in common_codes}
code_for_token={v:k for k,v in token_for_code.items()}
token_by_code={}
for c in sorted(set(codes.values())):
    if c in token_for_code: token_by_code[c]=token_for_code[c]
    else:
        best=min(common_codes,key=lambda cc:(sum(a!=b for a,b in zip(c,cc)),token_for_code[cc]))
        token_by_code[c]=token_for_code[best]
token={oid:token_by_code[codes[oid]] for oid in rows}

# Slot geometry bins are fit on train masked slots only. No target topology enters these contexts.
slot_ids=sorted(oid for oid in rows if oid in parent)
train_slots=[oid for oid in slot_ids if rows[oid]['lane']=='train']
if not train_slots: raise RuntimeError('no train masked slots')
slot_raw={}
for oid in slot_ids:
    p=rows[parent[oid]]; r=rows[oid]; pc=center(p['region']); cc=center(r['region'])
    slot_raw[oid]={
      'dx':(cc[0]-pc[0])/max(1.0,p['region']['width']),
      'dy':(cc[1]-pc[1])/max(1.0,p['region']['height']),
      'logAreaRatio':math.log(area(r['region'])/area(p['region'])),
      'aspect':math.log((r['region']['width']/max(1.0,r['region']['height']))/(p['region']['width']/max(1.0,p['region']['height'])))
    }
geom_parts=int(protocol['maskedContext']['geometryQuantileBins'])
geom_cuts={k:quantile_cuts([slot_raw[oid][k] for oid in train_slots],geom_parts) for k in ['dx','dy','logAreaRatio','aspect']}

def sibling_ids(oid):
    pid=parent[oid]
    return [x for x in children[pid] if x!=oid]
def context_parts(oid):
    p=rows[parent[oid]]; sibs=sibling_ids(oid); g=slot_raw[oid]
    sib_tokens=sorted(token[x] for x in sibs)
    sb=min(len(sibs),int(protocol['maskedContext']['siblingCountCap']))
    geom=(qbin(g['dx'],geom_cuts['dx']),qbin(g['dy'],geom_cuts['dy']),qbin(g['logAreaRatio'],geom_cuts['logAreaRatio']),qbin(g['aspect'],geom_cuts['aspect']))
    exact=('scale='+p.get('proposalScale',''), 'geom='+'.'.join(map(str,geom)), 'n='+str(sb))
    atoms=[exact[0], exact[1], exact[2], 'kind='+p.get('proposalKind','')]
    atoms += ['sib:'+t for t in sib_tokens]
    if len(sib_tokens)>=2: atoms += ['sibpair:'+sib_tokens[i]+'+'+sib_tokens[j] for i in range(len(sib_tokens)) for j in range(i+1,min(len(sib_tokens),4))]
    return '|'.join(exact), atoms
context={}; atoms={}
for oid in slot_ids: context[oid],atoms[oid]=context_parts(oid)

# Train-only context distributions for each recurring physical occupant archetype.
token_occ=defaultdict(list)
for oid in train_slots: token_occ[token[oid]].append(oid)
eligible_tokens=sorted(t for t,ids in token_occ.items() if len(ids)>=int(protocol['substitutability']['minimumTokenSlotOccurrences']) and len({rows[oid]['sourceGroupId'] for oid in ids})>=min_src)
if len(eligible_tokens)<2: raise RuntimeError('fewer than two train occupant tokens have enough masked-slot support')
atom_counts={t:Counter() for t in eligible_tokens}; exact_sources={t:defaultdict(set) for t in eligible_tokens}
for t in eligible_tokens:
    for oid in token_occ[t]:
        for a in atoms[oid]: atom_counts[t][a]+=1
        exact_sources[t][context[oid]].add(rows[oid]['sourceGroupId'])

min_shared=int(protocol['substitutability']['minimumSharedExactContexts'])
min_cos=float(protocol['substitutability']['minimumContextCosine'])
max_partners=int(protocol['substitutability']['reciprocalTopPartners'])
pairs=[]; ranked=defaultdict(list)
for i,a in enumerate(eligible_tokens):
    for b in eligible_tokens[i+1:]:
        shared=sorted(set(exact_sources[a]) & set(exact_sources[b]))
        shared_supported=[k for k in shared if len(exact_sources[a][k] | exact_sources[b][k])>=2]
        shared_sources=set()
        for k in shared_supported: shared_sources.update(exact_sources[a][k]); shared_sources.update(exact_sources[b][k])
        cos=cosine_counter(atom_counts[a],atom_counts[b])
        ca,cb=code_for_token[a],code_for_token[b]
        hamming=sum(x!=y for x,y in zip(ca,cb)); frac=hamming/max(1,len(ca))
        score=cos*math.log1p(len(shared_supported))
        row={'leftToken':a,'rightToken':b,'contextCosine':cos,'sharedExactContexts':len(shared_supported),'sharedContextDistinctSources':len(shared_sources),'physicalHammingDistance':hamming,'physicalHammingFraction':frac,'substitutionScore':score}
        pairs.append(row)
        if len(shared_supported)>=min_shared and cos>=min_cos:
            ranked[a].append((score,b)); ranked[b].append((score,a))
for t in ranked: ranked[t].sort(key=lambda x:(-x[0],x[1]))
top={t:{b for _,b in vals[:max_partners]} for t,vals in ranked.items()}
family_edges=[]
for p in pairs:
    a,b=p['leftToken'],p['rightToken']
    if b in top.get(a,set()) and a in top.get(b,set()): family_edges.append(p)

# Connected components of reciprocal high-context edges; singleton tokens are left ungrouped.
adj=defaultdict(set)
for p in family_edges:
    adj[p['leftToken']].add(p['rightToken']); adj[p['rightToken']].add(p['leftToken'])
seen=set(); comps=[]
for t in sorted(adj):
    if t in seen: continue
    stack=[t]; seen.add(t); comp=[]
    while stack:
        x=stack.pop(); comp.append(x)
        for y in sorted(adj[x]):
            if y not in seen: seen.add(y); stack.append(y)
    if len(comp)>=2: comps.append(sorted(comp))
comps.sort(key=lambda c:(-len(c),c))
family_of={}; families=[]
for i,comp in enumerate(comps,1):
    fid=f'F{i:03d}'
    for t in comp: family_of[t]=fid
    fam_pairs=[p for p in family_edges if p['leftToken'] in comp and p['rightToken'] in comp]
    families.append({'familyId':fid,'tokens':comp,'tokenCount':len(comp),'trainReciprocalEdges':len(fam_pairs),'meanContextCosine':mean([p['contextCosine'] for p in fam_pairs]),'meanPhysicalHammingFraction':mean([p['physicalHammingFraction'] for p in fam_pairs])})

# Freeze family definitions before lane transfer statistics. Digest excludes downstream/transfer outcomes.
alias_core={
 'schema':'mark_masked_slot_family_definition_v1','experimentId':protocol['experimentId'],
 'topologyRowsSha256':summary['rowsSha256'],'physicalLedgerMerkleRoot':summary['physicalLedgerMerkleRoot'],
 'selectedPhysicalFeatures':selected,'trainFeatureMeans':means,'trainFeatureStandardDeviations':sds,
 'quantileCuts':cuts,'recurringArchetypes':[{'token':token_for_code[c],'code':list(c),'trainOccurrences':train_code_counts[c],'trainSources':len(train_code_sources[c]),'centroid':centroids[c]} for c in common_codes],
 'contextGeometryCuts':geom_cuts,'families':families,'familyEdges':sorted(family_edges,key=lambda r:(-r['substitutionScore'],r['leftToken'],r['rightToken'])),
 'contract':{'childStateUnavailable':True,'localStatesNotConsumed':True,'targetTopologyExcludedFromMaskedContext':True,'ancestorTopologyExcludedFromMaskedContext':True,'trainLaneDefinesArchetypesContextsAndFamilies':True,'holdoutControlCannotRefit':True}
}
family_sha=canonical_sha(alias_core)
family_definition={**alias_core,'maskedSlotFamilyDefinitionSha256':family_sha}


out_dir.mkdir(parents=True,exist_ok=True)
(out_dir/'masked-slot-family-definition.json').write_text(json.dumps(family_definition,indent=2,ensure_ascii=False)+'\n')
(out_dir/'summary.txt').write_text('\n'.join([
 f'family_definition_sha256={family_sha}',f'train_observations={len(rows)}',f'train_masked_slots={len(slot_ids)}',
 f'recurring_physical_archetypes={len(common_codes)}',f'eligible_train_tokens={len(eligible_tokens)}',f'substitution_families={len(families)}',
 'local_states_consumed=false','target_topology_in_masked_context=false','holdout_control_used_for_family_discovery=false','provenance_available_during_discovery=false'
])+'\n')
print(json.dumps(family_definition,indent=2,ensure_ascii=False))
