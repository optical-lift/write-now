#!/usr/bin/env python3
import hashlib
import json
import os
from collections import defaultdict
from pathlib import Path

blind_dir = Path(os.environ.get('MARK_RELATIONAL_STATE_BLIND', 'artifact-staging/blind-discovery'))
rejoin_path = Path(os.environ.get('MARK_HARVEST_REJOIN', 'artifact-staging/context-custody/mark-harvest-rejoin-v1/mark-harvest-custody-rejoin-v1.json'))
out_dir = Path(os.environ.get('MARK_RELATIONAL_STATE_REJOIN_OUT', 'artifacts/mark-relational-state-context-v1'))


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def canonical_sha(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode('utf-8')).hexdigest()

packet = load(blind_dir / 'relational-state-discovery.json')
if packet.get('schema') != 'mark_relational_state_discovery_v1':
    raise RuntimeError('unexpected blind relational-state schema')
claimed = packet.get('relationalStateDiscoverySha256')
core = {k:v for k,v in packet.items() if k != 'relationalStateDiscoverySha256'}
if canonical_sha(core) != claimed:
    raise RuntimeError('blind relational-state SHA failed before rejoin')
rejoin = load(rejoin_path)
if rejoin.get('schema') != 'mark_harvest_custody_rejoin_v1':
    raise RuntimeError('unexpected harvest rejoin schema')
if rejoin.get('sealedHarvestBlindSha256') != packet.get('sourceHarvestSha256'):
    raise RuntimeError('context custody does not belong to blind relational-state discovery')
context = {s['sourceGroupId']: s for s in rejoin.get('sources', [])}


def slim(s):
    return {
        'institution': s.get('institution'),
        'objectId': s.get('objectId'),
        'sourceId': s.get('sourceId'),
        'sourceUrl': s.get('sourceUrl'),
        'rightsBasis': s.get('rightsBasis'),
        'retrieval': s.get('retrieval'),
        'context': s.get('context'),
    }

out_dir.mkdir(parents=True, exist_ok=True)
regime_counts = defaultdict(lambda: defaultdict(int))
with (blind_dir / 'source-construction-regimes.jsonl').open('r', encoding='utf-8') as src, (out_dir / 'construction-regimes-context.jsonl').open('w', encoding='utf-8') as out:
    for line in src:
        if not line.strip():
            continue
        row = json.loads(line)
        ctx = context.get(row['sourceGroupId'])
        if ctx is None:
            raise RuntimeError(f"missing source context {row['sourceGroupId']}")
        regime_counts[str(row['regimeId'])][ctx.get('institution') or 'unlabeled'] += 1
        out.write(json.dumps({
            'schema':'mark_construction_regime_context_v1',
            'relationalStateDiscoverySha256':claimed,
            'blindRow':row,
            'sourceContext':slim(ctx)
        }, separators=(',', ':'), ensure_ascii=False)+'\n')

twin_combo = defaultdict(int)
with (blind_dir / 'structural-twins.jsonl').open('r', encoding='utf-8') as src, (out_dir / 'structural-twins-context.jsonl').open('w', encoding='utf-8') as out:
    for line in src:
        if not line.strip():
            continue
        row = json.loads(line)
        left = context.get(row['leftSourceGroupId'])
        right = context.get(row['rightSourceGroupId'])
        if left is None or right is None:
            raise RuntimeError('twin source missing from context custody')
        combo = ' <> '.join(sorted([left.get('institution') or 'unlabeled', right.get('institution') or 'unlabeled']))
        twin_combo[combo] += 1
        out.write(json.dumps({
            'schema':'mark_structural_twin_context_v1',
            'relationalStateDiscoverySha256':claimed,
            'blindTwin':row,
            'leftContext':slim(left),
            'rightContext':slim(right)
        }, separators=(',', ':'), ensure_ascii=False)+'\n')

summary = {
    'schema':'mark_relational_state_context_rejoin_v1',
    'sealedRelationalStateDiscoverySha256': claimed,
    'parentAtlasSha256': packet['parentAtlasSha256'],
    'constructionRegimeInstitutionCounts': {
        k: dict(sorted(v.items())) for k,v in sorted(regime_counts.items(), key=lambda x:int(x[0]))
    },
    'structuralTwinInstitutionCombinations': dict(sorted(twin_combo.items())),
    'contract': {
        'blindDiscoveryVerifiedBeforeRejoin': True,
        'signedStatesChanged': False,
        'regimeAssignmentsChanged': False,
        'twinRanksChanged': False,
        'whatRejoined': 'source custody and provenance only',
    }
}
(out_dir / 'summary.json').write_text(json.dumps(summary, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')
(out_dir / 'summary.txt').write_text(
    f"schema={summary['schema']}\nsealed_relational_state_discovery_sha256={claimed}\nregimes={len(regime_counts)}\ntwin_institution_combinations={len(twin_combo)}\n",
    encoding='utf-8'
)
print(json.dumps(summary, indent=2, ensure_ascii=False))
