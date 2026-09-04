#!/usr/bin/env python3
import json, os, random
from collections import Counter, defaultdict
from pathlib import Path
from mark_protected_relationship_intervention_common import *

protocol=load_json(os.environ.get("MARK_REL_PROTOCOL","research/mark/discovery-experiments/protected-relationship-intervention-v1.protocol.json"))
v5=Path(os.environ.get("MARK_REL_V5","artifact-staging/protected-relationship/v5"))
labels_dir=Path(os.environ.get("MARK_REL_LABELS","artifact-staging/protected-relationship/labels"))
freeze_dir=Path(os.environ.get("MARK_REL_FREEZE","artifacts/mark-protected-relationship-intervention-v1/frozen"))
out=Path(os.environ.get("MARK_REL_OUT","artifacts/mark-protected-relationship-intervention-v1/result")); out.mkdir(parents=True,exist_ok=True)

# The combined V5 label file must remain unavailable. Only the separately sealed V4 label packet may be opened now.
if list(v5.rglob("role-pair-labels.jsonl")): raise RuntimeError("combined V5 role labels present during scoring")
label_custody=load_json(locate(labels_dir,"label-custody.json"))
if label_custody["labelsSha256"]!=protocol["inputs"]["expectedLabelsSha256"]: raise RuntimeError("label SHA drift")
labels={r["pairId"]:r["label"] for r in (json.loads(x) for x in locate(labels_dir,"pair-labels.jsonl").read_text().splitlines() if x.strip())}

manifest=load_json(locate(v5,"edge-pair-manifest.json")); world=load_json(locate(v5,"critical-edge-world.json")); freeze=load_json(freeze_dir/"intervention-freeze.json")
if manifest["edgePairManifestSha256"]!=protocol["inputs"]["expectedEdgePairManifestSha256"]: raise RuntimeError("edge manifest SHA drift")
if world["criticalEdgeWorldSha256"]!=protocol["inputs"]["expectedCriticalEdgeWorldSha256"]: raise RuntimeError("edge world SHA drift")
if freeze["roleLabelsAvailableDuringFreeze"] is not False or freeze["scientificOutcomeAvailableDuringFreeze"] is not False: raise RuntimeError("blind freeze contract violated")

frozen=[json.loads(x) for x in (freeze_dir/"intervention-manifest.jsonl").read_text().splitlines() if x.strip()]
rows_text="".join(json.dumps(r,sort_keys=True,separators=(",",":"))+"\n" for r in sorted(frozen,key=lambda r:r["pairId"]))
import hashlib
if hashlib.sha256(rows_text.encode()).hexdigest()!=freeze["interventionRowsSha256"]: raise RuntimeError("intervention rows SHA drift")
if any(r["pairId"] not in labels for r in frozen): raise RuntimeError("missing post-freeze role label")
needed={r["observationA"] for r in frozen}|{r["observationB"] for r in frozen}; graphs=load_graphs(v5,needed)

scored=[]
for r in frozen:
    A=graphs[r["observationA"]]; B=graphs[r["observationB"]]; mapping,best=center_mapping(A,B)
    if best!=r["selectedTransform"] or canonical_sha(sorted(mapping.items()))!=r["mappingSha256"]: raise RuntimeError("mapping drift for "+r["pairId"])
    recomputed=select_intervention(A,mapping,protocol["blindIntervention"])
    if recomputed is None: raise RuntimeError("frozen intervention no longer selectable: "+r["pairId"])
    for key in ("edge1","edge2","rewiredEdge1","rewiredEdge2","edgeStratum","affectedRootCount"):
        if recomputed[key]!=r[key]: raise RuntimeError(f"intervention drift {r['pairId']} {key}")
    primary=score_intervention(A,B,mapping,r,"lengthAware",False)
    topo=score_intervention(A,B,mapping,r,"topology",False)
    direct=score_intervention(A,B,mapping,r,"lengthAware",True)
    if primary is None or topo is None or direct is None: raise RuntimeError("missing frozen intervention score "+r["pairId"])
    scored.append({
        "pairId":r["pairId"],"lane":r["lane"],"occupantFamilyA":r["occupantFamilyA"],"occupantFamilyB":r["occupantFamilyB"],
        "label":labels[r["pairId"]],"primaryDelta":primary["delta"],"primaryAffectedRoots":primary["roots"],
        "primaryRenderingDistance":primary["renderDistance"],"primaryRelationshipDistance":primary["relationshipDistance"],
        "topologyDelta":topo["delta"],"directRootDelta":direct["delta"],
        "residualGeometrySeparation":float(r["residualGeometrySeparation"]),
        "maxChordShift":max(abs(float(a)-float(b)) for a,b in zip(r["oldChord"],r["newChord"])),
    })

