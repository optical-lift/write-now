#!/usr/bin/env python3
"""Reconstruct the frozen V2 monolithic result from deterministic shard outputs."""

import hashlib
import json
import os
import statistics
from collections import Counter
from pathlib import Path

from mark_graph_compression_v8_core import canonical_sha, sha256_file


PROTO = Path(os.environ.get(
    "MARK_TYPED_RELATIONAL_PROTOCOL",
    "research/mark/discovery-experiments/typed-relational-intervention-v2.protocol.json",
))
V5 = Path(os.environ.get("MARK_TYPED_RELATIONAL_V5", "artifact-staging/typed-relational/v5"))
V8 = Path(os.environ.get("MARK_TYPED_RELATIONAL_V8", "artifact-staging/typed-relational/v8"))
SHARDS = Path(os.environ.get("MARK_TYPED_RELATIONAL_SHARDS", "artifact-staging/typed-relational/shards"))
OUT = Path(os.environ.get("MARK_TYPED_RELATIONAL_OUT", "artifacts/mark-typed-relational-intervention-v2"))


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def locate(root, name):
    hits = list(Path(root).rglob(name))
    if len(hits) != 1:
        raise RuntimeError(f"expected one {name} under {root}, found {len(hits)}")
    return hits[0]


def signflip_p(values, iterations, salt):
    ids = [item[0] for item in values]
    nums = [item[1] for item in values]
    observed = statistics.mean(nums)
    nulls = []
    for iteration in range(int(iterations)):
        signed = []
        for oid, value in zip(ids, nums):
            h = hashlib.sha256(f"{salt}|{iteration}|{oid}".encode()).digest()
            sign = 1.0 if (h[0] & 1) else -1.0
            signed.append(sign * value)
        nulls.append(statistics.mean(signed))
    p = (1 + sum(x >= observed for x in nulls)) / (1 + len(nulls))
    return observed, p, {
        "iterations": len(nulls),
        "mean": statistics.mean(nulls),
        "min": min(nulls),
        "max": max(nulls),
        "nullAtLeastObserved": sum(x >= observed for x in nulls),
    }


def lane_summary(rows, null_cfg):
    values = [(r["observationId"], r["hierarchicalNormalizedTypedSelectivePenalty"]) for r in rows]
    observed, p, null = signflip_p(values, null_cfg["iterations"], null_cfg["seedSalt"])
    gaps = [r["hierarchicalTypedSelectivePenaltyBits"] for r in rows]
    return {
        "eligibleObservations": len(rows),
        "meanNormalizedTypedSelectivePenalty": observed,
        "medianTypedSelectivePenaltyBits": statistics.median(gaps),
        "meanTypedSelectivePenaltyBits": statistics.mean(gaps),
        "positiveFraction": sum(x > 0 for x in gaps) / len(gaps),
        "zeroFraction": sum(x == 0 for x in gaps) / len(gaps),
        "signFlipP": p,
        "null": null,
        "meanIdentityRewirePenaltyBits": statistics.mean(r["hierarchicalIdentityRewirePenaltyBits"] for r in rows),
        "meanTypeBreakingRewirePenaltyBits": statistics.mean(r["hierarchicalTypeBreakingRewirePenaltyBits"] for r in rows),
        "meanFlatTypedSelectivePenaltyBits": statistics.mean(r["flatTypedSelectivePenaltyBits"] for r in rows),
        "meanTopologyTypedSelectivePenaltyBits": statistics.mean(r["topologyTypedSelectivePenaltyBits"] for r in rows),
    }


protocol = load_json(PROTO)
if protocol.get("schema") != "mark_typed_relational_intervention_protocol_v2":
    raise RuntimeError("wrong typed relational intervention protocol")

manifest = load_json(locate(V5, "edge-pair-manifest.json"))
world = load_json(locate(V5, "critical-edge-world.json"))
projector = locate(V5, "critical-edge-observations.jsonl")
grammar_path = locate(V8, "hierarchical-graph-grammar-freeze.json")
grammar_packet = load_json(grammar_path)

if manifest.get("edgePairManifestSha256") != protocol["parentV5"]["expectedEdgePairManifestSha256"]:
    raise RuntimeError("V5 manifest parent drift")
if world.get("criticalEdgeWorldSha256") != protocol["parentV5"]["expectedCriticalEdgeWorldSha256"]:
    raise RuntimeError("V5 world parent drift")
projector_sha = sha256_file(projector)
if projector_sha != protocol["parentV5"]["expectedProjectorRowsSha256"]:
    raise RuntimeError("V5 projector rows drift")
freeze_sha = grammar_packet.get("grammarFreezeSha256")
if canonical_sha({k: v for k, v in grammar_packet.items() if k != "grammarFreezeSha256"}) != freeze_sha:
    raise RuntimeError("V8 grammar internal hash mismatch")
