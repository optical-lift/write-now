#!/usr/bin/env python3
import os
from pathlib import Path

from mark_coarse_boundary_book_block_v26_core import (
    freeze_model, read_json, read_jsonl, sha256_json, write_json,
)

protocol = read_json(os.environ["MARK_V26_PROTOCOL"])
train_dir = Path(os.environ["MARK_V26_TRAIN"])
out = Path(os.environ["MARK_V26_FREEZE_OUT"])
train_rows = read_jsonl(train_dir / "train.jsonl")
model = freeze_model(train_rows, protocol)
model["schema"] = "mark_coarse_boundary_book_block_freeze_v26"
model["protocolSha256"] = sha256_json(protocol)
model["evaluationOpenedDuringFreeze"] = False
minimum = int(protocol["evaluation"]["minimumEvaluableOperators"])
model["trainFeasible"] = len(model["system"]["operators"]) >= minimum
model["freezeAdjudication"] = "FEASIBLE" if model["trainFeasible"] else "INSUFFICIENT_BOOK_BLOCKED_SUPPORT"
model["freezeSha256"] = sha256_json({k: v for k, v in model.items() if k != "freezeSha256"})
out.mkdir(parents=True, exist_ok=True)
write_json(out / "freeze.json", model)

lines = [
    "# V26 pre-evaluation coarse book-block freeze",
    "",
    f'- freeze adjudication: **{model["freezeAdjudication"]}**',
    f'- evaluation opened during freeze: **{model["evaluationOpenedDuringFreeze"]}**',
    f'- frozen operators: **{len(model["system"]["operators"])}**',
    f'- resolved TRAIN events: **{model["system"]["resolvedTrainEvents"]}**',
    "",
    f'Freeze SHA-256: `{model["freezeSha256"]}`',
]
(out / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
print("\n".join(lines))
