#!/usr/bin/env python3
import hashlib
import json
import os
from collections import defaultdict
from pathlib import Path

atlas_dir = Path(os.environ.get("MARK_SOURCE_RULE_ATLAS", "artifact-staging/blind-atlas/source-rule-atlas"))
rejoin_path = Path(os.environ.get("MARK_HARVEST_REJOIN", "artifact-staging/context-custody/mark-harvest-rejoin-v1/mark-harvest-custody-rejoin-v1.json"))
out_dir = Path(os.environ.get("MARK_SOURCE_RULE_REJOIN_OUT", "artifacts/mark-source-rule-atlas-context-v1"))

summary_path = atlas_dir / "summary.json"
rows_path = atlas_dir / "source-rule-atlas.jsonl"
summary = json.loads(summary_path.read_text(encoding="utf-8"))
if summary.get("schema") != "mark_source_rule_atlas_summary_v1":
    raise RuntimeError("unexpected source-rule atlas schema")

rows_bytes = rows_path.read_bytes()
rows_sha = hashlib.sha256(rows_bytes).hexdigest()
if rows_sha != summary.get("rowsSha256"):
    raise RuntimeError("source-rule atlas row SHA-256 mismatch before provenance rejoin")

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
    raise RuntimeError("source-rule atlas SHA-256 verification failed before provenance rejoin")

rejoin = json.loads(rejoin_path.read_text(encoding="utf-8"))
if rejoin.get("schema") != "mark_harvest_custody_rejoin_v1":
    raise RuntimeError("unexpected harvest custody rejoin schema")
if rejoin.get("sealedHarvestBlindSha256") != summary.get("sourceHarvestSha256"):
    raise RuntimeError("harvest custody does not belong to frozen source-rule atlas")

source_context = {source["sourceGroupId"]: source for source in rejoin.get("sources", [])}
out_dir.mkdir(parents=True, exist_ok=True)
out_rows_path = out_dir / "source-rule-context.jsonl"
source_ids = set()
rule_stats = defaultdict(lambda: {
    "contextSourcesByInstitution": defaultdict(set),
    "matchedSourcesByInstitution": defaultdict(set),
    "contextRows": 0,
    "matchedRows": 0,
})

with rows_path.open("r", encoding="utf-8") as source_handle, out_rows_path.open("w", encoding="utf-8") as out_handle:
    for line in source_handle:
        line = line.strip()
        if not line:
            continue
        row = json.loads(line)
        source_id = row.get("sourceGroupId")
        contextual = source_context.get(source_id)
        if contextual is None:
            raise RuntimeError(f"atlas row references source missing from custody: {source_id}")
        source_ids.add(source_id)
        institution = contextual.get("institution") or "unlabeled"
        rank = str(row.get("blindRank"))
        rule_stats[rank]["contextRows"] += 1
        rule_stats[rank]["contextSourcesByInstitution"][institution].add(source_id)
        if int(row.get("predictedOutcomeCount", "0")) > 0:
            rule_stats[rank]["matchedRows"] += 1
            rule_stats[rank]["matchedSourcesByInstitution"][institution].add(source_id)
        enriched = {
            "schema": "mark_source_rule_context_row_v1",
            "atlasSha256": summary["atlasSha256"],
            "blindRow": row,
            "sourceContext": {
                "institution": contextual.get("institution"),
                "objectId": contextual.get("objectId"),
                "sourceId": contextual.get("sourceId"),
                "sourceUrl": contextual.get("sourceUrl"),
                "rightsBasis": contextual.get("rightsBasis"),
                "retrieval": contextual.get("retrieval"),
                "context": contextual.get("context"),
            },
        }
        out_handle.write(json.dumps(enriched, ensure_ascii=False, separators=(",", ":")) + "\n")

rule_summary = {}
for rank, stats in sorted(rule_stats.items(), key=lambda item: int(item[0])):
    rule_summary[rank] = {
        "contextRows": stats["contextRows"],
        "matchedRows": stats["matchedRows"],
        "contextSourcesByInstitution": {
            institution: len(ids)
            for institution, ids in sorted(stats["contextSourcesByInstitution"].items())
        },
        "matchedSourcesByInstitution": {
            institution: len(ids)
            for institution, ids in sorted(stats["matchedSourcesByInstitution"].items())
        },
    }

contextual_summary = {
    "schema": "mark_source_rule_atlas_context_rejoin_v1",
    "sealedAtlasSha256": summary["atlasSha256"],
    "sealedBlindDiscoverySha256": summary["sealedBlindDiscoverySha256"],
    "sourceHarvestSha256": summary.get("sourceHarvestSha256"),
    "sourceRuleRows": summary["sourceRuleRows"],
    "sourceObjectsRepresented": len(source_ids),
    "rules": summary["rules"],
    "ruleContext": rule_summary,
    "contract": {
        "blindAtlasVerifiedBeforeRejoin": True,
        "blindRowsChanged": False,
        "blindRanksChanged": False,
        "sourceRuleCountsChanged": False,
        "semanticMeaningAssigned": False,
        "whatRejoined": "source custody and institutional provenance only",
    },
}
(out_dir / "summary.json").write_text(json.dumps(contextual_summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
(out_dir / "summary.txt").write_text(
    "\n".join([
        f"schema={contextual_summary['schema']}",
        f"sealed_atlas_sha256={contextual_summary['sealedAtlasSha256']}",
        f"sealed_blind_discovery_sha256={contextual_summary['sealedBlindDiscoverySha256']}",
        f"source_rule_rows={contextual_summary['sourceRuleRows']}",
        f"source_objects_represented={contextual_summary['sourceObjectsRepresented']}",
        f"rules={contextual_summary['rules']}",
    ]) + "\n",
    encoding="utf-8",
)
print(json.dumps(contextual_summary, indent=2, ensure_ascii=False))
