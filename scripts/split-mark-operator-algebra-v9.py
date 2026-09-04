#!/usr/bin/env python3
import hashlib
import json
import os
from pathlib import Path

from mark_operator_algebra_v9_core import canonical_sha

protocol_path = Path(os.environ.get("MARK_V9_PROTOCOL", "research/mark/discovery-experiments/operator-composition-algebra-v9.protocol.json"))
v5_dir = Path(os.environ.get("MARK_V5_PACKET", "artifact-staging/v5"))
out_dir = Path(os.environ.get("MARK_V9_SPLIT", "artifact-staging/v9-split"))


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def locate(name):
    hits = list(v5_dir.rglob(name))
    if len(hits) != 1:
        raise RuntimeError(f"expected one V5 {name}, found {len(hits)}")
    return hits[0]


def sha_file(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()

protocol = load_json(protocol_path)
parent = protocol["parentV5"]
manifest = load_json(locate("edge-pair-manifest.json"))
world = load_json(locate("critical-edge-world.json"))
projector = locate("critical-edge-observations.jsonl")

manifest_sha = manifest.get("edgePairManifestSha256")
world_sha = world.get("criticalEdgeWorldSha256")
if canonical_sha({k: v for k, v in manifest.items() if k != "edgePairManifestSha256"}) != manifest_sha:
    raise RuntimeError("V5 edge-pair manifest self-hash mismatch")
if canonical_sha({k: v for k, v in world.items() if k != "criticalEdgeWorldSha256"}) != world_sha:
    raise RuntimeError("V5 critical-edge world self-hash mismatch")
if manifest_sha != parent["expectedEdgePairManifestSha256"]:
    raise RuntimeError("wrong V5 edge-pair manifest")
if world_sha != parent["expectedCriticalEdgeWorldSha256"]:
    raise RuntimeError("wrong V5 critical-edge world")
if sha_file(projector) != parent["expectedProjectorRowsSha256"] or sha_file(projector) != world["projectorRowsSha256"]:
    raise RuntimeError("V5 projector rows hash mismatch")

eligible = set(world["pairEligibleObservationIds"])
if len(eligible) != int(parent["expectedPairEligibleObservations"]):
    raise RuntimeError("unexpected V5 pair-eligible observation count")

out_dir.mkdir(parents=True, exist_ok=True)
paths = {lane: out_dir / f"{lane}.jsonl" for lane in ("train", "holdout", "control")}
handles = {lane: path.open("w", encoding="utf-8") for lane, path in paths.items()}
counts = {lane: 0 for lane in paths}
try:
    with projector.open("r", encoding="utf-8") as source:
        for raw in source:
            row = json.loads(raw)
            if row["observationId"] not in eligible:
                continue
            lane = row["lane"]
            if lane not in handles:
                raise RuntimeError(f"unexpected lane {lane}")
            handles[lane].write(raw if raw.endswith("\n") else raw + "\n")
            counts[lane] += 1
finally:
    for handle in handles.values():
        handle.close()

if sum(counts.values()) != len(eligible):
    raise RuntimeError(f"split count mismatch: {counts}")

split_manifest = {
    "schema": "mark_operator_algebra_split_v9",
    "experimentId": protocol["experimentId"],
    "parentEdgePairManifestSha256": manifest_sha,
    "parentCriticalEdgeWorldSha256": world_sha,
    "parentProjectorRowsSha256": world["projectorRowsSha256"],
    "eligibleObservations": len(eligible),
    "lanes": {
        lane: {"observations": counts[lane], "sha256": sha_file(paths[lane])}
        for lane in sorted(paths)
    },
    "featureComputationDuringSplit": False,
    "roleLabelsOpened": False
}
split_manifest["splitSha256"] = canonical_sha(split_manifest)
(out_dir / "split-manifest.json").write_text(json.dumps(split_manifest, indent=2) + "\n", encoding="utf-8")
print(json.dumps(split_manifest, indent=2))