counts=Counter(r["lane"] for r in scored); minimums={"train":protocol["feasibility"]["minimumInterventionsTrain"],"holdout":protocol["feasibility"]["minimumInterventionsHoldout"],"control":protocol["feasibility"]["minimumInterventionsControl"]}
feasible=all(counts[lane]>=minimums[lane] for lane in minimums)
lane_metrics={}
for lane in ("train","holdout","control"):
    rs=[r for r in scored if r["lane"]==lane]
    lane_metrics[lane]={"pairs":len(rs),"preserved":sum(r["label"]=="preserved" for r in rs),"broken":sum(r["label"]=="broken" for r in rs),"primary":balanced_effect(rs,"primaryDelta"),"topology":balanced_effect(rs,"topologyDelta"),"directRoot":balanced_effect(rs,"directRootDelta")}

null_values=[]; observed=lane_metrics["train"]["primary"]["balancedEffect"]
if feasible and observed is not None:
    train=[r for r in scored if r["lane"]=="train"]; strata=defaultdict(list)
    for r in train: strata[(r["occupantFamilyA"],r["occupantFamilyB"])].append(r)
    rng=random.Random(int(protocol["null"]["seed"]))
    for _ in range(int(protocol["null"]["worlds"])):
        override={}
        for key,rs in sorted(strata.items(),key=lambda kv:str(kv[0])):
            ls=[r["label"] for r in rs]; rng.shuffle(ls)
            for r,label in zip(rs,ls): override[r["pairId"]]=label
        null_values.append(balanced_effect(train,"primaryDelta",override)["balancedEffect"])
null_at_least=sum(abs(v)>=abs(observed) for v in null_values if v is not None) if observed is not None else None

g=protocol["gates"]; train_ok=feasible and observed is not None and observed>=float(g["trainFamilyBalancedEffectMinimum"]) and null_at_least is not None and null_at_least<=int(g["trainMaximumAbsoluteNullsAtLeastObserved"])
hold=lane_metrics["holdout"]["primary"]["balancedEffect"]; control=lane_metrics["control"]["primary"]["balancedEffect"]
hold_ok=feasible and hold is not None and hold>=float(g["holdoutEffectMinimum"])
if not feasible: adjudication="INFEASIBLE"
elif train_ok and hold_ok and control is not None and control>=float(g["controlEffectForThreeLaneClaim"]): adjudication="THREE_LANE_PROTECTED_RELATIONSHIP"
elif train_ok and hold_ok: adjudication="TWO_LANE_PROTECTED_RELATIONSHIP"
else: adjudication="GENERIC_GRAPH_DAMAGE_COMPATIBLE"

core={
    "schema":"mark_protected_relationship_intervention_result_v1","experimentId":protocol["experimentId"],"adjudication":adjudication,
    "interventionFreezeSha256":freeze["interventionFreezeSha256"],"labelsSha256":label_custody["labelsSha256"],"feasible":feasible,
    "countsByLane":dict(sorted(counts.items())),"laneMetrics":lane_metrics,"trainAbsoluteNullsAtLeastObserved":null_at_least,
    "nullWorlds":len(null_values),"trainGatePassed":train_ok,"holdoutGatePassed":hold_ok,
    "contract":{"interventionsFrozenBeforeLabelsOpened":True,"combinedV5LabelsUnavailableDuringScoring":True,"scientificFailureIsGreen":True}
}
core["resultSha256"]=canonical_sha(core)
(out/"result.json").write_text(json.dumps(core,indent=2,sort_keys=True)+"\n")
with (out/"scored-pairs.jsonl").open("w") as f:
    for r in sorted(scored,key=lambda r:r["pairId"]): f.write(json.dumps(r,sort_keys=True,separators=(",",":"))+"\n")
summary=["# Mark protected relationship intervention v1","",f"Adjudication: **{adjudication}**",f"Feasible: **{str(feasible).lower()}**",""]
for lane in ("train","holdout","control"):
    m=lane_metrics[lane]; summary.append(f"- {lane}: {m['pairs']} interventions ({m['preserved']} preserved / {m['broken']} broken); primary family-balanced effect {m['primary']['balancedEffect']:+.6f}; topology ablation {m['topology']['balancedEffect']:+.6f}; direct-root ablation {m['directRoot']['balancedEffect']:+.6f}")
summary += ["",f"- train absolute label-shuffle nulls >= observed: {null_at_least} / {len(null_values)}",f"- train gate passed: {str(train_ok).lower()}",f"- holdout gate passed: {str(hold_ok).lower()}","","Positive primary effect means the low-order-matched relationship rewire damages radius-2 compatibility with a role-preserved target more selectively than the residual-geometry twin. Scientific failure remains green and is not reinterpreted as context sensitivity.","",f"Result SHA-256: `{core['resultSha256']}`"]
(out/"summary.md").write_text("\n".join(summary)+"\n")
print("\n".join(summary))
