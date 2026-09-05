#!/usr/bin/env python3
import hashlib
import math
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path

from mark_hebrew_glyph_annotation_competition_v19_io import (
    NS, read_json, read_jsonl, sha256_json, write_json, write_jsonl,
)
from mark_hebrew_operator_representation_v21_core import _target_lemma_and_morph
from mark_verse_boundary_continuity_v25_core import (
    _anon, _build_shuffle_map, _median, _signflip, additive_distribution,
    boundary_origins, build_destination_model, resolved_within_verse_events,
)

REPRESENTATION = "lemmaCoarseMorph"


def _book_lane_map(book_ids, protocol):
    split = protocol["split"]
    salt = split["salt"]
    ordered = sorted(
        set(book_ids),
        key=lambda b: hashlib.sha256((salt + ":" + b).encode("utf-8")).hexdigest(),
    )
    residues = {
        "train": set(split["trainRankResidues"]),
        "holdout": set(split["holdoutRankResidues"]),
        "control": set(split["controlRankResidues"]),
    }
    mapping = {}
    for rank, book in enumerate(ordered):
        r = rank % 5
        lane = next(name for name, vals in residues.items() if r in vals)
        mapping[book] = lane
    return mapping, ordered


def parse_book_blocked_chapters(wlc_dir, protocol):
    raw = []
    books = []
    for path in sorted(Path(wlc_dir).glob("*.xml")):
        root = ET.parse(path).getroot()
        for chapter in root.findall(".//osis:chapter", NS):
            chapter_id = chapter.attrib.get("osisID")
            if not chapter_id:
                continue
            book = chapter_id.split(".")[0]
            books.append(book)
            verses_out = []
            for verse in chapter.findall(".//osis:verse", NS):
                verse_id = verse.attrib.get("osisID")
                if not verse_id:
                    continue
                lemma, coarse = [], []
                for w in verse.findall(".//osis:w", NS):
                    parsed = _target_lemma_and_morph(w)
                    if parsed is None:
                        continue
                    lem, c, _ = parsed
                    lemma.append(lem)
                    coarse.append(f"{lem}|M={c}")
                if not lemma:
                    continue
                verses_out.append({
                    "anonymousVerseId": _anon("V", verse_id),
                    "tokens": lemma,
                    "lemmaCoarseMorph": coarse,
                })
            if verses_out:
                raw.append((book, chapter_id, verses_out))

    lane_map, ordered_books = _book_lane_map(books, protocol)
    lanes = {"train": [], "holdout": [], "control": []}
    for book, chapter_id, verses in raw:
        lane = lane_map[book]
        lanes[lane].append({
            "anonymousChapterId": _anon("C", chapter_id),
            "anonymousBookId": _anon("B", book),
            "lane": lane,
            "verses": verses,
        })
    for lane in lanes:
        lanes[lane].sort(key=lambda x: x["anonymousChapterId"])

    # Reuse V25's frozen model-blind matched shuffle construction, with the V26 salt.
    shuffle_map = _build_shuffle_map(lanes, protocol)
    for chapters in lanes.values():
        for chapter in chapters:
            for verse in chapter["verses"][:-1]:
                verse["shuffleNextVerseId"] = shuffle_map.get(verse["anonymousVerseId"])
            chapter["verses"][-1]["shuffleNextVerseId"] = None

    lane_books = {
        lane: sorted({ch["anonymousBookId"] for ch in chapters})
        for lane, chapters in lanes.items()
    }
    if set(lane_books["train"]) & set(lane_books["holdout"]):
        raise ValueError("book custody overlap train/holdout")
    if set(lane_books["train"]) & set(lane_books["control"]):
        raise ValueError("book custody overlap train/control")
    if set(lane_books["holdout"]) & set(lane_books["control"]):
        raise ValueError("book custody overlap holdout/control")

    manifest = {
        "schema": "mark_coarse_boundary_book_block_packets_v26",
        "sourceCommit": protocol["hebrewSource"]["commit"],
        "bookCounts": {lane: len(ids) for lane, ids in lane_books.items()},
        "chapterCounts": {lane: len(rows) for lane, rows in lanes.items()},
        "verseCounts": {
            lane: sum(len(ch["verses"]) for ch in rows) for lane, rows in lanes.items()
        },
        "tokenCounts": {
            lane: sum(len(v["tokens"]) for ch in rows for v in ch["verses"])
            for lane, rows in lanes.items()
        },
        "bookAssignmentDigest": hashlib.sha256(
            "|".join(
                f"{_anon('B', b)}:{lane_map[b]}" for b in ordered_books
            ).encode("utf-8")
        ).hexdigest(),
        "bookDisjointAcrossLanes": True,
        "shuffleAssignments": sum(
            1 for rows in lanes.values() for ch in rows for v in ch["verses"]
            if v.get("shuffleNextVerseId")
        ),
        "representation": REPRESENTATION,
        "hardBoundary": "chapter",
    }
    return lanes, manifest


