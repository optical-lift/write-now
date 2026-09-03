#!/usr/bin/env python3
import hashlib
import json
import math
import os
import random
from collections import Counter, defaultdict
from pathlib import Path

protocol_path = Path(os.environ.get("MARK_MASKED_SLOT_PROTOCOL", "research/mark/discovery-experiments/masked-slot-substitution-v1.protocol.json"))
vocab_dir = Path(os.environ.get("MARK_MASKED_SLOT_VOCAB", "artifacts/mark-masked-slot-vocabulary-v1"))
out_dir = Path(os.environ.get("MARK_MASKED_SLOT_OUT", "artifacts/mark-masked-slot-substitution-v1"))

def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))

def canonical_bytes(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")

def canonical_sha(value):
    return hashlib.sha256(canonical_bytes(value)).hexdigest()

def mean(xs):
    return sum(xs) / len(xs) if xs else 0.0

def cosine(a, b):
    dot = sum(x*y for x, y in zip(a, b))
    na = math.sqrt(sum(x*x for x in a))
    nb = math.sqrt(sum(y*y for y in b))
    return dot / (na*nb) if na and nb else 0.0

def entropy(counts):
    total = sum(counts)
    if total <= 0:
        return 0.0
    out = 0.0
    for count in counts:
        if count:
            p = count / total
            out -= p * math.log(p)
    return out

def normalized_entropy(counts):
    if sum(1 for c in counts if c) <= 1:
        return 0.0
    return entropy(counts) / math.log(len(counts)) if len(counts) > 1 else 0.0

def normalized_mutual_information(rows, slot_ids, occupant_ids):
    total = len(rows)
    if total == 0:
        return 0.0
    sc = Counter(r["slotFamily"] for r in rows)
    oc = Counter(r["occupantFamily"] for r in rows)
    joint = Counter((r["slotFamily"], r["occupantFamily"]) for r in rows)
    mi = 0.0
    for (s, o), n in joint.items():
        p = n / total
        ps = sc[s] / total
        po = oc[o] / total
        mi += p * math.log(p / (ps * po))
    hs = entropy([sc[s] for s in slot_ids])
    ho = entropy([oc[o] for o in occupant_ids])
    denom = math.sqrt(hs * ho)
    return mi / denom if denom else 0.0

protocol = load_json(protocol_path)
if protocol.get("schema") != "mark_masked_slot_substitution_protocol_v1":
    raise RuntimeError("unexpected masked-slot protocol")

vocab = load_json(vocab_dir / "masked-slot-vocabulary.json")
if vocab.get("schema") != "mark_masked_slot_vocabulary_v1":
    raise RuntimeError("unexpected masked-slot vocabulary")
vocab_sha = vocab.get("maskedSlotVocabularySha256")
core = {k: v for k, v in vocab.items() if k != "maskedSlotVocabularySha256"}
if canonical_sha(core) != vocab_sha:
    raise RuntimeError("masked-slot vocabulary SHA mismatch")
if not vocab.get("contract", {}).get("slotAndOccupantVocabulariesFrozenBeforeTheirAssociationIsComputed"):
    raise RuntimeError("vocabulary was not frozen before association")
if not vocab.get("contract", {}).get("targetTopologyUnavailableToSlotDefinition"):
    raise RuntimeError("masked-slot leakage contract missing")
if vocab.get("provenanceAvailableDuringDiscovery"):
    raise RuntimeError("vocabulary consumed provenance")

slot_bytes = (vocab_dir / "slot-assignments.jsonl").read_bytes()
occ_bytes = (vocab_dir / "occupant-assignments.jsonl").read_bytes()
if hashlib.sha256(slot_bytes).hexdigest() != vocab["assignmentFiles"]["slotAssignmentsSha256"]:
    raise RuntimeError("slot assignment file SHA mismatch")
if hashlib.sha256(occ_bytes).hexdigest() != vocab["assignmentFiles"]["occupantAssignmentsSha256"]:
    raise RuntimeError("occupant assignment file SHA mismatch")

slots = {}
for line in slot_bytes.splitlines():
    if line.strip():
        r = json.loads(line)
        slots[r["observationId"]] = r
occupants = {}
for line in occ_bytes.splitlines():
    if line.strip():
        r = json.loads(line)
        occupants[r["observationId"]] = r
if set(slots) != set(occupants):
    raise RuntimeError("slot/occupant assignment observation mismatch")

joined = []
for oid in sorted(slots):
    s, o = slots[oid], occupants[oid]
    for key in ("sourceGroupId", "lane"):
        if s[key] != o[key]:
            raise RuntimeError(f"slot/occupant custody mismatch for {oid}")
    joined.append({
        "observationId": oid,
        "sourceGroupId": s["sourceGroupId"],
        "lane": s["lane"],
        "slotFamily": int(s["slotFamily"]),
        "occupantFamily": int(o["occupantFamily"]),
        "parentObservationId": s["parentObservationId"],
        "proposalScale": s.get("proposalScale", ""),
        "region": s["region"],
    })

slot_ids = sorted(map(int, vocab["slotVocabulary"]["centroids"].keys()))
occupant_ids = sorted(map(int, vocab["occupantVocabulary"]["centroids"].keys()))
lanes = ["train", "holdout", "control"]

def lane_rows(lane):
    return [r for r in joined if r["lane"] == lane]

def family_slot_vector(rows, occupant):
    counts = Counter(r["slotFamily"] for r in rows if r["occupantFamily"] == occupant)
    return [counts[s] for s in slot_ids]

def family_source_support(rows, occupant):
    return len({r["sourceGroupId"] for r in rows if r["occupantFamily"] == occupant})

def pair_stats(rows, a, b):
    va, vb = family_slot_vector(rows, a), family_slot_vector(rows, b)
    shared_slots = [slot_ids[i] for i, (x, y) in enumerate(zip(va, vb)) if x and y]
    source_slot_occ = defaultdict(lambda: defaultdict(set))
    for r in rows:
        if r["occupantFamily"] in (a, b):
            source_slot_occ[r["sourceGroupId"]][r["slotFamily"]].add(r["occupantFamily"])
    same_source_same_slot = sum(
        1 for source in source_slot_occ
        if any({a, b}.issubset(fams) for fams in source_slot_occ[source].values())
    )
    return {
        "cosineSlotDistribution": cosine(va, vb),
        "sharedSlotFamilies": len(shared_slots),
        "sharedSlotFamilyIds": shared_slots,
        "balancedSharedSlotMass": sum(min(x, y) for x, y in zip(va, vb)),
        "occupantAOccurrences": sum(va),
        "occupantBOccurrences": sum(vb),
        "occupantADistinctSources": family_source_support(rows, a),
        "occupantBDistinctSources": family_source_support(rows, b),
        "sourcesWithBothOccupantsInSameSlotFamily": same_source_same_slot,
    }

occ_centroids = {int(k): v for k, v in vocab["occupantVocabulary"]["centroids"].items()}
all_pairs = []
for i, a in enumerate(occupant_ids):
    for b in occupant_ids[i+1:]:
        d = math.sqrt(sum((x-y)**2 for x, y in zip(occ_centroids[a], occ_centroids[b])))
        all_pairs.append((a, b, d))
distance_median = sorted(d for _, _, d in all_pairs)[len(all_pairs)//2] if all_pairs else 0.0

train = lane_rows("train")
pair_candidates = []
min_sources = int(protocol["substitutionTest"]["minimumTrainDistinctSourcesPerOccupant"])
for a, b, d in all_pairs:
    stats = pair_stats(train, a, b)
    eligible = (
        d >= distance_median
        and stats["occupantADistinctSources"] >= min_sources
        and stats["occupantBDistinctSources"] >= min_sources
        and stats["sharedSlotFamilies"] > 0
    )
    if not eligible:
        continue
    pair_candidates.append({
        "occupantFamilyA": a,
        "occupantFamilyB": b,
        "physicalCentroidDistance": d,
        "train": stats,
    })
pair_candidates.sort(key=lambda r: (
    -r["train"]["cosineSlotDistribution"],
    -r["train"]["sharedSlotFamilies"],
    -min(r["train"]["occupantADistinctSources"], r["train"]["occupantBDistinctSources"]),
    -r["physicalCentroidDistance"],
    r["occupantFamilyA"],
    r["occupantFamilyB"],
))
max_pairs = int(protocol["substitutionTest"]["maximumFrozenCandidatePairs"])
frozen_pairs = pair_candidates[:max_pairs]

null_iterations = int(protocol["nullModel"]["iterations"])
def correspondence_null(rows, a, b, iteration, lane):
    if len(occupant_ids) < 2:
        return 0.0
    rng = random.Random(int(hashlib.sha256(f"masked-slot-correspondence|{lane}|{iteration}|{a}|{b}".encode()).hexdigest()[:16], 16))
    x, y = rng.sample(occupant_ids, 2)
    return pair_stats(rows, x, y)["cosineSlotDistribution"]

def eval_pair(pair, lane):
    rows = lane_rows(lane)
    a, b = pair["occupantFamilyA"], pair["occupantFamilyB"]
    observed = pair_stats(rows, a, b)
    nulls = [correspondence_null(rows, a, b, i, lane) for i in range(null_iterations)]
    all_lane_pair_sims = []
    for i, x in enumerate(occupant_ids):
        for y in occupant_ids[i+1:]:
            all_lane_pair_sims.append(pair_stats(rows, x, y)["cosineSlotDistribution"])
    obs = observed["cosineSlotDistribution"]
    observed.update({
        "randomPairNullMeanCosine": mean(nulls),
        "randomPairNullMaximumCosine": max(nulls) if nulls else 0.0,
        "randomPairNullAtLeastObserved": sum(v >= obs for v in nulls),
        "beatsAllRandomPairNulls": bool(nulls) and obs > max(nulls),
        "pairSimilarityPercentileAmongAllPhysicalFamilies": (
            sum(v <= obs for v in all_lane_pair_sims) / len(all_lane_pair_sims)
            if all_lane_pair_sims else 0.0
        ),
    })
    return observed

for pair in frozen_pairs:
    pair["holdout"] = eval_pair(pair, "holdout")
    pair["control"] = eval_pair(pair, "control")
    pair["samePairHighAcrossAllLanes"] = (
        pair["train"]["cosineSlotDistribution"] >= float(protocol["substitutionTest"]["minimumTrainCosineForStrongCandidate"])
        and pair["holdout"]["pairSimilarityPercentileAmongAllPhysicalFamilies"] >= 0.75
        and pair["control"]["pairSimilarityPercentileAmongAllPhysicalFamilies"] >= 0.75
    )

slot_family_rows = []
for slot in slot_ids:
    lane_metrics = {}
    for lane in lanes:
        rows = [r for r in lane_rows(lane) if r["slotFamily"] == slot]
        counts = Counter(r["occupantFamily"] for r in rows)
        lane_metrics[lane] = {
            "observations": len(rows),
            "distinctSources": len({r["sourceGroupId"] for r in rows}),
            "occupantFamilyCounts": {str(o): counts[o] for o in occupant_ids},
            "occupantFamilyDiversity": sum(1 for o in occupant_ids if counts[o]),
            "normalizedOccupantEntropy": normalized_entropy([counts[o] for o in occupant_ids]),
        }
    slot_family_rows.append({"slotFamily": slot, "lanes": lane_metrics})

lane_independence = {}
for lane in lanes:
    rows = lane_rows(lane)
    lane_independence[lane] = {
        "observations": len(rows),
        "slotOccupantNormalizedMutualInformation": normalized_mutual_information(rows, slot_ids, occupant_ids),
    }

core = {
    "schema": "mark_masked_slot_substitution_discovery_v1",
    "experimentId": protocol["experimentId"],
    "parentMaskedSlotVocabularySha256": vocab_sha,
    "provenanceAvailableDuringDiscovery": False,
    "question": protocol["question"],
    "maskableObservations": len(joined),
    "slotFamilies": len(slot_ids),
    "occupantFamilies": len(occupant_ids),
    "physicalDifferenceGate": {
        "occupantCentroidPairDistanceMedian": distance_median,
        "candidateRequiresDistanceAtOrAboveMedian": True,
    },
    "laneSlotOccupantDependence": lane_independence,
    "slotFamilyOccupantDiversity": slot_family_rows,
    "frozenSubstitutionCandidatePairs": frozen_pairs,
    "contract": {
        "candidatePairsSelectedFromTrainOnly": True,
        "holdoutAndControlDoNotAlterVocabularyOrPairSelection": True,
        "physicallyDifferentMeansTrainOccupantCentroidDistanceAtOrAbovePairMedian": True,
        "functionalSimilarityMeansSimilarityOfSlotFamilyOccupancyDistribution": True,
        "crossLaneNullRandomizesPhysicalFamilyCorrespondenceNotSlotAssignments": True,
        "noLocalStateIdsConsumed": True,
        "noTransitionGrammarConsumed": True,
        "noProvenanceConsumed": True,
    },
}
digest = canonical_sha(core)
packet = {**core, "maskedSlotSubstitutionDiscoverySha256": digest}

out_dir.mkdir(parents=True, exist_ok=True)
(out_dir / "masked-slot-substitution.json").write_text(json.dumps(packet, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
(out_dir / "substitution-pairs.json").write_text(json.dumps(frozen_pairs, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
(out_dir / "slot-family-diversity.json").write_text(json.dumps(slot_family_rows, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

summary_lines = [
    f"masked_slot_vocabulary_sha256={vocab_sha}",
    f"masked_slot_substitution_sha256={digest}",
    f"maskable_observations={len(joined)}",
    f"slot_families={len(slot_ids)}",
    f"occupant_families={len(occupant_ids)}",
    f"frozen_candidate_pairs={len(frozen_pairs)}",
]
for idx, pair in enumerate(frozen_pairs[:10], 1):
    summary_lines.append(
        f"pair_{idx}=O{pair['occupantFamilyA']}~O{pair['occupantFamilyB']};"
        f"physical_distance={pair['physicalCentroidDistance']:.6f};"
        f"train_cosine={pair['train']['cosineSlotDistribution']:.6f};"
        f"holdout_cosine={pair['holdout']['cosineSlotDistribution']:.6f};"
        f"control_cosine={pair['control']['cosineSlotDistribution']:.6f};"
        f"same_pair_high_all_lanes={str(pair['samePairHighAcrossAllLanes']).lower()}"
    )
(out_dir / "summary.txt").write_text("\n".join(summary_lines) + "\n", encoding="utf-8")
print(json.dumps(packet, indent=2, ensure_ascii=False))
