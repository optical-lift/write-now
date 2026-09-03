#!/usr/bin/env python3
import hashlib
import json
import os
import sqlite3
from collections import defaultdict
from pathlib import Path

atlas_dir = Path(os.environ.get("MARK_SOURCE_RULE_ATLAS", "artifacts/mark-source-rule-atlas-v1"))
compiler_dir = Path(os.environ.get("MARK_V7_OUT", "artifacts/mark-source-rule-compiler-v1"))
discovery_path = Path(os.environ.get("MARK_BLIND_DISCOVERY_PACKET", "artifacts/mark-blind-discovery-v1/blind-discovery.json"))
out_path = Path(os.environ.get("MARK_SOURCE_RULE_ASSERTION", atlas_dir / "exactness.json"))

summary = json.loads((atlas_dir / "summary.json").read_text(encoding="utf-8"))
if summary.get("schema") != "mark_source_rule_atlas_summary_v1":
    raise RuntimeError("unexpected source-rule atlas summary schema")

discovery = json.loads(discovery_path.read_text(encoding="utf-8"))
if discovery.get("schema") != "mark_v7_blind_discovery_packet_v1":
    raise RuntimeError("unexpected blind discovery packet schema")
if summary.get("sealedBlindDiscoverySha256") != discovery.get("blindDiscoverySha256"):
    raise RuntimeError("atlas/blind-discovery SHA chain mismatch")

rows_path = atlas_dir / "source-rule-atlas.jsonl"
rows_bytes = rows_path.read_bytes()
rows_sha = hashlib.sha256(rows_bytes).hexdigest()
if rows_sha != summary.get("rowsSha256"):
    raise RuntimeError("source-rule row SHA-256 mismatch")

preimage = "|".join([
    "mark_source_rule_atlas_v1",
    str(summary.get("sealedBlindDiscoverySha256", "")),
    str(summary.get("sourceBlindInputSha256", "")),
    str(summary.get("physicalLedgerMerkleRoot", "")),
    rows_sha,
    str(summary.get("sourceObjects", "")),
    str(summary.get("rules", "")),
    str(summary.get("sourceRuleRows", "")),
])
computed_atlas_sha = hashlib.sha256(preimage.encode("utf-8")).hexdigest()
if computed_atlas_sha != summary.get("atlasSha256"):
    raise RuntimeError("source-rule atlas SHA-256 mismatch")

frozen_rules = {}
for rule in discovery.get("rules", []):
    rank = int(rule["blindRank"])
    if rank in frozen_rules:
        raise RuntimeError(f"duplicate frozen blind rank {rank}")
    frozen_rules[rank] = rule
if len(frozen_rules) != int(summary.get("rules", -1)):
    raise RuntimeError("atlas rule count differs from frozen discovery")

aggregate = defaultdict(lambda: {"context": 0, "predicted": 0, "sources": set()})
row_count = 0
with rows_path.open("r", encoding="utf-8") as handle:
    for line in handle:
        line = line.strip()
        if not line:
            continue
        row = json.loads(line)
        if row.get("schema") != "mark_source_rule_atlas_row_v1":
            raise RuntimeError("unexpected atlas row schema")
        rank = int(row["blindRank"])
        rule = frozen_rules.get(rank)
        if rule is None:
            raise RuntimeError(f"atlas contains non-frozen rule rank {rank}")
        if row.get("context") != rule.get("context") or row.get("predictedOutcome") != rule.get("predictedOutcome"):
            raise RuntimeError(f"atlas row changed frozen rule identity at rank {rank}")
        if row.get("candidateTier") != rule.get("candidateTier"):
            raise RuntimeError(f"atlas row changed frozen candidate tier at rank {rank}")
        context_count = int(row["contextCount"])
        predicted_count = int(row["predictedOutcomeCount"])
        if context_count <= 0:
            raise RuntimeError("sparse atlas emitted a non-positive context row")
        if predicted_count < 0 or predicted_count > context_count:
            raise RuntimeError("invalid predicted/context multiplicity in atlas row")
        key = (row["lane"], rank)
        aggregate[key]["context"] += context_count
        aggregate[key]["predicted"] += predicted_count
        aggregate[key]["sources"].add(row["sourceGroupId"])
        row_count += 1

if row_count != int(summary.get("sourceRuleRows", -1)):
    raise RuntimeError("atlas row count differs from frozen summary")

connection = sqlite3.connect(f"file:{compiler_dir / 'grammar-stats.sqlite'}?mode=ro", uri=True)
checks = []
for rank, rule in sorted(frozen_rules.items()):
    context = rule["context"]
    outcome = rule["predictedOutcome"]
    for lane in ["train", "holdout", "control"]:
        expected_context = connection.execute(
            "SELECT COALESCE(SUM(count),0) FROM grammar_stats WHERE iteration=-1 AND lane=? AND context=?",
            (lane, context),
        ).fetchone()[0]
        expected_predicted = connection.execute(
            "SELECT COALESCE(count,0) FROM grammar_stats WHERE iteration=-1 AND lane=? AND context=? AND outcome=?",
            (lane, context, outcome),
        ).fetchone()
        expected_predicted = expected_predicted[0] if expected_predicted else 0
        actual = aggregate[(lane, rank)]
        if int(expected_context) != actual["context"]:
            raise RuntimeError(
                f"source-rule context total mismatch lane={lane} rank={rank}: atlas={actual['context']} compiler={expected_context}"
            )
        if int(expected_predicted) != actual["predicted"]:
            raise RuntimeError(
                f"source-rule predicted total mismatch lane={lane} rank={rank}: atlas={actual['predicted']} compiler={expected_predicted}"
            )
        checks.append({
            "lane": lane,
            "blindRank": rank,
            "context": context,
            "predictedOutcome": outcome,
            "contextCount": str(actual["context"]),
            "predictedOutcomeCount": str(actual["predicted"]),
            "sourceObjectsWithContext": len(actual["sources"]),
            "exactlyMatchesCompiler": True,
        })
connection.close()

assertion = {
    "schema": "mark_source_rule_atlas_exactness_v1",
    "atlasSha256": summary["atlasSha256"],
    "sealedBlindDiscoverySha256": summary["sealedBlindDiscoverySha256"],
    "rowsSha256": rows_sha,
    "sourceRuleRows": row_count,
    "frozenRules": len(frozen_rules),
    "laneRuleChecks": checks,
    "contract": {
        "allAtlasRowsBelongToFrozenRules": True,
        "blindRanksAndTiersPreserved": True,
        "sparseRowsHavePositiveContext": True,
        "sourceAggregatesExactlyEqualV7ObservedGrammarStatistics": True,
        "comparisonIteration": -1,
        "comparisonLanes": ["train", "holdout", "control"],
    },
    "status": "passed",
}
out_path.parent.mkdir(parents=True, exist_ok=True)
out_path.write_text(json.dumps(assertion, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print(json.dumps(assertion, indent=2, ensure_ascii=False))
