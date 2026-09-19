#!/usr/bin/env python3
"""Validate Cross-Source Overlap Graph v1."""
from __future__ import annotations
import json, pathlib

ROOT=pathlib.Path(__file__).resolve().parents[1]
EXP=ROOT/"research"/"mark"/"discovery-experiments"
G=json.loads((EXP/"cross-source-overlap-graph-v1.graph.json").read_text())

if G["schema"]!="cross_source_overlap_graph_v1":
    raise SystemExit("FAIL: wrong schema")
if len(G["source_nodes"])!=23:
    raise SystemExit("FAIL: expected 23 source nodes")
if {x["id"] for x in G["law_nodes"]}!={"EQC-001","EQC-002"}:
    raise SystemExit("FAIL: law node set changed")
if len(G["positive_edges"])!=20:
    raise SystemExit("FAIL: expected 20 positive edges")
if len(G["open_cells"])!=26:
    raise SystemExit("FAIL: expected 26 open cells")
if any(x["state"]!="PRESENT" for x in G["positive_edges"]):
    raise SystemExit("FAIL: non-PRESENT positive edge")
if any(x["state"]!="MEASUREMENT_UNRESOLVED" for x in G["open_cells"]):
    raise SystemExit("FAIL: v1 open cells should all remain MEASUREMENT_UNRESOLVED")

deg=G["diagnostics"]["law_degree"]
if deg!={"EQC-001":2,"EQC-002":18}:
    raise SystemExit(f"FAIL: law degree changed: {deg}")
if set(G["diagnostics"]["co_presence"]["sources"])!={"BOOK-Deu","BOOK-Jdg"}:
    raise SystemExit("FAIL: co-presence set changed")
if G["diagnostics"]["descriptive_set_inclusion"]["inference"]!="DESCRIPTIVE_SET_INCLUSION_ONLY":
    raise SystemExit("FAIL: nestedness guard removed")
if set(G["diagnostics"]["isolated_sources"])!={"BOOK-Ecc","BOOK-Job","BOOK-Nah","BOOK-Pro","BOOK-Psa"}:
    raise SystemExit("FAIL: isolated source set changed")
if G["diagnostics"]["model_dependence_edge_counts"]!={"V38_SHARED_TRAINING_MODEL":18,"V36_SHARED_TRAINING_MODEL":2}:
    raise SystemExit("FAIL: model-dependence counts changed")

for e in G["positive_edges"]:
    if not e.get("model_dependence_group"):
        raise SystemExit(f"FAIL: missing dependence group {e['edge_id']}")

print("PASS: 23 source nodes; 2 law nodes; 20 positive edges; 26 unresolved cells; dependence metadata preserved; no negative edges invented.")
