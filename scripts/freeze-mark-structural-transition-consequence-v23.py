#!/usr/bin/env python3
import os
from pathlib import Path

from mark_structural_transition_consequence_v23_core import (
    HEBREW_REPS, freeze_model, read_json, read_jsonl, sha256_json, write_json,
)

protocol = read_json(os.environ["MARK_V23_PROTOCOL"])
hd = Path(os.environ["MARK_V23_HEBREW_TRAIN"])
gd = Path(os.environ["MARK_V23_GLYPH_TRAIN"])
out = Path(os.environ["MARK_V23_FREEZE_OUT"])

model = freeze_model(
    read_jsonl(hd / "train.jsonl"),
    read_jsonl(gd / "train.jsonl"),
    protocol,
)
model["schema"] = "mark_structural_transition_consequence_freeze_v23"
model["evaluationOpenedDuringFreeze"] = False
model["protocolSha256"] = sha256_json(protocol)

minimum = int(protocol["evaluation"]["minimumEvaluableOperatorsPerSystem"])
feasible = {}
for rep in HEBREW_REPS:
    pair = model["systems"][rep]
    feasible[rep] = (
        len(pair["sharedStates"]) >= 3
        and len(pair["hebrew"]["operators"]) >= minimum
        and len(pair["glyph"]["operators"]) >= minimum
    )
model["representationTrainFeasible"] = feasible
model["freezeAdjudication"] = "FEASIBLE" if any(feasible.values()) else "INSUFFICIENT_STRUCTURAL_SUPPORT"
model["freezeSha256"] = sha256_json({k: v for k, v in model.items() if k != "freezeSha256"})
write_json(out / "freeze.json", model)

lines = [
    "# V23 pre-evaluation structural-transition freeze",
    "",
    f'- structurally generated outgoing-state alphabet: **{len(model["outcomes"])}** states',
    '- consequence uses next token: **false**',
    '- consequence is immediate outgoing relational state after current operator: **true**',
    '- evaluation opened: **false**',
    '- Hebrew↔glyph operator pairing constructed: **false**',
    "",
    "| relational representation | shared incoming states | Hebrew operators | glyph operators | feasible |",
    "|---|---:|---:|---:|---|",
]
for rep in HEBREW_REPS:
    pair = model["systems"][rep]
    lines.append(
        f'| {rep} | {len(pair["sharedStates"])} | '
        f'{len(pair["hebrew"]["operators"])} | {len(pair["glyph"]["operators"])} | '
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
