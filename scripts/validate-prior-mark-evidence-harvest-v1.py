#!/usr/bin/env python3
"""Validate Prior-Mark Evidence and Constraint Harvest v1.

Dependency-free custody validation. This does not adjudicate scientific
equivalence; it checks packet continuity, provenance, supersession, and the
no-law/no-matching boundary required before later comparison work.
"""

from __future__ import annotations
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
EXP = ROOT / "research" / "mark" / "discovery-experiments"

PARTS = [
    EXP / "relational-law-observation-packet-v1.pilot.part1.jsonl",
    EXP / "relational-law-observation-packet-v1.pilot.part2.jsonl",
    EXP / "relational-law-observation-packet-v1.pilot.part3.jsonl",
    EXP / "prior-mark-evidence-harvest-v1.part1.jsonl",
    EXP / "prior-mark-evidence-harvest-v1.part2.jsonl",
    EXP / "prior-mark-evidence-harvest-v1.part3.jsonl",
    EXP / "prior-mark-evidence-harvest-v1.part4.jsonl",
    EXP / "prior-mark-evidence-harvest-v1.part5.jsonl",
    EXP / "prior-mark-evidence-harvest-v1.part6.jsonl",
]

SUPERSEDED = {f"RLOP-{i:03d}" for i in range(1, 7)}
ACTIVE = {f"RLOP-{i:03d}" for i in range(7, 91)}

def fail(msg: str) -> None:
    raise SystemExit(f"FAIL: {msg}")

def main() -> None:
    packets = []
    for path in PARTS:
        if not path.exists():
            fail(f"missing part: {path.name}")
        for lineno, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if not raw.strip():
                continue
            try:
                p = json.loads(raw)
            except json.JSONDecodeError as exc:
                fail(f"{path.name}:{lineno}: invalid JSON: {exc}")
            packets.append((path.name, lineno, p))

    ids = [p["packet_id"] for _, _, p in packets]
    expected = [f"RLOP-{i:03d}" for i in range(1, 91)]

    if len(packets) != 90:
        fail(f"expected 90 packets, found {len(packets)}")
    if len(set(ids)) != 90:
        fail("duplicate packet IDs")
    if sorted(ids) != expected:
        fail("packet IDs are not exactly RLOP-001..RLOP-090")

    for source, lineno, p in packets:
        where = f"{source}:{lineno}"
        evidence = p.get("evidence", {})
        iso = p.get("isolation", {})
        epi = p.get("epistemic", {})
        lane = p.get("discovery_lane", {})

        if evidence.get("provenance_class") not in {
            "frozen_result",
            "post_result_synthesis",
            "diagnostic_result",
            "protocol_or_design_only",
        }:
            fail(f"{where}: missing/invalid provenance_class")
        if not evidence.get("source_refs"):
            fail(f"{where}: no source refs")
        if iso.get("packet_construction_independent") is not True:
            fail(f"{where}: independent packet construction not affirmed")
        if iso.get("cross_source_matching_performed") is not False:
            fail(f"{where}: new cross-source matching contamination")
        if iso.get("external_semantic_labels_used") != []:
            fail(f"{where}: external semantic label contamination")
        if iso.get("universal_law_label") is not None:
            fail(f"{where}: universal-law label assigned")
        if iso.get("candidate_equivalences") != []:
            fail(f"{where}: candidate equivalence created")
        if not epi.get("supported_statement"):
            fail(f"{where}: missing epistemic ceiling")
        if not lane.get("experiment_scope"):
            fail(f"{where}: missing historical experiment scope")

    all_ids = set(ids)
    if not SUPERSEDED <= all_ids:
        fail("superseded pilot IDs missing")
    if not ACTIVE <= all_ids:
        fail("active packet set incomplete")
    if SUPERSEDED & ACTIVE:
        fail("active and superseded sets overlap")

    manifest = json.loads(
        (EXP / "prior-mark-evidence-harvest-v1.manifest.json").read_text(encoding="utf-8")
    )
    if manifest["canonical_active_packet_set"]["count"] != 84:
        fail("manifest active count is not 84")
    if manifest["contamination_guard"]["universal_law_labels_assigned"] is not False:
        fail("manifest contamination guard changed")

    print(
        "PASS: 90 total packets; 84 active; RLOP-001..006 superseded only; "
        "provenance/source refs present; no law labels, candidate equivalences, "
        "external semantic labels, or new cross-source matching."
    )

if __name__ == "__main__":
    main()
