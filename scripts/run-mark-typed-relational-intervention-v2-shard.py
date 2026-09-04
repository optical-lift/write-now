#!/usr/bin/env python3
"""Execution-only deterministic shard wrapper for typed relational intervention v2.

This file does not alter the frozen scientific selector or scorer. It filters only
which observation rows are exposed to the existing V2 script's enumeration loop.
The original full projector remains in place so the existing custody SHA check is
still performed against the exact frozen V5 parent.
"""

import hashlib
import json
import os
import runpy
import tempfile
from pathlib import Path


SCRIPT = Path("scripts/test-mark-typed-relational-intervention-v2.py")
V5 = Path(os.environ.get("MARK_TYPED_RELATIONAL_V5", "artifact-staging/typed-relational/v5"))
OUT = Path(os.environ.get("MARK_TYPED_RELATIONAL_OUT", "artifacts/mark-typed-relational-intervention-v2"))
PROTO = Path(os.environ.get(
    "MARK_TYPED_RELATIONAL_PROTOCOL",
    "research/mark/discovery-experiments/typed-relational-intervention-v2.protocol.json",
))
SHARD_INDEX = int(os.environ["MARK_TYPED_RELATIONAL_SHARD_INDEX"])
SHARD_COUNT = int(os.environ["MARK_TYPED_RELATIONAL_SHARD_COUNT"])

if SHARD_COUNT < 1 or not (0 <= SHARD_INDEX < SHARD_COUNT):
    raise RuntimeError(f"invalid shard {SHARD_INDEX}/{SHARD_COUNT}")


def locate(root, name):
    hits = list(Path(root).rglob(name))
    if len(hits) != 1:
        raise RuntimeError(f"expected one {name} under {root}, found {len(hits)}")
    return hits[0]


def shard_for(observation_id):
    digest = hashlib.sha256(str(observation_id).encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big") % SHARD_COUNT


protocol = json.loads(PROTO.read_text(encoding="utf-8"))
world = json.loads(locate(V5, "critical-edge-world.json").read_text(encoding="utf-8"))
projector = locate(V5, "critical-edge-observations.jsonl")
eligible = set(world["pairEligibleObservationIds"])
lanes = {protocol["population"]["primaryLane"], protocol["population"]["replicationLane"]}

assigned_candidate_rows = 0
with tempfile.TemporaryDirectory(prefix=f"mark-v2-shard-{SHARD_INDEX:02d}-") as tmp:
    filtered = Path(tmp) / "critical-edge-observations.jsonl"
    with projector.open("r", encoding="utf-8") as source, filtered.open("w", encoding="utf-8") as target:
        for raw in source:
            if not raw.strip():
                continue
            row = json.loads(raw)
            if shard_for(row["observationId"]) != SHARD_INDEX:
                continue
            target.write(raw)
            if row["observationId"] in eligible and row["lane"] in lanes:
                assigned_candidate_rows += 1

    original_path_open = Path.open
    projector_resolved = projector.resolve()
    filtered_resolved = filtered.resolve()

    def sharded_path_open(self, mode="r", *args, **kwargs):
        # The frozen script's sha256_file() uses built-in open(), so its custody
        # hash continues to read the unmodified full projector. Only the later
        # Path.open() enumeration is redirected to this shard.
        if self.resolve() == projector_resolved and "r" in mode and "b" not in mode:
            return original_path_open(filtered_resolved, mode, *args, **kwargs)
        return original_path_open(self, mode, *args, **kwargs)

    Path.open = sharded_path_open
    no_interventions = False
    try:
        runpy.run_path(str(SCRIPT), run_name="__main__")
    except RuntimeError as exc:
        if str(exc) != "no eligible typed relational interventions":
            raise
        no_interventions = True
    finally:
        Path.open = original_path_open

OUT.mkdir(parents=True, exist_ok=True)
interventions_path = OUT / "interventions.jsonl"
if no_interventions:
    interventions_path.write_text("", encoding="utf-8")

if not interventions_path.exists():
    raise RuntimeError("shard completed without interventions.jsonl")

intervention_count = sum(1 for line in interventions_path.open("r", encoding="utf-8") if line.strip())
partial_result_path = OUT / "result.json"
if partial_result_path.exists():
    partial = json.loads(partial_result_path.read_text(encoding="utf-8"))
    if int(partial["candidatePopulationSeen"]) != assigned_candidate_rows:
        raise RuntimeError(
            f"shard seen-count drift: script={partial['candidatePopulationSeen']} expected={assigned_candidate_rows}"
        )
    if int(partial["eligibleInterventions"]) != intervention_count:
        raise RuntimeError("shard intervention-count drift")

worker = {
    "schema": "mark_typed_relational_intervention_shard_worker_v1",
    "shardIndex": SHARD_INDEX,
    "shardCount": SHARD_COUNT,
    "assignment": "uint64_be(sha256(observationId)[0:8]) mod shardCount",
    "candidatePopulationSeen": assigned_candidate_rows,
    "eligibleInterventions": intervention_count,
    "expectedGrammarFreezeSha256": protocol["parentV8"]["expectedGrammarFreezeSha256"],
    "expectedProjectorRowsSha256": protocol["parentV5"]["expectedProjectorRowsSha256"],
    "scientificScript": str(SCRIPT),
    "scientificSelectorModified": False,
    "scientificScorerModified": False,
}
(OUT / "worker.json").write_text(json.dumps(worker, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(
    f"shard={SHARD_INDEX}/{SHARD_COUNT};candidate_population={assigned_candidate_rows};"
    f"eligible_interventions={intervention_count}",
    flush=True,
)
