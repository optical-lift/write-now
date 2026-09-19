#!/usr/bin/env python3
"""Validate Source-Level Disaggregation and Independence Certification v1."""
from __future__ import annotations
import json, pathlib

ROOT=pathlib.Path(__file__).resolve().parents[1]
EXP=ROOT/"research"/"mark"/"discovery-experiments"

registry=json.loads((EXP/"source-level-disaggregation-v1.raw-book-registry.json").read_text())
cats=[json.loads(x) for x in (EXP/"source-level-disaggregation-v1.raw-book-catalogues.jsonl").read_text().splitlines() if x.strip()]
v38=json.loads((EXP/"source-level-disaggregation-v1.v38-block-replay.result.json").read_text())
verify=json.loads((EXP/"source-level-disaggregation-v1.v38-replay-verification.json").read_text())
v36=json.loads((EXP/"source-level-disaggregation-v1.v36-retrospective.json").read_text())

if len(registry["sources"])!=23:
    raise SystemExit(f"FAIL: expected 23 raw book sources, got {len(registry['sources'])}")
if len(cats)!=23:
    raise SystemExit(f"FAIL: expected 23 book catalogues, got {len(cats)}")
if len({c["source_id"] for c in cats})!=23:
    raise SystemExit("FAIL: duplicate book source IDs")
if any(s["raw_observation_independence"]!="CERTIFIED_NONOVERLAPPING_BOOK" for s in registry["sources"]):
    raise SystemExit("FAIL: raw book independence certification changed")
if len(v38["blocks"])!=41 or v38["source_local_support_blocks"]!=24 or v38["distinct_books_with_support"]!=18:
    raise SystemExit("FAIL: V38 replay counts changed")
if verify["absolute_differences"]["transitions"]!=0:
    raise SystemExit("FAIL: V38 transition count does not reproduce aggregate")
if verify["absolute_differences"]["conditional_ce"]>1e-5 or verify["absolute_differences"]["unigram_ce"]>1e-5:
    raise SystemExit("FAIL: V38 replay no longer matches published aggregate within rounding")
if {b["book"] for b in v36["books"] if b["derived_state"]=="PRESENT"}!={"Deu","Jdg"}:
    raise SystemExit("FAIL: V36 supported-book set changed")

present1=[]
present2=[]
both=[]
for c in cats:
    if len(c["law_entries"])!=2:
        raise SystemExit(f"FAIL: {c['source_id']} does not have exactly two shared-law entries")
    by={e["law_signature_id"]:e for e in c["law_entries"]}
    if set(by)!={"EQC-001","EQC-002"}:
        raise SystemExit(f"FAIL: {c['source_id']} target set changed")
    if by["EQC-001"]["derived_state"]=="PRESENT":
        present1.append(c["source_id"])
    elif by["EQC-001"]["derived_state"]!="MEASUREMENT_UNRESOLVED":
        raise SystemExit("FAIL: unexpected EQC-001 negative state")
    if by["EQC-002"]["derived_state"]=="PRESENT":
        present2.append(c["source_id"])
    elif by["EQC-002"]["derived_state"]!="MEASUREMENT_UNRESOLVED":
        raise SystemExit("FAIL: unexpected EQC-002 negative state")
    if all(e["derived_state"]=="PRESENT" for e in c["law_entries"]):
        both.append(c["source_id"])

if set(present1)!={"BOOK-Deu","BOOK-Jdg"}:
    raise SystemExit(f"FAIL: EQC-001 presence set changed: {present1}")
if len(present2)!=18:
    raise SystemExit(f"FAIL: expected 18 EQC-002 present books, got {len(present2)}")
if set(both)!={"BOOK-Deu","BOOK-Jdg"}:
    raise SystemExit(f"FAIL: co-presence set changed: {both}")

print("PASS: 23 non-overlapping book nodes; V38 replay 41 blocks/24 support/18 books; EQC-001 present in Deu+Jdg; EQC-002 present in 18 books; no false negative states.")
