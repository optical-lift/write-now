#!/usr/bin/env python3
import hashlib
import json
import os
from collections import defaultdict
from pathlib import Path

state_dir = Path(os.environ.get('MARK_LOCAL_STATE_FIELD', 'artifact-staging/local-state-field'))
rejoin_path = Path(os.environ.get('MARK_HARVEST_REJOIN', 'artifact-staging/context-custody/mark-harvest-rejoin-v1/mark-harvest-custody-rejoin-v1.json'))
out_dir = Path(os.environ.get('MARK_LOCAL_STATE_REJOIN_OUT', 'artifacts/mark-local-state-field-context-v1'))


def canonical_sha(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode('utf-8')).hexdigest()

packet = json.loads((state_dir/'local-state-field-discovery.json').read_text(encoding='utf-8'))
if packet.get('schema') != 'mark_local_state_field_discovery_v1':
    raise RuntimeError('unexpected local-state discovery packet')
recorded = packet.get('localStateFieldDiscoverySha256')
core = {k:v for k,v in packet.items() if k != 'localStateFieldDiscoverySha256'}
if canonical_sha(core) != recorded:
    raise RuntimeError('local-state discovery SHA verification failed before provenance rejoin')
rejoin = json.loads(rejoin_path.read_text(encoding='utf-8'))
if rejoin.get('schema') != 'mark_harvest_custody_rejoin_v1':
    raise RuntimeError('unexpected harvest rejoin schema')
if packet.get('sourceHarvestSha256') and rejoin.get('sealedHarvestBlindSha256') != packet.get('sourceHarvestSha256'):
    raise RuntimeError('context custody does not belong to local-state evidence')
context = {row['sourceGroupId']:row for row in rejoin.get('sources',[])}

out_dir.mkdir(parents=True, exist_ok=True)
inst = defaultdict(lambda: {'sources':0,'stateMass':None,'dominant':defaultdict(int)})
source_rows=[]
with (state_dir/'source-local-state-mixtures.jsonl').open(encoding='utf-8') as source, (out_dir/'source-local-state-context.jsonl').open('w',encoding='utf-8') as out:
    for line in source:
        if not line.strip(): continue
        row=json.loads(line); sid=row['sourceGroupId']; ctx=context.get(sid)
        if ctx is None: raise RuntimeError(f'missing source custody for {sid}')
        enriched={'schema':'mark_source_local_state_context_v1','localStateFieldDiscoverySha256':recorded,'blindMixture':row,'sourceContext':{'institution':ctx.get('institution'),'objectId':ctx.get('objectId'),'sourceId':ctx.get('sourceId'),'sourceUrl':ctx.get('sourceUrl'),'rightsBasis':ctx.get('rightsBasis'),'retrieval':ctx.get('retrieval'),'context':ctx.get('context')}}
        out.write(json.dumps(enriched,separators=(',',':'),ensure_ascii=False)+'\n')
        source_rows.append(enriched)
        name=ctx.get('institution') or 'unlabeled'; props=row['stateProportions']
        d=inst[name]; d['sources']+=1
        if d['stateMass'] is None: d['stateMass']=[0.0]*len(props)
        for i,p in enumerate(props): d['stateMass'][i]+=p
        if props: d['dominant'][str(max(range(len(props)),key=lambda i:(props[i],-i))+1)]+=1

institution_summary={}
for name,d in sorted(inst.items()):
    institution_summary[name]={'sources':d['sources'],'meanStateProportions':[x/d['sources'] for x in d['stateMass']],'dominantStateCounts':dict(sorted(d['dominant'].items()))}

# Keep the most state-pure source examples for inspection after discovery is frozen.
pure=[]
for row in source_rows:
    props=row['blindMixture']['stateProportions']
    if not props: continue
    dominant=max(range(len(props)),key=lambda i:(props[i],-i))
    pure.append({'stateId':dominant+1,'purity':props[dominant],'eligibleObservations':row['blindMixture']['eligibleObservations'],'sourceGroupId':row['blindMixture']['sourceGroupId'],'sourceContext':row['sourceContext']})
pure.sort(key=lambda r:(r['stateId'],-r['purity'],-r['eligibleObservations'],r['sourceGroupId']))
top_by_state={}
for state in sorted(set(r['stateId'] for r in pure)):
    top_by_state[str(state)]=[r for r in pure if r['stateId']==state][:20]

summary={'schema':'mark_local_state_field_context_rejoin_v1','sealedLocalStateFieldDiscoverySha256':recorded,'sourceObjectsRepresented':len(source_rows),'institutionStateMixtures':institution_summary,'mostStatePureSources':top_by_state,'contract':{'blindDiscoveryVerifiedBeforeRejoin':True,'localStateAssignmentsChanged':False,'sourceMixturesChanged':False,'spatialStatisticsChanged':False,'twinDepthStatisticsChanged':False,'whatRejoined':'source custody and institutional provenance only'}}
(out_dir/'summary.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
(out_dir/'summary.txt').write_text('\n'.join([f'schema={summary["schema"]}',f'sealed_local_state_field_sha256={recorded}',f'source_objects_represented={len(source_rows)}',f'institutions={len(institution_summary)}'])+'\n',encoding='utf-8')
print(json.dumps(summary,indent=2,ensure_ascii=False))
