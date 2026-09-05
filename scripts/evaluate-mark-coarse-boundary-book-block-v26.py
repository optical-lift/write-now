#!/usr/bin/env python3
import os
from pathlib import Path

from mark_coarse_boundary_book_block_v26_core import (
    adjudicate, evaluate_coarse, read_json, read_jsonl, sha256_json, write_json,
)

protocol = read_json(os.environ["MARK_V26_PROTOCOL"])
freeze = read_json(Path(os.environ["MARK_V26_FREEZE"]) / "freeze.json")
eval_dir = Path(os.environ["MARK_V26_EVAL"])
out = Path(os.environ["MARK_V26_RESULT_OUT"])

if freeze.get("freezeAdjudication") != "FEASIBLE":
    result = {
        "schema": "mark_coarse_boundary_book_block_result_v26",
        "freezeSha256": freeze.get("freezeSha256"),
        "adjudication": "INSUFFICIENT_BOOK_BLOCKED_SUPPORT",
    }
else:
    lanes = {}
    for lane in ("holdout", "control"):
        chapters = read_jsonl(eval_dir / f"{lane}.jsonl")
        lanes[lane] = evaluate_coarse(chapters, freeze["system"], protocol, lane)
    result = {
        "schema": "mark_coarse_boundary_book_block_result_v26",
        "freezeSha256": freeze["freezeSha256"],
        "lanes": lanes,
        "adjudication": adjudicate(lanes),
    }

result["resultSha256"] = sha256_json({k: v for k, v in result.items() if k != "resultSha256"})
out.mkdir(parents=True, exist_ok=True)
write_json(out / "result.json", result)

lines = [
    "# Mark coarse boundary book-block robustness experiment v26",
    "",
    f'Adjudication: **{result["adjudication"]}**',
    "",
    "This is a same-corpus robustness test, not an independent corpus replication. Whole books are disjoint across TRAIN, holdout, and control.",
    "",
]
if "lanes" in result:
    lines += [
        "| lane | eligible origins | common resolved | evaluable ops | real−shuffle bits | positive ops | sign-flip p | real recovery | shuffled recovery | guard | pass |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|",
    ]
    for lane in ("holdout", "control"):
        r = result["lanes"][lane]
        lines.append(
            f'| {lane} | {r["eligibleBoundaryOrigins"]} | {r["commonResolvedOrigins"]} | '
            f'{r["evaluableOperators"]}/{r["frozenOperators"]} | '
            f'{r["operatorBalancedRealMinusShuffleBits"]:+.5f} | '
            f'{r["positiveOperatorFraction"]:.3f} | {r["signFlipP"]:.5f} | '
            f'{r["realRecoveryFraction"]:.3f} | {r["shuffleRecoveryFraction"]:.3f} | '
            f'{r["recoveryGuardPass"]} | {r["pass"]} |'
        )
    lines += [
        "",
        "## Timing diagnostics (descriptive only)",
        "",
        "| lane | real-only | shuffle-only | real mean distance | real median | shuffle mean distance | shuffle median |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    def fmt(x):
        return "NA" if x is None else f"{x:.3f}"
    for lane in ("holdout", "control"):
        r = result["lanes"][lane]
        lines.append(
            f'| {lane} | {r["realOnlyResolved"]} | {r["shuffleOnlyResolved"]} | '
            f'{fmt(r["realMeanDistance"])} | {fmt(r["realMedianDistance"])} | '
            f'{fmt(r["shuffleMeanDistance"])} | {fmt(r["shuffleMedianDistance"])} |'
        )
lines += ["", f'Result SHA-256: `{result["resultSha256"]}`']
(out / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
print("\n".join(lines))
