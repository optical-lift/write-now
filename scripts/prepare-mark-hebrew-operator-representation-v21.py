#!/usr/bin/env python3
import os
from pathlib import Path

from mark_hebrew_operator_representation_v21_core import (
    parse_hebrew_representations, read_json, write_json, write_jsonl,
)

protocol = read_json(os.environ["MARK_V21_PROTOCOL"])
lanes, manifest = parse_hebrew_representations(os.environ["MARK_V21_WLC"], protocol)
out = Path(os.environ["MARK_V21_HEBREW_OUT"])

for lane, rows in lanes.items():
    write_jsonl(out / f"{lane}.jsonl", rows)
write_json(out / "manifest.json", manifest)
