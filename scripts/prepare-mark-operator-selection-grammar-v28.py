#!/usr/bin/env python3
import os
from pathlib import Path
from mark_operator_selection_grammar_v28_core import parse_hebrew_books, read_json, write_json, write_jsonl

protocol = read_json(os.environ["MARK_V28_PROTOCOL"])
lanes, manifest = parse_hebrew_books(os.environ["MARK_V28_WLC"], protocol)
out = Path(os.environ["MARK_V28_OUT"])
out.mkdir(parents=True, exist_ok=True)
for lane, rows in lanes.items():
    write_jsonl(out / f"{lane}.jsonl", rows)
write_json(out / "manifest.json", manifest)
print("V28 Hebrew book packets prepared")
print(manifest)
