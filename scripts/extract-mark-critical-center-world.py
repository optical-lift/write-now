#!/usr/bin/env python3
import hashlib, json, math, os
from collections import Counter, defaultdict
from pathlib import Path

protocol_path=Path(os.environ.get("MARK_VERTEX_PROTOCOL","research/mark/discovery-experiments/critical-center-correspondence-v4.protocol.json"))
manifest_dir=Path(os.environ.get("MARK_VERTEX_PAIR_MANIFEST","artifacts/mark-vertex-pair-manifest-v4"))
subset_custody_path=Path(os.environ.get("MARK_VERTEX_SUBSET_CUSTODY","artifacts/mark-vertex-subset-custody-v4/subset-custody.json"))
subset_input_path=Path(os.environ["MARK_VERTEX_COMPILER_INPUT"])
compiler_dir=Path(os.environ.get("MARK_VERTEX_COMPILER_OUT","artifacts/mark-vertex-selected-compiler-v4"))
topology_dir=Path(os.environ.get("MARK_TOPOLOGY_ATLAS","artifact-staging/topology-cache/topology-atlas"))
out_dir=Path(os.environ.get("MARK_VERTEX_WORLD_OUT","artifacts/mark-critical-center-world-v4"))

def load_json(p): return json.loads(Path(p).read_text(encoding="utf-8"))
def canonical_sha(v): return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
def merkle_root(hex_hashes):
    if not hex_hashes: return hashlib.sha256(b"").hexdigest()
    layer=[bytes.fromhex(x) for x in hex_hashes]
    while len(layer)>1:
        nxt=[]
        for i in range(0,len(layer),2):
            left=layer[i]; right=layer[i+1] if i+1<len(layer) else left
            nxt.append(hashlib.sha256(left+right).digest())
        layer=nxt
    return layer[0].hex()
def degree_bucket(d):
    return str(d) if d<=4 else "5plus"
def signature(kind,h):
    e=int(h.get("PATH_TO_ENDPOINT",0)); j=int(h.get("PATH_TO_JUNCTION",0)); u=int(h.get("UNRESOLVED",0))
    other=sum(int(v) for k,v in h.items() if k not in ("PATH_TO_ENDPOINT","PATH_TO_JUNCTION","UNRESOLVED"))
    return f"{kind}|E={e}|J={j}|U={u}|O={other}"

protocol=load_json(protocol_path)
manifest=load_json(manifest_dir/"vertex-pair-manifest.json")
msha=manifest.get("vertexPairManifestSha256")
if canonical_sha({k:v for k,v in manifest.items() if k!="vertexPairManifestSha256"})!=msha: raise RuntimeError("manifest SHA mismatch")
subset_custody=load_json(subset_custody_path); scsha=subset_custody.get("vertexSubsetCustodySha256")
if canonical_sha({k:v for k,v in subset_custody.items() if k!="vertexSubsetCustodySha256"})!=scsha: raise RuntimeError("subset custody SHA mismatch")
subset=load_json(subset_input_path)
if subset.get("blindInputSha256")!=subset_custody["selectedCompilerBlindInputSha256"]: raise RuntimeError("subset input/custody mismatch")
obs={o["id"]:o for o in subset["observations"]}
if set(obs)!=set(manifest["selectedObservationIds"]): raise RuntimeError("subset observation world differs from frozen manifest")

compiler_custody=load_json(compiler_dir/"custody.json")
if compiler_custody.get("schema")!="mark_sparse_ledger_custody_v2": raise RuntimeError("unexpected compiler custody")
if compiler_custody["sourceBlindInputSha256"]!=subset["blindInputSha256"]: raise RuntimeError("compiler did not consume selected blind input")
events_path=compiler_dir/"events.jsonl"
chunk_lines=int(compiler_custody["physicalLedger"]["chunkLines"])
observed_chunks=[]; h=hashlib.sha256(); in_chunk=0; total=0
centers=defaultdict(list); boundaries={}; aggregate=defaultdict(lambda:{"centerCount":0,"countFeatures":Counter()})
with events_path.open("rb") as f:
    for raw in f:
        total+=1; h.update(raw); in_chunk+=1
        if in_chunk==chunk_lines:
            observed_chunks.append(h.hexdigest()); h=hashlib.sha256(); in_chunk=0
        row=json.loads(raw)
        oid=row.get("observationId")
        if oid not in obs: raise RuntimeError(f"event outside selected world: {oid}")
        if row.get("kind")=="CENTER":
            kind=row["centerKind"]; ah={k:int(v) for k,v in row.get("armHistogram",{}).items()}
            degree=sum(ah.values())
            centers[oid].append({
              "eventId":row["eventId"],"kind":kind,"x":int(row["x"]),"y":int(row["y"]),
              "degree":degree,"armHistogram":ah,"tileIndex":int(row.get("tileIndex",0))
            })
            a=aggregate[oid]; a["centerCount"]+=1
            a["countFeatures"][f"center:{kind}"]+=1
            a["countFeatures"][f"degree:{kind}:{degree_bucket(degree)}"]+=1
            for arm,count in ah.items(): a["countFeatures"][f"arm:{kind}:{arm}"]+=count
            a["countFeatures"][f"signature:{signature(kind,ah)}"]+=1
        elif row.get("schema")=="mark_sparse_observation_boundary_v1":
            if oid in boundaries: raise RuntimeError(f"duplicate observation boundary {oid}")
            boundaries[oid]=row
