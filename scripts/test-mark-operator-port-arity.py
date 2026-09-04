#!/usr/bin/env python3
import json, math, os, statistics, hashlib
from pathlib import Path

PROTO=Path(os.environ.get('MARK_OPERATOR_PROTOCOL','research/mark/discovery-experiments/operator-port-arity-v1.protocol.json'))
CORR=Path(os.environ.get('MARK_OPERATOR_CORR','artifact-staging/operator-port/correspondence'))
LABELS=Path(os.environ.get('MARK_OPERATOR_LABELS','artifact-staging/operator-port/labels'))
OUT=Path(os.environ.get('MARK_OPERATOR_OUT','artifacts/mark-operator-port-arity-v1'))
OUT.mkdir(parents=True,exist_ok=True)
p=json.loads(PROTO.read_text())
freeze=json.loads((CORR/'correspondence-freeze.json').read_text())
label_custody=json.loads((LABELS/'label-custody.json').read_text())
assert freeze['criticalCenterCorrespondenceSha256']==p['inputs']['expectedCorrespondenceSha256']
assert label_custody['labelsSha256']==p['inputs']['expectedLabelsSha256']
labels={r['pairId']:r['label'] for r in map(json.loads,(LABELS/'pair-labels.jsonl').read_text().splitlines())}
rows=[]
for r in map(json.loads,(CORR/'correspondence-pairs.jsonl').read_text().splitlines()):
    if r['pairId'] not in labels: raise RuntimeError('missing label '+r['pairId'])
    rows.append({'pairId':r['pairId'],'lane':r['lane'],'y':1 if labels[r['pairId']]=='preserved' else 0,**r['metrics']})

def fit(features):
    tr=[r for r in rows if r['lane']==p['model']['trainLane']]
    means={f:statistics.mean(r[f] for r in tr) for f in features}
    sds={f:(statistics.pstdev(r[f] for r in tr) or 1.0) for f in features}
    w=[0.0]*(len(features)+1); n1=sum(r['y'] for r in tr); n0=len(tr)-n1
    for it in range(p['model']['iterations']):
        g=[0.0]*len(w)
        for r in tr:
            x=[(r[f]-means[f])/sds[f] for f in features]
            z=w[0]+sum(w[i+1]*x[i] for i in range(len(x)))
            q=1/(1+math.exp(-max(-30,min(30,z))))
            cw=len(tr)/(2*(n1 if r['y'] else n0)); e=(q-r['y'])*cw
            g[0]+=e
            for i,v in enumerate(x): g[i+1]+=e*v
        lr=p['model']['baseLearningRate']/(1+it/1500)
        for i in range(len(w)): w[i]-=lr*g[i]/len(tr)
    return {'features':features,'weights':w,'means':means,'sds':sds}

def score(r,m):
    z=m['weights'][0]
    for i,f in enumerate(m['features']): z+=m['weights'][i+1]*(r[f]-m['means'][f])/m['sds'][f]
    return 1/(1+math.exp(-max(-30,min(30,z))))
def auc(rs,m):
    pos=[score(r,m) for r in rs if r['y']==1]; neg=[score(r,m) for r in rs if r['y']==0]
    return sum((a>b)+0.5*(a==b) for a in pos for b in neg)/(len(pos)*len(neg))

typed=fit(p['typedFeatures']); geom=fit(p['geometryComparatorFeatures'])
metrics={}
for lane in ['train','holdout','control']:
    rs=[r for r in rows if r['lane']==lane]
    metrics[lane]={'pairs':len(rs),'preserved':sum(r['y'] for r in rs),'typedAuc':auc(rs,typed),'geometryAuc':auc(rs,geom)}
    metrics[lane]['typedMinusGeometry']=metrics[lane]['typedAuc']-metrics[lane]['geometryAuc']
g=p['gates']
passed=(metrics['holdout']['typedAuc']>=g['typedHoldoutAucMinimum'] and metrics['control']['typedAuc']>=g['typedControlAucMinimum'] and metrics['holdout']['typedMinusGeometry']>=g['typedMinusGeometryHoldoutMinimum'] and metrics['control']['typedMinusGeometry']>=g['typedMinusGeometryControlMinimum'])
result={'schema':'mark_operator_port_arity_result_v1','experimentId':p['experimentId'],'passed':passed,'metrics':metrics,'typedModel':typed,'geometryModel':geom,'scientificFailureIsGreen':True}
raw=json.dumps(result,sort_keys=True,separators=(',',':')).encode(); result['resultSha256']=hashlib.sha256(raw).hexdigest()
(OUT/'result.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
summary=['# Mark operator / port / arity v1','',f"Result: **{'PASS' if passed else 'FAIL'}**",'']
for lane in ['train','holdout','control']:
    m=metrics[lane]; summary.append(f"- {lane}: typed AUC {m['typedAuc']:.3f}; geometry AUC {m['geometryAuc']:.3f}; advantage {m['typedMinusGeometry']:+.3f}; {m['preserved']}/{m['pairs']} preserved")
summary += ['', 'Interpretation: typed critical-structure survival, endpoint/junction identity, degree and arm-class mutation are compared against residual geometric realization using Cleveland only for fitting and unchanged transfer to Bavaria and LOC.', '', f"Result SHA-256: `{result['resultSha256']}`"]
(OUT/'summary.md').write_text('\n'.join(summary)+'\n')
print('\n'.join(summary))
