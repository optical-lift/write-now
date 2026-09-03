#!/usr/bin/env python3
import hashlib, json, os
from collections import Counter, defaultdict
from pathlib import Path

operator_dir=Path(os.environ.get("MARK_OPERATOR_PACKET","artifact-staging/operator"))
context_dir=Path(os.environ.get("MARK_SOURCE_CONTEXT","artifact-staging/context"))
out_dir=Path(os.environ.get("MARK_OPERATOR_REJOIN_OUT","artifacts/mark-state-operator-discovery-v1-context"))

def load_json(p): return json.loads(Path(p).read_text(encoding="utf-8"))
def canonical_sha(v): return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()

packet=load_json(operator_dir/"state-operator-discovery.json")
if packet.get("schema")!="mark_state_operator_discovery_v1": raise RuntimeError("unexpected operator packet")
sha=packet.get("stateOperatorDiscoverySha256")
core={k:v for k,v in packet.items() if k!="stateOperatorDiscoverySha256"}
if canonical_sha(core)!=sha: raise RuntimeError("operator packet SHA mismatch")
if packet.get("provenanceAvailableDuringDiscovery"): raise RuntimeError("operator packet was not blind")

summary=load_json(context_dir/"summary.json")
if summary.get("schema")!="mark_source_rule_atlas_context_rejoin_v1": raise RuntimeError("unexpected source context schema")
contexts={}
with (context_dir/"source-rule-context.jsonl").open(encoding="utf-8") as h:
    for line in h:
        if line.strip():
            r=json.loads(line); contexts.setdefault(r["blindRow"]["sourceGroupId"],r["sourceContext"])

edges=[]
with (operator_dir/"state2-operator-edges.jsonl").open(encoding="utf-8") as h:
    for line in h:
        if line.strip(): edges.append(json.loads(line))
missing=sorted({e["sourceGroupId"] for e in edges}-set(contexts))
if missing: raise RuntimeError(f"missing provenance for {len(missing)} operator sources")

# High-margin correctly classified carriers are examples of a frozen operator signature, not inputs to its discovery.
def top_examples(state,limit=12):
    rows=[e for e in edges if e["childState"]==state and e["topologyPrediction"]==state]
    rows.sort(key=lambda e:(-float(e["topologyMargin"]),e["edgeId"]))
    out=[]; seen=set()
    for e in rows:
        if e["sourceGroupId"] in seen: continue
        seen.add(e["sourceGroupId"])
        out.append({
          "edgeId":e["edgeId"],"sourceGroupId":e["sourceGroupId"],"lane":e["lane"],"childState":state,
          "topologyMargin":e["topologyMargin"],"parentRegion":e["parentRegion"],"childRegion":e["childRegion"],
          "sourceContext":contexts[e["sourceGroupId"]]
        })
        if len(out)>=limit: break
    return out

institution=defaultdict(lambda:{"edges":0,"correct":0,"branches":Counter(),"sources":set()})
for e in edges:
    inst=contexts[e["sourceGroupId"]].get("institution","unknown")
    slot=institution[inst]; slot["edges"]+=1; slot["correct"]+=int(e["topologyPrediction"]==e["childState"])
    slot["branches"][str(e["childState"])]+=1; slot["sources"].add(e["sourceGroupId"])
institution_rows=[]
for inst,slot in sorted(institution.items()):
    institution_rows.append({"institution":inst,"sources":len(slot["sources"]),"state2BranchEdges":slot["edges"],
                             "topologyPredictionAccuracy":slot["correct"]/slot["edges"] if slot["edges"] else 0.0,
                             "branchCounts":dict(slot["branches"])})

feature_context=[]
for row in packet["topologyFeatureSelection"]["rankedFeatureBehavior"][:12]:
    feature_context.append({"feature":row["feature"],"trainAnovaScore":row["trainAnovaScore"],
                            "sameOrderingAcrossAllLanes":row["sameOrderingAcrossAllLanes"],
                            "branchMeanDeltasByLane":row["branchMeanDeltasByLane"]})

core={
 "schema":"mark_state_operator_context_rejoin_v1",
 "sealedStateOperatorDiscoverySha256":sha,
 "blindOperatorStatisticsPreserved":True,
 "models":packet["models"],"primaryFalsifier":packet["primaryFalsifier"],
 "topPhysicalOperatorFeatures":feature_context,
 "institutionOperatorDynamics":institution_rows,
 "highMarginContextExamples":{"2_to_1":top_examples(1),"2_to_2":top_examples(2),"2_to_3":top_examples(3)},
 "contract":{"selectedFeaturesUnchanged":True,"modelPredictionsUnchanged":True,"statisticsUnchanged":True,
             "sourceContextAttachedOnlyAfterOperatorSha":True,"contextExamplesDidNotDefineOperator":True,
             "semanticOrHistoricalMeaningNotAutomaticallyAssigned":True}
}
digest=canonical_sha(core); out={**core,"contextRejoinSha256":digest}
out_dir.mkdir(parents=True,exist_ok=True)
(out_dir/"state-operator-context-rejoin.json").write_text(json.dumps(out,indent=2,ensure_ascii=False)+"\n")
(out_dir/"summary.txt").write_text("\n".join([
 f"sealed_operator_sha256={sha}",f"context_rejoin_sha256={digest}",f"institutions={len(institution_rows)}",
 "selected_features_preserved=true","predictions_preserved=true"
])+"\n")
print(json.dumps(out,indent=2,ensure_ascii=False))
