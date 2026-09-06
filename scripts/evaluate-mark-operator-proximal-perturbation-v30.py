#!/usr/bin/env python3
import os
from pathlib import Path

from mark_hebrew_glyph_annotation_competition_v19_io import read_json, read_jsonl, sha256_json, write_json
from mark_operator_proximal_perturbation_v30_core import CLASSES, adjudicate, evaluate_lane

protocol = read_json(os.environ["MARK_V30_PROTOCOL"])
freeze = read_json(Path(os.environ["MARK_V30_FREEZE"]) / "freeze.json")
hd = Path(os.environ["MARK_V30_HEBREW_EVAL"])
out = Path(os.environ["MARK_V30_RESULT_OUT"])

if freeze.get("freezeAdjudication") != "FEASIBLE":
    result = {
        "schema": "mark_operator_proximal_perturbation_result_v30",
        "freezeSha256": freeze.get("freezeSha256"),
        "adjudication": "INSUFFICIENT_MATCHED_PERTURBATION_SUPPORT",
    }
else:
    lanes = {
        lane: evaluate_lane(read_jsonl(hd / f"{lane}.jsonl"), freeze, protocol, lane)
        for lane in ("holdout", "control")
    }
    result = {
        "schema": "mark_operator_proximal_perturbation_result_v30",
        "freezeSha256": freeze["freezeSha256"],
        "lanes": lanes,
        "adjudication": adjudicate(lanes),
    }
result["resultSha256"] = sha256_json({k:v for k,v in result.items() if k != "resultSha256"})
out.mkdir(parents=True, exist_ok=True)
write_json(out / "result.json", result)

lines = [
    "# Mark operator proximal-perturbation experiment v30",
    "",
    f'Adjudication: **{result["adjudication"]}**',
    "",
    "V30 keeps V29's origin mask and anonymous four-history transition signature. Only the frozen operator-conditioned source is substituted; the observed anonymous neighborhood is unchanged. Positive D_local means the actual operator fits +1/+2 better than its matched substitute, above the average advantage at -2/-1 and +5/+6.",
    "",
]
if "lanes" in result:
    lines += [
        "| class | lane | qualified operators | pre damage | local +1/+2 damage | far +5/+6 damage | D_local | sign-flip p | pass |",
        "|---|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for kind in CLASSES:
        for lane in ("holdout", "control"):
            r = result["lanes"][lane][kind]
            def f(key):
                return "NA" if key not in r else f'{r[key]:+.6f}'
            lines.append(
                f'| {kind} | {lane} | {r["qualifiedOperators"]} | {f("meanPreDamage")} | '
                f'{f("meanLocalDamage")} | {f("meanFarDamage")} | {f("meanDLocal")} | '
                f'{r.get("signFlipP",1.0):.5f} | {r["pass"]} |'
            )
    lines += ["", "## Frozen six-distance damage curves", ""]
    for kind in CLASSES:
        for lane in ("holdout", "control"):
            r = result["lanes"][lane][kind]
            curve = r.get("meanDistanceDamage", {})
            vals = ", ".join(f'{d}:{curve.get(str(d), float("nan")):+.6f}' for d in protocol["distances"])
            lines.append(f'- **{kind} / {lane}:** {vals}')
lines += ["", f'Result SHA-256: `{result["resultSha256"]}`']
(out / "summary.md").write_text("\n".join(lines)+"\n", encoding="utf-8")
print("\n".join(lines))
