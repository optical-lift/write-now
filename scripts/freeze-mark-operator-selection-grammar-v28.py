#!/usr/bin/env python3
import os
from pathlib import Path
from mark_operator_selection_grammar_v28_core import (
    REPRESENTATIONS, freeze_models, read_json, read_jsonl, sha256_json, write_json,
)

protocol = read_json(os.environ["MARK_V28_PROTOCOL"])
hd = Path(os.environ["MARK_V28_HEBREW_TRAIN"])
gd = Path(os.environ["MARK_V28_GLYPH_TRAIN"])
out = Path(os.environ["MARK_V28_FREEZE_OUT"])
model = freeze_models(read_jsonl(hd / "train.jsonl"), read_jsonl(gd / "train.jsonl"), protocol)
model["schema"] = "mark_operator_selection_grammar_freeze_v28"
model["protocolSha256"] = sha256_json(protocol)
model["evaluationOpenedDuringFreeze"] = False
minimum_ops = int(protocol["evaluation"]["minimumEvaluableOperators"])
minimum_states = int(protocol["training"]["minimumEligibleStates"])
feasible = {rep: len(model["hebrew"][rep]["operators"]) >= minimum_ops and len(model["hebrew"][rep]["states"]) >= minimum_states for rep in REPRESENTATIONS}
glyph_feasible = len(model["glyph"]["operators"]) >= minimum_ops and len(model["glyph"]["states"]) >= minimum_states
model["trainFeasible"] = {"hebrew": feasible, "glyph": glyph_feasible}
model["freezeAdjudication"] = "FEASIBLE" if any(feasible.values()) or glyph_feasible else "INSUFFICIENT_SELECTION_SUPPORT"
model["freezeSha256"] = sha256_json({k:v for k,v in model.items() if k != "freezeSha256"})
out.mkdir(parents=True, exist_ok=True)
write_json(out / "freeze.json", model)
lines = [
    "# V28 pre-evaluation operator-selection freeze", "",
    f'- evaluation opened during freeze: **{model["evaluationOpenedDuringFreeze"]}**',
    '- current operator included in incoming state: **false**',
    '- Hebrew↔glyph operator pairing constructed: **false**', "",
    "| system | representation | operators | states | TRAIN events | feasible |",
    "|---|---|---:|---:|---:|---|",
]
for rep in REPRESENTATIONS:
    m=model["hebrew"][rep]
    lines.append(f'| Hebrew | {rep} | {len(m["operators"])} | {len(m["states"])} | {m["trainEvents"]} | {feasible[rep]} |')
g=model["glyph"]
lines.append(f'| glyph | identity | {len(g["operators"])} | {len(g["states"])} | {g["trainEvents"]} | {glyph_feasible} |')
lines += ["", f'- freeze adjudication: **{model["freezeAdjudication"]}**', f'- freeze SHA-256: `{model["freezeSha256"]}`']
(out / "summary.md").write_text("\n".join(lines)+"\n", encoding="utf-8")
print("\n".join(lines))
