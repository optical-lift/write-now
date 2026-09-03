#!/usr/bin/env python3
import hashlib, json, math, os, statistics
from collections import Counter, defaultdict
from pathlib import Path

protocol_path=Path(os.environ.get('MARK_EDIT_PROTOCOL','research/mark/discovery-experiments/topology-edit-invariance-v3.protocol.json'))
v2_dir=Path(os.environ.get('MARK_SIBLING_ROLE_V2','artifact-staging/sibling-role-v2'))
out_dir=Path(os.environ.get('MARK_ROLE_PAIR_OUT','artifacts/mark-role-pair-freeze-v3'))

def load_json(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def canonical_sha(v): return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
def distance(a,b): return math.sqrt(sum((x-y)**2 for x,y in zip(a,b)))

def locate(name):
    hits=list(v2_dir.rglob(name))
    if len(hits)!=1: raise RuntimeError(f'expected exactly one {name}, found {len(hits)}')
    return hits[0]

def source_balanced(rows,family,lane):
    by_source=defaultdict(list)
    for r in rows:
        if r['occupantFamily']==family and r['lane']==lane: by_source[r['sourceGroupId']].append(r)
    out=[]
    for source,items in sorted(by_source.items()):
        out.append(min(items,key=lambda r:(hashlib.sha256(f"sibling-role-representative|{lane}|{family}|{source}|{r['observationId']}".encode()).hexdigest(),r['observationId'])))
    return out

def reciprocal(left,right,key):
    def nearest(a_rows,b_rows):
        out={}
        for a in a_rows:
            eligible=[b for b in b_rows if b['sourceGroupId']!=a['sourceGroupId']]
            if not eligible: continue
            b=min(eligible,key=lambda x:(distance(a[key],x[key]),x['sourceGroupId'],x['observationId']))
            out[a['observationId']]=b['observationId']
        return out
    ab=nearest(left,right); ba=nearest(right,left)
    return {(a,b) for a,b in ab.items() if ba.get(b)==a}

protocol=load_json(protocol_path)
if protocol.get('schema')!='mark_topology_edit_invariance_protocol_v3': raise RuntimeError('unexpected v3 protocol')
vocab=load_json(locate('sibling-role-vocabulary.json')); sub=load_json(locate('sibling-role-substitution.json'))
vocab_sha=vocab.get('siblingRoleVocabularySha256'); sub_sha=sub.get('siblingRoleSubstitutionDiscoverySha256')
if canonical_sha({k:v for k,v in vocab.items() if k!='siblingRoleVocabularySha256'})!=vocab_sha: raise RuntimeError('v2 vocabulary SHA mismatch')
if canonical_sha({k:v for k,v in sub.items() if k!='siblingRoleSubstitutionDiscoverySha256'})!=sub_sha: raise RuntimeError('v2 substitution SHA mismatch')
if sub.get('parentSiblingRoleVocabularySha256')!=vocab_sha: raise RuntimeError('v2 substitution/vocabulary mismatch')
if vocab.get('provenanceAvailableDuringDiscovery') or sub.get('provenanceAvailableDuringDiscovery'): raise RuntimeError('v2 was not blind')
role_path=locate('masked-sibling-role-vectors.jsonl'); occ_path=locate('occupant-assignments.jsonl')
role_bytes=role_path.read_bytes(); occ_bytes=occ_path.read_bytes()
if hashlib.sha256(role_bytes).hexdigest()!=vocab['assignmentFiles']['maskedRoleVectorsSha256']: raise RuntimeError('role vectors SHA mismatch')
if hashlib.sha256(occ_bytes).hexdigest()!=vocab['assignmentFiles']['occupantAssignmentsSha256']: raise RuntimeError('occupant assignments SHA mismatch')
roles={json.loads(x)['observationId']:json.loads(x) for x in role_bytes.splitlines() if x.strip()}
occs={json.loads(x)['observationId']:json.loads(x) for x in occ_bytes.splitlines() if x.strip()}
if set(roles)!=set(occs): raise RuntimeError('v2 role/occupant observation mismatch')
rows=[]
for oid in sorted(roles):
    r=roles[oid]; o=occs[oid]
    if r['sourceGroupId']!=o['sourceGroupId'] or r['lane']!=o['lane']: raise RuntimeError(f'v2 custody mismatch {oid}')
    rows.append({**r,'occupantFamily':int(o['occupantFamily'])})
families=sorted(map(int,vocab['occupantVocabulary']['centroids'].keys()))
mult=int(protocol['rolePairFreeze']['negativeMultiplierPerPositive'])
pair_rows=[]; summary_by_lane={}
for lane in ('train','holdout','control'):
    lane_counts=Counter()
    for ai,a in enumerate(families):
        for b in families[ai+1:]:
            A=source_balanced(rows,a,lane); B=source_balanced(rows,b,lane)
            g=reciprocal(A,B,'geometryVector'); u=reciprocal(A,B,'augmentedVector'); positives=sorted(g & u)
            if not positives: continue
            by_id={r['observationId']:r for r in A+B}
            possible=[]
            posset=set(positives)
            for ar in A:
                for br in B:
                    if ar['sourceGroupId']==br['sourceGroupId'] or (ar['observationId'],br['observationId']) in posset: continue
                    dg=distance(ar['geometryVector'],br['geometryVector']); da=distance(ar['augmentedVector'],br['augmentedVector'])
                    possible.append((dg,da,ar,br))
            if not possible: continue
            mg=statistics.median(x[0] for x in possible); ma=statistics.median(x[1] for x in possible)
            hard=[x for x in possible if x[0]>=mg and x[1]>=ma]
            hard.sort(key=lambda x:(hashlib.sha256(f"edit-neg|{lane}|{a}|{b}|{x[2]['observationId']}|{x[3]['observationId']}".encode()).hexdigest(),x[2]['observationId'],x[3]['observationId']))
            negatives=hard[:len(positives)*mult]
            for oa,ob in positives:
                ar,br=by_id[oa],by_id[ob]
                pair_rows.append({'schema':'mark_role_pair_label_v3','lane':lane,'occupantFamilyA':a,'occupantFamilyB':b,'observationA':oa,'observationB':ob,'sourceGroupA':ar['sourceGroupId'],'sourceGroupB':br['sourceGroupId'],'label':'preserved','geometryDistance':distance(ar['geometryVector'],br['geometryVector']),'augmentedDistance':distance(ar['augmentedVector'],br['augmentedVector'])})
                lane_counts[(a,b,'preserved')]+=1
            for dg,da,ar,br in negatives:
                pair_rows.append({'schema':'mark_role_pair_label_v3','lane':lane,'occupantFamilyA':a,'occupantFamilyB':b,'observationA':ar['observationId'],'observationB':br['observationId'],'sourceGroupA':ar['sourceGroupId'],'sourceGroupB':br['sourceGroupId'],'label':'broken','geometryDistance':dg,'augmentedDistance':da})
                lane_counts[(a,b,'broken')]+=1
    summary_by_lane[lane]=[{'occupantFamilyA':a,'occupantFamilyB':b,'preserved':lane_counts[(a,b,'preserved')],'broken':lane_counts[(a,b,'broken')]} for a in families for b in families if a<b and (lane_counts[(a,b,'preserved')] or lane_counts[(a,b,'broken')])]

out_dir.mkdir(parents=True,exist_ok=True); rows_path=out_dir/'role-pair-labels.jsonl'; h=hashlib.sha256()
with rows_path.open('wb') as f:
    for r in pair_rows:
        b=json.dumps(r,separators=(',',':'),ensure_ascii=False).encode()+b'\n'; f.write(b); h.update(b)
core={'schema':'mark_role_pair_freeze_v3','experimentId':protocol['experimentId'],'parentSiblingRoleVocabularySha256':vocab_sha,'parentSiblingRoleSubstitutionSha256':sub_sha,'physicalLedgerMerkleRoot':vocab['physicalLedgerMerkleRoot'],'sourceBlindInputSha256':vocab['sourceBlindInputSha256'],'topologyRowsSha256':vocab['topologyRowsSha256'],'rolePairRowsSha256':h.hexdigest(),'rows':len(pair_rows),'laneFamilyPairCounts':summary_by_lane,'contract':{'topologyAvailableDuringRolePairFreeze':False,'rolePairLabelsUseOnlyFrozenMaskedRoleVectors':True,'positiveRequiresReciprocalNearestInBothRoleSpaces':True,'negativesMatchedWithinFamilyPairAndLane':True,'negativeSelectionUsesOnlyRoleDistance':True,'noStateVocabularyConsumed':True,'noTransitionGrammarConsumed':True,'noProvenanceConsumed':True}}
digest=canonical_sha(core); packet={**core,'rolePairFreezeSha256':digest}
(out_dir/'role-pair-freeze.json').write_text(json.dumps(packet,indent=2)+'\n')
lines=[f'role_pair_freeze_sha256={digest}',f'rows={len(pair_rows)}']
for lane in ('train','holdout','control'):
    p=sum(x['preserved'] for x in summary_by_lane[lane]); n=sum(x['broken'] for x in summary_by_lane[lane]); lines.append(f'{lane}_preserved={p}'); lines.append(f'{lane}_broken={n}')
(out_dir/'summary.txt').write_text('\n'.join(lines)+'\n')
print(json.dumps(packet,indent=2))
