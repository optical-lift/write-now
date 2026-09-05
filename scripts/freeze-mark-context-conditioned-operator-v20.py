#!/usr/bin/env python3
import os
from pathlib import Path
from mark_context_conditioned_operator_v20_core import (
    freeze_model, read_json, read_jsonl, sha256_json, write_json,
)

protocol = read_json(os.environ["MARK_V20_PROTOCOL"])
hd = Path(os.environ["MARK_V20_HEBREW_TRAIN"])
gd = Path(os.environ["MARK_V20_GLYPH_TRAIN"])
out = Path(os.environ["MARK_V20_FREEZE_OUT"])

model = freeze_model(
    read_jsonl(hd / "train.jsonl"),
    read_jsonl(gd / "train.jsonl"),
    protocol,
)
model["schema"] = "mark_context_conditioned_operator_freeze_v20"
model["evaluationOpenedDuringFreeze"] = False
model["protocolSha256"] = sha256_json(protocol)

minimum_ops = int(protocol["evaluation"]["minimumEvaluableOperatorsPerCorpus"])
minimum_states = int(protocol["evaluation"]["contextProfile"]["minimumCommonStates"])
feasible = (
    len(model["sharedStates"]) >= minimum_states
    and len(model["systems"]["hebrew"]["operators"]) >= minimum_ops
    and len(model["systems"]["glyph"]["operators"]) >= minimum_ops
)
model["freezeAdjudication"] = "FEASIBLE" if feasible else "INSUFFICIENT_CONTEXT_SUPPORT"
model["freezeSha256"] = sha256_json({k: v for k, v in model.items() if k != "freezeSha256"})
write_json(out / "freeze.json", model)

lines = [
    "# V20 pre-evaluation context-conditioned operator freeze",
    "",
    f'- shared anonymous structural states: **{len(model["sharedStates"])}**',
    f'- Hebrew frozen operators: **{len(model["systems"]["hebrew"]["operators"])}**',
    f'- glyph frozen operators: **{len(model["systems"]["glyph"]["operators"])}**',
    f'- Hebrew train events: **{model["trainEventCounts"]["hebrew"]:,}**',
    f'- glyph train events: **{model["trainEventCounts"]["glyph"]:,}**',
    f'- freeze adjudication: **{model["freezeAdjudication"]}**',
    '- Hebrew↔glyph operator pairing constructed: **false**',
    '- evaluation opened: **false**',
    f'- freeze SHA-256: `{model["freezeSha256"]}`',
]
out.mkdir(parents=True, exist_ok=True)
(out / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
print("\n".join(lines))
