#!/usr/bin/env python3
import os
from pathlib import Path

from mark_verse_boundary_continuity_v25_core import (
    parse_ordered_chapters, read_json, write_json, write_jsonl,
)

protocol = read_json(os.environ["MARK_V25_PROTOCOL"])
lanes, manifest = parse_ordered_chapters(os.environ["MARK_V25_WLC"], protocol)
out = Path(os.environ["MARK_V25_OUT"])
out.mkdir(parents=True, exist_ok=True)
for lane, rows in lanes.items():
    write_jsonl(out / f"{lane}.jsonl", rows)
write_json(out / "manifest.json", manifest)
print("V25 chapter packets prepared")
print(manifest)
