#!/usr/bin/env python3
import hashlib, json, math, os, random
from collections import Counter, defaultdict
from pathlib import Path

protocol_path = Path(os.environ.get("MARK_OPERATOR_PROTOCOL", "research/mark/discovery-experiments/state-operator-discovery-v1.protocol.json"))
topology_dir = Path(os.environ.get("MARK_TOPOLOGY_ATLAS", "artifacts/mark-observation-topology-atlas-v1"))
field_dir = Path(os.environ.get("MARK_LOCAL_STATE_FIELD", "artifact-staging/local-state-field"))
transition_dir = Path(os.environ.get("MARK_TRANSITION_GRAMMAR", "artifact-staging/transition-grammar"))
out_dir = Path(os.environ.get("MARK_OPERATOR_OUT", "artifacts/mark-state-operator-discovery-v1"))

def load_json(path): return json.loads(Path(path).read_text(encoding="utf-8"))
def canonical_bytes(value): return json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()
def canonical_sha(value): return hashlib.sha256(canonical_bytes(value)).hexdigest()
def mean(xs): return sum(xs)/len(xs) if xs else 0.0
def stdev(xs):
    if not xs: return 0.0
    m=mean(xs); return math.sqrt(mean([(x-m)**2 for x in xs]))
def area(r): return max(1,int(r["width"])*int(r["height"]))
def center(r): return (r["x"]+r["width"]/2.0,r["y"]+r["height"]/2.0)
def contains(parent,child):
    return area(parent)>area(child) and parent["x"]<=child["x"] and parent["y"]<=child["y"] and parent["x"]+parent["width"]>=child["x"]+child["width"] and parent["y"]+parent["height"]>=child["y"]+child["height"]
def distance(a,b): return math.sqrt(sum((x-y)**2 for x,y in zip(a,b)))

protocol=load_json(protocol_path)
if protocol.get("schema")!="mark_state_operator_discovery_protocol_v1": raise RuntimeError("unexpected operator protocol")
field=load_json(field_dir/"local-state-field-discovery.json")
if field.get("localStateFieldDiscoverySha256")!=protocol["parentEvidence"]["localStateFieldDiscoverySha256"]: raise RuntimeError("wrong local-state parent")
transition=load_json(transition_dir/"state-transition-grammar-discovery.json")
if transition.get("stateTransitionGrammarDiscoverySha256")!=protocol["parentEvidence"]["stateTransitionGrammarDiscoverySha256"]: raise RuntimeError("wrong transition parent")
if transition.get("provenanceAvailableDuringDiscovery"): raise RuntimeError("transition parent was not blind")
topo_summary=load_json(topology_dir/"summary.json")
if not topo_summary.get("contract",{}).get("noProvenanceConsumed"): raise RuntimeError("topology atlas provenance contract failed")
compiler_custody=load_json(field_dir/"compiler-custody"/"custody.json")
if topo_summary["physicalLedgerMerkleRoot"]!=compiler_custody["physicalLedger"]["merkleRoot"]: raise RuntimeError("topology atlas physical Merkle mismatch")

states={}
with (field_dir/"observation-local-states.jsonl").open(encoding="utf-8") as h:
    for line in h:
        if line.strip():
            r=json.loads(line); states[r["observationId"]]=r

topology={}
with (topology_dir/"observation-topology-atlas.jsonl").open(encoding="utf-8") as h:
    for line in h:
        if line.strip():
            r=json.loads(line); topology[r["observationId"]]=r
if set(states)!=set(topology): raise RuntimeError(f"state/topology observation mismatch: {len(states)} vs {len(topology)}")

by_source=defaultdict(list)
for r in states.values(): by_source[r["sourceGroupId"]].append(r)
parent={}
for source,items in by_source.items():
    for child in items:
        candidates=[p for p in items if p["observationId"]!=child["observationId"] and contains(p["region"],child["region"])]
        if candidates:
            p=min(candidates,key=lambda x:(area(x["region"]),x["observationId"]))
            parent[child["observationId"]]=p["observationId"]

def normalized_features(row):
    centers=max(1,int(row["centerCount"])); out={}
    for k,v in row["countFeatures"].items(): out[k]=float(v)/centers
    out["derived:centerDensityPerMillionPixelsLog1p"]=math.log1p(float(row["centerCount"])*1_000_000.0/area(row["region"]))
    return out
norm={oid:normalized_features(r) for oid,r in topology.items()}

