#!/usr/bin/env python3
"""Validate Mark Relational Law Observation Packet v1 pilot custody.

This is intentionally dependency-free. The JSON Schema remains the normative
shape contract; this script enforces the pilot's most important contamination
and completeness invariants.
"""

from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
EXP = ROOT / "research" / "mark" / "discovery-experiments"
PARTS = [
    EXP / "relational-law-observation-packet-v1.pilot.part1.jsonl",
    EXP / "relational-law-observation-packet-v1.pilot.part2.jsonl",
    EXP / "relational-law-observation-packet-v1.pilot.part3.jsonl",
]

TOP_REQUIRED = {
    "schema_version",
    "packet_id",
    "observation_kind",
    "discovery_lane",
    "evidence",
    "observation",
    "relational",
    "epistemic",
    "isolation",
}

REL_REQUIRED = {
    "participants",
    "relations_before",
    "relations_changed",
    "relations_after",
    "preserved_invariants",
    "changed_properties",
    "dependencies",
    "role_constraints",
    "boundary_conditions",
    "sequence_properties",
    "unknowns",
}


def fail(message: str) -> None:
    raise SystemExit(f"FAIL: {message}")


def main() -> None:
    packets = []
    for path in PARTS:
        if not path.exists():
            fail(f"missing pilot part: {path}")
        for lineno, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if not raw.strip():
                continue
            try:
                packet = json.loads(raw)
            except json.JSONDecodeError as exc:
                fail(f"{path.name}:{lineno}: invalid JSON: {exc}")
            packet["_source_file"] = path.name
            packet["_source_line"] = lineno
            packets.append(packet)

    if len(packets) != 27:
        fail(f"expected 27 pilot packets, found {len(packets)}")

    ids = [p.get("packet_id") for p in packets]
    if len(set(ids)) != len(ids):
        fail("duplicate packet_id detected")

    expected = [f"RLOP-{i:03d}" for i in range(1, 28)]
    if sorted(ids) != expected:
        fail(f"packet id set differs from expected RLOP-001..RLOP-027: {sorted(ids)}")

    for p in packets:
        where = f"{p['_source_file']}:{p['_source_line']}"
        missing = TOP_REQUIRED - p.keys()
        if missing:
            fail(f"{where}: missing top-level fields {sorted(missing)}")
        if p["schema_version"] != "mark_relational_law_observation_packet_v1":
            fail(f"{where}: wrong schema_version")

        evidence = p["evidence"]
        if not evidence.get("source_refs"):
            fail(f"{where}: evidence.source_refs must not be empty")
        if not evidence.get("observation_summary"):
            fail(f"{where}: evidence.observation_summary must not be empty")

        rel = p["relational"]
        missing_rel = REL_REQUIRED - rel.keys()
        if missing_rel:
            fail(f"{where}: missing relational fields {sorted(missing_rel)}")

        epi = p["epistemic"]
        if not epi.get("supported_statement"):
            fail(f"{where}: epistemic.supported_statement must not be empty")
        if "prohibited_inferences" not in epi or "unresolved" not in epi:
            fail(f"{where}: epistemic ceiling is incomplete")

        iso = p["isolation"]
        if iso.get("cross_source_matching_performed") is not False:
            fail(f"{where}: cross-source matching contamination")
        if iso.get("external_semantic_labels_used") != []:
            fail(f"{where}: external semantic labels present")
        if iso.get("universal_law_label") is not None:
            fail(f"{where}: universal law assigned during observation stage")
        if iso.get("candidate_equivalences") != []:
            fail(f"{where}: candidate equivalence assigned during observation stage")

    print(
        "PASS: 27 packets parsed; IDs complete; provenance present; "
        "epistemic ceilings present; no universal-law labels, candidate "
        "equivalences, external semantic labels, or new cross-source matching."
    )


if __name__ == "__main__":
    main()
