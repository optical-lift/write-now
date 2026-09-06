#!/usr/bin/env python3
import os
from pathlib import Path

from mark_hebrew_glyph_annotation_competition_v19_io import read_json, read_jsonl, sha256_json, write_json
from mark_operator_proximal_perturbation_v30_core import CLASSES, freeze_model

protocol = read_json(os.environ["MARK_V30_PROTOCOL"])
hd = Path(os.environ["MARK_V30_HEBREW_TRAIN"])
out = Path(os.environ["MARK_V30_FREEZE_OUT"])
freeze = freeze_model(read_jsonl(hd / "train.jsonl"), protocol)
freeze["schema"] = "mark_operator_proximal_perturbation_freeze_v30"
freeze["protocolSha256"] = sha256_json(protocol)
freeze["evaluationOpenedDuringFreeze"] = False
minimum = int(protocol["evaluation"]["minimumQualifiedOperatorsPerClass"])
freeze["trainFeasible"] = {
    kind: freeze["candidateCounts"][kind] >= minimum for kind in CLASSES
}
freeze["freezeAdjudication"] = (
    "FEASIBLE" if any(freeze["trainFeasible"][k] for k in CLASSES[:2])
    else "INSUFFICIENT_MATCHED_PERTURBATION_SUPPORT"
)
freeze["freezeSha256"] = sha256_json({k:v for k,v in freeze.items() if k != "freezeSha256"})
out.mkdir(parents=True, exist_ok=True)
write_json(out / "freeze.json", freeze)

lines = [
    "# V30 pre-evaluation matched proximal-perturbation freeze",
    "",
    "- inherited V29 anonymous four-history transition signature: **yes**",
    "- origin masked before every target signature: **yes**",
    "- fresh whole-book split: **yes**",
    "- representation: **lemmaFullMorph only**",
    "- evaluation opened during freeze: **false**",
    "",
    "| substitution class | frozen matched actual operators | TRAIN-feasible |",
    "|---|---:|---|",
]
for kind in CLASSES:
    lines.append(f'| {kind} | {freeze["candidateCounts"][kind]} | {freeze["trainFeasible"][kind]} |')
lines += [
    "",
    f'- freeze adjudication: **{freeze["freezeAdjudication"]}**',
    f'- freeze SHA-256: `{freeze["freezeSha256"]}`',
]
(out / "summary.md").write_text("\n".join(lines)+"\n", encoding="utf-8")
print("\n".join(lines))
