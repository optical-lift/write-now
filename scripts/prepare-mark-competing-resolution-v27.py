#!/usr/bin/env python3
import os
from pathlib import Path

from mark_competing_resolution_v27_core import (
    parse_book_blocked_chapters, read_json, write_json, write_jsonl,
)

protocol = read_json(os.environ["MARK_V27_PROTOCOL"])
lanes, manifest = parse_book_blocked_chapters(os.environ["MARK_V27_WLC"], protocol)
out = Path(os.environ["MARK_V27_OUT"])
out.mkdir(parents=True, exist_ok=True)
for lane, rows in lanes.items():
    write_jsonl(out / f"{lane}.jsonl", rows)
write_json(out / "manifest.json", manifest)
print("V27 competing-resolution book packets prepared")
print(manifest)
