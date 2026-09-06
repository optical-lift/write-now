#!/usr/bin/env python3
import os
from pathlib import Path

from mark_hebrew_glyph_annotation_competition_v19_io import read_json, read_jsonl, sha256_json, write_json
from mark_operator_temporal_footprint_v29_core import REPRESENTATIONS, freeze_models

protocol = read_json(os.environ["MARK_V29_PROTOCOL"])
hd = Path(os.environ["MARK_V29_HEBREW_TRAIN"])
gd = Path(os.environ["MARK_V29_GLYPH_TRAIN"])
out = Path(os.environ["MARK_V29_FREEZE_OUT"])
model = freeze_models(read_jsonl(hd / "train.jsonl"), read_jsonl(gd / "train.jsonl"), protocol)
model["schema"] = "mark_operator_temporal_footprint_freeze_v29"
model["protocolSha256"] = sha256_json(protocol)
model["evaluationOpenedDuringFreeze"] = False
min_ops = int(protocol["evaluation"]["minimumEvaluableOperatorsPerDistance"])
min_ds = int(protocol["evaluation"]["minimumDistancesWithSupport"])
feasible = {}
for rep in REPRESENTATIONS:
    m = model["hebrew"][rep]
    supported = sum(1 for d in protocol["distances"] if len(m["operators"]) >= min_ops and m["distances"][str(d)]["trainEvents"] > 0)
    feasible[rep] = len(m["operators"]) >= min_ops and supported >= min_ds
gm = model["glyph"]
g_supported = sum(1 for d in protocol["distances"] if len(gm["operators"]) >= min_ops and gm["distances"][str(d)]["trainEvents"] > 0)
feasible["glyph"] = len(gm["operators"]) >= min_ops and g_supported >= min_ds
model["trainFeasible"] = feasible
model["freezeAdjudication"] = "FEASIBLE" if any(feasible.values()) else "INSUFFICIENT_TEMPORAL_SUPPORT"
model["freezeSha256"] = sha256_json({k:v for k,v in model.items() if k != "freezeSha256"})
out.mkdir(parents=True, exist_ok=True)
write_json(out / "freeze.json", model)
lines = [
    "# V29 pre-evaluation masked temporal-footprint freeze",
    "",
    f'- structural signature alphabet: **{model["signatureAlphabetSize"]}** masked local transitions',
    '- current operator present in signature: **false**',
    '- signed distances frozen before evaluation: **-12..-1, +1..+12**',
    '- evaluation opened during freeze: **false**',
    "",
    "| system | representation | frozen operators | TRAIN footprint events | feasible |",
    "|---|---|---:|---:|---|",
]
for rep in REPRESENTATIONS:
    m=model["hebrew"][rep]
    lines.append(f'| Hebrew | {rep} | {len(m["operators"])} | {m["trainEvents"]} | {feasible[rep]} |')
lines.append(f'| glyph | identity | {len(gm["operators"])} | {gm["trainEvents"]} | {feasible["glyph"]} |')
lines += ["", f'- freeze adjudication: **{model["freezeAdjudication"]}**', f'- freeze SHA-256: `{model["freezeSha256"]}`']
(out / "summary.md").write_text("\n".join(lines)+"\n", encoding="utf-8")
print("\n".join(lines))