def freeze_model(train_chapters, protocol):
    events = resolved_within_verse_events(train_chapters, REPRESENTATION)
    model = build_destination_model(events, protocol)
    return {
        "representation": REPRESENTATION,
        "system": model,
    }


def evaluate_coarse(chapters, model, protocol, lane):
    origins = [
        e for e in boundary_origins(chapters, REPRESENTATION)
        if e["operator"] in set(model["operators"])
    ]
    real_resolved = [e for e in origins if e["realF"] is not None]
    shuffle_resolved = [e for e in origins if e["shuffleF"] is not None]
    common = [e for e in origins if e["realF"] is not None and e["shuffleF"] is not None]

    by_op = defaultdict(list)
    for e in common:
        dist = additive_distribution(model, e["S0"], e["S1"], e["operator"])
        delta = math.log2(max(dist[e["realF"]], 1e-300)) - math.log2(max(dist[e["shuffleF"]], 1e-300))
        by_op[e["operator"]].append(delta)

    min_events = int(protocol["evaluation"]["minimumBoundaryOriginsPerOperator"])
    op_means = {
        op: sum(vals) / len(vals)
        for op, vals in by_op.items() if len(vals) >= min_events
    }
    values = list(op_means.values())
    observed = sum(values) / len(values) if values else 0.0
    positive = sum(v > 0 for v in values) / len(values) if values else 0.0
    p = _signflip(
        values,
        f"mark-v26-coarse-book-block:{lane}",
        int(protocol["evaluation"]["permutationCount"]),
    )
    real_fraction = len(real_resolved) / len(origins) if origins else 0.0
    shuffle_fraction = len(shuffle_resolved) / len(origins) if origins else 0.0
    gate = protocol["evaluation"]["primaryGatePerLane"]
    sufficient = (
        len(op_means) >= int(protocol["evaluation"]["minimumEvaluableOperators"])
        and len(common) >= int(gate["minimumCommonResolvedOrigins"])
    )
    recovery_guard = real_fraction >= shuffle_fraction - 1e-15
    passed = (
        sufficient
        and observed > float(gate["operatorBalancedRealMinusShuffleBitsGreaterThan"])
        and p <= float(gate["pairedSignFlipPAtMost"])
        and positive >= float(gate["positiveOperatorFractionAtLeast"])
        and recovery_guard
    )
    rd = [e["realDistance"] for e in real_resolved if e["realDistance"] is not None]
    sd = [e["shuffleDistance"] for e in shuffle_resolved if e["shuffleDistance"] is not None]
    return {
        "representation": REPRESENTATION,
        "lane": lane,
        "eligibleBoundaryOrigins": len(origins),
        "commonResolvedOrigins": len(common),
        "evaluableOperators": len(op_means),
        "frozenOperators": len(model["operators"]),
        "operatorBalancedRealMinusShuffleBits": observed,
        "positiveOperatorFraction": positive,
        "signFlipP": p,
        "realRecoveryFraction": real_fraction,
        "shuffleRecoveryFraction": shuffle_fraction,
        "recoveryGuardPass": recovery_guard,
        "realOnlyResolved": sum(e["realF"] is not None and e["shuffleF"] is None for e in origins),
        "shuffleOnlyResolved": sum(e["realF"] is None and e["shuffleF"] is not None for e in origins),
        "realMeanDistance": sum(rd) / len(rd) if rd else None,
        "realMedianDistance": _median(rd),
        "shuffleMeanDistance": sum(sd) / len(sd) if sd else None,
        "shuffleMedianDistance": _median(sd),
        "sufficient": sufficient,
        "pass": passed,
        "operators": {
            op: {"commonResolvedOrigins": len(by_op[op]), "meanDeltaBits": mean}
            for op, mean in sorted(op_means.items())
        },
    }


def adjudicate(results):
    if not all(results[lane]["sufficient"] for lane in ("holdout", "control")):
        return "INSUFFICIENT_BOOK_BLOCKED_SUPPORT"
    if all(results[lane]["pass"] for lane in ("holdout", "control")):
        return "COARSE_BOUNDARY_EFFECT_ROBUST_UNDER_BOOK_BLOCKING"
    if all(results[lane]["operatorBalancedRealMinusShuffleBits"] > 0 for lane in ("holdout", "control")):
        return "COARSE_BOUNDARY_DIRECTION_REPEATS_BUT_CONFIRMATORY_GATE_FAILS"
    if all(results[lane]["operatorBalancedRealMinusShuffleBits"] <= 0 for lane in ("holdout", "control")):
        return "SHUFFLED_CONTINUATION_MATCHES_OR_BEATS_REAL"
    return "COARSE_BOUNDARY_EFFECT_DOES_NOT_REPLICATE_ACROSS_BOOK_BLOCKS"
