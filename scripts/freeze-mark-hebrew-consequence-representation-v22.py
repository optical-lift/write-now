#!/usr/bin/env python3
import os
from pathlib import Path

from mark_hebrew_consequence_representation_v22_core import (
    PRIMARY, REPRESENTATIONS, cell_id, freeze_model, read_json, read_jsonl,
    sha256_json, write_json,
)

protocol = read_json(os.environ["MARK_V22_PROTOCOL"])
baseline = read_json(os.environ["MARK_V22_BASELINE"])
hd = Path(os.environ["MARK_V22_HEBREW_TRAIN"])
v20d = Path(os.environ["MARK_V22_V20_FREEZE"])
out = Path(os.environ["MARK_V22_FREEZE_OUT"])

if baseline.get("v21RunId") != protocol["lineage"]["v21RunId"]:
    raise ValueError("V21 baseline run mismatch")
if baseline.get("v21ResultSha256") != protocol["lineage"]["v21ResultSha256"]:
    raise ValueError("V21 baseline result SHA mismatch")

manifest = read_json(hd / "manifest.json")
if manifest.get("schema") != "mark_hebrew_operator_representation_split_v21":
    raise ValueError("unexpected inherited V21 train artifact schema")
if manifest.get("stateAndOutcomeUseBaseLemmaOnly") is not True:
    raise ValueError("V21 source rows do not carry the frozen base-lemma structural target")

v20 = read_json(v20d / "freeze.json")
model = freeze_model(read_jsonl(hd / "train.jsonl"), v20, protocol)
model["schema"] = "mark_hebrew_consequence_representation_freeze_v22"
model["evaluationOpenedDuringFreeze"] = False
model["protocolSha256"] = sha256_json(protocol)
model["baselineManifestSha256"] = sha256_json(baseline)
model["sourceV21TrainManifest"] = manifest

minimum = int(protocol["evaluation"]["minimumEvaluableOperatorsPerCell"])
primary_counts = {
    r: len(model["cells"][cell_id(r, r)]["operators"])
    for r in PRIMARY
}
model["primaryTrainFeasible"] = {
    r: n >= minimum for r, n in primary_counts.items()
}
model["freezeAdjudication"] = (
    "FEASIBLE" if any(model["primaryTrainFeasible"].values())
    else "INSUFFICIENT_CELL_SUPPORT"
)
model["freezeSha256"] = sha256_json(
    {k: v for k, v in model.items() if k != "freezeSha256"}
)
write_json(out / "freeze.json", model)

lines = [
    "# V22 pre-evaluation consequence-representation freeze",
    "",
    f'- inherited V20 freeze SHA-256: `{model["inheritedV20FreezeSha256"]}`',
    f'- inherited shared structural states: **{len(model["sharedStates"])}**',
    '- state representation changed: **false**',
    '- consequence representations frozen: **lemma / lemma+coarse-morph / lemma+full-morph**',
    '- all 3 x 3 operator/consequence cells frozen before evaluation: **true**',
    '',
    '| operator \\ consequence | lemma | coarse morph | full morph |',
    '|---|---:|---:|---:|',
]
for op_rep in REPRESENTATIONS:
    counts = [
        len(model["cells"][cell_id(op_rep, cons_rep)]["operators"])
        for cons_rep in REPRESENTATIONS
    ]
    lines.append(f'| {op_rep} | {counts[0]} | {counts[1]} | {counts[2]} |')
lines += [
    '',
    f'- coarse diagonal train feasible: **{model["primaryTrainFeasible"]["lemmaCoarseMorph"]}**',
    f'- full diagonal train feasible: **{model["primaryTrainFeasible"]["lemmaFullMorph"]}**',
    f'- freeze adjudication: **{model["freezeAdjudication"]}**',
    '- Hebrew↔glyph operator pairing constructed: **false**',
    '- evaluation opened: **false**',
    f'- freeze SHA-256: `{model["freezeSha256"]}`',
]
out.mkdir(parents=True, exist_ok=True)
(out / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
print("\n".join(lines))
