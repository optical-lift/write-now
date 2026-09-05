#!/usr/bin/env python3
import os
from pathlib import Path

from mark_first_passage_trajectory_v24_core import (
    HEBREW_REPS, freeze_model, read_json, read_jsonl, sha256_json, write_json,
)

protocol = read_json(os.environ["MARK_V24_PROTOCOL"])
hd = Path(os.environ["MARK_V24_HEBREW_TRAIN"])
gd = Path(os.environ["MARK_V24_GLYPH_TRAIN"])
out = Path(os.environ["MARK_V24_FREEZE_OUT"])

hebrew_rows = read_jsonl(hd / "train.jsonl")
glyph_rows = read_jsonl(gd / "train.jsonl")
model = freeze_model(hebrew_rows, glyph_rows, protocol)
model["schema"] = "mark_first_passage_trajectory_freeze_v24"
model["evaluationOpenedDuringFreeze"] = False
model["protocolSha256"] = sha256_json(protocol)
model["lineage"] = protocol["lineage"]

minimum = int(protocol["evaluation"]["minimumEvaluableOperatorsPerSystem"])
feasible = {}
for rep in HEBREW_REPS:
    pair = model["systems"][rep]
    feasible[rep] = (
        len(pair["sharedImmediateStates"]) >= 3
        and len(pair["hebrew"]["operators"]) >= minimum
        and len(pair["glyph"]["operators"]) >= minimum
    )
model["candidateTrainFeasible"] = feasible
model["freezeAdjudication"] = "FEASIBLE" if any(feasible.values()) else "INSUFFICIENT_FIRST_PASSAGE_SUPPORT"
model["freezeSha256"] = sha256_json({k: v for k, v in model.items() if k != "freezeSha256"})
write_json(out / "freeze.json", model)

lines = [
    "# V24 pre-evaluation first-passage trajectory freeze",
    "",
    f'- outcome alphabet size: **{len(model["outcomes"])}** (anonymous structural states plus unit-end/no-departure)',
    '- first-passage rule: **first downstream anonymous state different from immediate S1; no fixed lag**',
    '- interaction tested: **operator × incoming S0, conditional on immediate S1, beyond additive context + operator main effects**',
    '- evaluation opened: **false**',
    "",
    "| representation | shared S1 states | Hebrew frozen operators | glyph frozen operators | Hebrew train events | glyph train events | feasible |",
    "|---|---:|---:|---:|---:|---:|---|",
]
for rep in HEBREW_REPS:
    pair = model["systems"][rep]
    lines.append(
        f'| {rep} | {len(pair["sharedImmediateStates"])} | '
        f'{len(pair["hebrew"]["operators"])} | {len(pair["glyph"]["operators"])} | '
        f'{pair["trainEventCounts"]["hebrew"]} | {pair["trainEventCounts"]["glyph"]} | '
        f'{feasible[rep]} |'
    )
lines += [
    "",
    f'- freeze adjudication: **{model["freezeAdjudication"]}**',
    f'- freeze SHA-256: `{model["freezeSha256"]}`',
]
out.mkdir(parents=True, exist_ok=True)
(out / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
print("\n".join(lines))
