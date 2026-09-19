#!/usr/bin/env python3
"""Validate Mark Constraint Re-Reading v1."""
from __future__ import annotations
import json, pathlib

ROOT=pathlib.Path(__file__).resolve().parents[1]
EXP=ROOT/"research"/"mark"/"discovery-experiments"
PARTS=[EXP/f"constraint-rereading-v1.part{i}.jsonl" for i in range(1,5)]
ALLOWED_LEVEL={"observed_system","representation","measurement","cross_system","instrument_calibration"}
ALLOWED_KIND={"exclusion","dependency","non_equivalence","invariance","composition","boundary","underdetermination","transfer_limit","population_dependence"}
ALLOWED_STATUS={"eligible","supporting_only","deferred","ineligible"}

def fail(msg): raise SystemExit("FAIL: "+msg)

rows=[]
for path in PARTS:
    if not path.exists(): fail(f"missing {path.name}")
    for ln,raw in enumerate(path.read_text(encoding="utf-8").splitlines(),1):
        if not raw.strip(): continue
        try: r=json.loads(raw)
        except json.JSONDecodeError as e: fail(f"{path.name}:{ln}: {e}")
        rows.append((path.name,ln,r))

if len(rows)!=84: fail(f"expected 84 records, got {len(rows)}")
ids=[r["constraint_id"] for _,_,r in rows]
expected=[f"MCR-{i:03d}" for i in range(7,91)]
if sorted(ids)!=expected: fail("IDs not exactly MCR-007..MCR-090")
if len(set(ids))!=84: fail("duplicate IDs")

for src,ln,r in rows:
    w=f"{src}:{ln}"
    if r.get("constraint_level") not in ALLOWED_LEVEL: fail(f"{w}: invalid level")
    if r.get("constraint_kind") not in ALLOWED_KIND: fail(f"{w}: invalid kind")
    if r.get("law_candidate_status") not in ALLOWED_STATUS: fail(f"{w}: invalid status")
    if r.get("source_packet") != "RLOP-"+r["constraint_id"][4:]: fail(f"{w}: source packet mismatch")
    if not r.get("cannot_statement"): fail(f"{w}: empty cannot statement")
    if r.get("no_cross_source_matching") is not True: fail(f"{w}: matching boundary violated")
    if r.get("universal_law_label") is not None: fail(f"{w}: universal law label assigned")
    if not r.get("evidence_ceiling"): fail(f"{w}: no evidence ceiling")

eligible=[r for _,_,r in rows if r["law_candidate_status"]=="eligible"]
if len(eligible)!=28: fail(f"expected 28 eligible, got {len(eligible)}")
if any(r["constraint_level"]!="observed_system" for r in eligible):
    fail("eligible set contains non-observed-system constraint")

print("PASS: 84 constraint projections; MCR-007..090 complete; 28 eligible observed-system candidates; no cross-source matching or universal-law labels.")
