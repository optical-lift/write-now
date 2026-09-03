#!/usr/bin/env python3
import bisect
import hashlib
import json
import math
import os
from collections import defaultdict
from pathlib import Path

atlas_dir = Path(os.environ.get('MARK_SOURCE_RULE_ATLAS', 'artifact-staging/blind-atlas/source-rule-atlas'))
discovery_path = Path(os.environ.get('MARK_BLIND_DISCOVERY_PACKET', 'artifact-staging/blind-atlas/blind-discovery/blind-discovery.json'))
protocol_path = Path(os.environ.get('MARK_RELATIONAL_STATE_PROTOCOL', 'research/mark/discovery-experiments/relational-state-discovery-v1.protocol.json'))
out_dir = Path(os.environ.get('MARK_RELATIONAL_STATE_OUT', 'artifacts/mark-relational-state-discovery-v1'))


def load_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def canonical_bytes(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode('utf-8')


def canonical_sha(value):
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def mean(values):
    return sum(values) / len(values) if values else 0.0


def stdev(values):
    if len(values) < 2:
        return 1.0
    m = mean(values)
    v = sum((x - m) ** 2 for x in values) / len(values)
    return math.sqrt(v) or 1.0


def distance(a, b):
    return math.sqrt(sum((x-y)**2 for x, y in zip(a, b)))


def percentile(sorted_values, value):
    if not sorted_values:
        return 1.0
    return bisect.bisect_right(sorted_values, value) / len(sorted_values)


def init_centroids(points, k):
    dim = len(points[0])
    global_mean = [mean([p[d] for p in points]) for d in range(dim)]
    first = max(range(len(points)), key=lambda i: (distance(points[i], global_mean), tuple(points[i]), -i))
    chosen = [first]
    while len(chosen) < k:
        idx = max(
            (i for i in range(len(points)) if i not in chosen),
            key=lambda i: (min(distance(points[i], points[j]) for j in chosen), tuple(points[i]), -i),
        )
        chosen.append(idx)
    return [list(points[i]) for i in chosen]


def kmeans(points, k, max_iter=100):
    centroids = init_centroids(points, k)
    assignments = None
    for _ in range(max_iter):
        new_assignments = []
        for p in points:
            idx = min(range(k), key=lambda j: (distance(p, centroids[j]), j))
            new_assignments.append(idx)
        if assignments == new_assignments:
            break
        assignments = new_assignments
        new_centroids = []
        for j in range(k):
            members = [points[i] for i, a in enumerate(assignments) if a == j]
            if not members:
                return None
            new_centroids.append([mean([p[d] for p in members]) for d in range(len(points[0]))])
        centroids = new_centroids
    return assignments, centroids


def silhouette(points, assignments, k):
    clusters = [[i for i, a in enumerate(assignments) if a == j] for j in range(k)]
    scores = []
    for i, p in enumerate(points):
        own = assignments[i]
        own_members = [j for j in clusters[own] if j != i]
        a = mean([distance(p, points[j]) for j in own_members]) if own_members else 0.0
        b = min(
            mean([distance(p, points[j]) for j in clusters[c]])
            for c in range(k) if c != own and clusters[c]
        )
        denom = max(a, b)
        scores.append((b-a)/denom if denom else 0.0)
    return mean(scores)

protocol = load_json(protocol_path)
if protocol.get('schema') != 'mark_relational_state_discovery_protocol_v1':
    raise RuntimeError('unexpected relational-state protocol schema')

atlas_summary = load_json(atlas_dir / 'summary.json')
if atlas_summary.get('schema') != 'mark_source_rule_atlas_summary_v1':
    raise RuntimeError('unexpected atlas summary schema')
rows_path = atlas_dir / 'source-rule-atlas.jsonl'
rows_bytes = rows_path.read_bytes()
if hashlib.sha256(rows_bytes).hexdigest() != atlas_summary.get('rowsSha256'):
    raise RuntimeError('atlas rows SHA mismatch')

discovery = load_json(discovery_path)
if discovery.get('schema') != 'mark_v7_blind_discovery_packet_v1':
    raise RuntimeError('unexpected blind discovery schema')
if discovery.get('blindDiscoverySha256') != atlas_summary.get('sealedBlindDiscoverySha256'):
    raise RuntimeError('blind discovery does not belong to frozen atlas')

# Experiment 1: treat attraction and exclusion symmetrically.
signed_rules = []
for rule in discovery.get('rules', []):
    holdout = rule['holdout']
    control = rule['control']
    lift = float(holdout['accuracyLift'])
    ctl_lift = float(control['accuracyLift'])
    if lift > 0:
        state = 'attraction'
        beyond_all = float(holdout['accuracy']) > float(holdout['nullAccuracyMaximum'])
        control_same_direction = max(0.0, ctl_lift)
    elif lift < 0:
        state = 'exclusion'
        beyond_all = float(holdout['accuracy']) < float(holdout['nullAccuracyMinimum'])
        control_same_direction = max(0.0, -ctl_lift)
    else:
        state = 'neutral'
        beyond_all = False
        control_same_direction = 0.0
    magnitude = abs(lift)
    specificity = magnitude - control_same_direction
    signed_rules.append({
        'schema': 'mark_signed_relational_state_v1',
        'blindRank': int(rule['blindRank']),
        'context': rule['context'],
        'predictedOutcome': rule['predictedOutcome'],
        'originalCandidateTier': rule['candidateTier'],
        'state': state,
        'holdoutObservedAccuracy': holdout['accuracy'],
        'holdoutNullMeanAccuracy': holdout['nullMeanAccuracy'],
        'holdoutNullMinimum': holdout['nullAccuracyMinimum'],
        'holdoutNullMaximum': holdout['nullAccuracyMaximum'],
        'signedLift': lift,
        'absoluteLift': magnitude,
        'controlSignedLift': ctl_lift,
        'sameDirectionControlPenalty': control_same_direction,
        'directionalSpecificity': specificity,
        'observedBeyondAllNullsInSignedDirection': beyond_all,
        'strongBlindState': bool(beyond_all and specificity > 0),
    })
signed_rules.sort(key=lambda r: (-int(r['strongBlindState']), -r['directionalSpecificity'], -r['absoluteLift'], r['blindRank']))
for i, row in enumerate(signed_rules, 1):
    row['signedStateRank'] = i

# Read source profiles.
profiles = defaultdict(dict)
lanes = {}
with rows_path.open('r', encoding='utf-8') as handle:
    for line in handle:
        if not line.strip():
            continue
        row = json.loads(line)
        source = row['sourceGroupId']
        rank = int(row['blindRank'])
        lanes[source] = row['lane']
        profiles[source][rank] = {
            'contextCount': int(row['contextCount']),
            'predictedOutcomeCount': int(row['predictedOutcomeCount']),
            'accuracy': float(row['accuracy']),
        }

feature_ranks = [int(x) for x in protocol['constructionRegimeExperiment']['featureRuleRanks']]
if len(feature_ranks) != 2:
    raise RuntimeError('v1 construction regime requires exactly two feature rule ranks')
r1, r2 = feature_ranks
eligible = sorted(s for s, data in profiles.items() if r1 in data and r2 in data)
if len(eligible) < 20:
    raise RuntimeError('too few sources have both rule contexts for regime/twin discovery')

raw_by_source = {}
for source in eligible:
    a = profiles[source][r1]
    b = profiles[source][r2]
    ctx1, ctx2 = a['contextCount'], b['contextCount']
    raw_by_source[source] = [
        a['accuracy'],
        b['accuracy'],
        math.log((ctx2 + 1.0) / (ctx1 + 1.0)),
        math.log(ctx1 + ctx2 + 1.0),
    ]
feature_names = ['rule1Accuracy', 'rule2Accuracy', 'logRule2ToRule1ContextRatio', 'logTotalContextMass']
means = [mean([raw_by_source[s][d] for s in eligible]) for d in range(4)]
stdevs = [stdev([raw_by_source[s][d] for s in eligible]) for d in range(4)]
z_by_source = {s: [(raw_by_source[s][d]-means[d])/stdevs[d] for d in range(4)] for s in eligible}
points = [z_by_source[s] for s in eligible]

# Experiment 2: discover unlabeled construction regimes.
min_k = int(protocol['constructionRegimeExperiment']['minimumK'])
max_k = int(protocol['constructionRegimeExperiment']['maximumK'])
min_cluster = int(protocol['constructionRegimeExperiment']['minimumClusterSize'])
candidates = []
for k in range(min_k, min(max_k, len(points)-1)+1):
    result = kmeans(points, k)
    if result is None:
        continue
    assignments, centroids = result
    sizes = [assignments.count(j) for j in range(k)]
    if min(sizes) < min_cluster:
        continue
    score = silhouette(points, assignments, k)
    candidates.append((score, k, assignments, centroids, sizes))
if not candidates:
    raise RuntimeError('no valid construction-regime clustering')
score, chosen_k, assignments, centroids, sizes = max(candidates, key=lambda x: (x[0], -x[1]))

# Stabilize regime ids by lexicographic centroid order.
order = sorted(range(chosen_k), key=lambda j: tuple(centroids[j]))
remap = {old: new+1 for new, old in enumerate(order)}
assignments = [remap[a] for a in assignments]
centroids = [centroids[j] for j in order]
regime_rows = []
for i, source in enumerate(eligible):
    regime_rows.append({
        'schema': 'mark_blind_construction_regime_source_v1',
        'sourceGroupId': source,
        'lane': lanes[source],
        'regimeId': assignments[i],
        'features': dict(zip(feature_names, raw_by_source[source])),
        'zFeatures': dict(zip(feature_names, z_by_source[source])),
    })
regime_summary = []
for regime_id in range(1, chosen_k+1):
    members = [row for row in regime_rows if row['regimeId'] == regime_id]
    centroid_raw = {name: mean([row['features'][name] for row in members]) for name in feature_names}
    regime_summary.append({
        'regimeId': regime_id,
        'sourceObjects': len(members),
        'laneCounts': {lane: sum(1 for row in members if row['lane'] == lane) for lane in ['train','holdout','control']},
        'centroid': centroid_raw,
    })
cluster_quality = [{'k': k, 'silhouette': s, 'clusterSizes': sz} for s, k, _, _, sz in sorted(candidates, key=lambda x: x[1])]

# Experiment 3: cross-lane structural twins in the same blind feature space.
all_cross_distances = []
nearest = {}
for i, left in enumerate(eligible):
    best = None
    for j in range(i+1, len(eligible)):
        right = eligible[j]
        if lanes[left] == lanes[right]:
            continue
        d = distance(z_by_source[left], z_by_source[right])
        all_cross_distances.append(d)
        if best is None or (d, right) < best:
            best = (d, right)
        prev = nearest.get(right)
        if prev is None or (d, left) < prev:
            nearest[right] = (d, left)
    for j in range(0, i):
        right = eligible[j]
        if lanes[left] == lanes[right]:
            continue
        d = distance(z_by_source[left], z_by_source[right])
        if best is None or (d, right) < best:
            best = (d, right)
    if best is not None:
        nearest[left] = best
all_cross_distances.sort()
mutual = []
seen = set()
for source, (d, mate) in nearest.items():
    if nearest.get(mate, (None, None))[1] != source:
        continue
    pair = tuple(sorted([source, mate]))
    if pair in seen:
        continue
    seen.add(pair)
    left, right = pair
    d = distance(z_by_source[left], z_by_source[right])
    mutual.append({
        'schema': 'mark_blind_structural_twin_v1',
        'leftSourceGroupId': left,
        'leftLane': lanes[left],
        'rightSourceGroupId': right,
        'rightLane': lanes[right],
        'distance': d,
        'crossLaneDistancePercentile': percentile(all_cross_distances, d),
        'leftFeatures': dict(zip(feature_names, raw_by_source[left])),
        'rightFeatures': dict(zip(feature_names, raw_by_source[right])),
    })
mutual.sort(key=lambda row: (row['distance'], row['leftSourceGroupId'], row['rightSourceGroupId']))
limit = int(protocol['structuralTwinExperiment']['maximumFrozenPairs'])
mutual = mutual[:limit]
for i, row in enumerate(mutual, 1):
    row['twinRank'] = i

out_dir.mkdir(parents=True, exist_ok=True)
(out_dir / 'signed-relational-states.json').write_text(json.dumps(signed_rules, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')
with (out_dir / 'source-construction-regimes.jsonl').open('w', encoding='utf-8') as handle:
    for row in regime_rows:
        handle.write(json.dumps(row, separators=(',', ':'), ensure_ascii=False)+'\n')
with (out_dir / 'structural-twins.jsonl').open('w', encoding='utf-8') as handle:
    for row in mutual:
        handle.write(json.dumps(row, separators=(',', ':'), ensure_ascii=False)+'\n')

core = {
    'schema': 'mark_relational_state_discovery_v1',
    'experimentId': protocol['experimentId'],
    'parentAtlasSha256': atlas_summary['atlasSha256'],
    'parentBlindDiscoverySha256': discovery['blindDiscoverySha256'],
    'sourceHarvestSha256': atlas_summary.get('sourceHarvestSha256'),
    'provenanceAvailableDuringDiscovery': False,
    'theoryMode': protocol['theoryMode'],
    'signedRelationalStates': signed_rules,
    'constructionRegimes': {
        'eligibleSourceObjects': len(eligible),
        'featureRuleRanks': feature_ranks,
        'featureNames': feature_names,
        'featureMeans': dict(zip(feature_names, means)),
        'featureStandardDeviations': dict(zip(feature_names, stdevs)),
        'clusterSearch': cluster_quality,
        'chosenK': chosen_k,
        'chosenSilhouette': score,
        'regimes': regime_summary,
    },
    'structuralTwins': {
        'eligibleSourceObjects': len(eligible),
        'mutualCrossLanePairsFrozen': len(mutual),
        'crossLanePairComparisons': len(all_cross_distances),
        'distanceP01': all_cross_distances[max(0, int(0.01*len(all_cross_distances))-1)] if all_cross_distances else None,
        'distanceP05': all_cross_distances[max(0, int(0.05*len(all_cross_distances))-1)] if all_cross_distances else None,
        'distanceMedian': all_cross_distances[len(all_cross_distances)//2] if all_cross_distances else None,
    },
    'contract': {
        'usesOnlyPreviouslyFrozenAtlas': True,
        'noSourcePixelsRemeasured': True,
        'noProvenanceUsedToDefineStatesRegimesOrTwins': True,
        'negativeAndPositiveDeviationsTreatedSymmetrically': True,
        'clustersChosenWithoutInstitutionLabels': True,
        'twinsChosenAcrossAnonymousLanesBeforeProvenance': True,
        'allBlindProductsFrozenBeforeRejoin': True,
    },
}
sha = canonical_sha(core)
packet = {**core, 'relationalStateDiscoverySha256': sha}
(out_dir / 'relational-state-discovery.json').write_text(json.dumps(packet, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')
summary = {
    'schema': 'mark_relational_state_discovery_summary_v1',
    'relationalStateDiscoverySha256': sha,
    'parentAtlasSha256': atlas_summary['atlasSha256'],
    'signedStates': len(signed_rules),
    'strongAttractions': sum(1 for r in signed_rules if r['strongBlindState'] and r['state']=='attraction'),
    'strongExclusions': sum(1 for r in signed_rules if r['strongBlindState'] and r['state']=='exclusion'),
    'constructionRegimeK': chosen_k,
    'constructionRegimeSilhouette': score,
    'eligibleSourceObjects': len(eligible),
    'frozenStructuralTwins': len(mutual),
}
(out_dir / 'summary.json').write_text(json.dumps(summary, indent=2)+'\n', encoding='utf-8')
(out_dir / 'summary.txt').write_text('\n'.join(f'{k}={v}' for k,v in summary.items())+'\n', encoding='utf-8')
print(json.dumps(summary, indent=2))
