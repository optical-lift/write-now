#!/usr/bin/env python3
import hashlib
import json
import os
from collections import Counter, defaultdict
from pathlib import Path

operator_dir = Path(os.environ.get("MARK_OPERATOR_PACKET", "artifact-staging/operator"))
context_dir = Path(os.environ.get("MARK_SOURCE_CONTEXT", "artifact-staging/context"))
out_dir = Path(os.environ.get("MARK_OPERATOR_REJOIN_OUT", "artifacts/mark-state-operator-discovery-v1-context"))


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def canonical_sha(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).hexdigest()


packet = load_json(operator_dir / "state-operator-discovery.json")
if packet.get("schema") != "mark_state_operator_discovery_v1":
    raise RuntimeError("unexpected operator packet")
sha = packet.get("stateOperatorDiscoverySha256")
core = {k: v for k, v in packet.items() if k != "stateOperatorDiscoverySha256"}
if canonical_sha(core) != sha:
    raise RuntimeError("operator packet SHA mismatch")
if packet.get("provenanceAvailableDuringDiscovery"):
    raise RuntimeError("operator packet was not blind")
cluster_sha = packet.get("state2LatentAliasDefinitionSha256")
if not cluster_sha:
    raise RuntimeError("operator packet lacks frozen State 2 alias definition")

summary = load_json(context_dir / "summary.json")
if summary.get("schema") != "mark_source_rule_atlas_context_rejoin_v1":
    raise RuntimeError("unexpected source context schema")
contexts = {}
with (context_dir / "source-rule-context.jsonl").open(encoding="utf-8") as handle:
    for line in handle:
        if line.strip():
            row = json.loads(line)
            contexts.setdefault(row["blindRow"]["sourceGroupId"], row["sourceContext"])

clusters = []
with (operator_dir / "state2-latent-clusters.jsonl").open(encoding="utf-8") as handle:
    for line in handle:
        if line.strip():
            row = json.loads(line)
            if row.get("state2LatentAliasDefinitionSha256") != cluster_sha:
                raise RuntimeError("latent alias assignment SHA mismatch during context rejoin")
            clusters.append(row)

edges = []
with (operator_dir / "state2-cluster-exit-edges.jsonl").open(encoding="utf-8") as handle:
    for line in handle:
        if line.strip():
            row = json.loads(line)
            if row.get("state2LatentAliasDefinitionSha256") != cluster_sha:
                raise RuntimeError("exit edge SHA mismatch during context rejoin")
            edges.append(row)

missing = sorted(({row["sourceGroupId"] for row in clusters} | {row["sourceGroupId"] for row in edges}) - set(contexts))
if missing:
    raise RuntimeError(f"missing provenance for {len(missing)} operator sources")

alias_ids = sorted({int(row["latentAliasId"]) for row in clusters})


def top_alias_examples(alias_id, limit=12):
    rows = [row for row in clusters if int(row["latentAliasId"]) == alias_id]
    rows.sort(key=lambda row: (-float(row.get("nearestCentroidMargin", 0.0)), row["observationId"]))
    out = []
    seen = set()
    for row in rows:
        source = row["sourceGroupId"]
        if source in seen:
            continue
        seen.add(source)
        out.append(
            {
                "observationId": row["observationId"],
                "sourceGroupId": source,
                "lane": row["lane"],
                "latentAliasId": alias_id,
                "nearestCentroidMargin": row.get("nearestCentroidMargin", 0.0),
                "region": row["region"],
                "sourceContext": contexts[source],
            }
        )
        if len(out) >= limit:
            break
    return out


institution = defaultdict(lambda: {"state2": 0, "sources": set(), "aliases": Counter(), "outcomes": Counter(), "aliasOutcomes": defaultdict(Counter)})
for row in clusters:
    source = row["sourceGroupId"]
    inst = contexts[source].get("institution", "unknown")
    slot = institution[inst]
    slot["state2"] += 1
    slot["sources"].add(source)
    slot["aliases"][str(row["latentAliasId"])] += 1
for edge in edges:
    source = edge["sourceGroupId"]
    inst = contexts[source].get("institution", "unknown")
    slot = institution[inst]
    slot["outcomes"][str(edge["childState"])] += 1
    slot["aliasOutcomes"][str(edge["latentAliasId"])][str(edge["childState"])] += 1

institution_rows = []
for inst, slot in sorted(institution.items()):
    alias_outcomes = {}
    for alias in sorted(slot["aliasOutcomes"], key=int):
        counts = slot["aliasOutcomes"][alias]
        total = sum(counts.values())
        exits = counts["1"] + counts["3"]
        alias_outcomes[alias] = {
            "outcomeCounts": dict(counts),
            "stayRate": counts["2"] / total if total else 0.0,
            "exitRate": exits / total if total else 0.0,
            "state3AmongExitsRate": counts["3"] / exits if exits else 0.0,
        }
    institution_rows.append(
        {
            "institution": inst,
            "sources": len(slot["sources"]),
            "state2Observations": slot["state2"],
            "latentAliasCounts": dict(slot["aliases"]),
            "exitOutcomeCounts": dict(slot["outcomes"]),
            "latentAliasExitBehavior": alias_outcomes,
        }
    )

context_core = {
    "schema": "mark_state_operator_context_rejoin_v1",
    "sealedStateOperatorDiscoverySha256": sha,
    "sealedState2LatentAliasDefinitionSha256": cluster_sha,
    "blindOperatorStatisticsPreserved": True,
    "primaryQuestion": packet["primaryQuestion"],
    "primaryFalsifier": packet["primaryFalsifier"],
    "institutionAliasDynamics": institution_rows,
    "highMarginContextExamplesByLatentAlias": {str(alias): top_alias_examples(alias) for alias in alias_ids},
    "contract": {
        "selectedFeaturesUnchanged": True,
        "chosenKUnchanged": True,
        "trainCentroidsUnchanged": True,
        "aliasAssignmentsUnchanged": True,
        "exitAssociationStatisticsUnchanged": True,
        "sourceContextAttachedOnlyAfterOperatorSha": True,
        "contextExamplesDidNotDefineAliases": True,
        "semanticOrHistoricalMeaningNotAutomaticallyAssigned": True,
    },
}
digest = canonical_sha(context_core)
out = {**context_core, "contextRejoinSha256": digest}
out_dir.mkdir(parents=True, exist_ok=True)
(out_dir / "state-operator-context-rejoin.json").write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
(out_dir / "summary.txt").write_text(
    "\n".join(
        [
            f"sealed_operator_sha256={sha}",
            f"sealed_state2_latent_alias_definition_sha256={cluster_sha}",
            f"context_rejoin_sha256={digest}",
            f"institutions={len(institution_rows)}",
            f"latent_aliases={len(alias_ids)}",
            "selected_features_preserved=true",
            "chosen_k_preserved=true",
            "alias_assignments_preserved=true",
            "exit_statistics_preserved=true",
        ]
    )
    + "\n",
    encoding="utf-8",
)
print(json.dumps(out, indent=2, ensure_ascii=False))
