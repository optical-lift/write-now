#!/usr/bin/env python3
import hashlib, json, math, os, random
from collections import Counter, defaultdict
from pathlib import Path

protocol_path=Path(os.environ.get('MARK_MASKED_SLOT_PROTOCOL','research/mark/discovery-experiments/masked-slot-substitutability-v1.protocol.json'))
topology_dir=Path(os.environ.get('MARK_TOPOLOGY_ATLAS','artifacts/mark-observation-topology-atlas-v1'))
family_dir=Path(os.environ.get('MARK_MASKED_SLOT_FAMILY_DIR','artifacts/mark-masked-slot-family-freeze-v1'))
out_dir=Path(os.environ.get('MARK_MASKED_SLOT_OUT','artifacts/mark-masked-slot-substitutability-v1'))

def load_json(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def canonical_bytes(v): return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
def canonical_sha(v): return hashlib.sha256(canonical_bytes(v)).hexdigest()
def mean(xs): return sum(xs)/len(xs) if xs else 0.0
def area(r): return max(1,int(r['width'])*int(r['height']))
def center(r): return (r['x']+r['width']/2.0,r['y']+r['height']/2.0)
def contains(p,c):
    return area(p)>area(c) and p['x']<=c['x'] and p['y']<=c['y'] and p['x']+p['width']>=c['x']+c['width'] and p['y']+p['height']>=c['y']+c['height']
def cosine_counter(a,b):
    if not a or not b: return 0.0
    dot=sum(v*b.get(k,0.0) for k,v in a.items())
    na=math.sqrt(sum(v*v for v in a.values())); nb=math.sqrt(sum(v*v for v in b.values()))
    return dot/(na*nb) if na and nb else 0.0
def qbin(value,cuts):
    for i,c in enumerate(cuts):
        if value<=c: return i
    return len(cuts)
def normalized_features(row):
    centers=max(1,int(row['centerCount'])); out={}
    for k,v in row['countFeatures'].items(): out[k]=float(v)/centers
    out['derived:centerDensityPerMillionPixelsLog1p']=math.log1p(float(row['centerCount'])*1_000_000.0/area(row['region']))
    return out

protocol=load_json(protocol_path)
if protocol.get('schema')!='mark_masked_slot_substitutability_protocol_v1': raise RuntimeError('unexpected masked-slot protocol')
summary=load_json(topology_dir/'summary.json')
pe=protocol['parentEvidence']
if summary.get('schema')!='mark_observation_topology_atlas_summary_v1' or not summary.get('contract',{}).get('noProvenanceConsumed'): raise RuntimeError('invalid blind topology atlas')
if summary.get('sourceBlindInputSha256')!=pe['sourceBlindInputSha256'] or summary.get('physicalLedgerMerkleRoot')!=pe['physicalLedgerMerkleRoot'] or int(summary.get('observations',-1))!=int(pe['observations']): raise RuntimeError('topology atlas parent custody mismatch')
family_def=load_json(family_dir/'masked-slot-family-definition.json')
if family_def.get('schema')!='mark_masked_slot_family_definition_v1': raise RuntimeError('unexpected family definition')
family_sha=family_def.get('maskedSlotFamilyDefinitionSha256')
family_core={k:v for k,v in family_def.items() if k!='maskedSlotFamilyDefinitionSha256'}
if canonical_sha(family_core)!=family_sha: raise RuntimeError('family definition SHA mismatch')
if family_def.get('topologyRowsSha256')!=summary.get('rowsSha256') or family_def.get('physicalLedgerMerkleRoot')!=summary.get('physicalLedgerMerkleRoot'): raise RuntimeError('family definition/topology mismatch')

rows={}
with (topology_dir/'observation-topology-atlas.jsonl').open(encoding='utf-8') as h:
    for line in h:
        if not line.strip(): continue
        r=json.loads(line); oid=r['observationId']
        if oid in rows: raise RuntimeError(f'duplicate observation {oid}')
        rows[oid]=r
if len(rows)!=int(summary['observations']): raise RuntimeError('topology row count mismatch')

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
slot_ids=sorted(parent)

selected=family_def['selectedPhysicalFeatures']; means=family_def['trainFeatureMeans']; sds=family_def['trainFeatureStandardDeviations']; cuts=family_def['quantileCuts']
common={tuple(r['code']):r['token'] for r in family_def['recurringArchetypes']}
if not common: raise RuntimeError('frozen family definition has no recurring physical archetypes')
norm={oid:normalized_features(r) for oid,r in rows.items()}
codes={}
for oid in rows:
    z=[(norm[oid].get(k,0.0)-means[k])/sds[k] for k in selected]
    codes[oid]=tuple(qbin(z[d],cuts[d]) for d in range(len(selected)))
token_by_code={}
for c in sorted(set(codes.values())):
    if c in common: token_by_code[c]=common[c]
    else:
        best=min(common,key=lambda cc:(sum(a!=b for a,b in zip(c,cc)),common[cc]))
        token_by_code[c]=common[best]
token={oid:token_by_code[codes[oid]] for oid in rows}

geom_cuts=family_def['contextGeometryCuts']
slot_raw={}
for oid in slot_ids:
    p=rows[parent[oid]]; r=rows[oid]; pc=center(p['region']); cc=center(r['region'])
    slot_raw[oid]={'dx':(cc[0]-pc[0])/max(1.0,p['region']['width']),'dy':(cc[1]-pc[1])/max(1.0,p['region']['height']),'logAreaRatio':math.log(area(r['region'])/area(p['region'])),'aspect':math.log((r['region']['width']/max(1.0,r['region']['height']))/(p['region']['width']/max(1.0,p['region']['height'])))}
def sibling_ids(oid): return [x for x in children[parent[oid]] if x!=oid]
def context_parts(oid):
    p=rows[parent[oid]]; sibs=sibling_ids(oid); sib_tokens=sorted(token[x] for x in sibs); g=slot_raw[oid]
    sb=min(len(sibs),int(protocol['maskedContext']['siblingCountCap']))
    geom=(qbin(g['dx'],geom_cuts['dx']),qbin(g['dy'],geom_cuts['dy']),qbin(g['logAreaRatio'],geom_cuts['logAreaRatio']),qbin(g['aspect'],geom_cuts['aspect']))
    exact=('scale='+p.get('proposalScale',''),'geom='+'.'.join(map(str,geom)),'n='+str(sb))
    atoms=[exact[0],exact[1],exact[2],'kind='+p.get('proposalKind','')]+['sib:'+t for t in sib_tokens]
    if len(sib_tokens)>=2: atoms += ['sibpair:'+sib_tokens[i]+'+'+sib_tokens[j] for i in range(len(sib_tokens)) for j in range(i+1,min(len(sib_tokens),4))]
    return '|'.join(exact),atoms
context={}; atoms={}
for oid in slot_ids: context[oid],atoms[oid]=context_parts(oid)

families=family_def['families']; family_of={t:f['familyId'] for f in families for t in f['tokens']}

def lane_token_context(lane):
    c=defaultdict(Counter); exact=defaultdict(lambda:defaultdict(set)); downstream=defaultdict(Counter)
    for oid in slot_ids:
        if rows[oid]['lane']!=lane: continue
        t=token[oid]
        for a in atoms[oid]: c[t][a]+=1
        exact[t][context[oid]].add(rows[oid]['sourceGroupId'])
        for child in children.get(oid,[]): downstream[t][token[child]]+=1
    return c,exact,downstream

def family_pair_rows(counters,exact,downstream):
    out=[]
    for fam in families:
        toks=[t for t in fam['tokens'] if counters.get(t)]
        for i,a in enumerate(toks):
            for b in toks[i+1:]:
                shared=set(exact[a])&set(exact[b]); shared_sources=set()
                for k in shared: shared_sources.update(exact[a][k]); shared_sources.update(exact[b][k])
                out.append({'familyId':fam['familyId'],'leftToken':a,'rightToken':b,'contextCosine':cosine_counter(counters[a],counters[b]),'sharedExactContexts':len(shared),'sharedContextDistinctSources':len(shared_sources),'downstreamChildProgramCosine':cosine_counter(downstream[a],downstream[b])})
    return out

def collision_count(lane,fam_map):
    by_ctx=defaultdict(lambda:defaultdict(set))
    for oid in slot_ids:
        if rows[oid]['lane']!=lane: continue
        fid=fam_map.get(token[oid])
        if fid: by_ctx[context[oid]][fid].add(token[oid])
    return sum(1 for fmap in by_ctx.values() for toks in fmap.values() if len(toks)>=2)
def null_family_maps(lane,iters):
    sizes=[len(f['tokens']) for f in families]; toks=sorted({t for f in families for t in f['tokens']}); out=[]
    for it in range(iters):
        shuffled=toks[:]; rnd=random.Random(int(hashlib.sha256(f'masked-slot-family-null|{lane}|{it}'.encode()).hexdigest()[:16],16)); rnd.shuffle(shuffled)
        m={}; pos=0
        for i,size in enumerate(sizes,1):
            for t in shuffled[pos:pos+size]: m[t]=f'F{i:03d}'
            pos+=size
        out.append(m)
    return out

iters=int(protocol['nullModel']['iterations']); transfer={}; lane_pairs={}
for lane in ['train','holdout','control']:
    counters,exact,downstream=lane_token_context(lane); prs=family_pair_rows(counters,exact,downstream); lane_pairs[lane]=prs
    obs_cos=mean([r['contextCosine'] for r in prs]); obs_down=mean([r['downstreamChildProgramCosine'] for r in prs]); obs_coll=collision_count(lane,family_of)
    null_cos=[]; null_down=[]; null_coll=[]
    for fmap in null_family_maps(lane,iters):
        faux=[]
        for fid in sorted(set(fmap.values())):
            toks=sorted(t for t,f in fmap.items() if f==fid and counters.get(t))
            for i,a in enumerate(toks):
                for b in toks[i+1:]: faux.append((a,b))
        null_cos.append(mean([cosine_counter(counters[a],counters[b]) for a,b in faux])); null_down.append(mean([cosine_counter(downstream[a],downstream[b]) for a,b in faux])); null_coll.append(collision_count(lane,fmap))
    transfer[lane]={'familyPairsEvaluated':len(prs),'meanFamilyContextCosine':obs_cos,'nullMeanContextCosine':mean(null_cos),'contextCosineBeyondAllNulls':bool(null_cos) and obs_cos>max(null_cos),'meanFamilyDownstreamChildProgramCosine':obs_down,'nullMeanDownstreamChildProgramCosine':mean(null_down),'downstreamBeyondAllNulls':bool(null_down) and obs_down>max(null_down),'crossTokenSameFamilyExactContextCollisions':obs_coll,'nullMeanExactContextCollisions':mean(null_coll),'collisionCountBeyondAllNulls':bool(null_coll) and obs_coll>max(null_coll)}

occ=[]
for oid in slot_ids:
    t=token[oid]
    occ.append({'schema':'mark_masked_slot_occurrence_v1','observationId':oid,'sourceGroupId':rows[oid]['sourceGroupId'],'lane':rows[oid]['lane'],'parentObservationId':parent[oid],'occupantToken':t,'familyId':family_of.get(t),'maskedContextKey':context[oid],'region':rows[oid]['region']})
core={'schema':'mark_masked_slot_substitutability_v1','experimentId':protocol['experimentId'],'maskedSlotFamilyDefinitionSha256':family_sha,'physicalLedgerMerkleRoot':summary['physicalLedgerMerkleRoot'],'topologyRowsSha256':summary['rowsSha256'],'provenanceAvailableDuringDiscovery':False,'observations':len(rows),'maskedSlots':len(slot_ids),'recurringPhysicalArchetypes':len(common),'substitutionFamilies':len(families),'families':families,'strongestCrossFormSubstitutions':sorted(family_def.get('familyEdges',[]),key=lambda r:(-r['physicalHammingFraction'],-r['substitutionScore'],r['leftToken'],r['rightToken']))[:50],'transfer':transfer,'contract':{'familyDefinitionReadFromFrozenSha':True,'familyDefinitionNotRefit':True,'localStateFieldNotConsumed':True,'stateTransitionGrammarNotConsumed':True,'provenanceUnavailableUntilFinalSha':True,'targetTopologyExcludedFromMaskedContext':True,'downstreamChildrenUsedOnlyAfterFamilyFreeze':True}}
digest=canonical_sha(core); packet={**core,'maskedSlotSubstitutabilitySha256':digest}
out_dir.mkdir(parents=True,exist_ok=True)
(out_dir/'masked-slot-family-definition.json').write_text(json.dumps(family_def,indent=2,ensure_ascii=False)+'\n')
(out_dir/'masked-slot-substitutability.json').write_text(json.dumps(packet,indent=2,ensure_ascii=False)+'\n')
(out_dir/'lane-family-pairs.json').write_text(json.dumps(lane_pairs,indent=2,ensure_ascii=False)+'\n')
with (out_dir/'masked-slot-occurrences.jsonl').open('w',encoding='utf-8') as h:
    for r in occ: h.write(json.dumps(r,separators=(',',':'),ensure_ascii=False)+'\n')
(out_dir/'summary.txt').write_text('\n'.join([f'masked_slot_substitutability_sha256={digest}',f'family_definition_sha256={family_sha}',f'observations={len(rows)}',f'masked_slots={len(slot_ids)}',f'recurring_physical_archetypes={len(common)}',f'substitution_families={len(families)}',f"holdout_mean_family_context_cosine={transfer['holdout']['meanFamilyContextCosine']:.6f}",f"holdout_null_mean_context_cosine={transfer['holdout']['nullMeanContextCosine']:.6f}",f"control_mean_family_context_cosine={transfer['control']['meanFamilyContextCosine']:.6f}",f"control_null_mean_context_cosine={transfer['control']['nullMeanContextCosine']:.6f}",f"holdout_downstream_cosine={transfer['holdout']['meanFamilyDownstreamChildProgramCosine']:.6f}",f"control_downstream_cosine={transfer['control']['meanFamilyDownstreamChildProgramCosine']:.6f}",'local_states_consumed=false','family_definition_refit=false','provenance_available_during_discovery=false'])+'\n')
print(json.dumps(packet,indent=2,ensure_ascii=False))
