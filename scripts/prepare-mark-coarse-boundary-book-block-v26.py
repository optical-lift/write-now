#!/usr/bin/env python3
import os
from pathlib import Path

from mark_coarse_boundary_book_block_v26_core import (
    parse_book_blocked_chapters, read_json, write_json, write_jsonl,
)

protocol = read_json(os.environ["MARK_V26_PROTOCOL"])
lanes, manifest = parse_book_blocked_chapters(os.environ["MARK_V26_WLC"], protocol)
out = Path(os.environ["MARK_V26_OUT"])
out.mkdir(parents=True, exist_ok=True)
for lane, rows in lanes.items():
    write_jsonl(out / f"{lane}.jsonl", rows)
write_json(out / "manifest.json", manifest)
print("V26 book-blocked coarse packets prepared")
print(manifest)
