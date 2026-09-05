#!/usr/bin/env python3
import os
from pathlib import Path

from mark_competing_resolution_v27_core import (
    REPRESENTATIONS, adjudicate, evaluate_representation,
    read_json, read_jsonl, sha256_json, write_json,
)

protocol = read_json(os.environ["MARK_V27_PROTOCOL"])
freeze = read_json(Path(os.environ["MARK_V27_FREEZE"]) / "freeze.json")
eval_dir = Path(os.environ["MARK_V27_EVAL"])
out = Path(os.environ["MARK_V27_RESULT_OUT"])

if freeze.get("freezeAdjudication") != "FEASIBLE":
    result = {
        "schema": "mark_competing_resolution_result_v27",
        "freezeSha256": freeze.get("freezeSha256"),
        "adjudication": "INSUFFICIENT_COMPETING_RESOLUTION_SUPPORT",
    }
else:
    lanes = {"holdout": {}, "control": {}}
    for lane in ("holdout", "control"):
        chapters = read_jsonl(eval_dir / f"{lane}.jsonl")
        for rep in REPRESENTATIONS:
            lanes[lane][rep] = evaluate_representation(
                chapters, rep, freeze["systems"][rep], protocol, lane
            )
    result = {
        "schema": "mark_competing_resolution_result_v27",
        "freezeSha256": freeze["freezeSha256"],
        "lanes": lanes,
        "adjudication": adjudicate(lanes),
    }

result["resultSha256"] = sha256_json({k: v for k, v in result.items() if k != "resultSha256"})
out.mkdir(parents=True, exist_ok=True)
write_json(out / "result.json", result)

lines = [
    "# Mark competing-resolution experiment v27",
    "",
    f'Adjudication: **{result["adjudication"]}**',
    "",
]
if "lanes" in result:
    lines += [
        "## Full competing-resolution trajectory",
        "",
        "Each origin is followed only inside its inherited verse. Risk rows are CONTINUE until the first terminal event: anonymous structural DEPARTURE or VERSE_BOUNDARY. The primary interaction contrast is Pctx versus the additive context+operator model.",
        "",
        "| representation | lane | origins | eval ops | interaction over additive | gain over context-only | gain over operator-only | +ops | sign-flip p | pass |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for rep in REPRESENTATIONS:
        for lane in ("holdout", "control"):
            r = result["lanes"][lane][rep]
            lines.append(
                f'| {rep} | {lane} | {r["evaluationOrigins"]} | {r["evaluableOperators"]}/{r["frozenOperators"]} | '
                f'{r["operatorBalancedInteractionGain"]:+.5f} | '
                f'{r["operatorBalancedGainOverContextOnly"]:+.5f} | '
                f'{r["operatorBalancedGainOverOperatorOnly"]:+.5f} | '
                f'{r["positiveInteractionOperatorFraction"]:.3f} | {r["signFlipP"]:.5f} | {r["pass"]} |'
            )
    lines += [
        "",
        "## Predeclared localization diagnostics",
        "",
        "Timing gain collapses DEPARTURE+VERSE_BOUNDARY into TERMINAL versus CONTINUE. Cause gain conditions the terminal row on DEPARTURE versus VERSE_BOUNDARY. These do not gate adjudication.",
        "",
        "| representation | lane | timing interaction gain | cause interaction gain | departure fraction | boundary fraction | mean resolution step | median step |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for rep in REPRESENTATIONS:
        for lane in ("holdout", "control"):
            r = result["lanes"][lane][rep]
            def fmt(x):
                return "NA" if x is None else f"{x:.3f}"
            lines.append(
                f'| {rep} | {lane} | {r["operatorBalancedTimingInteractionGain"]:+.5f} | '
                f'{r["operatorBalancedCauseInteractionGain"]:+.5f} | '
                f'{r["departureFraction"]:.3f} | {r["verseBoundaryFraction"]:.3f} | '
                f'{fmt(r["meanResolutionStep"])} | {fmt(r["medianResolutionStep"])} |'
            )
lines += ["", f'Result SHA-256: `{result["resultSha256"]}`']
(out / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
print("\n".join(lines))
