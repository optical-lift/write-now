#!/usr/bin/env python3
import hashlib
import json
import math
import os
import random
from collections import Counter, defaultdict
from pathlib import Path

obs_dir = Path(os.environ.get('MARK_OBSERVATION_RULE_ATLAS', 'artifacts/mark-observation-rule-atlas-v1'))
source_dir = Path(os.environ.get('MARK_SOURCE_RULE_ATLAS', 'artifact-staging/parent-atlas/source-rule-atlas'))
parent_state_dir = Path(os.environ.get('MARK_PARENT_RELATIONAL_STATE', 'artifact-staging/parent-state'))
protocol_path = Path(os.environ.get('MARK_LOCAL_STATE_PROTOCOL', 'research/mark/discovery-experiments/local-state-field-v1.protocol.json'))
out_dir = Path(os.environ.get('MARK_LOCAL_STATE_OUT', 'artifacts/mark-local-state-field-v1'))


def load_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def canonical_bytes(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode('utf-8')


def canonical_sha(value):
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def mean(xs):
    return sum(xs) / len(xs) if xs else 0.0


def stdev(xs):
    if len(xs) < 2:
        return 1.0
    m = mean(xs)
    v = sum((x-m)**2 for x in xs) / len(xs)
    return math.sqrt(v) or 1.0


def distance(a, b):
    return math.sqrt(sum((x-y)**2 for x, y in zip(a, b)))


def kmeans(points, k, max_iter=100):
    global_mean = [mean([p[d] for p in points]) for d in range(len(points[0]))]
    first = max(range(len(points)), key=lambda i: (distance(points[i], global_mean), tuple(points[i]), -i))
    chosen = [first]
    while len(chosen) < k:
        idx = max((i for i in range(len(points)) if i not in chosen), key=lambda i: (min(distance(points[i], points[j]) for j in chosen), tuple(points[i]), -i))
        chosen.append(idx)
    centroids = [list(points[i]) for i in chosen]
    assignments = None
    for _ in range(max_iter):
        new_assignments = [min(range(k), key=lambda j: (distance(p, centroids[j]), j)) for p in points]
        if assignments == new_assignments:
            break
        assignments = new_assignments
        next_centroids = []
        for j in range(k):
            members = [points[i] for i, a in enumerate(assignments) if a == j]
            if not members:
                return None
            next_centroids.append([mean([p[d] for p in members]) for d in range(len(points[0]))])
        centroids = next_centroids
    return assignments, centroids


def sampled_silhouette(points, assignments, k, ids, limit=1024):
    order = sorted(range(len(ids)), key=lambda i: hashlib.sha256(ids[i].encode()).hexdigest())[:min(limit, len(ids))]
    clusters = {c: [i for i in order if assignments[i] == c] for c in range(k)}
    if any(not clusters[c] for c in range(k)):
        return -1.0
    scores = []
    for i in order:
        own = assignments[i]
        own_members = [j for j in clusters[own] if j != i]
        a = mean([distance(points[i], points[j]) for j in own_members]) if own_members else 0.0
        b = min(mean([distance(points[i], points[j]) for j in clusters[c]]) for c in range(k) if c != own)
        denom = max(a, b)
        scores.append((b-a)/denom if denom else 0.0)
    return mean(scores)


def feature_vector(rule_map):
    a, b = rule_map[1], rule_map[2]
    c1, c2 = a['contextCount'], b['contextCount']
    return [a['accuracy'], b['accuracy'], math.log((c2+1.0)/(c1+1.0)), math.log(c1+c2+1.0)]


def state_entropy(counts, k):
    total = sum(counts)
    if total == 0 or k <= 1:
        return 0.0
    h = 0.0
    for count in counts:
        if count:
            p = count / total
            h -= p * math.log(p)
    return h / math.log(k)

protocol = load_json(protocol_path)
if protocol.get('schema') != 'mark_local_state_field_protocol_v1':
    raise RuntimeError('unexpected local state field protocol')
obs_summary = load_json(obs_dir / 'summary.json')
source_summary = load_json(source_dir / 'summary.json')
if obs_summary.get('schema') != 'mark_observation_rule_atlas_summary_v1':
    raise RuntimeError('unexpected observation atlas schema')
if source_summary.get('schema') != 'mark_source_rule_atlas_summary_v1':
    raise RuntimeError('unexpected source atlas schema')
if source_summary.get('atlasSha256') != protocol['parentEvidence']['sourceRuleAtlasSha256']:
    raise RuntimeError('wrong frozen parent source atlas')
if obs_summary.get('physicalLedgerMerkleRoot') != source_summary.get('physicalLedgerMerkleRoot'):
    raise RuntimeError('observation atlas did not reproduce parent physical ledger')

# Exact observation -> source aggregation proof.
source_expected = {}
with (source_dir / 'source-rule-atlas.jsonl').open(encoding='utf-8') as handle:
    for line in handle:
        if line.strip():
            r = json.loads(line)
            source_expected[(r['sourceGroupId'], int(r['blindRank']))] = (int(r['contextCount']), int(r['predictedOutcomeCount']))

observations = defaultdict(dict)
obs_meta = {}
source_actual = defaultdict(lambda: [0, 0])
with (obs_dir / 'observation-rule-atlas.jsonl').open(encoding='utf-8') as handle:
    for line in handle:
        if not line.strip():
            continue
        r = json.loads(line)
        oid, rank = r['observationId'], int(r['blindRank'])
        observations[oid][rank] = {
            'contextCount': int(r['contextCount']),
            'predictedOutcomeCount': int(r['predictedOutcomeCount']),
            'accuracy': float(r['accuracy']),
        }
        obs_meta[oid] = {
            'sourceGroupId': r['sourceGroupId'], 'lane': r['lane'], 'region': r['region'],
            'proposalKind': r.get('proposalKind',''), 'proposalScale': r.get('proposalScale','')
        }
        slot = source_actual[(r['sourceGroupId'], rank)]
        slot[0] += int(r['contextCount']); slot[1] += int(r['predictedOutcomeCount'])
if set(source_actual) != set(source_expected):
    raise RuntimeError('observation projection/source atlas key mismatch')
for key, expected in source_expected.items():
    if tuple(source_actual[key]) != expected:
        raise RuntimeError(f'observation projection fails exact source aggregation for {key}: {source_actual[key]} != {expected}')

feature_names = ['rule1Accuracy','rule2Accuracy','logRule2ToRule1ContextRatio','logTotalContextMass']
threshold_results = []
assignments_by_threshold = {}
for threshold in protocol['localStateDiscovery']['minimumContextMasses']:
    ids = sorted(oid for oid, rules in observations.items() if 1 in rules and 2 in rules and rules[1]['contextCount'] + rules[2]['contextCount'] >= threshold)
    raw = {oid: feature_vector(observations[oid]) for oid in ids}
    means = [mean([raw[oid][d] for oid in ids]) for d in range(4)]
    sds = [stdev([raw[oid][d] for oid in ids]) for d in range(4)]
    z = {oid: [(raw[oid][d]-means[d])/sds[d] for d in range(4)] for oid in ids}
    points = [z[oid] for oid in ids]
    candidates = []
    for k in protocol['localStateDiscovery']['candidateK']:
        if k >= len(points):
            continue
        result = kmeans(points, k)
        if result is None:
            continue
        assignments, centroids = result
        sizes = [assignments.count(j) for j in range(k)]
        if min(sizes) < 8:
            continue
        score = sampled_silhouette(points, assignments, k, ids)
        candidates.append((score, k, assignments, centroids, sizes))
    if not candidates:
        raise RuntimeError(f'no valid local state solution at threshold {threshold}')
    score, k, assignments, centroids, sizes = max(candidates, key=lambda row: (row[0], -row[1]))
    # Stable ids: endpoint-heavy / low rule1 coordinates sort first, then remaining centroid coordinates.
    order = sorted(range(k), key=lambda j: (centroids[j][2], centroids[j][0], centroids[j][1], tuple(centroids[j])))
    remap = {old: new+1 for new, old in enumerate(order)}
    mapped = {oid: remap[assignments[i]] for i, oid in enumerate(ids)}
    assignments_by_threshold[int(threshold)] = mapped
    centroids_raw = []
    for state_id in range(1, k+1):
        members = [oid for oid in ids if mapped[oid] == state_id]
        centroids_raw.append({
            'stateId': state_id,
            'observations': len(members),
            'centroid': {feature_names[d]: mean([raw[oid][d] for oid in members]) for d in range(4)}
        })
    threshold_results.append({
        'minimumContextMass': threshold, 'eligibleObservations': len(ids), 'chosenK': k,
        'sampledSilhouette': score, 'stateSizes': [sum(1 for x in mapped.values() if x == state_id) for state_id in range(1,k+1)],
        'states': centroids_raw,
        'candidateScores': [{'k': row[1], 'sampledSilhouette': row[0], 'sizes': row[4]} for row in sorted(candidates, key=lambda x:x[1])]
    })

primary_threshold = int(protocol['localStateDiscovery']['primaryDepth'])
primary = next(row for row in threshold_results if int(row['minimumContextMass']) == primary_threshold)
state_map = assignments_by_threshold[primary_threshold]
k = int(primary['chosenK'])

# Freeze observation states and source mixtures.
out_dir.mkdir(parents=True, exist_ok=True)
with (out_dir / 'observation-local-states.jsonl').open('w', encoding='utf-8') as handle:
    for oid in sorted(state_map):
        m = obs_meta[oid]
        row = {'schema':'mark_observation_local_state_v1','observationId':oid,'sourceGroupId':m['sourceGroupId'],'lane':m['lane'],'stateId':state_map[oid],'region':m['region'],'proposalKind':m['proposalKind'],'proposalScale':m['proposalScale'],'features':dict(zip(feature_names, feature_vector(observations[oid])))}
        handle.write(json.dumps(row, separators=(',',':'), ensure_ascii=False)+'\n')

source_obs = defaultdict(list)
for oid, state in state_map.items():
    source_obs[obs_meta[oid]['sourceGroupId']].append((oid,state))
source_mixtures = {}
mixture_rows = []
for source, items in sorted(source_obs.items()):
    counts = [sum(1 for _,state in items if state == sid) for sid in range(1,k+1)]
    proportions = [c/len(items) for c in counts]
    source_mixtures[source] = proportions
    mixture_rows.append({'schema':'mark_source_local_state_mixture_v1','sourceGroupId':source,'lane':obs_meta[items[0][0]]['lane'],'eligibleObservations':len(items),'stateCounts':counts,'stateProportions':proportions,'normalizedEntropy':state_entropy(counts,k),'mixedStates':sum(c>0 for c in counts)>1})
with (out_dir / 'source-local-state-mixtures.jsonl').open('w', encoding='utf-8') as handle:
    for row in mixture_rows:
        handle.write(json.dumps(row, separators=(',',':'))+'\n')

multi = [row for row in mixture_rows if row['eligibleObservations'] >= 2]
mixture_summary = {
    'sourcesWithAtLeastTwoEligibleObservations': len(multi),
    'mixedStateSources': sum(1 for row in multi if row['mixedStates']),
    'mixedStateFraction': mean([1.0 if row['mixedStates'] else 0.0 for row in multi]),
    'meanNormalizedEntropy': mean([row['normalizedEntropy'] for row in multi]),
}

# Spatial nearest-neighbor concordance, null by within-source state shuffles.
observed_same = 0; observed_edges = 0
source_edges = {}
for source, items in source_obs.items():
    if len(items) < 2:
        continue
    centers = {}
    for oid, _ in items:
        r = obs_meta[oid]['region']; centers[oid] = (r['x']+r['width']/2, r['y']+r['height']/2)
    edges = []
    for oid, state in items:
        x,y = centers[oid]
        mate = min((other for other,_ in items if other != oid), key=lambda other: ((x-centers[other][0])**2+(y-centers[other][1])**2, other))
        pair = tuple(sorted((oid,mate)))
        if pair not in edges:
            edges.append(pair)
    source_edges[source] = edges
    for a,b in edges:
        observed_edges += 1; observed_same += int(state_map[a] == state_map[b])
observed_fraction = observed_same/observed_edges if observed_edges else 0.0
nulls = []
for iteration in range(64):
    same=0; total=0
    for source, edges in source_edges.items():
        ids = [oid for oid,_ in source_obs[source]]
        labels = [state_map[oid] for oid in ids]
        seed = int(hashlib.sha256(f'local-state-spatial|{source}|{iteration}'.encode()).hexdigest()[:16],16)
        rnd = random.Random(seed); rnd.shuffle(labels)
        perm = dict(zip(ids,labels))
        for a,b in edges:
            total += 1; same += int(perm[a] == perm[b])
    nulls.append(same/total if total else 0.0)
spatial = {'edges':observed_edges,'observedSameStateFraction':observed_fraction,'nullMean':mean(nulls),'nullMinimum':min(nulls) if nulls else 0.0,'nullMaximum':max(nulls) if nulls else 0.0,'liftOverNullMean':observed_fraction-mean(nulls),'observedAboveAllNulls':bool(nulls) and observed_fraction>max(nulls)}

# Reconstruct frozen source-level regimes from local-state mixture only.
parent_regimes = {}
with (parent_state_dir / 'source-construction-regimes.jsonl').open(encoding='utf-8') as handle:
    for line in handle:
        if line.strip():
            r=json.loads(line); parent_regimes[r['sourceGroupId']] = int(r['regimeId'])
common = sorted(set(source_mixtures) & set(parent_regimes))
regime_ids = sorted(set(parent_regimes[s] for s in common))
centroids = {rid:[mean([source_mixtures[s][d] for s in common if parent_regimes[s]==rid]) for d in range(k)] for rid in regime_ids}
correct=0
for source in common:
    truth=parent_regimes[source]
    # Leave-one-out centroid for truth regime; fixed other regime centroids.
    local_centroids={}
    for rid in regime_ids:
        members=[s for s in common if parent_regimes[s]==rid and s!=source]
        local_centroids[rid]=[mean([source_mixtures[s][d] for s in members]) for d in range(k)] if members else centroids[rid]
    pred=min(regime_ids,key=lambda rid:(distance(source_mixtures[source],local_centroids[rid]),rid))
    correct += int(pred==truth)
regime_composition = {'sourcesCompared':len(common),'sourceRegimes':regime_ids,'meanLocalStateMixtureBySourceRegime':{str(rid):centroids[rid] for rid in regime_ids},'leaveOneOutNearestMixtureCentroidAccuracy':correct/len(common) if common else 0.0}

# Are the already-frozen structural twins also unusually close in local-state mixture?
twins=[]
with (parent_state_dir / 'structural-twins.jsonl').open(encoding='utf-8') as handle:
    for line in handle:
        if line.strip(): twins.append(json.loads(line))
lanes = {row['sourceGroupId']:row['lane'] for row in mixture_rows}
background=[]
sources=sorted(source_mixtures)
for i,left in enumerate(sources):
    for right in sources[i+1:]:
        if lanes[left] != lanes[right]: background.append(distance(source_mixtures[left],source_mixtures[right]))
background.sort()
twin_dist=[]
for twin in twins:
    a=twin['leftSourceGroupId']; b=twin['rightSourceGroupId']
    if a in source_mixtures and b in source_mixtures: twin_dist.append(distance(source_mixtures[a],source_mixtures[b]))
def percentile(values,x):
    if not values:return 1.0
    import bisect
    return bisect.bisect_right(values,x)/len(values)
twin_depth={'frozenTwinsWithLocalMixtures':len(twin_dist),'medianTwinLocalStateDistance':sorted(twin_dist)[len(twin_dist)//2] if twin_dist else None,'meanTwinLocalStateDistance':mean(twin_dist),'backgroundCrossLanePairs':len(background),'backgroundMedianDistance':background[len(background)//2] if background else None,'medianTwinDistancePercentile':percentile(background,sorted(twin_dist)[len(twin_dist)//2]) if twin_dist else None}

core={
    'schema':'mark_local_state_field_discovery_v1','experimentId':protocol['experimentId'],'parentObservationAtlasSha256':obs_summary['observationAtlasSha256'],'parentSourceAtlasSha256':source_summary['atlasSha256'],'provenanceAvailableDuringDiscovery':False,
    'exactObservationToSourceAggregation':True,'thresholdRobustness':threshold_results,'primaryThreshold':primary_threshold,'primaryLocalStates':k,'withinSourceMixture':mixture_summary,'spatialOrganization':spatial,'sourceRegimeComposition':regime_composition,'structuralTwinDepth':twin_depth,
    'contract':{'localStatesDiscoveredWithoutSourceRegimeLabels':True,'sourceRegimesUsedOnlyAfterLocalStateFreeze':True,'structuralTwinsPreviouslyFrozen':True,'noProvenanceUsed':True,'theoryTestedRatherThanSuppressed':True}
}
sha=canonical_sha(core); packet={**core,'localStateFieldDiscoverySha256':sha}
(out_dir/'local-state-field-discovery.json').write_text(json.dumps(packet,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
(out_dir/'summary.txt').write_text('\n'.join([
    f'local_state_field_sha256={sha}',f'primary_threshold={primary_threshold}',f'primary_local_states={k}',f'eligible_observations={primary["eligibleObservations"]}',f'mixed_source_fraction={mixture_summary["mixedStateFraction"]}',f'spatial_same_state_lift={spatial["liftOverNullMean"]}',f'spatial_above_all_nulls={spatial["observedAboveAllNulls"]}',f'source_regime_from_local_mixture_accuracy={regime_composition["leaveOneOutNearestMixtureCentroidAccuracy"]}',f'twin_median_local_state_distance_percentile={twin_depth["medianTwinDistancePercentile"]}'
])+'\n',encoding='utf-8')
print(json.dumps(packet,indent=2,ensure_ascii=False))
