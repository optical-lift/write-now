#!/usr/bin/env python3
import hashlib
import json
import os
from collections import Counter, defaultdict
from pathlib import Path

packet_dir = Path(os.environ.get("MARK_MASKED_SLOT_PACKET", "artifact-staging/masked-slot"))
context_dir = Path(os.environ.get("MARK_SOURCE_CONTEXT", "artifact-staging/context"))
out_dir = Path(os.environ.get("MARK_MASKED_SLOT_REJOIN_OUT", "artifacts/mark-masked-slot-substitution-v1-context"))

def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))

def canonical_sha(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest()

vocab = load_json(packet_dir / "vocabulary" / "masked-slot-vocabulary.json")
vocab_sha = vocab["maskedSlotVocabularySha256"]
if canonical_sha({k:v for k,v in vocab.items() if k != "maskedSlotVocabularySha256"}) != vocab_sha:
    raise RuntimeError("masked-slot vocabulary SHA mismatch")

sub = load_json(packet_dir / "substitution" / "masked-slot-substitution.json")
sub_sha = sub["maskedSlotSubstitutionDiscoverySha256"]
if canonical_sha({k:v for k,v in sub.items() if k != "maskedSlotSubstitutionDiscoverySha256"}) != sub_sha:
    raise RuntimeError("masked-slot substitution SHA mismatch")
if sub["parentMaskedSlotVocabularySha256"] != vocab_sha:
    raise RuntimeError("substitution/vocabulary parent mismatch")
if sub.get("provenanceAvailableDuringDiscovery"):
    raise RuntimeError("substitution packet was not blind")

summary = load_json(context_dir / "summary.json")
if summary.get("schema") != "mark_source_rule_atlas_context_rejoin_v1":
    raise RuntimeError("unexpected source context schema")

contexts = {}
with (context_dir / "source-rule-context.jsonl").open(encoding="utf-8") as handle:
    for line in handle:
        if line.strip():
            row = json.loads(line)
            contexts.setdefault(row["blindRow"]["sourceGroupId"], row["sourceContext"])

slots = {}
with (packet_dir / "vocabulary" / "slot-assignments.jsonl").open(encoding="utf-8") as handle:
    for line in handle:
        if line.strip():
            r = json.loads(line)
            slots[r["observationId"]] = r
occupants = {}
with (packet_dir / "vocabulary" / "occupant-assignments.jsonl").open(encoding="utf-8") as handle:
    for line in handle:
        if line.strip():
            r = json.loads(line)
            occupants[r["observationId"]] = r
if set(slots) != set(occupants):
    raise RuntimeError("assignment mismatch during context rejoin")

missing = sorted({r["sourceGroupId"] for r in slots.values()} - set(contexts))
if missing:
    raise RuntimeError(f"missing provenance for {len(missing)} masked-slot sources")

joined = []
for oid in sorted(slots):
    s, o = slots[oid], occupants[oid]
    joined.append({
        "observationId": oid,
        "sourceGroupId": s["sourceGroupId"],
        "lane": s["lane"],
        "slotFamily": int(s["slotFamily"]),
        "occupantFamily": int(o["occupantFamily"]),
        "region": s["region"],
    })

def example_rows(pair, limit_per_side=5):
    a, b = pair["occupantFamilyA"], pair["occupantFamilyB"]
    shared = set(pair["train"]["sharedSlotFamilyIds"]) | set(pair["holdout"]["sharedSlotFamilyIds"]) | set(pair["control"]["sharedSlotFamilyIds"])
    out = {"occupantA": [], "occupantB": []}
    seen = {"occupantA": set(), "occupantB": set()}
    for side, family in (("occupantA", a), ("occupantB", b)):
        candidates = [r for r in joined if r["occupantFamily"] == family and r["slotFamily"] in shared]
        candidates.sort(key=lambda r: (r["lane"], r["slotFamily"], r["sourceGroupId"], r["observationId"]))
        for r in candidates:
            if r["sourceGroupId"] in seen[side]:
                continue
            seen[side].add(r["sourceGroupId"])
            out[side].append({**r, "sourceContext": contexts[r["sourceGroupId"]]})
            if len(out[side]) >= limit_per_side:
                break
    return out

pair_context = []
for pair in sub["frozenSubstitutionCandidatePairs"][:12]:
    pair_context.append({
        "occupantFamilyA": pair["occupantFamilyA"],
        "occupantFamilyB": pair["occupantFamilyB"],
        "physicalCentroidDistance": pair["physicalCentroidDistance"],
        "trainCosine": pair["train"]["cosineSlotDistribution"],
        "holdoutCosine": pair["holdout"]["cosineSlotDistribution"],
        "controlCosine": pair["control"]["cosineSlotDistribution"],
        "samePairHighAcrossAllLanes": pair["samePairHighAcrossAllLanes"],
        "examples": example_rows(pair),
    })

institution = defaultdict(lambda: {"observations": 0, "sources": set(), "occupantFamilies": Counter(), "slotFamilies": Counter()})
for r in joined:
    inst = contexts[r["sourceGroupId"]].get("institution", "unknown")
    slot = institution[inst]
    slot["observations"] += 1
    slot["sources"].add(r["sourceGroupId"])
    slot["occupantFamilies"][str(r["occupantFamily"])] += 1
    slot["slotFamilies"][str(r["slotFamily"])] += 1

institution_rows = []
for inst, values in sorted(institution.items()):
    institution_rows.append({
        "institution": inst,
        "sources": len(values["sources"]),
        "observations": values["observations"],
        "occupantFamilyCounts": dict(values["occupantFamilies"]),
        "slotFamilyCounts": dict(values["slotFamilies"]),
    })

core = {
    "schema": "mark_masked_slot_substitution_context_rejoin_v1",
    "sealedMaskedSlotVocabularySha256": vocab_sha,
    "sealedMaskedSlotSubstitutionDiscoverySha256": sub_sha,
    "blindStatisticsPreserved": True,
    "topSubstitutionPairContext": pair_context,
    "institutionDistributionsAfterFreeze": institution_rows,
    "contract": {
        "slotVocabularyUnchanged": True,
        "occupantVocabularyUnchanged": True,
        "pairSelectionUnchanged": True,
        "substitutionStatisticsUnchanged": True,
        "sourceContextAttachedOnlyAfterSubstitutionSha": True,
        "historicalOrSemanticMeaningNotAutomaticallyAssigned": True,
    },
}
digest = canonical_sha(core)
packet = {**core, "contextRejoinSha256": digest}
out_dir.mkdir(parents=True, exist_ok=True)
(out_dir / "masked-slot-substitution-context-rejoin.json").write_text(json.dumps(packet, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
(out_dir / "summary.txt").write_text("\n".join([
    f"masked_slot_vocabulary_sha256={vocab_sha}",
    f"masked_slot_substitution_sha256={sub_sha}",
    f"context_rejoin_sha256={digest}",
    f"institutions={len(institution_rows)}",
    f"contextualized_pairs={len(pair_context)}",
    "blind_statistics_preserved=true",
]) + "\n", encoding="utf-8")
print(json.dumps(packet, indent=2, ensure_ascii=False))