def geometry_features(p,c):
    pr,cr=p["region"],c["region"]; pc=center(pr); cc=center(cr)
    return {
      "geometry:logAreaRatio":math.log(area(cr)/area(pr)),
      "geometry:dxParentWidth":(cc[0]-pc[0])/max(1.0,pr["width"]),
      "geometry:dyParentHeight":(cc[1]-pc[1])/max(1.0,pr["height"]),
      "geometry:aspectDelta":math.log((cr["width"]/max(1.0,cr["height"]))/(pr["width"]/max(1.0,pr["height"]))),
    }

edges=[]
for child_id,parent_id in parent.items():
    p=states[parent_id]; c=states[child_id]
    if int(p["stateId"])!=2: continue
    if p["sourceGroupId"]!=c["sourceGroupId"] or p["lane"]!=c["lane"]: raise RuntimeError("containment edge crossed custody boundary")
    pf,cf=norm[parent_id],norm[child_id]
    keys=set(pf)|set(cf)
    delta={k:cf.get(k,0.0)-pf.get(k,0.0) for k in keys}
    geom=geometry_features(p,c)
    edge_id="O"+hashlib.sha256(f"{p['sourceGroupId']}|{parent_id}|{child_id}".encode()).hexdigest()[:20]
    edges.append({
      "edgeId":edge_id,"sourceGroupId":p["sourceGroupId"],"lane":p["lane"],
      "parentObservationId":parent_id,"childObservationId":child_id,"childState":int(c["stateId"]),
      "parentProposalScale":p.get("proposalScale",""),"parentRegion":p["region"],"childRegion":c["region"],
      "topologyDelta":delta,"geometry":geom
    })
if not edges: raise RuntimeError("no State 2 branch edges")
labels=[1,2,3]
train=[e for e in edges if e["lane"]=="train"]
if not train or set(e["childState"] for e in train)!=set(labels): raise RuntimeError("train lane lacks a State 2 branch outcome")

# Dynamic center signatures must earn their vocabulary from training edges only.
signature_support=Counter()
for e in train:
    for k,v in e["topologyDelta"].items():
        if k.startswith("signature:") and abs(v)>1e-15: signature_support[k]+=1
min_sig=int(protocol["featureDiscovery"]["minimumTrainTransitionSupportForDynamicCenterSignature"])
all_non_signature=sorted({k for e in train for k in e["topologyDelta"] if not k.startswith("signature:")})
eligible=all_non_signature+sorted(k for k,n in signature_support.items() if n>=min_sig)

def anova_score(feature):
    vals=[e["topologyDelta"].get(feature,0.0) for e in train]; overall=mean(vals)
    between=0.0; within=0.0
    for label in labels:
        xs=[e["topologyDelta"].get(feature,0.0) for e in train if e["childState"]==label]
        if not xs: continue
        m=mean(xs); between+=len(xs)*(m-overall)**2; within+=sum((x-m)**2 for x in xs)
    return between/(within+1e-12)
feature_rank=sorted((anova_score(f),f) for f in eligible if stdev([e["topologyDelta"].get(f,0.0) for e in train])>1e-12)
feature_rank.reverse()
max_features=int(protocol["featureDiscovery"]["maximumTopologyFeatures"])
selected=[f for _,f in feature_rank[:max_features]]
if not selected: raise RuntimeError("no topology operator features selected")

geom_names=sorted(train[0]["geometry"])

def fit_stats(items,names,kind):
    out={}
    for name in names:
        xs=[e[kind].get(name,0.0) for e in items]; out[name]=(mean(xs),stdev(xs) or 1.0)
    return out
topo_stats=fit_stats(train,selected,"topologyDelta")
geom_stats=fit_stats(train,geom_names,"geometry")
def vector(e,names,stats,kind): return [(e[kind].get(n,0.0)-stats[n][0])/stats[n][1] for n in names]
for e in edges:
    e["topologyVector"]=vector(e,selected,topo_stats,"topologyDelta")
    e["geometryVector"]=vector(e,geom_names,geom_stats,"geometry")
    e["combinedVector"]=e["topologyVector"]+e["geometryVector"]

def centroids(items,key):
    dims=len(items[0][key]); out={}
    for label in labels:
        rows=[e[key] for e in items if e["childState"]==label]
        out[label]=[mean([r[d] for r in rows]) for d in range(dims)]
    return out
