#!/usr/bin/env python3
import hashlib, json, os
from collections import defaultdict
from pathlib import Path

subset_dir=Path(os.environ.get("MARK_V4_SUBSET","artifacts/mark-critical-center-subset-v4"))
replay_dir=Path(os.environ.get("MARK_V4_REPLAY","artifacts/mark-critical-center-replay-v4"))
topology_dir=Path(os.environ.get("MARK_TOPOLOGY_ATLAS","artifact-staging/topology-cache/topology-atlas"))
out_dir=Path(os.environ.get("MARK_V4_CENTER_OUT","artifacts/mark-critical-centers-v4"))
derived_input=Path(os.environ["MARK_V4_DERIVED_INPUT"])

def load_json(p): return json.loads(Path(p).read_text())
def signature(kind,h):
    return f"{kind}|E={int(h.get('PATH_TO_ENDPOINT',0))}|J={int(h.get('PATH_TO_JUNCTION',0))}|U={int(h.get('UNRESOLVED',0))}|O={sum(int(v) for k,v in h.items() if k not in ('PATH_TO_ENDPOINT','PATH_TO_JUNCTION','UNRESOLVED'))}"
def degree_bucket(d):
    return str(d) if d<=4 else "5plus"
def add(m,k,v=1):
    if v: m[k]+=v

subset=load_json(subset_dir/"subset-custody.json")
inp=load_json(derived_input)
if inp.get("blindInputSha256")!=subset["derivedBlindInputSha256"]: raise RuntimeError("derived input/custody mismatch")
replay_custody=load_json(replay_dir/"custody.json")
if replay_custody.get("sourceBlindInputSha256")!=subset["derivedBlindInputSha256"]: raise RuntimeError("replay/derived input mismatch")
summary=load_json(topology_dir/"summary.json")
if summary.get("sourceBlindInputSha256")!=subset["parentBlindInputSha256"]: raise RuntimeError("topology cache not from frozen parent")
rows={}
with (topology_dir/"observation-topology-atlas.jsonl").open() as f:
    for line in f:
        if line.strip():
            r=json.loads(line); rows[r["observationId"]]=r
selected={o["id"]:o for o in inp["observations"]}
if set(selected)-set(rows): raise RuntimeError("selected observation absent from parent topology atlas")

aggregates={oid:{"centerCount":0,"countFeatures":defaultdict(int)} for oid in selected}
out_dir.mkdir(parents=True,exist_ok=True)
center_path=out_dir/"critical-centers.jsonl"; h=hashlib.sha256(); center_rows=0
with (replay_dir/"events.jsonl").open() as src, center_path.open("wb") as out:
    for line in src:
        if '"kind":"CENTER"' not in line: continue
        e=json.loads(line)
        oid=e["observationId"]
        if oid not in selected: raise RuntimeError(f"replay emitted unexpected observation {oid}")
        arm={str(k):int(v) for k,v in e.get("armHistogram",{}).items()}
        degree=sum(arm.values()); kind=e["centerKind"]
        a=aggregates[oid]; a["centerCount"]+=1
        cf=a["countFeatures"]
        add(cf,f"center:{kind}")
        add(cf,f"degree:{kind}:{degree_bucket(degree)}")
        for k,v in arm.items(): add(cf,f"arm:{kind}:{k}",v)
        add(cf,f"signature:{signature(kind,arm)}")
        payload={
          "schema":"mark_critical_center_vertex_v4",
          "observationId":oid,
          "sourceGroupId":e["sourceGroupId"],
          "lane":e["lane"],
          "eventId":e.get("eventId"),
          "kind":kind,
          "x":int(e["x"]),"y":int(e["y"]),
          "degree":degree,
          "endpointArms":int(arm.get("PATH_TO_ENDPOINT",0)),
          "junctionArms":int(arm.get("PATH_TO_JUNCTION",0)),
          "unresolvedArms":int(arm.get("UNRESOLVED",0)),
          "otherArms":sum(v for k,v in arm.items() if k not in ("PATH_TO_ENDPOINT","PATH_TO_JUNCTION","UNRESOLVED"))
        }
        b=json.dumps(payload,separators=(",",":")).encode()+b"\n"; out.write(b); h.update(b); center_rows+=1

mismatches=[]
for oid,o in selected.items():
    got=aggregates[oid]; expected=rows[oid]
    if got["centerCount"]!=int(expected["centerCount"]) or dict(got["countFeatures"])!={k:int(v) for k,v in expected["countFeatures"].items()}:
        mismatches.append({"observationId":oid,"gotCenters":got["centerCount"],"expectedCenters":int(expected["centerCount"])})
if mismatches:
    raise RuntimeError(f"subset physical replay differs from frozen topology for {len(mismatches)} observations; first={mismatches[:3]}")
regions_path=out_dir/"observation-regions.jsonl"; rh=hashlib.sha256()
with regions_path.open("wb") as f:
    for oid in sorted(selected):
        o=selected[oid]
        payload={"schema":"mark_critical_center_region_v4","observationId":oid,"sourceGroupId":o["sourceGroupId"],"lane":o["lane"],"region":o["region"]}
        b=json.dumps(payload,separators=(",",":")).encode()+b"\n"; f.write(b); rh.update(b)
exact={
  "schema":"mark_critical_center_replay_exactness_v4",
  "pairWorldFreezeSha256":subset["pairWorldFreezeSha256"],
  "parentBlindInputSha256":subset["parentBlindInputSha256"],
  "derivedBlindInputSha256":subset["derivedBlindInputSha256"],
  "derivedPhysicalLedgerMerkleRoot":replay_custody["physicalLedger"]["merkleRoot"],
  "observations":len(selected),
  "criticalCenters":center_rows,
  "criticalCentersSha256":h.hexdigest(),
  "observationRegionsSha256":rh.hexdigest(),
  "allSelectedObservationsExactlyMatchFrozenAggregateTopology":True,
  "contract":{
    "samePhysicalCompiler":True,
    "sameTileSize512":True,
    "sameOverlap32":True,
    "provenanceAvailable":False
  }
}
(out_dir/"replay-exactness.json").write_text(json.dumps(exact,indent=2)+"\n")
(out_dir/"summary.txt").write_text(
  f"observations={len(selected)}\ncritical_centers={center_rows}\ncritical_centers_sha256={h.hexdigest()}\nexact_parent_topology_match=true\n"
)
print(json.dumps(exact,indent=2))
