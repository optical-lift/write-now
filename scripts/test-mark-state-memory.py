#!/usr/bin/env python3
import json, math, os, random, hashlib
from pathlib import Path

PROTO=Path(os.environ.get('MARK_MEMORY_PROTOCOL','research/mark/discovery-experiments/state-memory-v1.protocol.json'))
STATE=Path(os.environ.get('MARK_MEMORY_STATE','artifact-staging/state-memory/state'))
OUT=Path(os.environ.get('MARK_MEMORY_OUT','artifacts/mark-state-memory-v1'))
OUT.mkdir(parents=True,exist_ok=True)
p=json.loads(PROTO.read_text())
disc=json.loads((STATE/'state-transition-grammar-discovery.json').read_text())
assert disc['stateTransitionGrammarDiscoverySha256']==p['input']['expectedDiscoverySha256']
rows=[json.loads(x) for x in (STATE/'source-transition-profiles.jsonl').read_text().splitlines() if x.strip()]
states=['1','2','3']; alpha=0.5

def fit(train):
    first={(b,c):0 for b in states for c in states}; second={(a,b,c):0 for a in states for b in states for c in states}
    for r in train:
        for motif,n in r['programCounts'].items():
            a,b,c=motif.split('->'); first[(b,c)]+=n; second[(a,b,c)]+=n
    p1={}; p2={}
    for b in states:
        den=sum(first[(b,c)] for c in states)+alpha*3
        for c in states:p1[(b,c)]=(first[(b,c)]+alpha)/den
    for a in states:
        for b in states:
            den=sum(second[(a,b,c)] for c in states)+alpha*3
            for c in states:p2[(a,b,c)]=(second[(a,b,c)]+alpha)/den
    return p1,p2

def score(rs,p1,p2):
    loss1=loss2=n=0.0
    for r in rs:
        for motif,count in r['programCounts'].items():
            if not count: continue
            a,b,c=motif.split('->'); n+=count
            loss1-=count*math.log2(p1[(b,c)]); loss2-=count*math.log2(p2[(a,b,c)])
    return {'programEvents':int(n),'firstOrderBits':loss1/n,'secondOrderBits':loss2/n,'historyGainBits':(loss1-loss2)/n}

train=[r for r in rows if r['lane']=='train']; p1,p2=fit(train)
rng=random.Random(p['bootstrap']['seed']); lane_results={}
for lane in ['train','holdout','control']:
    rs=[r for r in rows if r['lane']==lane]; base=score(rs,p1,p2); gains=[]
    for _ in range(p['bootstrap']['iterations']):
        sample=[rs[rng.randrange(len(rs))] for __ in range(len(rs))]
        gains.append(score(sample,p1,p2)['historyGainBits'])
    base['sources']=len(rs); base['bootstrapPositiveFraction']=sum(x>0 for x in gains)/len(gains); base['bootstrapMinimum']=min(gains); base['bootstrapMaximum']=max(gains)
    lane_results[lane]=base
passed=all(lane_results[l]['historyGainBits']>0 and lane_results[l]['bootstrapPositiveFraction']>=p['bootstrap']['successFraction'] for l in ['train','holdout','control'])
conditional={'firstOrder':{f'{b}->{c}':p1[(b,c)] for b in states for c in states},'secondOrder':{f'{a}->{b}->{c}':p2[(a,b,c)] for a in states for b in states for c in states}}
result={'schema':'mark_state_memory_result_v1','experimentId':p['experimentId'],'passed':passed,'lanes':lane_results,'conditionalProbabilitiesFromTrain':conditional,'scientificFailureIsGreen':True}
raw=json.dumps(result,sort_keys=True,separators=(',',':')).encode(); result['resultSha256']=hashlib.sha256(raw).hexdigest()
(OUT/'result.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
summary=['# Mark state memory / execution history v1','',f"Result: **{'PASS' if passed else 'FAIL'}**",'']
for lane in ['train','holdout','control']:
    r=lane_results[lane]; summary.append(f"- {lane}: current-only {r['firstOrderBits']:.4f} bits; +previous-state {r['secondOrderBits']:.4f}; gain {r['historyGainBits']:+.4f} bits/event; bootstrap positive {r['bootstrapPositiveFraction']:.3f} across {r['sources']} sources")
summary += ['', f"Train P(1 next | current 1) = {p1[('1','1')]:.3f}; P(1 next | previous 2,current 1) = {p2[('2','1','1')]:.3f}.", f"Train P(3 next | current 3) = {p1[('3','3')]:.3f}; P(3 next | previous 2,current 3) = {p2[('2','3','3')]:.3f}.", '', 'Interpretation: the gate concerns predictive information from structural history, not whether any particular transition should be named ENTER or COMMIT. Those operator names remain theory until separately identified.', '', f"Result SHA-256: `{result['resultSha256']}`"]
(OUT/'summary.md').write_text('\n'.join(summary)+'\n'); print('\n'.join(summary))
