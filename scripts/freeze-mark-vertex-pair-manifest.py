#!/usr/bin/env python3
import hashlib, json, os
from collections import Counter
from pathlib import Path

protocol_path=Path(os.environ.get("MARK_VERTEX_PROTOCOL","research/mark/discovery-experiments/critical-center-correspondence-v4.protocol.json"))
v3_dir=Path(os.environ.get("MARK_V3_PACKET","artifact-staging/v3"))
out_dir=Path(os.environ.get("MARK_VERTEX_PAIR_OUT","artifacts/mark-vertex-pair-manifest-v4"))

def load_json(p): return json.loads(Path(p).read_text(encoding="utf-8"))
def canonical_sha(v): return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
def locate(name):
    hits=list(v3_dir.rglob(name))
    if len(hits)!=1: raise RuntimeError(f"expected one {name}, found {len(hits)}")
    return hits[0]

protocol=load_json(protocol_path)
if protocol.get("schema")!="mark_critical_center_correspondence_protocol_v4": raise RuntimeError("unexpected v4 protocol")
freeze=load_json(locate("role-pair-freeze.json"))
psha=freeze.get("rolePairFreezeSha256")
if canonical_sha({k:v for k,v in freeze.items() if k!="rolePairFreezeSha256"})!=psha: raise RuntimeError("v3 role-pair freeze SHA mismatch")
expected=protocol["pairFreeze"]
if psha!=expected["expectedParentRolePairFreezeSha256"]: raise RuntimeError("unexpected v3 parent role-pair SHA")
pair_path=locate("role-pair-labels.jsonl")
pair_bytes=pair_path.read_bytes()
rows_sha=hashlib.sha256(pair_bytes).hexdigest()
if rows_sha!=freeze["rolePairRowsSha256"] or rows_sha!=expected["expectedRolePairRowsSha256"]: raise RuntimeError("v3 role-pair rows SHA mismatch")
pairs=[json.loads(x) for x in pair_bytes.splitlines() if x.strip()]
if len(pairs)!=int(expected["expectedPairs"]): raise RuntimeError(f"unexpected v3 pair count {len(pairs)}")
obs=set(); lane_pairs=Counter(); label_pairs=Counter()
for r in pairs:
    if r["sourceGroupA"]==r["sourceGroupB"]: raise RuntimeError("v3 pair is not cross-source")
    if r["label"] not in ("preserved","broken"): raise RuntimeError("unexpected role-pair label")
    obs.add(r["observationA"]); obs.add(r["observationB"])
    lane_pairs[r["lane"]]+=1; label_pairs[(r["lane"],r["label"])]+=1
if len(obs)!=int(expected["expectedUniqueObservations"]): raise RuntimeError(f"unexpected selected observation count {len(obs)}")
core={
  "schema":"mark_vertex_pair_manifest_v4",
  "experimentId":protocol["experimentId"],
  "parentRolePairFreezeSha256":psha,
  "parentRolePairRowsSha256":rows_sha,
  "parentFullWorldSourceBlindInputSha256":freeze["sourceBlindInputSha256"],
  "parentFullWorldPhysicalLedgerMerkleRoot":freeze["physicalLedgerMerkleRoot"],
  "parentFullWorldTopologyRowsSha256":freeze["topologyRowsSha256"],
  "pairRows":len(pairs),
  "selectedObservationIds":sorted(obs),
  "selectedObservations":len(obs),
  "pairCountsByLane":dict(sorted(lane_pairs.items())),
  "pairCountsByLaneAndLabel":[{"lane":lane,"label":label,"count":count} for (lane,label),count in sorted(label_pairs.items())],
  "contract":{
    "physicalGeometryAvailableDuringManifestFreeze":False,
    "topologyAvailableDuringManifestFreeze":False,
    "roleLabelsInheritedWithoutChange":True,
    "allPairsCrossSourceGroupId":True,
    "noStateVocabularyConsumed":True,
    "noTransitionGrammarConsumed":True,
    "noProvenanceConsumed":True
  }
}
digest=canonical_sha(core); packet={**core,"vertexPairManifestSha256":digest}
out_dir.mkdir(parents=True,exist_ok=True)
(out_dir/"vertex-pair-manifest.json").write_text(json.dumps(packet,indent=2)+"\n")
(out_dir/"role-pair-labels.jsonl").write_bytes(pair_bytes)
(out_dir/"summary.txt").write_text(
    f"vertex_pair_manifest_sha256={digest}\nrole_pair_freeze_sha256={psha}\npairs={len(pairs)}\nselected_observations={len(obs)}\n"
)
print(json.dumps(packet,indent=2))
