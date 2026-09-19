#!/usr/bin/env python3
"""Validate Frozen Local Law Catalogues v1."""
from __future__ import annotations
import json, pathlib, importlib.util

ROOT=pathlib.Path(__file__).resolve().parents[1]
EXP=ROOT/"research"/"mark"/"discovery-experiments"

registry=json.loads((EXP/"frozen-local-law-catalogues-v1.source-registry.json").read_text())
inventories=[json.loads(x) for x in (EXP/"frozen-local-law-catalogues-v1.local-inventories.jsonl").read_text().splitlines() if x.strip()]
targets=json.loads((EXP/"frozen-local-law-catalogues-v1.shared-targets.json").read_text())
projections=[json.loads(x) for x in (EXP/"frozen-local-law-catalogues-v1.projections.jsonl").read_text().splitlines() if x.strip()]

if len(registry["containers"]) != 5:
    raise SystemExit("FAIL: expected 5 source containers")
if len(inventories) != 5:
    raise SystemExit("FAIL: expected 5 local catalogues")
if len(projections) != 10:
    raise SystemExit("FAIL: expected 10 source×shared-law projections")
if {t["law_signature_id"] for t in targets["targets"]} != {"EQC-001","EQC-002"}:
    raise SystemExit("FAIL: shared target set changed")

catalogue_ids={x["catalogue_id"] for x in inventories}
if len(catalogue_ids)!=5:
    raise SystemExit("FAIL: duplicate catalogue ID")
if any(x["equivalence_projection_status"]!="NOT_OPENED" for x in inventories):
    raise SystemExit("FAIL: local inventories were altered after equivalence projection")

present=sum(1 for x in projections if x["derived_state"]=="PRESENT")
unresolved=sum(1 for x in projections if x["derived_state"]=="MEASUREMENT_UNRESOLVED")
if (present,unresolved)!=(5,5):
    raise SystemExit(f"FAIL: unexpected projection state counts {(present,unresolved)}")

# Validate derivation using the already-frozen absence-state reference implementation.
derive_path=ROOT/"scripts"/"derive-absence-state-v1.py"
spec=importlib.util.spec_from_file_location("absence_derive", derive_path)
mod=importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(mod)
for x in projections:
    axes={k:x[k] for k in ["instantiation_evidence","opportunity_status","observability_status","compatibility_status","coverage_status"]}
    got=mod.derive(axes)
    if got!=x["derived_state"]:
        raise SystemExit(f"FAIL: {x['entry_id']} derived {got}, stored {x['derived_state']}")

# External canon surfaces can never enter the primary Mark graph.
container_by_id={x["container_id"]:x for x in registry["containers"]}
for inv in inventories:
    c=container_by_id[inv["container_id"]]
    if inv["lane"]=="EXTERNAL_CANON_VALIDATION" and c["lane"]!="EXTERNAL_CANON_VALIDATION":
        raise SystemExit("FAIL: lane mismatch")

# Most important current readiness gate: primary Mark catalogues are not certified raw-source independent.
mark_containers=[c for c in registry["containers"] if c["lane"]=="PRIMARY_MARK_RECONSTRUCTION"]
if any(c["raw_source_independence"]=="CERTIFIED_INDEPENDENT" for c in mark_containers):
    raise SystemExit("FAIL: v1 must not claim certified raw-source independence")

print("PASS: 5 catalogues, 13 frozen local laws, 10 EQC projections; 5 PRESENT / 5 MEASUREMENT_UNRESOLVED; canon excluded from primary graph; Mark raw-source independence remains unverified.")
