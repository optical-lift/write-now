#!/usr/bin/env python3
"""Build the V47 regime-blind geometric cross-scale parent graph.

Parent selection consumes only opaque IDs, source grouping, proposal scale, and
rectangular geometry from the frozen blind observation packet. It never reads
V46 regime labels.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

EXPERIMENT_ID = "mark:regime-transition-grammar:v47"
FULL_INPUT_SHA256 = "4b64315a037b6ff6dfca3d99bade96e4c9c453f589e4beb0aa3dd5e0c2b92786"
POOL_SOURCE_SHA256 = "b9cc1accbca97380178d8408e7c4d38f9b18ad22c64a785c5f5a8e835c82c729"
POOL_OBSERVATIONS = 9244
POOL_SOURCES = 283
EXCLUSION_ID_LIST_SHA256 = "1735dbadeb93241237af7af3efbe22a7b4a942a80cf94db301e43caaef827076"
SALT = "mark-v47-regime-transition-grammar|"
SCALE_RANK = {"local":1,"neighborhood":2,"field":3,"object":4}

EXPECTED = {
 "discovery":{"sources":171,"observations":5305,"sourceSha":"b77f4f48353764d42888a0de4fb6f1027c78d11565b69ecefe88dd74dffbddbc","obsSha":"c219978ab6ad8e81bf3ce55634ea9c167c00d4d666e214c43bef093dd2b13795"},
 "validation":{"sources":59,"observations":2332,"sourceSha":"daa2f0e62f0925ad3ebf7cd533ce3ceb9a27f68585d3209fbf5de9066e3b34e4","obsSha":"d1a5a58178866bd61fc4f671e8c08d30e09f225da010c485a46640d20a19d91c"},
 "confirmation":{"sources":53,"observations":1607,"sourceSha":"4d947806cb30d62785165a75b2b718da750e476b719711a0a8fa8abc9bd99599","obsSha":"9652f6d2411e6dc975466bddfe8ba1cd98b69affaec012168e550d51cba387e2"},
}

def compact(obj: Any) -> bytes:
    return json.dumps(obj,separators=(",",":"),ensure_ascii=False).encode()

def list_sha(values: list[str]) -> str:
    return hashlib.sha256(compact(values)).hexdigest()

def file_sha(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):
            h.update(chunk)
    return h.hexdigest()

def lane(source_id: str) -> str:
    d=hashlib.sha256((SALT+source_id).encode()).digest()
    b=int.from_bytes(d[:4],"big")%100
    return "discovery" if b<=59 else ("validation" if b<=79 else "confirmation")

def area(r: dict[str,int]) -> int:
    return int(r["width"])*int(r["height"])

def containment(child: dict[str,int], parent: dict[str,int]) -> float:
    cx1,cy1=int(child["x"]),int(child["y"])
    cx2,cy2=cx1+int(child["width"]),cy1+int(child["height"])
    px1,py1=int(parent["x"]),int(parent["y"])
    px2,py2=px1+int(parent["width"]),py1+int(parent["height"])
    iw=max(0,min(cx2,px2)-max(cx1,px1))
    ih=max(0,min(cy2,py2)-max(cy1,py1))
    return (iw*ih)/area(child) if area(child) else 0.0

def verify_blind_input(doc: dict[str,Any]) -> None:
    if doc.get("schema")!="mark_observable_input_blind_v1":
        raise RuntimeError("blind input schema drift")
    supplied=doc.get("blindInputSha256")
    core={k:v for k,v in doc.items() if k!="blindInputSha256"}
    computed=hashlib.sha256(compact(core)).hexdigest()
    if supplied!=computed or supplied!=FULL_INPUT_SHA256:
        raise RuntimeError(f"blind input SHA drift: {computed} / {supplied}")

def load_pool(doc: dict[str,Any], v46_partition: dict[str,Any], exclusions: dict[str,Any]) -> tuple[list[dict[str,Any]],set[str]]:
    source_ids=sorted(
        v46_partition["source_partitions"]["validation"]["source_group_ids"]+
        v46_partition["source_partitions"]["confirmation"]["source_group_ids"]
    )
    if len(source_ids)!=POOL_SOURCES or len(set(source_ids))!=POOL_SOURCES:
        raise RuntimeError("V47 source pool count drift")
    if list_sha(source_ids)!=POOL_SOURCE_SHA256:
        raise RuntimeError("V47 source pool SHA drift")
    source_set=set(source_ids)
    excluded_ids=sorted(exclusions.get("observation_ids",[]))
    if len(excluded_ids)!=435 or list_sha(excluded_ids)!=EXCLUSION_ID_LIST_SHA256:
        raise RuntimeError("V46 exclusion custody drift")
    excluded=set(excluded_ids)
    obs=[o for o in doc["observations"] if o["sourceGroupId"] in source_set and o["id"] not in excluded]
    obs.sort(key=lambda o:(o["sourceGroupId"],o["id"]))
    if len(obs)!=POOL_OBSERVATIONS:
        raise RuntimeError(f"V47 observation pool count drift: {len(obs)}")
    return obs,source_set

def verify_partitions(obs: list[dict[str,Any]], source_set: set[str]) -> dict[str,dict[str,Any]]:
    out={}
    for ln in ("discovery","validation","confirmation"):
        src=sorted(s for s in source_set if lane(s)==ln)
        rows=[o for o in obs if lane(o["sourceGroupId"])==ln]
        ids=sorted(o["id"] for o in rows)
        e=EXPECTED[ln]
        if len(src)!=e["sources"] or len(rows)!=e["observations"] or list_sha(src)!=e["sourceSha"] or list_sha(ids)!=e["obsSha"]:
            raise RuntimeError(f"{ln} partition drift")
        out[ln]={"sourceIds":src,"observations":rows}
    return out

def choose_parent(child: dict[str,Any], candidates: list[dict[str,Any]]) -> tuple[dict[str,Any]|None,float]:
    cr=SCALE_RANK[child["proposalScale"]]
    eligible=[]
    for p in candidates:
        pr=SCALE_RANK[p["proposalScale"]]
        if pr<=cr:
            continue
        frac=containment(child["region"],p["region"])
        if frac>=0.95:
            eligible.append((pr,-frac,area(p["region"]),p["id"],p,frac))
    if not eligible:
        return None,0.0
    eligible.sort(key=lambda x:(x[0],x[1],x[2],x[3]))
    best=eligible[0]
    return best[4],best[5]

def build_graph(obs: list[dict[str,Any]]) -> list[dict[str,Any]]:
    by_source=defaultdict(list)
    for o in obs:
        by_source[o["sourceGroupId"]].append(o)
    rows=[]
    for src in sorted(by_source):
        group=by_source[src]
        for child in sorted(group,key=lambda o:o["id"]):
            parent,frac=choose_parent(child,group)
            rows.append({
                "schema":"mark_regime_transition_geometry_row_v47_v1",
                "experimentId":EXPERIMENT_ID,
                "sourceGroupId":src,
                "observationId":child["id"],
                "proposalScale":child["proposalScale"],
                "proposalKind":child.get("proposalKind",""),
                "region":child["region"],
                "parentObservationId":parent["id"] if parent else None,
                "parentScale":parent["proposalScale"] if parent else None,
                "childContainmentFraction":frac if parent else None,
            })
    return rows

def graph_summary(rows: list[dict[str,Any]], ln: str) -> dict[str,Any]:
    parent={r["observationId"]:r["parentObservationId"] for r in rows}
    scale_pair=Counter()
    links=0
    roots=0
    for r in rows:
        if r["parentObservationId"] is None:
            roots+=1
        else:
            links+=1
            scale_pair[f'{r["proposalScale"]}->{r["parentScale"]}']+=1
    depth=Counter()
    for oid in parent:
        n=1; seen={oid}; cur=oid
        while parent[cur] is not None:
            cur=parent[cur]
            if cur in seen or cur not in parent:
                raise RuntimeError("invalid parent chain")
            seen.add(cur); n+=1
            if n>4: raise RuntimeError("scale chain exceeds four levels")
        depth[str(n)]+=1
    return {
        "lane":ln,
        "observations":len(rows),
        "sources":len(set(r["sourceGroupId"] for r in rows)),
        "linkedObservations":links,
        "roots":roots,
        "linkedFraction":links/len(rows) if rows else 0.0,
        "scalePairInventory":dict(sorted(scale_pair.items())),
        "nodeToRootChainLengthInventory":dict(sorted(depth.items())),
    }

def main() -> None:
    ap=argparse.ArgumentParser()
    ap.add_argument("--blind-input",type=Path,required=True)
    ap.add_argument("--v46-partition-freeze",type=Path,required=True)
    ap.add_argument("--v46-exclusions",type=Path,required=True)
    ap.add_argument("--out",type=Path,required=True)
    args=ap.parse_args()

    doc=json.loads(args.blind_input.read_text())
    verify_blind_input(doc)
    v46=json.loads(args.v46_partition_freeze.read_text())
    exclusions=json.loads(args.v46_exclusions.read_text())
    obs,source_set=load_pool(doc,v46,exclusions)
    parts=verify_partitions(obs,source_set)
    args.out.mkdir(parents=True,exist_ok=True)

    summaries={}
    artifact_hashes={}
    all_rows=[]
    for ln in ("discovery","validation","confirmation"):
        rows=build_graph(parts[ln]["observations"])
        path=args.out/f"{ln}-geometry.jsonl"
        h=hashlib.sha256()
        with path.open("wb") as f:
            for row in rows:
                b=compact(row)+b"\n"; f.write(b); h.update(b)
        artifact_hashes[ln]=h.hexdigest()
        summaries[ln]=graph_summary(rows,ln)
        all_rows.extend(rows)

    combined=args.out/"all-geometry.jsonl"
    h=hashlib.sha256()
    with combined.open("wb") as f:
        for row in sorted(all_rows,key=lambda r:(r["sourceGroupId"],r["observationId"])):
            b=compact(row)+b"\n"; f.write(b); h.update(b)

    summary={
        "schema":"mark_regime_transition_geometry_summary_v47_v1",
        "experimentId":EXPERIMENT_ID,
        "blindInputSha256":FULL_INPUT_SHA256,
        "sourcePoolSha256":POOL_SOURCE_SHA256,
        "regimeLabelsConsumedForParentSelection":False,
        "minimumChildContainmentFraction":0.95,
        "scaleRank":SCALE_RANK,
        "parentSelection":["lowest_higher_scale_rank","greatest_child_containment","smallest_parent_area","lexicographic_parent_observation_id"],
        "lanes":summaries,
        "laneArtifactSha256":artifact_hashes,
        "allGeometrySha256":h.hexdigest(),
    }
    (args.out/"geometry-summary.json").write_text(json.dumps(summary,indent=2)+"\n")
    print(json.dumps(summary,indent=2))

if __name__=="__main__":
    main()
