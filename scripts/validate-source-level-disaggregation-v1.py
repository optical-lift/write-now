#!/usr/bin/env python3
"""Validate Source-Level Disaggregation and Independence Certification v1."""
from __future__ import annotations
import json, pathlib

ROOT=pathlib.Path(__file__).resolve().parents[1]
EXP=ROOT/"research"/"mark"/"discovery-experiments"

def load(name):
    return json.loads((EXP/name).read_text(encoding="utf-8"))

v36=load("source-level-disaggregation-v1.v36-book-localization.json")
v38=load("source-level-disaggregation-v1.v38-block-replay.result.json")
v40=load("source-level-disaggregation-v1.v40-block-replay.result.json")
summary=load("source-level-disaggregation-v1.summary.json")
co=load("source-level-disaggregation-v1.cooccurrence.json")
manifest=load("source-level-disaggregation-v1.manifest.json")
units=[json.loads(x) for x in (EXP/"source-level-disaggregation-v1.source-units.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]

# V36 whole-book localization.
assert [x["book"] for x in v36["books"] if x["local_status"]=="SOURCE_LOCAL_SUPPORT"] == ["Deu","Jdg"]
assert {x["book"] for x in v36["books"] if x["local_status"]!="SOURCE_LOCAL_SUPPORT"} == {"Psa","Job"}

# V38 replay integrity.
assert len(v38["blocks"]) == 41
assert sum(x["local_status"]=="SOURCE_LOCAL_SUPPORT" for x in v38["blocks"]) == 24
assert len({x["book"] for x in v38["blocks"] if x["local_status"]=="SOURCE_LOCAL_SUPPORT"}) == 18
n=sum(x["transitions"] for x in v38["blocks"])
c=sum(x["transitions"]*x["conditional_ce"] for x in v38["blocks"])/n
u=sum(x["transitions"]*x["unigram_ce"] for x in v38["blocks"])/n
assert n == 58691
assert abs(c-2.8360684584054106) < 1e-12
assert abs(u-2.843766082917836) < 1e-12

# V40 replay identity + local result.
assert len(v40["blocks"]) == 41
assert v40["support_blocks"] == 29
assert v40["unresolved_blocks"] == 12
assert v40["distinct_support_books"] == 18
assert abs(v40["replay_validation"]["replay_real_c1_ce"]-2.85942910519731) < 1e-12
assert len(v40["replay_validation"]["replay_null_series"]) == 20
for got,want in zip(v40["replay_validation"]["replay_null_series"],v40["replay_validation"]["published_null_series"]):
    assert abs(got-want) < 1e-6

# Strict source-unit certification.
assert len(units) == 86
classes={}
for x in units:
    classes[x["certification_class"]]=classes.get(x["certification_class"],0)+1
    assert x["independent_law_discovery"] is False
    assert x["independent_discovery_count_eligible"] is False
assert classes == {
    "WHOLE_SOURCE_HELDOUT_TRANSFER":2,
    "NONOVERLAPPING_UNIT_SHARED_TRAINING":53,
    "UNRESOLVED_SOURCE_UNIT":31,
}

# Same raw-block co-occurrence is preserved but never promoted to independence.
assert co["exact_overlap_blocks"] == 10
assert co["dual_support_blocks"] == 6
assert set(co["dual_support_source_units"]) == {"Zec:2","Deu:3","Dan:1","Gen:1","Isa:10","2Ch:0"}

# Whole-system readiness remains gated.
assert summary["law_counts"]["EQC-001"]["independent_discovery_count"] == 0
assert summary["law_counts"]["EQC-002"]["independent_discovery_count"] == 0
assert manifest["descriptive_provenance_graph_ready"] is True
assert manifest["primary_independent_discovery_graph_ready"] is False
assert manifest["next_checkpoint"] == "independent_source_law_discovery_v1"

print("PASS: V36/V38/V40 localized; 86 certified source units; 53 shared-training supports + 2 whole-book transfers; 6 exact dual-law blocks; independent discovery count remains 0.")
