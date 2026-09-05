#!/usr/bin/env python3
import os
from pathlib import Path

from mark_verse_boundary_continuity_v25_core import (
    REPRESENTATIONS, freeze_models, read_json, read_jsonl, sha256_json, write_json,
)

protocol = read_json(os.environ["MARK_V25_PROTOCOL"])
train_dir = Path(os.environ["MARK_V25_TRAIN"])
out = Path(os.environ["MARK_V25_FREEZE_OUT"])
train_rows = read_jsonl(train_dir / "train.jsonl")
model = freeze_models(train_rows, protocol)
model["schema"] = "mark_verse_boundary_continuity_freeze_v25"
model["protocolSha256"] = sha256_json(protocol)
model["evaluationOpenedDuringFreeze"] = False
minimum = int(protocol["evaluation"]["minimumEvaluableOperators"])
model["trainFeasible"] = {
    rep: len(model["systems"][rep]["operators"]) >= minimum
    for rep in REPRESENTATIONS
}
model["freezeAdjudication"] = "FEASIBLE" if any(model["trainFeasible"].values()) else "INSUFFICIENT_BOUNDARY_SUPPORT"
model["freezeSha256"] = sha256_json({k: v for k, v in model.items() if k != "freezeSha256"})
out.mkdir(parents=True, exist_ok=True)
write_json(out / "freeze.json", model)

lines = [
    "# V25 pre-evaluation verse-boundary continuity freeze",
    "",
    f'- freeze adjudication: **{model["freezeAdjudication"]}**',
    f'- evaluation opened during freeze: **{model["evaluationOpenedDuringFreeze"]}**',
    "",
    "| representation | frozen operators | resolved TRAIN events | feasible |",
    "|---|---:|---:|---|",
]
for rep in REPRESENTATIONS:
    s = model["systems"][rep]
    lines.append(
        f'| {rep} | {len(s["operators"])} | {s["resolvedTrainEvents"]} | {model["trainFeasible"][rep]} |'
    )
lines += ["", f'Freeze SHA-256: `{model["freezeSha256"]}`']
(out / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
print("\n".join(lines))