cent_topo=centroids(train,"topologyVector"); cent_geom=centroids(train,"geometryVector"); cent_comb=centroids(train,"combinedVector")
def predict(vec,cents):
    ds=sorted((distance(vec,c),label) for label,c in cents.items())
    return ds[0][1], ds[1][0]-ds[0][0], {str(label):distance(vec,c) for label,c in cents.items()}
for e in edges:
    e["topologyPrediction"],e["topologyMargin"],e["topologyDistances"]=predict(e["topologyVector"],cent_topo)
    e["geometryPrediction"],e["geometryMargin"],_=predict(e["geometryVector"],cent_geom)
    e["combinedPrediction"],e["combinedMargin"],_=predict(e["combinedVector"],cent_comb)

def metrics(items,pred_key,labels_override=None):
    truth=labels_override if labels_override is not None else [e["childState"] for e in items]
    preds=[e[pred_key] for e in items]
    acc=sum(a==b for a,b in zip(truth,preds))/len(items) if items else 0.0
    recalls=[]
    for label in labels:
        idx=[i for i,x in enumerate(truth) if x==label]
        if idx: recalls.append(sum(preds[i]==label for i in idx)/len(idx))
    return {"accuracy":acc,"macroRecall":mean(recalls),"rows":len(items),"truthCounts":dict(Counter(map(str,truth))),"predictionCounts":dict(Counter(map(str,preds)))}

