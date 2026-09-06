#!/usr/bin/env python3
import os
from pathlib import Path

from mark_hebrew_glyph_annotation_competition_v19_io import read_json, write_json, write_jsonl
from mark_operator_selection_grammar_v28_core import parse_hebrew_books

protocol = read_json(os.environ["MARK_V30_PROTOCOL"])
lanes, manifest = parse_hebrew_books(os.environ["MARK_V30_WLC"], protocol)
manifest["schema"] = "mark_operator_proximal_perturbation_hebrew_packets_v30"
manifest["experimentId"] = protocol["experimentId"]
out = Path(os.environ["MARK_V30_OUT"])
out.mkdir(parents=True, exist_ok=True)
for lane, rows in lanes.items():
    write_jsonl(out / f"{lane}.jsonl", rows)
write_json(out / "manifest.json", manifest)