if in_chunk: observed_chunks.append(h.hexdigest())
pc=compiler_custody["physicalLedger"]
if total!=int(pc["lines"]) or observed_chunks!=pc["chunkHashes"] or merkle_root(observed_chunks)!=pc["merkleRoot"]:
    raise RuntimeError("selected physical ledger custody verification failed")
if set(boundaries)!=set(obs): raise RuntimeError(f"observation boundary mismatch {len(boundaries)} vs {len(obs)}")

top_summary=load_json(topology_dir/"summary.json")
if top_summary.get("schema")!="mark_observation_topology_atlas_summary_v1": raise RuntimeError("unexpected frozen topology cache")
if top_summary["sourceBlindInputSha256"]!=manifest["parentFullWorldSourceBlindInputSha256"] or top_summary["physicalLedgerMerkleRoot"]!=manifest["parentFullWorldPhysicalLedgerMerkleRoot"] or top_summary["rowsSha256"]!=manifest["parentFullWorldTopologyRowsSha256"]:
    raise RuntimeError("frozen topology cache differs from v3 parent world")
frozen={}
with (topology_dir/"observation-topology-atlas.jsonl").open(encoding="utf-8") as f:
    for line in f:
        if line.strip():
            r=json.loads(line)
            if r["observationId"] in obs: frozen[r["observationId"]]=r
if set(frozen)!=set(obs): raise RuntimeError("selected observations missing from frozen full-world topology")
mismatches=[]
for oid,o in obs.items():
    fr=frozen[oid]; ag=aggregate[oid]
    if fr["sourceGroupId"]!=o["sourceGroupId"] or fr["lane"]!=o["lane"] or fr["region"]!=o["region"]:
        mismatches.append((oid,"metadata"))
    if int(fr["centerCount"])!=int(ag["centerCount"]):
        mismatches.append((oid,"centerCount"))
    if {k:int(v) for k,v in fr["countFeatures"].items()}!={k:int(v) for k,v in ag["countFeatures"].items() if v}:
        mismatches.append((oid,"countFeatures"))
if mismatches: raise RuntimeError(f"selected replay differs from frozen full-world topology: {mismatches[:10]}")

out_dir.mkdir(parents=True,exist_ok=True)
rows_path=out_dir/"critical-center-world.jsonl"; wh=hashlib.sha256(); center_total=0
with rows_path.open("wb") as out:
    for oid in sorted(obs):
        o=obs[oid]; r=o["region"]; cs=sorted(centers[oid],key=lambda x:(x["kind"],x["x"],x["y"],x["eventId"]))
        center_total+=len(cs)
        normalized=[]
        for c in cs:
            normalized.append({**c,
              "u":(c["x"]-int(r["x"]))/max(1.0,float(r["width"])),
              "v":(c["y"]-int(r["y"]))/max(1.0,float(r["height"]))
            })
        payload={"schema":"mark_critical_center_observation_v4","observationId":oid,"sourceGroupId":o["sourceGroupId"],"lane":o["lane"],"region":r,"centers":normalized}
        b=json.dumps(payload,separators=(",",":"),ensure_ascii=False).encode()+b"\n"; out.write(b); wh.update(b)
core={
  "schema":"mark_critical_center_world_v4",
  "experimentId":protocol["experimentId"],
  "vertexPairManifestSha256":msha,
  "vertexSubsetCustodySha256":scsha,
  "selectedCompilerBlindInputSha256":subset["blindInputSha256"],
  "selectedPhysicalLedgerMerkleRoot":pc["merkleRoot"],
  "parentFullWorldSourceBlindInputSha256":manifest["parentFullWorldSourceBlindInputSha256"],
  "parentFullWorldPhysicalLedgerMerkleRoot":manifest["parentFullWorldPhysicalLedgerMerkleRoot"],
  "parentFullWorldTopologyRowsSha256":manifest["parentFullWorldTopologyRowsSha256"],
  "observations":len(obs),"centers":center_total,"criticalCenterRowsSha256":wh.hexdigest(),
  "replayEquivalence":{"selectedObservationsChecked":len(obs),"mismatches":0,"exactAggregateEquivalence":True},
  "availableVertexEvidence":["absolute center x/y","normalized center u/v","center kind","center degree","arm histogram"],
  "unavailableEdgeEvidence":["target center ID per arm","within-tile path pixel sequence","explicit loop edge identity"],
  "contract":{"selectedReplayExactToFrozenFullWorldAggregates":True,"noProvenanceConsumed":True}
}
digest=canonical_sha(core); packet={**core,"criticalCenterWorldSha256":digest}
(out_dir/"critical-center-world.json").write_text(json.dumps(packet,indent=2)+"\n")
(out_dir/"summary.txt").write_text(
    f"critical_center_world_sha256={digest}\nselected_physical_ledger_merkle_root={pc['merkleRoot']}\nobservations={len(obs)}\ncenters={center_total}\nfull_world_aggregate_mismatches=0\n"
)
print(json.dumps(packet,indent=2))
