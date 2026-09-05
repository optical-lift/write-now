#!/usr/bin/env python3
import os
from pathlib import Path
from mark_hebrew_glyph_annotation_competition_v19_core import read_json,parse_hebrew_wlc,write_json,write_jsonl
protocol=read_json(os.environ["MARK_V19_PROTOCOL"]); lanes,cmap,manifest=parse_hebrew_wlc(os.environ["MARK_V19_WLC"],protocol); out=Path(os.environ["MARK_V19_HEBREW_OUT"])
for lane,rows in lanes.items(): write_jsonl(out/f"{lane}.jsonl",rows)
write_json(out/"conventional-train-map.json",cmap); write_json(out/"manifest.json",manifest)
