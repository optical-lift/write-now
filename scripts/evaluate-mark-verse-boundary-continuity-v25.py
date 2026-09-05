#!/usr/bin/env python3
import os
from pathlib import Path

from mark_verse_boundary_continuity_v25_core import (
    REPRESENTATIONS, adjudicate, evaluate_representation,
    read_json, read_jsonl, sha256_json, write_json,
)

protocol = read_json(os.environ["MARK_V25_PROTOCOL"])
freeze = read_json(Path(os.environ["MARK_V25_FREEZE"]) / "freeze.json")
eval_dir = Path(os.environ["MARK_V25_EVAL"])
out = Path(os.environ["MARK_V25_RESULT_OUT"])

if freeze.get("freezeAdjudication") != "FEASIBLE":
    result = {
        "schema": "mark_verse_boundary_continuity_result_v25",
        "freezeSha256": freeze.get("freezeSha256"),
        "adjudication": "INSUFFICIENT_BOUNDARY_SUPPORT",
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
        "schema": "mark_verse_boundary_continuity_result_v25",
        "freezeSha256": freeze["freezeSha256"],
        "lanes": lanes,
        "adjudication": adjudicate(lanes, freeze, protocol),
    }

result["resultSha256"] = sha256_json({k: v for k, v in result.items() if k != "resultSha256"})
out.mkdir(parents=True, exist_ok=True)
write_json(out / "result.json", result)

lines = [
    "# Mark verse-boundary continuity experiment v25",
    "",
    f'Adjudication: **{result["adjudication"]}**',
    "",
]
if "lanes" in result:
    lines += [
        "## Real adjacent verse versus matched shuffled continuation",
        "",
        "The destination model was trained only on first-passage trajectories that resolved inside TRAIN verses. The primary contrast asks whether the real next verse produces a first post-boundary destination more coherent with that frozen within-verse process than the shuffled splice does.",
        "",
        "| representation | lane | eligible boundary origins | common resolved | evaluable ops | real−shuffle bits | positive ops | sign-flip p | real recovery | shuffled recovery | guard | pass |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|",
    ]
    for rep in REPRESENTATIONS:
        for lane in ("holdout", "control"):
            r = result["lanes"][lane][rep]
            lines.append(
                f'| {rep} | {lane} | {r["eligibleBoundaryOrigins"]} | {r["commonResolvedOrigins"]} | '
                f'{r["evaluableOperators"]}/{r["frozenOperators"]} | '
                f'{r["operatorBalancedRealMinusShuffleBits"]:+.5f} | '
                f'{r["positiveOperatorFraction"]:.3f} | {r["signFlipP"]:.5f} | '
                f'{r["realRecoveryFraction"]:.3f} | {r["shuffleRecoveryFraction"]:.3f} | '
                f'{r["recoveryGuardPass"]} | {r["pass"]} |'
            )
    lines += [
        "",
        "## Boundary timing diagnostics (descriptive only)",
        "",
        "| representation | lane | real-only resolved | shuffle-only resolved | real mean distance | real median | shuffle mean distance | shuffle median |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for rep in REPRESENTATIONS:
        for lane in ("holdout", "control"):
            r = result["lanes"][lane][rep]
            def fmt(x):
                return "NA" if x is None else f"{x:.3f}"
            lines.append(
                f'| {rep} | {lane} | {r["realOnlyResolved"]} | {r["shuffleOnlyResolved"]} | '
                f'{fmt(r["realMeanDistance"])} | {fmt(r["realMedianDistance"])} | '
                f'{fmt(r["shuffleMeanDistance"])} | {fmt(r["shuffleMedianDistance"])} |'
            )
lines += ["", f'Result SHA-256: `{result["resultSha256"]}`']
(out / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
print("\n".join(lines))
