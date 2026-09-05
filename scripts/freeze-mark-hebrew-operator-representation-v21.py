#!/usr/bin/env python3
import os
from pathlib import Path

from mark_hebrew_operator_representation_v21_core import (
    freeze_model, read_json, read_jsonl, sha256_json, write_json,
)

protocol = read_json(os.environ["MARK_V21_PROTOCOL"])
hd = Path(os.environ["MARK_V21_HEBREW_TRAIN"])
v20d = Path(os.environ["MARK_V21_V20_FREEZE"])
out = Path(os.environ["MARK_V21_FREEZE_OUT"])

v20 = read_json(v20d / "freeze.json")
if v20.get("freezeSha256") != protocol["lineage"]["v20FreezeSha256"]:
    raise ValueError("inherited V20 freeze SHA mismatch")
if v20.get("protocolSha256") != protocol["lineage"]["v20ProtocolSha256"]:
    raise ValueError("inherited V20 protocol SHA mismatch")
model = freeze_model(read_jsonl(hd / "train.jsonl"), v20, protocol)

model["schema"] = "mark_hebrew_operator_representation_freeze_v21"
model["evaluationOpenedDuringFreeze"] = False
model["protocolSha256"] = sha256_json(protocol)

minimum = int(protocol["evaluation"]["minimumEvaluableOperatorsPerRepresentation"])
candidate_counts = {
    rep: len(model["systems"][rep]["operators"])
    for rep in ("lemmaCoarseMorph", "lemmaFullMorph")
}
model["candidateTrainFeasible"] = {
    rep: n >= minimum for rep, n in candidate_counts.items()
}
model["freezeAdjudication"] = (
    "FEASIBLE" if any(model["candidateTrainFeasible"].values())
    else "INSUFFICIENT_REFINED_SUPPORT"
)
model["freezeSha256"] = sha256_json(
    {k: v for k, v in model.items() if k != "freezeSha256"}
)
write_json(out / "freeze.json", model)

lines = [
    "# V21 pre-evaluation Hebrew operator-representation freeze",
    "",
    f'- inherited V20 freeze SHA-256: `{model["inheritedV20FreezeSha256"]}`',
    f'- inherited shared structural states: **{len(model["sharedStates"])}**',
    f'- inherited lemma operators: **{len(model["systems"]["lemma"]["operators"])}**',
    f'- inherited glyph operators: **{len(model["systems"]["glyph"]["operators"])}**',
    f'- coarse-morph frozen operators: **{candidate_counts["lemmaCoarseMorph"]}**',
    f'- full-morph frozen operators: **{candidate_counts["lemmaFullMorph"]}**',
    f'- freeze adjudication: **{model["freezeAdjudication"]}**',
    '- state/outcome changed by morphology: **false**',
    '- Hebrew↔glyph operator pairing constructed: **false**',
    '- evaluation opened: **false**',
    f'- freeze SHA-256: `{model["freezeSha256"]}`',
]
out.mkdir(parents=True, exist_ok=True)
(out / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
print("\n".join(lines))
