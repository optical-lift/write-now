#!/usr/bin/env python3
import os
from pathlib import Path

from mark_hebrew_glyph_annotation_competition_v19_core import (
    read_json,
    read_jsonl,
    sha256_json,
    write_json,
)
from mark_hebrew_glyph_annotation_competition_v19_eval import (
    adjudicate,
    map_lane,
    pairing_lane,
)

protocol = read_json(os.environ["MARK_V19_PROTOCOL"])
freeze = read_json(Path(os.environ["MARK_V19_FREEZE"]) / "freeze.json")
hebrew_dir = Path(os.environ["MARK_V19_HEBREW_EVAL"])
glyph_dir = Path(os.environ["MARK_V19_GLYPH_EVAL"])
out = Path(os.environ["MARK_V19_RESULT_OUT"])

if freeze.get("freezeAdjudication") != "FEASIBLE":
    result = {
        "schema": "mark_hebrew_glyph_annotation_competition_result_v19",
        "adjudication": "INSUFFICIENT_SONG_COVERED_PANEL",
        "freezeSha256": freeze.get("freezeSha256"),
    }
else:
    pairing = {}
    maps = {name: {} for name in ("song", "conventional", "blind")}
    for lane in ("holdout", "control"):
        hebrew_rows = read_jsonl(hebrew_dir / f"{lane}.jsonl")
        glyph_rows = read_jsonl(glyph_dir / f"{lane}.jsonl")
        pairing[lane] = pairing_lane(hebrew_rows, glyph_rows, freeze, protocol, lane)
        for map_name in maps:
            maps[map_name][lane] = map_lane(
                glyph_rows, freeze, protocol, lane, map_name
            )
    result = {
        "schema": "mark_hebrew_glyph_annotation_competition_result_v19",
        "freezeSha256": freeze["freezeSha256"],
        "pairing": pairing,
        "maps": maps,
        "adjudication": adjudicate(pairing, maps),
    }

result["resultSha256"] = sha256_json(
    {key: value for key, value in result.items() if key != "resultSha256"}
)
write_json(out / "result.json", result)

lines = [
    "# Mark Hebrew ↔ glyph annotation competition v19",
    "",
    f'Adjudication: **{result["adjudication"]}**',
    "",
]
if "pairing" in result:
    lines += [
        "## Label-blind common-panel transfer",
        "",
        "| lane | evaluable | mean | p | rank | pass |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for lane in ("holdout", "control"):
        value = result["pairing"][lane]
        lines.append(
            f'| {lane} | {value["evaluablePairs"]}/{value["frozenPairs"]} | '
            f'{value["meanSimilarity"]:+.4f} | {value["permutationP"]:.4f} | '
            f'{value["medianRankPercentile"]:.3f} | {value["pass"]} |'
        )
    lines += [
        "",
        "## Competing annotation maps",
        "",
        "| map | holdout effect | holdout p | holdout z | holdout pass | control effect | control p | control z | control pass |",
        "|---|---:|---:|---:|---|---:|---:|---:|---|",
    ]
    for map_name in ("song", "conventional", "blind"):
        holdout = result["maps"][map_name]["holdout"]
        control = result["maps"][map_name]["control"]
        lines.append(
            f'| {map_name} | {holdout["operatorBalancedAdvantage"]:+.4f} | '
            f'{holdout["permutationP"]:.4f} | {holdout["permutationZ"]:+.2f} | '
            f'{holdout["pass"]} | {control["operatorBalancedAdvantage"]:+.4f} | '
            f'{control["permutationP"]:.4f} | {control["permutationZ"]:+.2f} | '
            f'{control["pass"]} |'
        )
lines += ["", f'Result SHA-256: `{result["resultSha256"]}`']
out.mkdir(parents=True, exist_ok=True)
(out / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
print("\n".join(lines))
