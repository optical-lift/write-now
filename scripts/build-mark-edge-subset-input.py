#!/usr/bin/env python3
import hashlib, json, os
from pathlib import Path

protocol_path=Path(os.environ.get('MARK_EDGE_PROTOCOL','research/mark/discovery-experiments/critical-edge-correspondence-v5.protocol.json'))
manifest_dir=Path(os.environ.get('MARK_EDGE_PAIR_MANIFEST','artifacts/mark-edge-pair-manifest-v5'))
full_input=Path(os.environ['MARK_FULL_COMPILER_INPUT'])
out_input=Path(os.environ['MARK_EDGE_COMPILER_INPUT'])
out_custody=Path(os.environ.get('MARK_EDGE_SUBSET_CUSTODY','artifacts/mark-edge-subset-custody-v5/subset-custody.json'))

def load_json(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def canonical_sha(v): return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
def compact(v): return json.dumps(v,separators=(',',':'),ensure_ascii=False).encode()
protocol=load_json(protocol_path); manifest=load_json(manifest_dir/'edge-pair-manifest.json')
if protocol.get('schema')!='mark_critical_edge_correspondence_protocol_v5': raise RuntimeError('unexpected protocol')
msha=manifest.get('edgePairManifestSha256')
if canonical_sha({k:v for k,v in manifest.items() if k!='edgePairManifestSha256'})!=msha: raise RuntimeError('edge-pair manifest SHA mismatch')
full=load_json(full_input)
if full.get('schema')!='mark_observable_input_blind_v1': raise RuntimeError('unexpected compiler input')
if full.get('blindInputSha256')!=manifest['parentFullWorldSourceBlindInputSha256']: raise RuntimeError('sealed source world changed')
selected=set(manifest['selectedObservationIds']); obs_by_id={o['id']:o for o in full['observations']}
missing=sorted(selected-set(obs_by_id))
if missing: raise RuntimeError(f'selected observations missing: {missing[:5]}')
selected_obs=[o for o in full['observations'] if o['id'] in selected]
source_ids={o['sourceGroupId'] for o in selected_obs}; selected_sources=[s for s in full['sources'] if s['sourceGroupId'] in source_ids]
if {s['sourceGroupId'] for s in selected_sources}!=source_ids: raise RuntimeError('selected source set incomplete')
core={k:v for k,v in full.items() if k!='blindInputSha256'};core['sources']=selected_sources;core['observations']=selected_obs
subset_sha=hashlib.sha256(compact(core)).hexdigest();subset={**core,'blindInputSha256':subset_sha}
out_input.parent.mkdir(parents=True,exist_ok=True);out_input.write_text(json.dumps(subset,separators=(',',':'),ensure_ascii=False)+'\n')
custody_core={
 'schema':'mark_edge_subset_custody_v5','experimentId':protocol['experimentId'],'edgePairManifestSha256':msha,
 'parentFullWorldSourceBlindInputSha256':full['blindInputSha256'],'selectedCompilerBlindInputSha256':subset_sha,
 'selectedSources':len(selected_sources),'selectedObservations':len(selected_obs),
 'selectedSourcePayloadSha256':hashlib.sha256(compact(selected_sources)).hexdigest(),
 'selectedObservationPayloadSha256':hashlib.sha256(compact(selected_obs)).hexdigest(),
 'contract':{'sourceObjectsCopiedExactlyFromParent':True,'observationObjectsCopiedExactlyFromParent':True,'capturePathsUnchanged':True,'onlySelectionOperationApplied':True,'noProvenanceConsumed':True}
}
csha=canonical_sha(custody_core);custody={**custody_core,'edgeSubsetCustodySha256':csha}
out_custody.parent.mkdir(parents=True,exist_ok=True);out_custody.write_text(json.dumps(custody,indent=2)+'\n');print(json.dumps(custody,indent=2))
