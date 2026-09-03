#!/usr/bin/env python3
import hashlib, json, os
from collections import Counter, defaultdict
from pathlib import Path

packet_dir=Path(os.environ.get('MARK_MASKED_SLOT_PACKET','artifact-staging/masked-slot'))
context_dir=Path(os.environ.get('MARK_SOURCE_CONTEXT','artifact-staging/context'))
out_dir=Path(os.environ.get('MARK_MASKED_SLOT_REJOIN_OUT','artifacts/mark-masked-slot-substitutability-v1-context'))

def load_json(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def canonical_sha(v): return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()

packet=load_json(packet_dir/'masked-slot-substitutability.json')
if packet.get('schema')!='mark_masked_slot_substitutability_v1': raise RuntimeError('unexpected masked-slot packet')
sha=packet.get('maskedSlotSubstitutabilitySha256')
core={k:v for k,v in packet.items() if k!='maskedSlotSubstitutabilitySha256'}
if canonical_sha(core)!=sha: raise RuntimeError('masked-slot packet SHA mismatch')
if packet.get('provenanceAvailableDuringDiscovery'): raise RuntimeError('masked-slot discovery was not blind')
family_def=load_json(packet_dir/'masked-slot-family-definition.json')
family_sha=family_def.get('maskedSlotFamilyDefinitionSha256')
family_core={k:v for k,v in family_def.items() if k!='maskedSlotFamilyDefinitionSha256'}
if canonical_sha(family_core)!=family_sha or family_sha!=packet['maskedSlotFamilyDefinitionSha256']: raise RuntimeError('family definition SHA mismatch')

summary=load_json(context_dir/'summary.json')
if summary.get('schema')!='mark_source_rule_atlas_context_rejoin_v1': raise RuntimeError('unexpected source context schema')
contexts={}
with (context_dir/'source-rule-context.jsonl').open(encoding='utf-8') as h:
    for line in h:
        if line.strip():
            r=json.loads(line); contexts.setdefault(r['blindRow']['sourceGroupId'],r['sourceContext'])

occ=[]
with (packet_dir/'masked-slot-occurrences.jsonl').open(encoding='utf-8') as h:
    for line in h:
        if line.strip(): occ.append(json.loads(line))
missing=sorted({r['sourceGroupId'] for r in occ}-set(contexts))
if missing: raise RuntimeError(f'missing provenance for {len(missing)} masked-slot sources')

by_token_context=defaultdict(lambda:defaultdict(list))
for r in occ: by_token_context[r['occupantToken']][r['maskedContextKey']].append(r)

def pair_examples(pair,limit=4):
    a,b=pair['leftToken'],pair['rightToken']; shared=sorted(set(by_token_context[a]) & set(by_token_context[b])); out=[]
    for key in shared:
        left=sorted(by_token_context[a][key],key=lambda r:(r['sourceGroupId'],r['observationId']))
        right=sorted(by_token_context[b][key],key=lambda r:(r['sourceGroupId'],r['observationId']))
        chosen=None
        for x in left:
            for y in right:
                if x['sourceGroupId']!=y['sourceGroupId']:
                    chosen=(x,y); break
            if chosen: break
        if not chosen and left and right: chosen=(left[0],right[0])
        if not chosen: continue
        x,y=chosen
        out.append({
          'maskedContextKey':key,
          'left':{'observationId':x['observationId'],'sourceGroupId':x['sourceGroupId'],'lane':x['lane'],'region':x['region'],'sourceContext':contexts[x['sourceGroupId']]},
          'right':{'observationId':y['observationId'],'sourceGroupId':y['sourceGroupId'],'lane':y['lane'],'region':y['region'],'sourceContext':contexts[y['sourceGroupId']]}
        })
        if len(out)>=limit: break
    return out

family_inst=defaultdict(lambda:defaultdict(lambda:{'occurrences':0,'sources':set(),'tokens':Counter()}))
for r in occ:
    fid=r.get('familyId')
    if not fid: continue
    inst=contexts[r['sourceGroupId']].get('institution','unknown')
    slot=family_inst[fid][inst]; slot['occurrences']+=1; slot['sources'].add(r['sourceGroupId']); slot['tokens'][r['occupantToken']]+=1
institution_rows=[]
for fid,insts in sorted(family_inst.items()):
    institution_rows.append({'familyId':fid,'institutions':[{'institution':inst,'occurrences':v['occurrences'],'sources':len(v['sources']),'tokenCounts':dict(v['tokens'])} for inst,v in sorted(insts.items())]})

pair_rows=[]
for pair in packet.get('strongestCrossFormSubstitutions',[])[:20]:
    pair_rows.append({**pair,'contextExamples':pair_examples(pair)})

core={
 'schema':'mark_masked_slot_context_rejoin_v1','sealedMaskedSlotSubstitutabilitySha256':sha,'sealedFamilyDefinitionSha256':family_sha,
 'blindStatisticsPreserved':True,'familyInstitutionDistribution':institution_rows,'strongestCrossFormSubstitutionExamples':pair_rows,
 'contract':{'physicalArchetypesUnchanged':True,'maskedContextsUnchanged':True,'familiesUnchanged':True,'transferStatisticsUnchanged':True,'sourceContextAttachedOnlyAfterFinalSha':True,'contextExamplesDidNotDefineFamilies':True,'semanticOrHistoricalMeaningNotAutomaticallyAssigned':True}
}
digest=canonical_sha(core); out={**core,'contextRejoinSha256':digest}
out_dir.mkdir(parents=True,exist_ok=True)
(out_dir/'masked-slot-context-rejoin.json').write_text(json.dumps(out,indent=2,ensure_ascii=False)+'\n')
(out_dir/'summary.txt').write_text('\n'.join([f'sealed_masked_slot_sha256={sha}',f'sealed_family_definition_sha256={family_sha}',f'context_rejoin_sha256={digest}',f'families_with_context={len(institution_rows)}','families_preserved=true','statistics_preserved=true'])+'\n')
print(json.dumps(out,indent=2,ensure_ascii=False))
