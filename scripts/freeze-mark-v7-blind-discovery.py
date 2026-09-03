#!/usr/bin/env python3
import hashlib
import json
import math
import os
import sqlite3
from pathlib import Path

compiler_out = Path(os.environ.get("MARK_V7_OUT", "artifacts/mark-blind-discovery-compiler-v1"))
compiler_input_path = Path(os.environ.get("MARK_V7_COMPILER_INPUT", "artifact-staging/blind-evidence/mark-conveyor-input-v1/mark-observable-input-blind-v1.compiler.json"))
protocol_path = Path(os.environ.get("MARK_DISCOVERY_PROTOCOL", "research/mark/discovery-experiments/blind-discovery-v1.protocol.json"))
out_dir = Path(os.environ.get("MARK_DISCOVERY_OUT", "artifacts/mark-blind-discovery-v1"))


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_sha256(value) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return sha256_bytes(payload)


protocol_bytes = protocol_path.read_bytes()
protocol = json.loads(protocol_bytes)
if protocol.get("schema") != "mark_blind_discovery_protocol_v1":
    raise RuntimeError(f"unsupported discovery protocol {protocol.get('schema')}")
summary = load_json(compiler_out / "summary.json")
custody = load_json(compiler_out / "custody.json")
evaluation = load_json(compiler_out / "evaluation.json")
compiler_input = load_json(compiler_input_path)
if summary.get("schema") != "mark_sparse_compiler_summary_v2":
    raise RuntimeError("unexpected compiler summary schema")
if custody.get("schema") != "mark_sparse_ledger_custody_v2":
    raise RuntimeError("unexpected compiler custody schema")
if summary.get("sourceBlindInputSha256") != custody.get("sourceBlindInputSha256"):
    raise RuntimeError("summary/custody blind-input hash mismatch")
if summary.get("sourceBlindInputSha256") != compiler_input.get("blindInputSha256"):
    raise RuntimeError("compiler input hash does not match compiler output")
if summary.get("grammarRowsMaterialized") != 0:
    raise RuntimeError("blind science must run on the frozen rowless v7 contract")

stats_db = compiler_out / "grammar-stats.sqlite"
db_bytes = stats_db.read_bytes()
db_sha = sha256_bytes(db_bytes)
if db_sha != custody.get("grammarStatistics", {}).get("databaseSha256"):
    raise RuntimeError("sufficient-statistics database SHA-256 mismatch")

rules = []
with (compiler_out / "rules.jsonl").open("r", encoding="utf-8") as handle:
    for line in handle:
        line = line.strip()
        if line:
            rules.append(json.loads(line))
if len(rules) != evaluation.get("rules"):
    raise RuntimeError("rules.jsonl count disagrees with compiler evaluation")

null_iterations = int(protocol["evaluation"]["nullIterations"])
if null_iterations != int(summary.get("nullIterations", -1)):
    raise RuntimeError("protocol null-iteration count disagrees with compiler run")
minimum_sources = int(protocol["evaluation"]["minimumTrainSourceObjectsPerRule"])

connection = sqlite3.connect(f"file:{stats_db}?mode=ro", uri=True)
connection.row_factory = sqlite3.Row


def scalar(query, params):
    row = connection.execute(query, params).fetchone()
    if row is None or row[0] is None:
        return 0
    return int(row[0])


def lane_rule_stats(lane: str, context: str, outcome: str):
    observed_total = scalar(
        "SELECT SUM(count) FROM grammar_stats WHERE iteration=-1 AND lane=? AND context=?",
        (lane, context),
    )
    observed_predicted = scalar(
        "SELECT count FROM grammar_stats WHERE iteration=-1 AND lane=? AND context=? AND outcome=?",
        (lane, context, outcome),
    )
    context_sources = scalar(
        "SELECT source_count FROM context_stats WHERE iteration=-1 AND lane=? AND context=?",
        (lane, context),
    )
    predicted_sources = scalar(
        "SELECT source_count FROM grammar_stats WHERE iteration=-1 AND lane=? AND context=? AND outcome=?",
        (lane, context, outcome),
    )
    observed_accuracy = (observed_predicted / observed_total) if observed_total else 0.0
    null_accuracies = []
    for iteration in range(null_iterations):
        total = scalar(
            "SELECT SUM(count) FROM grammar_stats WHERE iteration=? AND lane=? AND context=?",
            (iteration, lane, context),
        )
        predicted = scalar(
            "SELECT count FROM grammar_stats WHERE iteration=? AND lane=? AND context=? AND outcome=?",
            (iteration, lane, context, outcome),
        )
        null_accuracies.append((predicted / total) if total else 0.0)
    null_mean = sum(null_accuracies) / len(null_accuracies) if null_accuracies else 0.0
    lift = observed_accuracy - null_mean
    null_exceedances = sum(1 for value in null_accuracies if value >= observed_accuracy)
    return {
        "contextCount": str(observed_total),
        "predictedOutcomeCount": str(observed_predicted),
        "contextSourceObjects": context_sources,
        "predictedOutcomeSourceObjects": predicted_sources,
        "accuracy": observed_accuracy,
        "nullMeanAccuracy": null_mean,
        "accuracyLift": lift,
        "nullIterations": null_iterations,
        "nullAccuracyMinimum": min(null_accuracies) if null_accuracies else 0.0,
        "nullAccuracyMaximum": max(null_accuracies) if null_accuracies else 0.0,
        "nullExceedances": null_exceedances,
        "observedBeatsAllNulls": bool(null_accuracies) and null_exceedances == 0,
    }


