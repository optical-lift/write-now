#!/usr/bin/env python3
import hashlib, json, os
from pathlib import Path

protocol_path=Path(os.environ.get("MARK_V4_PROTOCOL","research/mark/discovery-experiments/critical-center-correspondence-v4.protocol.json"))
v3_dir=Path(os.environ.get("MARK_V3_FROZEN","artifact-staging/v3"))
out_unlabeled=Path(os.environ.get("MARK_V4_UNLABELED_OUT","artifacts/mark-v4-unlabeled-pairs"))
out_labels=Path(os.environ.get("MARK_V4_LABELS_OUT","artifacts/mark-v4-labels-sealed"))

def canonical_sha(v):
    return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
def locate(name):
    hits=list(v3_dir.rglob(name))
    if len(hits)!=1: raise RuntimeError(f"expected one {name}, found {len(hits)}")
    return hits[0]

protocol=json.loads(protocol_path.read_text())
if protocol.get("schema")!="mark_critical_center_correspondence_protocol_v4":
    raise RuntimeError("unexpected v4 protocol")
pf=json.loads(locate("role-pair-freeze.json").read_text())
if pf.get("rolePairFreezeSha256")!=protocol["parentEvidence"]["rolePairFreezeSha256"]:
    raise RuntimeError("v3 role-pair freeze is not the pinned parent")
if canonical_sha({k:v for k,v in pf.items() if k!="rolePairFreezeSha256"})!=pf["rolePairFreezeSha256"]:
    raise RuntimeError("v3 role-pair freeze SHA mismatch")
v3=json.loads(locate("topology-edit-invariance.json").read_text())
if v3.get("topologyEditInvarianceSha256")!=protocol["parentEvidence"]["topologyEditInvarianceSha256"]:
    raise RuntimeError("v3 final packet is not the pinned parent")
if canonical_sha({k:v for k,v in v3.items() if k!="topologyEditInvarianceSha256"})!=v3["topologyEditInvarianceSha256"]:
    raise RuntimeError("v3 final packet SHA mismatch")
if v3.get("parentRolePairFreezeSha256")!=pf["rolePairFreezeSha256"]:
    raise RuntimeError("v3 final packet / role-pair freeze mismatch")

pair_path=locate("role-pair-labels.jsonl")
pair_bytes=pair_path.read_bytes()
if hashlib.sha256(pair_bytes).hexdigest()!=pf["rolePairRowsSha256"]:
    raise RuntimeError("v3 role-pair rows SHA mismatch")
rows=[json.loads(x) for x in pair_bytes.splitlines() if x.strip()]
if len(rows)!=pf["rows"]:
    raise RuntimeError("v3 role-pair row count mismatch")

unlabeled=[]
labels=[]
obs=set()
sources=set()
for r in rows:
    pair_key="|".join(map(str,[r["lane"],r["occupantFamilyA"],r["occupantFamilyB"],r["observationA"],r["observationB"],r["sourceGroupA"],r["sourceGroupB"]]))
    pair_id="P"+hashlib.sha256(pair_key.encode()).hexdigest()[:20].upper()
    u={
      "schema":"mark_unlabeled_correspondence_pair_v4",
      "pairId":pair_id,
      "lane":r["lane"],
      "occupantFamilyA":r["occupantFamilyA"],
      "occupantFamilyB":r["occupantFamilyB"],
      "observationA":r["observationA"],
      "observationB":r["observationB"],
      "sourceGroupA":r["sourceGroupA"],
      "sourceGroupB":r["sourceGroupB"]
    }
    unlabeled.append(u)
    labels.append({"schema":"mark_correspondence_pair_label_v4","pairId":pair_id,"label":r["label"]})
    obs.update([r["observationA"],r["observationB"]]); sources.update([r["sourceGroupA"],r["sourceGroupB"]])

unlabeled.sort(key=lambda r:r["pairId"]); labels.sort(key=lambda r:r["pairId"])
out_unlabeled.mkdir(parents=True,exist_ok=True); out_labels.mkdir(parents=True,exist_ok=True)
up=out_unlabeled/"unlabeled-pairs.jsonl"; lp=out_labels/"pair-labels.jsonl"
ub=b"".join(json.dumps(r,separators=(",",":")).encode()+b"\n" for r in unlabeled)
lb=b"".join(json.dumps(r,separators=(",",":")).encode()+b"\n" for r in labels)
up.write_bytes(ub); lp.write_bytes(lb)
core={
  "schema":"mark_v4_pair_world_freeze",
  "experimentId":protocol["experimentId"],
  "parentRolePairFreezeSha256":pf["rolePairFreezeSha256"],
  "parentTopologyEditInvarianceSha256":v3["topologyEditInvarianceSha256"],
  "parentSourceBlindInputSha256":pf["sourceBlindInputSha256"],
  "parentPhysicalLedgerMerkleRoot":pf["physicalLedgerMerkleRoot"],
  "unlabeledPairsSha256":hashlib.sha256(ub).hexdigest(),
  "labelsSha256":hashlib.sha256(lb).hexdigest(),
  "pairs":len(unlabeled),
  "uniqueObservations":len(obs),
  "uniqueSources":len(sources),
  "observationIdsSha256":hashlib.sha256(("\n".join(sorted(obs))+"\n").encode()).hexdigest(),
  "contract":{
    "unlabeledManifestContainsNoPreservedBrokenLabel":True,
    "labelsStoredSeparately":True,
    "allV3PairsRetained":True,
    "noStateVocabularyConsumed":True,
    "noTransitionGrammarConsumed":True,
    "noProvenanceConsumed":True
  }
}
digest=canonical_sha(core); packet={**core,"pairWorldFreezeSha256":digest}
(out_unlabeled/"pair-world-freeze.json").write_text(json.dumps(packet,indent=2)+"\n")
(out_unlabeled/"observation-ids.txt").write_text("\n".join(sorted(obs))+"\n")
(out_labels/"label-custody.json").write_text(json.dumps({
  "schema":"mark_v4_label_custody",
  "pairWorldFreezeSha256":digest,
  "labelsSha256":hashlib.sha256(lb).hexdigest(),
  "pairs":len(labels)
},indent=2)+"\n")
(out_unlabeled/"summary.txt").write_text(
  f"pair_world_freeze_sha256={digest}\npairs={len(unlabeled)}\nunique_observations={len(obs)}\nunique_sources={len(sources)}\n"
)
print(json.dumps(packet,indent=2))
