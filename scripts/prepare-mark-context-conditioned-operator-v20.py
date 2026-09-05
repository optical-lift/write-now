#!/usr/bin/env python3
import os
from pathlib import Path
from mark_context_conditioned_operator_v20_core import (
    parse_hebrew_wlc, read_json, write_json, write_jsonl,
)

protocol = read_json(os.environ["MARK_V20_PROTOCOL"])
lanes, _, manifest = parse_hebrew_wlc(os.environ["MARK_V20_WLC"], protocol)
out = Path(os.environ["MARK_V20_HEBREW_OUT"])
for lane, rows in lanes.items():
    write_jsonl(out / f"{lane}.jsonl", rows)
write_json(out / "manifest.json", manifest)
