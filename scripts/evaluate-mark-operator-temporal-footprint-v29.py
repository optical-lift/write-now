#!/usr/bin/env python3
import os
from pathlib import Path

from mark_hebrew_glyph_annotation_competition_v19_io import read_json, read_jsonl, sha256_json, write_json
from mark_operator_temporal_footprint_v29_core import REPRESENTATIONS, adjudicate, evaluate_all

protocol = read_json(os.environ["MARK_V29_PROTOCOL"])
freeze = read_json(Path(os.environ["MARK_V29_FREEZE"]) / "freeze.json")
hd = Path(os.environ["MARK_V29_HEBREW_EVAL"])
gd = Path(os.environ["MARK_V29_GLYPH_EVAL"])
out = Path(os.environ["MARK_V29_RESULT_OUT"])

if freeze.get("freezeAdjudication") != "FEASIBLE":
    result = {
        "schema": "mark_operator_temporal_footprint_result_v29",
        "freezeSha256": freeze.get("freezeSha256"),
        "adjudication": "INSUFFICIENT_TEMPORAL_SUPPORT",
    }
else:
    hebrew_eval = {lane: read_jsonl(hd / f"{lane}.jsonl") for lane in ("holdout","control")}
    glyph_eval = {lane: read_jsonl(gd / f"{lane}.jsonl") for lane in ("holdout","control")}
    lanes, glyph = evaluate_all(hebrew_eval, glyph_eval, freeze, protocol)
    result = {
        "schema": "mark_operator_temporal_footprint_result_v29",
        "freezeSha256": freeze["freezeSha256"],
        "lanes": lanes,
        "glyph": glyph,
        "adjudication": adjudicate(lanes, glyph),
    }
result["resultSha256"] = sha256_json({k:v for k,v in result.items() if k != "resultSha256"})
out.mkdir(parents=True, exist_ok=True)
write_json(out / "result.json", result)

lines = [
    "# Mark operator temporal-footprint experiment v29",
    "",
    f'Adjudication: **{result["adjudication"]}**',
    "",
]
if "lanes" in result:
    lines += [
        "## Outcome-agnostic masked temporal footprint",
        "",
        "The current operator was replaced by a unique sentinel before every surrounding structural signature was computed. The primary gate is positive footprint mass across all 24 predeclared signed distances under a joint residual-reassignment null; no distance is selected post hoc.",
        "",
        "| system | representation | lane | events | supported distances | positive mass | mass p | peak d | peak gain | familywise peak p | pre mass | post mass | center | pass |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for lane in ("holdout","control"):
        g = result["glyph"][lane]
        def fmt(x):
            return "NA" if x is None else f"{x:+.5f}"
        lines.append(
            f'| glyph | identity | {lane} | {g["evaluationEvents"]} | {g["supportedDistances"]} | '
            f'{g["positiveFootprintMass"]:+.5f} | {g["positiveFootprintMassP"]:.5f} | '
            f'{g["familywisePeakDistance"]} | {g["familywisePeakGain"]:+.5f} | {g["familywisePeakP"]:.5f} | '
            f'{g["preOperatorPositiveMass"]:+.5f} | {g["postOperatorPositiveMass"]:+.5f} | {fmt(g["centerOfPositiveMass"])} | {g["pass"]} |'
        )
        for rep in REPRESENTATIONS:
            h = result["lanes"][lane][rep]["hebrew"]
            lines.append(
                f'| Hebrew | {rep} | {lane} | {h["evaluationEvents"]} | {h["supportedDistances"]} | '
                f'{h["positiveFootprintMass"]:+.5f} | {h["positiveFootprintMassP"]:.5f} | '
                f'{h["familywisePeakDistance"]} | {h["familywisePeakGain"]:+.5f} | {h["familywisePeakP"]:.5f} | '
                f'{h["preOperatorPositiveMass"]:+.5f} | {h["postOperatorPositiveMass"]:+.5f} | {fmt(h["centerOfPositiveMass"])} | {h["pass"]} |'
            )
    lines += [
        "",
        "## Frozen distance curves",
        "",
        "| system | representation | lane | gain by signed distance (-12..-1,+1..+12) |",
        "|---|---|---|---|",
    ]
    order = [int(d) for d in protocol["distances"]]
    for lane in ("holdout","control"):
        g=result["glyph"][lane]
        gcurve=", ".join(f'{d}:{g["gainCurve"].get(str(d)):+.5f}' if g["gainCurve"].get(str(d)) is not None else f'{d}:NA' for d in order)
        lines.append(f'| glyph | identity | {lane} | {gcurve} |')
        for rep in REPRESENTATIONS:
            h=result["lanes"][lane][rep]["hebrew"]
            curve=", ".join(f'{d}:{h["gainCurve"].get(str(d)):+.5f}' if h["gainCurve"].get(str(d)) is not None else f'{d}:NA' for d in order)
            lines.append(f'| Hebrew | {rep} | {lane} | {curve} |')
    lines += [
        "",
        "## Cross-system temporal curve alignment",
        "",
        "No Hebrew operator is paired with any glyph. Correlation is over signed-distance footprint shape only.",
        "",
        "| Hebrew representation | lane | common distances | Pearson r | permutation p | pass |",
        "|---|---|---:|---:|---:|---|",
    ]
    for rep in REPRESENTATIONS:
        for lane in ("holdout","control"):
            c=result["lanes"][lane][rep]["cross"]
            lines.append(f'| {rep} | {lane} | {c["commonDistances"]} | {c["pearsonR"]:+.5f} | {c["permutationP"]:.5f} | {c["pass"]} |')
lines += ["", f'Result SHA-256: `{result["resultSha256"]}`']
(out / "summary.md").write_text("\n".join(lines)+"\n", encoding="utf-8")
print("\n".join(lines))
