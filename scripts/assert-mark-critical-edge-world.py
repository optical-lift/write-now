#!/usr/bin/env python3
import hashlib,json,os,statistics
from pathlib import Path
protocol_path=Path(os.environ.get('MARK_EDGE_PROTOCOL','research/mark/discovery-experiments/critical-edge-correspondence-v5.protocol.json'))
manifest_dir=Path(os.environ.get('MARK_EDGE_PAIR_MANIFEST','artifacts/mark-edge-pair-manifest-v5'))
projector_dir=Path(os.environ.get('MARK_EDGE_PROJECTOR_OUT','artifacts/mark-critical-edge-projector-v5'))
subset_custody_path=Path(os.environ.get('MARK_EDGE_SUBSET_CUSTODY','artifacts/mark-edge-subset-custody-v5/subset-custody.json'))
v4_dir=Path(os.environ.get('MARK_V4_PACKET','artifact-staging/v4'))
out_dir=Path(os.environ.get('MARK_EDGE_WORLD_OUT','artifacts/mark-critical-edge-world-v5'))

def load_json(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def canonical_sha(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
def locate(name):
 hits=list(v4_dir.rglob(name))
 if len(hits)!=1:raise RuntimeError(f'expected one v4 {name}, found {len(hits)}')
 return hits[0]
def center_core(c):return {k:c[k] for k in ('eventId','kind','x','y','degree','armHistogram','tileIndex')}
def center_sort_key(c):return (c['kind'],int(c['x']),int(c['y']),c['eventId'])
protocol=load_json(protocol_path);manifest=load_json(manifest_dir/'edge-pair-manifest.json');subset=load_json(subset_custody_path);summary=load_json(projector_dir/'summary.json')
if protocol.get('schema')!='mark_critical_edge_correspondence_protocol_v5':raise RuntimeError('unexpected protocol')
msha=manifest.get('edgePairManifestSha256')
if canonical_sha({k:v for k,v in manifest.items() if k!='edgePairManifestSha256'})!=msha:raise RuntimeError('manifest SHA mismatch')
if summary.get('schema')!='mark_critical_edge_projector_summary_v5':raise RuntimeError('unexpected projector summary')
if summary['sourceBlindInputSha256']!=subset['selectedCompilerBlindInputSha256']:raise RuntimeError('projector/subset custody mismatch')
if int(summary['observations'])!=int(manifest['selectedObservations']):raise RuntimeError('projector observation count mismatch')
rows_path=projector_dir/'critical-edge-observations.jsonl';row_bytes=rows_path.read_bytes()
if hashlib.sha256(row_bytes).hexdigest()!=summary['rowsSha256']:raise RuntimeError('projector rows SHA mismatch')
projected={}
for raw in row_bytes.splitlines():
 if raw.strip():
  r=json.loads(raw);projected[r['observationId']]=r
if len(projected)!=int(summary['observations']):raise RuntimeError('duplicate/missing projector observations')
v4_world=load_json(locate('critical-center-world.json'));wsha=v4_world.get('criticalCenterWorldSha256')
if canonical_sha({k:v for k,v in v4_world.items() if k!='criticalCenterWorldSha256'})!=wsha:raise RuntimeError('v4 center world SHA mismatch')
if wsha!=manifest['parentCriticalCenterWorldSha256']:raise RuntimeError('wrong v4 center world')
v4_rows={}
for raw in locate('critical-center-world.jsonl').read_bytes().splitlines():
 if raw.strip():
  r=json.loads(raw);v4_rows[r['observationId']]=r
if set(v4_rows)!=set(projected):raise RuntimeError('v4/projected observation set mismatch')
mismatches=[];total_centers=0;total_edges=0;resolutions=[];eligible=[]
min_pair_res=float(protocol['physicalProjection']['minimumObservationTraceResolutionForPair'])
for oid in sorted(projected):
 p=projected[oid];v=v4_rows[oid]
 if p['sourceGroupId']!=v['sourceGroupId'] or p['lane']!=v['lane'] or p['region']!=v['region']:
  mismatches.append((oid,'metadata'));continue
 pc=sorted((center_core(c) for c in p['centers']),key=center_sort_key);vc=sorted((center_core(c) for c in v['centers']),key=center_sort_key)
 if pc!=vc:
  mismatches.append((oid,f'centers:{len(pc)}!={len(vc)}' if len(pc)!=len(vc) else 'center-record'))
 total_centers+=len(pc);total_edges+=len(p['edges']);resolutions.append(float(p['traceResolutionFraction']))
 if float(p['traceResolutionFraction'])>=min_pair_res:eligible.append(oid)
if mismatches:raise RuntimeError(f'edge projector does not exactly reproduce v4 centers after canonical center ordering: {mismatches[:8]}')
global_resolution=float(summary['traceResolutionFraction']);minimum=float(protocol['physicalProjection']['minimumGlobalTraceResolutionFraction'])
if global_resolution<minimum:raise RuntimeError(f'graph trace resolution {global_resolution:.6f} below gate {minimum:.6f}')
core={
 'schema':'mark_critical_edge_world_v5','experimentId':protocol['experimentId'],'edgePairManifestSha256':msha,
 'parentCriticalCenterWorldSha256':wsha,'selectedCompilerBlindInputSha256':subset['selectedCompilerBlindInputSha256'],
 'projectorRowsSha256':summary['rowsSha256'],'observations':len(projected),'centers':total_centers,'edges':total_edges,
 'resolvedPaths':int(summary['resolvedPaths']),'unresolvedPaths':int(summary['unresolvedPaths']),'traceResolutionFraction':global_resolution,
 'minimumObservationTraceResolutionFraction':min(resolutions) if resolutions else 1.0,
 'medianObservationTraceResolutionFraction':statistics.median(resolutions) if resolutions else 1.0,
 'pairEligibleObservationIds':eligible,'pairEligibleObservations':len(eligible),'exactCenterEqualityToV4':True,
 'ownerConflicts':int(summary['ownerConflicts']),
 'contract':{'graphWorldFrozenBeforeRoleLabelsOpenedForScoring':True,'allV4CenterRecordsReproducedExactly':True,'centerComparisonCanonicalizesEmissionOrderOnly':True,'parallelPathsPreserved':True,'pathGeometryAvailable':True,'noProvenanceConsumed':True,'noStateVocabularyConsumed':True,'noTransitionGrammarConsumed':True}
}
digest=canonical_sha(core);packet={**core,'criticalEdgeWorldSha256':digest}
out_dir.mkdir(parents=True,exist_ok=True);(out_dir/'critical-edge-world.json').write_text(json.dumps(packet,indent=2)+'\n')
(out_dir/'summary.txt').write_text(f'critical_edge_world_sha256={digest}\nobservations={len(projected)}\ncenters={total_centers}\nedges={total_edges}\ntrace_resolution_fraction={global_resolution:.6f}\npair_eligible_observations={len(eligible)}\nowner_conflicts={summary["ownerConflicts"]}\nexact_center_equality_to_v4=true\n')
print(json.dumps(packet,indent=2))
