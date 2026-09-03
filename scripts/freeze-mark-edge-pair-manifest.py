#!/usr/bin/env python3
import hashlib, json, os
from pathlib import Path

protocol_path=Path(os.environ.get('MARK_EDGE_PROTOCOL','research/mark/discovery-experiments/critical-edge-correspondence-v5.protocol.json'))
v4_dir=Path(os.environ.get('MARK_V4_PACKET','artifact-staging/v4'))
out_dir=Path(os.environ.get('MARK_EDGE_PAIR_OUT','artifacts/mark-edge-pair-manifest-v5'))

def load_json(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def canonical_sha(v): return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
def locate(name):
    hits=list(v4_dir.rglob(name))
    if len(hits)!=1: raise RuntimeError(f'expected one {name}, found {len(hits)}')
    return hits[0]

protocol=load_json(protocol_path)
if protocol.get('schema')!='mark_critical_edge_correspondence_protocol_v5': raise RuntimeError('unexpected v5 protocol')
expected=protocol['pairFreeze']
vertex=load_json(locate('vertex-pair-manifest.json'))
vsha=vertex.get('vertexPairManifestSha256')
if canonical_sha({k:v for k,v in vertex.items() if k!='vertexPairManifestSha256'})!=vsha: raise RuntimeError('v4 vertex manifest SHA mismatch')
if vsha!=expected['expectedParentVertexPairManifestSha256']: raise RuntimeError('unexpected v4 vertex manifest')
world=load_json(locate('critical-center-world.json'))
wsha=world.get('criticalCenterWorldSha256')
if canonical_sha({k:v for k,v in world.items() if k!='criticalCenterWorldSha256'})!=wsha: raise RuntimeError('v4 center-world SHA mismatch')
if wsha!=expected['expectedParentCriticalCenterWorldSha256']: raise RuntimeError('unexpected v4 center world')
correspondence=load_json(locate('critical-center-correspondence.json'))
csha=correspondence.get('criticalCenterCorrespondenceSha256')
if canonical_sha({k:v for k,v in correspondence.items() if k!='criticalCenterCorrespondenceSha256'})!=csha: raise RuntimeError('v4 correspondence SHA mismatch')
if csha!=expected['expectedParentCorrespondenceSha256']: raise RuntimeError('unexpected v4 correspondence result')
pair_path=locate('role-pair-labels.jsonl'); pair_bytes=pair_path.read_bytes()
if hashlib.sha256(pair_bytes).hexdigest()!=vertex['parentRolePairRowsSha256']: raise RuntimeError('v4 pair rows changed')
pairs=[json.loads(x) for x in pair_bytes.splitlines() if x.strip()]
if len(pairs)!=int(expected['expectedPairs']): raise RuntimeError(f'unexpected pair count {len(pairs)}')
obs=sorted({r['observationA'] for r in pairs}|{r['observationB'] for r in pairs})
if len(obs)!=int(expected['expectedUniqueObservations']): raise RuntimeError(f'unexpected observation count {len(obs)}')
core={
 'schema':'mark_edge_pair_manifest_v5',
 'experimentId':protocol['experimentId'],
 'parentVertexPairManifestSha256':vsha,
 'parentCriticalCenterWorldSha256':wsha,
 'parentCriticalCenterCorrespondenceSha256':csha,
 'parentRolePairFreezeSha256':vertex['parentRolePairFreezeSha256'],
 'parentRolePairRowsSha256':vertex['parentRolePairRowsSha256'],
 'parentFullWorldSourceBlindInputSha256':vertex['parentFullWorldSourceBlindInputSha256'],
 'parentFullWorldPhysicalLedgerMerkleRoot':vertex['parentFullWorldPhysicalLedgerMerkleRoot'],
 'selectedObservationIds':obs,
 'selectedObservations':len(obs),
 'pairRows':len(pairs),
 'contract':{
   'sourcePixelsAvailableDuringFreeze':False,
   'roleLabelsInheritedWithoutChange':True,
   'v4CenterWorldFrozenBeforeV5Projection':True,
   'noProvenanceConsumed':True,
   'noStateVocabularyConsumed':True,
   'noTransitionGrammarConsumed':True
 }
}
digest=canonical_sha(core);packet={**core,'edgePairManifestSha256':digest}
out_dir.mkdir(parents=True,exist_ok=True)
(out_dir/'edge-pair-manifest.json').write_text(json.dumps(packet,indent=2)+'\n')
(out_dir/'vertex-pair-manifest.json').write_text(json.dumps(vertex,indent=2)+'\n')
(out_dir/'role-pair-labels.jsonl').write_bytes(pair_bytes)
(out_dir/'summary.txt').write_text(f'edge_pair_manifest_sha256={digest}\nparent_vertex_pair_manifest_sha256={vsha}\nparent_critical_center_world_sha256={wsha}\npairs={len(pairs)}\nselected_observations={len(obs)}\n')
print(json.dumps(packet,indent=2))
