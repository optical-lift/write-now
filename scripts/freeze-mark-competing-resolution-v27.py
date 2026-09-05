#!/usr/bin/env python3
import os
from pathlib import Path

from mark_competing_resolution_v27_core import (
    REPRESENTATIONS, freeze_models, read_json, read_jsonl, sha256_json, write_json,
)

protocol = read_json(os.environ["MARK_V27_PROTOCOL"])
train_dir = Path(os.environ["MARK_V27_TRAIN"])
out = Path(os.environ["MARK_V27_FREEZE_OUT"])
train_rows = read_jsonl(train_dir / "train.jsonl")
model = freeze_models(train_rows, protocol)
model["schema"] = "mark_competing_resolution_freeze_v27"
model["protocolSha256"] = sha256_json(protocol)
model["evaluationOpenedDuringFreeze"] = False
minimum = int(protocol["evaluation"]["minimumEvaluableOperators"])
model["trainFeasible"] = {
    rep: len(model["systems"][rep]["operators"]) >= minimum
    for rep in REPRESENTATIONS
}
model["freezeAdjudication"] = "FEASIBLE" if any(model["trainFeasible"].values()) else "INSUFFICIENT_COMPETING_RESOLUTION_SUPPORT"
model["freezeSha256"] = sha256_json({k: v for k, v in model.items() if k != "freezeSha256"})
out.mkdir(parents=True, exist_ok=True)
write_json(out / "freeze.json", model)

lines = [
    "# V27 pre-evaluation competing-resolution freeze",
    "",
    f'- freeze adjudication: **{model["freezeAdjudication"]}**',
    f'- evaluation opened during freeze: **{model["evaluationOpenedDuringFreeze"]}**',
    "",
    "| representation | frozen operators | TRAIN origins | TRAIN risk rows | interaction cells | feasible |",
    "|---|---:|---:|---:|---:|---|",
]
for rep in REPRESENTATIONS:
    s = model["systems"][rep]
    lines.append(
        f'| {rep} | {len(s["operators"])} | {s["trainOrigins"]} | {s["trainRiskRows"]} | {s["interactionCells"]} | {model["trainFeasible"][rep]} |'
    )
lines += ["", f'Freeze SHA-256: `{model["freezeSha256"]}`']
(out / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
print("\n".join(lines))
