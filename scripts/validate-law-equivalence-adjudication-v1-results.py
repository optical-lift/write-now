#!/usr/bin/env python3
"""Validate complete Law-Equivalence Adjudication v1 results."""
from __future__ import annotations
import json, pathlib

ROOT=pathlib.Path(__file__).resolve().parents[1]
P=ROOT/"research"/"mark"/"discovery-experiments"/"law-equivalence-adjudication-v1.results.json"
data=json.loads(P.read_text(encoding="utf-8"))
rows=data["adjudications"]

expected=[f"LEA-{i:03d}" for i in range(1,29)]
ids=[r["adjudication_id"] for r in rows]
if ids!=expected:
    raise SystemExit("FAIL: adjudication IDs not exactly LEA-001..LEA-028")
if len({*ids})!=28:
    raise SystemExit("FAIL: duplicate adjudication IDs")

counts={}
for r in rows:
    counts[r["primary_relation"]]=counts.get(r["primary_relation"],0)+1
    if r.get("universal_law_label") is not None:
        raise SystemExit("FAIL: universal law label assigned")

wanted={
    "SAME_LAW":6,
    "DISTINCT_LAW_SHARED_PATTERN":17,
    "UNDERDETERMINED":3,
    "ANALOGOUS_ONLY":2,
}
if counts!=wanted:
    raise SystemExit(f"FAIL: unexpected counts {counts}")

clusters=data["same_law_equivalence_clusters"]
if len(clusters)!=2:
    raise SystemExit("FAIL: expected exactly two current same-law equivalence clusters")
if set(clusters[0]["mark_constraints"])!={"MCR-016","MCR-034","MCR-083","MCR-087","MCR-007"}:
    raise SystemExit("FAIL: EQC-001 membership changed")
if clusters[0]["canon_rule"]!="CIR-018":
    raise SystemExit("FAIL: EQC-001 canon anchor changed")
if clusters[1]["mark_constraints"]!=["MCR-010"] or clusters[1]["canon_rule"]!="CIR-022":
    raise SystemExit("FAIL: EQC-002 membership changed")

print("PASS: 28 adjudications; 6 SAME_LAW in 2 equivalence clusters; 17 distinct shared-pattern; 3 underdetermined; 2 analogous; no universal-law labels.")
