#!/usr/bin/env python3
import hashlib, json, os
from pathlib import Path

protocol_path=Path(os.environ.get("MARK_VERTEX_PROTOCOL","research/mark/discovery-experiments/critical-center-correspondence-v4.protocol.json"))
manifest_dir=Path(os.environ.get("MARK_VERTEX_PAIR_MANIFEST","artifacts/mark-vertex-pair-manifest-v4"))
full_input=Path(os.environ["MARK_FULL_COMPILER_INPUT"])
out_input=Path(os.environ["MARK_VERTEX_COMPILER_INPUT"])
out_custody=Path(os.environ.get("MARK_VERTEX_SUBSET_CUSTODY","artifacts/mark-vertex-subset-custody-v4/subset-custody.json"))

def load_json(p): return json.loads(Path(p).read_text(encoding="utf-8"))
def canonical_sha(v): return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
def compact_bytes(v): return json.dumps(v,separators=(",",":"),ensure_ascii=False).encode()

protocol=load_json(protocol_path)
manifest=load_json(manifest_dir/"vertex-pair-manifest.json")
msha=manifest.get("vertexPairManifestSha256")
if canonical_sha({k:v for k,v in manifest.items() if k!="vertexPairManifestSha256"})!=msha: raise RuntimeError("vertex-pair manifest SHA mismatch")
full=load_json(full_input)
if full.get("schema")!="mark_observable_input_blind_v1": raise RuntimeError("unexpected compiler input schema")
if full.get("blindInputSha256")!=manifest["parentFullWorldSourceBlindInputSha256"]: raise RuntimeError("sealed compiler input is not the v3 parent blind world")
selected=set(manifest["selectedObservationIds"])
obs_by_id={o["id"]:o for o in full["observations"]}
missing=sorted(selected-set(obs_by_id))
if missing: raise RuntimeError(f"selected observations missing from sealed input: {missing[:5]}")
selected_obs=[o for o in full["observations"] if o["id"] in selected]
source_ids={o["sourceGroupId"] for o in selected_obs}
selected_sources=[s for s in full["sources"] if s["sourceGroupId"] in source_ids]
source_by_id={s["sourceGroupId"]:s for s in selected_sources}
if len(source_by_id)!=len(source_ids): raise RuntimeError("selected source set incomplete")

pairs=[json.loads(x) for x in (manifest_dir/"role-pair-labels.jsonl").read_text().splitlines() if x.strip()]
for r in pairs:
    for side in ("A","B"):
        oid=r[f"observation{side}"]; sid=r[f"sourceGroup{side}"]
        o=obs_by_id[oid]
        if o["sourceGroupId"]!=sid or o["lane"]!=r["lane"]: raise RuntimeError(f"pair/sealed-input mismatch for {oid}")
        if source_by_id[sid].get("lane","")!=r["lane"]: raise RuntimeError(f"source lane mismatch for {sid}")

core={k:v for k,v in full.items() if k!="blindInputSha256"}
core["sources"]=selected_sources
core["observations"]=selected_obs
subset_sha=hashlib.sha256(compact_bytes(core)).hexdigest()
subset={**core,"blindInputSha256":subset_sha}
out_input.parent.mkdir(parents=True,exist_ok=True)
out_input.write_text(json.dumps(subset,separators=(",",":"),ensure_ascii=False)+"\n")

source_payload_sha=hashlib.sha256(compact_bytes(selected_sources)).hexdigest()
observation_payload_sha=hashlib.sha256(compact_bytes(selected_obs)).hexdigest()
custody_core={
  "schema":"mark_vertex_subset_custody_v4",
  "experimentId":protocol["experimentId"],
  "vertexPairManifestSha256":msha,
  "parentFullWorldSourceBlindInputSha256":full["blindInputSha256"],
  "selectedCompilerBlindInputSha256":subset_sha,
  "selectedSources":len(selected_sources),
  "selectedObservations":len(selected_obs),
  "selectedSourcePayloadSha256":source_payload_sha,
  "selectedObservationPayloadSha256":observation_payload_sha,
  "contract":{
    "sourceObjectsCopiedExactlyFromParent":True,
    "observationObjectsCopiedExactlyFromParent":True,
    "capturePathsUnchanged":True,
    "onlySelectionOperationApplied":True,
    "noProvenanceConsumed":True
  }
}
csha=canonical_sha(custody_core); custody={**custody_core,"vertexSubsetCustodySha256":csha}
out_custody.parent.mkdir(parents=True,exist_ok=True)
out_custody.write_text(json.dumps(custody,indent=2)+"\n")
print(json.dumps(custody,indent=2))