ranked = []
for rule in rules:
    context = rule["context"]
    outcome = rule["predictedOutcome"]
    holdout = lane_rule_stats("holdout", context, outcome)
    control = lane_rule_stats("control", context, outcome)
    specificity_lift = holdout["accuracyLift"] - max(0.0, control["accuracyLift"])
    support_ok = holdout["predictedOutcomeSourceObjects"] >= minimum_sources
    if support_ok and holdout["accuracyLift"] > 0 and specificity_lift > 0 and holdout["observedBeatsAllNulls"]:
        tier = "A"
    elif support_ok and holdout["accuracyLift"] > 0 and specificity_lift > 0:
        tier = "B"
    elif support_ok and holdout["accuracyLift"] > 0:
        tier = "C"
    else:
        tier = "exploratory"
    ranked.append({
        "schema": "mark_v7_blind_rule_evaluation_v1",
        "context": context,
        "predictedOutcome": outcome,
        "train": {
            "distinctSourceObjects": int(rule["distinctSourceObjects"]),
            "contextSourceObjects": int(rule["contextSourceObjects"]),
            "supportCount": str(rule["supportCount"]),
        },
        "holdout": holdout,
        "control": control,
        "specificityLift": specificity_lift,
        "candidateTier": tier,
    })

ranked.sort(key=lambda row: (
    -row["specificityLift"],
    -row["holdout"]["accuracyLift"],
    -row["holdout"]["predictedOutcomeSourceObjects"],
    row["control"]["accuracyLift"],
    row["context"],
    row["predictedOutcome"],
))
for index, row in enumerate(ranked, start=1):
    row["blindRank"] = index

packet_core = {
    "schema": "mark_v7_blind_discovery_packet_v1",
    "experimentId": protocol["experimentId"],
    "protocolSha256": sha256_bytes(protocol_bytes),
    "sourceBlindInputSha256": summary["sourceBlindInputSha256"],
    "sourceHarvestSha256": compiler_input.get("sourceHarvestSha256"),
    "compilerCustody": {
        "physicalLedgerMerkleRoot": summary.get("physicalLedgerMerkleRoot"),
        "grammarContributionMerkleRoot": summary.get("grammarContributionMerkleRoot"),
        "grammarStatisticsDatabaseSha256": db_sha,
        "sources": summary.get("sources"),
        "observations": summary.get("observations"),
        "grammarRowsMaterialized": summary.get("grammarRowsMaterialized"),
        "grammarStatRows": summary.get("grammarStatRows"),
        "contextStatRows": summary.get("contextStatRows"),
    },
    "aggregateEvaluation": evaluation,
    "rankingContract": protocol["ranking"],
    "candidateTierContract": protocol["candidateTiers"],
    "allTrainDerivedRulesFrozen": True,
    "ruleCount": len(ranked),
    "rules": ranked,
    "blindnessContract": protocol["blindnessContract"],
    "rejoinContract": protocol["rejoinContract"],
    "scientificInterpretationAuthorized": False,
    "semanticClaimsAuthorized": False,
    "provenanceRejoinMayProceed": True,
}
packet_sha = canonical_sha256(packet_core)
packet = {**packet_core, "blindDiscoverySha256": packet_sha}
out_dir.mkdir(parents=True, exist_ok=True)
(out_dir / "blind-discovery.json").write_text(json.dumps(packet, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
summary_lines = [
    f"schema={packet['schema']}",
    f"blind_discovery_sha256={packet_sha}",
    f"rules={len(ranked)}",
    f"tier_A={sum(1 for row in ranked if row['candidateTier'] == 'A')}",
    f"tier_B={sum(1 for row in ranked if row['candidateTier'] == 'B')}",
    f"tier_C={sum(1 for row in ranked if row['candidateTier'] == 'C')}",
    f"exploratory={sum(1 for row in ranked if row['candidateTier'] == 'exploratory')}",
    f"holdout_accuracy={evaluation.get('holdout', {}).get('accuracy')}",
    f"holdout_null_mean_accuracy={evaluation.get('holdout', {}).get('nullMeanAccuracy')}",
    f"control_accuracy={evaluation.get('control', {}).get('accuracy')}",
    f"control_null_mean_accuracy={evaluation.get('control', {}).get('nullMeanAccuracy')}",
]
(out_dir / "summary.txt").write_text("\n".join(summary_lines) + "\n", encoding="utf-8")
connection.close()
print(json.dumps({"blindDiscoverySha256": packet_sha, "rules": len(ranked), "tiers": {tier: sum(1 for row in ranked if row["candidateTier"] == tier) for tier in ["A", "B", "C", "exploratory"]}}, indent=2))
