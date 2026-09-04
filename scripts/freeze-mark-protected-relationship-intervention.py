#!/usr/bin/env python3
import hashlib, json, os
from collections import Counter
from pathlib import Path
from mark_protected_relationship_intervention_common import *

protocol=load_json(os.environ.get("MARK_REL_PROTOCOL","research/mark/discovery-experiments/protected-relationship-intervention-v1.protocol.json"))
v5=Path(os.environ.get("MARK_REL_V5","artifact-staging/protected-relationship/v5"))
pairs_dir=Path(os.environ.get("MARK_REL_PAIRS","artifact-staging/protected-relationship/pairs"))
out=Path(os.environ.get("MARK_REL_FREEZE","artifacts/mark-protected-relationship-intervention-v1/frozen")); out.mkdir(parents=True,exist_ok=True)

if list(v5.rglob("role-pair-labels.jsonl")): raise RuntimeError("role labels present during blind intervention freeze")
manifest=load_json(locate(v5,"edge-pair-manifest.json")); world=load_json(locate(v5,"critical-edge-world.json")); pair_freeze=load_json(locate(pairs_dir,"pair-world-freeze.json"))
if manifest["edgePairManifestSha256"]!=protocol["inputs"]["expectedEdgePairManifestSha256"]: raise RuntimeError("edge manifest SHA drift")
if world["criticalEdgeWorldSha256"]!=protocol["inputs"]["expectedCriticalEdgeWorldSha256"]: raise RuntimeError("edge world SHA drift")
if pair_freeze["pairWorldFreezeSha256"]!=protocol["inputs"]["expectedPairWorldFreezeSha256"]: raise RuntimeError("pair world SHA drift")

pairs=[json.loads(x) for x in locate(pairs_dir,"unlabeled-pairs.jsonl").read_text().splitlines() if x.strip()]
if any("label" in r for r in pairs): raise RuntimeError("label leaked into unlabeled pair world")
needed={r["observationA"] for r in pairs}|{r["observationB"] for r in pairs}; graphs=load_graphs(v5,needed); rows=[]; counts=Counter()
for pair in pairs:
    A=graphs[pair["observationA"]]; B=graphs[pair["observationB"]]; mapping,best=center_mapping(A,B); intervention=select_intervention(A,mapping,protocol["blindIntervention"])
    if intervention is None: continue
    row={**pair,"selectedTransform":best,"mappedCenters":len(mapping),"mappingSha256":canonical_sha(sorted(mapping.items())),**intervention}; rows.append(row); counts[pair["lane"]]+=1
rows.sort(key=lambda r:r["pairId"]); text="".join(json.dumps(r,sort_keys=True,separators=(",",":"))+"\n" for r in rows); (out/"intervention-manifest.jsonl").write_text(text)
core={"schema":"mark_protected_relationship_intervention_freeze_v1","experimentId":protocol["experimentId"],"edgePairManifestSha256":manifest["edgePairManifestSha256"],"criticalEdgeWorldSha256":world["criticalEdgeWorldSha256"],"pairWorldFreezeSha256":pair_freeze["pairWorldFreezeSha256"],"interventions":len(rows),"countsByLane":dict(sorted(counts.items())),"interventionRowsSha256":hashlib.sha256(text.encode()).hexdigest(),"roleLabelsAvailableDuringFreeze":False,"scientificOutcomeAvailableDuringFreeze":False}
core["interventionFreezeSha256"]=canonical_sha(core); (out/"intervention-freeze.json").write_text(json.dumps(core,indent=2,sort_keys=True)+"\n")
(out/"summary.txt").write_text("\n".join([f"intervention_freeze_sha256={core['interventionFreezeSha256']}",f"interventions={len(rows)}"]+[f"{k}={v}" for k,v in sorted(counts.items())])+"\n")
print(json.dumps(core,indent=2))
