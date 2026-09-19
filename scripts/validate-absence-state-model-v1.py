#!/usr/bin/env python3
"""Validate Absence-State Model v1 and its calibration."""
from __future__ import annotations
import json, pathlib, importlib.util

ROOT=pathlib.Path(__file__).resolve().parents[1]
EXP=ROOT/"research"/"mark"/"discovery-experiments"
CAL=EXP/"absence-state-model-v1.calibration.json"
RES=EXP/"absence-state-model-v1.calibration-results.json"
DERIVE=ROOT/"scripts"/"derive-absence-state-v1.py"

spec=importlib.util.spec_from_file_location("absence_derive", DERIVE)
mod=importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(mod)

cal=json.loads(CAL.read_text(encoding="utf-8"))
stored=json.loads(RES.read_text(encoding="utf-8"))
cases=cal["cases"]

if len(cases)!=13:
    raise SystemExit(f"FAIL: expected 13 calibration cases, got {len(cases)}")

failures=[]
states=set()
for c in cases:
    got=mod.derive(c["axes"])
    states.add(got)
    if got!=c["expected"]:
        failures.append((c["id"],c["expected"],got))

if failures:
    raise SystemExit(f"FAIL: calibration mismatch {failures}")

if stored["passed"]!=13 or stored["total"]!=13:
    raise SystemExit("FAIL: stored calibration summary changed")

required_states={
"PRESENT",
"OPPORTUNITY_PRESENT_PROHIBITED",
"OPPORTUNITY_PRESENT_NO_INSTANCE",
"COMPATIBLE_UNUSED",
"NOT_PRESERVED",
"OUTSIDE_EXPOSED_REGION",
"NOT_YET_OBSERVED",
"STRUCTURALLY_INCOMPATIBLE",
"MEASUREMENT_UNRESOLVED",
"UNKNOWN_ABSENCE",
}
if states!=required_states:
    raise SystemExit(f"FAIL: calibration does not exercise every derived state: {states}")

print("PASS: 13 calibration cases; all 10 derived absence states exercised; precedence and tested-opportunity negative evidence preserved.")
