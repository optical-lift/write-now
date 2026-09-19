#!/usr/bin/env python3
"""Validate Law-Equivalence Adjudication Language v1 instrument files."""
from __future__ import annotations
import json, pathlib

ROOT=pathlib.Path(__file__).resolve().parents[1]
EXP=ROOT/"research"/"mark"/"discovery-experiments"

spec=EXP/"law-equivalence-adjudication-v1.spec.md"
schema=EXP/"law-equivalence-adjudication-v1.schema.json"
cal=EXP/"law-equivalence-adjudication-v1.calibration.json"
res=EXP/"law-equivalence-adjudication-v1.calibration-results.json"

for p in (spec,schema,cal,res):
    if not p.exists():
        raise SystemExit(f"FAIL: missing {p.name}")

cases=json.loads(cal.read_text())["cases"]
results=json.loads(res.read_text())["results"]
if len(cases)!=8 or len(results)!=8:
    raise SystemExit("FAIL: expected 8 calibration cases/results")

expected={c["id"]:c["expected"] for c in cases}
actual={r["case_id"]:r["primary_relation"] for r in results}
if expected!=actual:
    raise SystemExit(f"FAIL: calibration mismatch: {expected} != {actual}")

allowed={
"SAME_LAW","SAME_LAW_OPPOSITE_VIEW","SAME_LAW_DIFFERENT_PATH",
"DISTINCT_LAW_SHARED_PATTERN","COMPOSED_RELATION","ANALOGOUS_ONLY",
"UNDERDETERMINED","CONTRADICTORY"
}
if set(actual.values())!=allowed:
    raise SystemExit("FAIL: calibration does not exercise every relation class exactly once")

text=spec.read_text()
guards=[
"genuinely different relevant condition means a different law",
"number of physical steps",
"Dependency topology is decisive",
"Strict condition rule",
"Freeze-before-application rule",
]
for g in guards:
    if g not in text:
        raise SystemExit(f"FAIL: missing guard phrase: {g}")

print("PASS: law-equivalence instrument present; all 8 relation classes calibrated; strict condition/path/view guards preserved.")