if freeze_sha != protocol["parentV8"]["expectedGrammarFreezeSha256"]:
    raise RuntimeError("wrong V8 grammar freeze")
if grammar_packet.get("roleLabelsOpenedDuringInduction") is not False:
    raise RuntimeError("V8 grammar label-custody contract violated")
if grammar_packet.get("parentProjectorRowsSha256") != projector_sha:
    raise RuntimeError("V8/V5 projector lineage mismatch")

worker_paths = sorted(SHARDS.rglob("worker.json"))
if not worker_paths:
    raise RuntimeError("no shard worker packets found")
workers = [load_json(path) for path in worker_paths]
shard_counts = {int(worker["shardCount"]) for worker in workers}
if len(shard_counts) != 1:
    raise RuntimeError(f"mixed shard counts: {sorted(shard_counts)}")
shard_count = next(iter(shard_counts))
if len(workers) != shard_count:
    raise RuntimeError(f"expected {shard_count} worker packets, found {len(workers)}")
indices = sorted(int(worker["shardIndex"]) for worker in workers)
if indices != list(range(shard_count)):
    raise RuntimeError(f"missing or duplicate shard indices: {indices}")


def shard_for(observation_id):
    digest = hashlib.sha256(str(observation_id).encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big") % shard_count


for worker in workers:
    if worker.get("schema") != "mark_typed_relational_intervention_shard_worker_v1":
        raise RuntimeError("wrong shard worker schema")
    if worker.get("assignment") != "uint64_be(sha256(observationId)[0:8]) mod shardCount":
        raise RuntimeError("shard assignment rule drift")
    if worker.get("scientificSelectorModified") is not False or worker.get("scientificScorerModified") is not False:
        raise RuntimeError("worker reports scientific-code modification")
    if worker.get("expectedGrammarFreezeSha256") != freeze_sha:
        raise RuntimeError("worker grammar parent drift")
    if worker.get("expectedProjectorRowsSha256") != projector_sha:
        raise RuntimeError("worker projector parent drift")

eligible = set(world["pairEligibleObservationIds"])
lanes = {protocol["population"]["primaryLane"], protocol["population"]["replicationLane"]}
expected_counts = Counter()
projector_order = {}
ordered_candidate_ids = []
with projector.open("r", encoding="utf-8") as handle:
    for raw in handle:
        if not raw.strip():
            continue
        row = json.loads(raw)
        oid = row["observationId"]
        if oid not in eligible or row["lane"] not in lanes:
            continue
        if oid in projector_order:
            raise RuntimeError(f"duplicate candidate observation ID in frozen projector: {oid}")
        projector_order[oid] = len(ordered_candidate_ids)
        ordered_candidate_ids.append(oid)
        expected_counts[shard_for(oid)] += 1

worker_by_index = {int(worker["shardIndex"]): worker for worker in workers}
for index in range(shard_count):
    observed = int(worker_by_index[index]["candidatePopulationSeen"])
    expected = int(expected_counts[index])
    if observed != expected:
        raise RuntimeError(f"shard {index} candidate coverage drift: worker={observed} expected={expected}")

rows = []
seen_intervention_ids = set()
for worker_path, worker in zip(worker_paths, workers):
    index = int(worker["shardIndex"])
    interventions_path = worker_path.with_name("interventions.jsonl")
    if not interventions_path.exists():
        raise RuntimeError(f"missing interventions.jsonl for shard {index}")
    local_count = 0
    with interventions_path.open("r", encoding="utf-8") as handle:
        for raw in handle:
            if not raw.strip():
                continue
            row = json.loads(raw)
            oid = row["observationId"]
            if oid not in projector_order:
                raise RuntimeError(f"shard {index} emitted noncandidate observation {oid}")
            if shard_for(oid) != index:
                raise RuntimeError(f"observation {oid} emitted by wrong shard {index}")
            if oid in seen_intervention_ids:
                raise RuntimeError(f"duplicate intervention observation {oid}")
            seen_intervention_ids.add(oid)
            rows.append(row)
            local_count += 1
    if local_count != int(worker["eligibleInterventions"]):
        raise RuntimeError(
            f"shard {index} intervention coverage drift: rows={local_count} worker={worker['eligibleInterventions']}"
        )

if not rows:
    raise RuntimeError("no eligible typed relational interventions across shards")

# Restore the exact monolithic projector order before scientific aggregation.
rows.sort(key=lambda row: projector_order[row["observationId"]])
seen = len(ordered_candidate_ids)

summaries = {}
for lane in sorted(lanes):
    lane_rows = [r for r in rows if r["lane"] == lane]
    summaries[lane] = lane_summary(lane_rows, protocol["null"]) if lane_rows else None

g = protocol["gates"]
holdout = summaries.get("holdout")
control = summaries.get("control")
if holdout is None or control is None:
    adjudication = "INFEASIBLE"
elif (
    holdout["eligibleObservations"] < g["minimumEligibleHoldoutObservations"]
    or control["eligibleObservations"] < g["minimumEligibleControlObservations"]
):
    adjudication = "INFEASIBLE"
else:
    passes = (
        holdout["positiveFraction"] >= g["holdoutPositiveFractionMinimum"]
        and control["positiveFraction"] >= g["controlPositiveFractionMinimum"]
        and holdout["meanNormalizedTypedSelectivePenalty"] > g["holdoutMeanNormalizedSelectivePenaltyMinimum"]
        and control["meanNormalizedTypedSelectivePenalty"] > g["controlMeanNormalizedSelectivePenaltyMinimum"]
        and holdout["signFlipP"] <= g["holdoutSignFlipPMaximum"]
        and control["signFlipP"] <= g["controlSignFlipPMaximum"]
    )
    adjudication = "TYPED_RELATION_CLASS_SUPPORTED" if passes else "TYPED_RELATION_CLASS_NOT_DISTINGUISHED"

OUT.mkdir(parents=True, exist_ok=True)
with (OUT / "interventions.jsonl").open("w", encoding="utf-8") as handle:
    for row in rows:
        handle.write(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n")

# Keep the scientific result schema byte-for-byte compatible in structure with
# the original monolithic script. Sharding provenance lives in execution.json.
result = {
    "schema": "mark_typed_relational_intervention_result_v2",
    "experimentId": protocol["experimentId"],
    "designContext": protocol["designContext"],
    "grammarFreezeSha256": freeze_sha,
    "parentEdgePairManifestSha256": manifest.get("edgePairManifestSha256"),
    "parentCriticalEdgeWorldSha256": world.get("criticalEdgeWorldSha256"),
    "projectorRowsSha256": projector_sha,
    "candidatePopulationSeen": seen,
    "eligibleInterventions": len(rows),
    "laneSummaries": summaries,
    "adjudication": adjudication,
}
result_sha = canonical_sha(result)
result["resultSha256"] = result_sha
(OUT / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")

execution = {
    "schema": "mark_typed_relational_intervention_execution_v1",
    "mode": "deterministic-sharded",
    "shardCount": shard_count,
    "assignment": "uint64_be(sha256(observationId)[0:8]) mod shardCount",
    "scientificScriptModified": False,
    "scientificSelectorModified": False,
    "scientificScorerModified": False,
    "monolithicProjectorOrderRestoredBeforeAggregation": True,
    "candidatePopulationCoverageVerifiedAgainstFrozenProjector": True,
    "workers": workers,
}
(OUT / "execution.json").write_text(json.dumps(execution, indent=2, sort_keys=True) + "\n", encoding="utf-8")

lines = [
    "# Mark typed relational intervention v2",
    "",
    f"Adjudication: **{adjudication}**",
    f"Eligible matched interventions: **{len(rows)}** from {seen} pair-eligible heldout/control observations.",
    "",
]
for lane in ("holdout", "control"):
    s = summaries.get(lane)
    if s is None:
        lines.append(f"- {lane}: no eligible interventions")
        continue
    lines.append(
        f"- {lane}: n={s['eligibleObservations']}; "
        f"mean normalized type-breaking-minus-identity penalty={s['meanNormalizedTypedSelectivePenalty']:+.8f}; "
        f"median bits={s['medianTypedSelectivePenaltyBits']:+.1f}; "
        f"positive fraction={s['positiveFraction']:.3f}; "
        f"sign-flip p={s['signFlipP']:.6f}; "
        f"identity rewire penalty={s['meanIdentityRewirePenaltyBits']:+.2f} bits; "
        f"type-breaking rewire penalty={s['meanTypeBreakingRewirePenaltyBits']:+.2f} bits; "
        f"flat mean selective={s['meanFlatTypedSelectivePenaltyBits']:+.2f} bits; "
        f"topology mean selective={s['meanTopologyTypedSelectivePenaltyBits']:+.2f} bits"
    )
lines.extend([
    "",
    "Both counterfactuals change exact node adjacency using the same two edges. Both preserve node identities and terminal labels, node/edge count, per-node degree, complete edge-label inventory, connected components, cycle rank, and raw V8 code length. The identity rewire preserves the selected endpoint structural-type relation signature; the type-breaking rewire changes that signature.",
    "",
    "This test was designed after V1 returned RELATIONSHIP_EFFECT_NOT_DISTINGUISHED. It therefore does not rescue V1's literal node-identity claim; it tests a narrower representational claim aligned to what the frozen V8 grammar actually encodes.",
    "",
    "A pass supports typed structural relationship classes as a protected level in the frozen blind grammar. It does not establish historical semantics or prove conscious machine encoding.",
    "",
    f"Result SHA-256: `{result_sha}`",
])
(OUT / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
print("\n".join(lines), flush=True)