def contraction_quartiles(items):
    ordered=sorted(items,key=lambda e:(e["geometry"]["geometry:logAreaRatio"],e["edgeId"])); n=len(ordered); out={}
    for i,e in enumerate(ordered): out[e["edgeId"]]=min(3,(i*4)//max(1,n))
    return out
q_by_lane={lane:contraction_quartiles([e for e in edges if e["lane"]==lane]) for lane in ["holdout","control"]}
def null_accuracies(items,pred_key,lane,iters):
    strata=defaultdict(list)
    q=q_by_lane[lane]
    for i,e in enumerate(items): strata[(e["parentProposalScale"],q[e["edgeId"]])].append(i)
    observed_labels=[e["childState"] for e in items]; out=[]
    for it in range(iters):
        shuffled=observed_labels[:]
        for key,idxs in strata.items():
            vals=[observed_labels[i] for i in idxs]
            seed=int(hashlib.sha256(f"mark-operator-null|{lane}|{it}|{key}".encode()).hexdigest()[:16],16)
            rnd=random.Random(seed); rnd.shuffle(vals)
            for i,v in zip(idxs,vals): shuffled[i]=v
        out.append(metrics(items,pred_key,shuffled)["accuracy"])
    return out
iters=int(protocol["nullModel"]["iterations"])
model_results={}
for lane in ["holdout","control"]:
    items=[e for e in edges if e["lane"]==lane]
    model_results[lane]={}
    for name,key in [("topologyOnly","topologyPrediction"),("geometryOnly","geometryPrediction"),("combined","combinedPrediction")]:
        m=metrics(items,key); nulls=null_accuracies(items,key,lane,iters)
        m.update({"nullMeanAccuracy":mean(nulls),"nullMaximumAccuracy":max(nulls),"accuracyLiftOverNullMean":m["accuracy"]-mean(nulls),"beatsAllNulls":m["accuracy"]>max(nulls),"nullAtLeastObserved":sum(x>=m["accuracy"] for x in nulls)})
        model_results[lane][name]=m

# Freeze feature behavior across lanes; consistent ordering is stronger than one-institution separation.
feature_behavior=[]
for name in selected:
    lane_means={}
    lane_orders={}
    for lane in ["train","holdout","control"]:
        lane_means[lane]={str(label):mean([e["topologyDelta"].get(name,0.0) for e in edges if e["lane"]==lane and e["childState"]==label]) for label in labels}
        lane_orders[lane]=[int(x) for x in sorted(labels,key=lambda label:(lane_means[lane][str(label)],label))]
    feature_behavior.append({"feature":name,"trainAnovaScore":anova_score(name),"branchMeanDeltasByLane":lane_means,"branchOrderingByLane":lane_orders,"sameOrderingAcrossAllLanes":len({tuple(x) for x in lane_orders.values()})==1})
feature_behavior.sort(key=lambda r:(-int(r["sameOrderingAcrossAllLanes"]),-r["trainAnovaScore"],r["feature"]))

# Compact per-edge frozen record; topology vectors remain anonymous until the separate rejoin.
edge_rows=[]
for e in sorted(edges,key=lambda x:x["edgeId"]):
    edge_rows.append({
      "schema":"mark_state2_operator_edge_v1","edgeId":e["edgeId"],"sourceGroupId":e["sourceGroupId"],"lane":e["lane"],
      "parentObservationId":e["parentObservationId"],"childObservationId":e["childObservationId"],"childState":e["childState"],
      "parentRegion":e["parentRegion"],"childRegion":e["childRegion"],"parentProposalScale":e["parentProposalScale"],
      "topologyPrediction":e["topologyPrediction"],"topologyMargin":e["topologyMargin"],
      "geometryPrediction":e["geometryPrediction"],"combinedPrediction":e["combinedPrediction"],
      "selectedTopologyDeltas":{name:e["topologyDelta"].get(name,0.0) for name in selected}
    })

branch_counts={lane:{str(label):sum(e["lane"]==lane and e["childState"]==label for e in edges) for label in labels} for lane in ["train","holdout","control"]}
core={
 "schema":"mark_state_operator_discovery_v1","experimentId":protocol["experimentId"],
 "parentLocalStateFieldDiscoverySha256":field["localStateFieldDiscoverySha256"],
 "parentStateTransitionGrammarDiscoverySha256":transition["stateTransitionGrammarDiscoverySha256"],
 "physicalLedgerMerkleRoot":topo_summary["physicalLedgerMerkleRoot"],"provenanceAvailableDuringDiscovery":False,
 "state2ContainmentEdges":len(edges),"branchCounts":branch_counts,
 "topologyFeatureSelection":{"eligibleFeatures":len(eligible),"selectedFeatures":selected,"trainStandardization":{k:{"mean":v[0],"sd":v[1]} for k,v in topo_stats.items()},"rankedFeatureBehavior":feature_behavior},
 "geometryFeatures":geom_names,
 "models":model_results,
 "primaryFalsifier":{
   "holdoutTopologyMinusGeometryAccuracy":model_results["holdout"]["topologyOnly"]["accuracy"]-model_results["holdout"]["geometryOnly"]["accuracy"],
   "controlTopologyMinusGeometryAccuracy":model_results["control"]["topologyOnly"]["accuracy"]-model_results["control"]["geometryOnly"]["accuracy"],
   "topologyOutperformsGeometryInBothIndependentLanes":model_results["holdout"]["topologyOnly"]["accuracy"]>model_results["holdout"]["geometryOnly"]["accuracy"] and model_results["control"]["topologyOnly"]["accuracy"]>model_results["control"]["geometryOnly"]["accuracy"]
 },
 "contract":{"rawRuleAccuracyCoordinatesExcluded":True,"featureSelectionTrainOnly":True,"evaluationLabelsFrozen":True,"positiveAndNegativeTopologyDeltasSymmetric":True,"allState2EdgesRetained":True,"provenanceUnavailableUntilFreeze":True,"physicalLedgerFullyVerifiedBeforeProjection":True,"theoryGeneratingNotCausalProof":True}
}
sha=canonical_sha(core); packet={**core,"stateOperatorDiscoverySha256":sha}
out_dir.mkdir(parents=True,exist_ok=True)
(out_dir/"state-operator-discovery.json").write_text(json.dumps(packet,indent=2)+"\n")
with (out_dir/"state2-operator-edges.jsonl").open("w",encoding="utf-8") as h:
    for r in edge_rows: h.write(json.dumps(r,separators=(",",":"))+"\n")
(out_dir/"summary.txt").write_text("\n".join([
 f"state_operator_discovery_sha256={sha}",
 f"state2_containment_edges={len(edges)}",
 f"selected_topology_features={len(selected)}",
 f"holdout_topology_accuracy={model_results['holdout']['topologyOnly']['accuracy']}",
 f"holdout_geometry_accuracy={model_results['holdout']['geometryOnly']['accuracy']}",
 f"holdout_topology_null_mean={model_results['holdout']['topologyOnly']['nullMeanAccuracy']}",
 f"control_topology_accuracy={model_results['control']['topologyOnly']['accuracy']}",
 f"control_geometry_accuracy={model_results['control']['geometryOnly']['accuracy']}",
 f"control_topology_null_mean={model_results['control']['topologyOnly']['nullMeanAccuracy']}",
 f"topology_beats_geometry_both_lanes={core['primaryFalsifier']['topologyOutperformsGeometryInBothIndependentLanes']}",
 f"features_same_branch_order_all_lanes={sum(r['sameOrderingAcrossAllLanes'] for r in feature_behavior)}"
])+"\n")
print(json.dumps(packet,indent=2))
