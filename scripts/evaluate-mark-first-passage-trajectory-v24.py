#!/usr/bin/env python3
import os
from pathlib import Path

from mark_first_passage_trajectory_v24_core import (
    HEBREW_REPS, adjudicate, compare_profiles, evaluate_system,
    read_json, read_jsonl, sha256_json, write_json,
)

protocol = read_json(os.environ["MARK_V24_PROTOCOL"])
freeze = read_json(Path(os.environ["MARK_V24_FREEZE"]) / "freeze.json")
hd = Path(os.environ["MARK_V24_HEBREW_EVAL"])
gd = Path(os.environ["MARK_V24_GLYPH_EVAL"])
out = Path(os.environ["MARK_V24_RESULT_OUT"])

if freeze.get("freezeAdjudication") != "FEASIBLE":
    result = {
        "schema": "mark_first_passage_trajectory_result_v24",
        "freezeSha256": freeze.get("freezeSha256"),
        "adjudication": "INSUFFICIENT_FIRST_PASSAGE_SUPPORT",
    }
else:
    results = {"holdout": {}, "control": {}}
    profiles = {rep: {} for rep in HEBREW_REPS}
    for lane in ("holdout", "control"):
        hrows = read_jsonl(hd / f"{lane}.jsonl")
        grows = read_jsonl(gd / f"{lane}.jsonl")
        for rep in HEBREW_REPS:
            pair = freeze["systems"][rep]
            h = evaluate_system(hrows, "hebrew", rep, pair, protocol, lane)
            g = evaluate_system(grows, "glyph", rep, pair, protocol, lane)
            results[lane][rep] = {"hebrew": h, "glyph": g}
            profiles[rep][lane] = compare_profiles(h, g, protocol, lane, rep)

    result = {
        "schema": "mark_first_passage_trajectory_result_v24",
        "freezeSha256": freeze["freezeSha256"],
        "lanes": results,
        "crossSystemFirstPassageProfiles": profiles,
        "adjudication": adjudicate(results, profiles, freeze, protocol),
    }

result["resultSha256"] = sha256_json({k: v for k, v in result.items() if k != "resultSha256"})
write_json(out / "result.json", result)

lines = [
    "# Mark first-passage trajectory experiment v24",
    "",
    f'Adjudication: **{result["adjudication"]}**',
    "",
]
if "lanes" in result:
    lines += [
        "## First downstream relational departure",
        "",
        "S0 is the incoming anonymous relational state, S1 is the immediate state after the current operator, and F is the first subsequent anonymous state different from S1 (or unit-end/no-departure). The interaction model must beat an additive context+operator model, a context-only model, and an invariant-operator model.",
        "",
        "| representation | system | lane | evaluable ops | interaction over additive | gain over context-only | gain over invariant operator | positive ops | permutation p | pass |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for rep in HEBREW_REPS:
        for kind in ("hebrew", "glyph"):
            for lane in ("holdout", "control"):
                r = result["lanes"][lane][rep][kind]
                lines.append(
                    f'| {rep} | {kind} | {lane} | {r["evaluableOperators"]}/{r["frozenOperators"]} | '
                    f'{r["operatorBalancedInteractionGainOverAdditiveBitsPerEvent"]:+.5f} | '
                    f'{r["operatorBalancedGainOverContextOnlyBitsPerEvent"]:+.5f} | '
                    f'{r["operatorBalancedGainOverInvariantOperatorBitsPerEvent"]:+.5f} | '
                    f'{r["positiveInteractionOperatorFraction"]:.3f} | {r["permutationP"]:.5f} | {r["pass"]} |'
                )

    lines += [
        "",
        "## First-passage timing diagnostics (descriptive only)",
        "",
        "| representation | system | lane | mean steps to departure | median steps | unit-end/no-departure fraction |",
        "|---|---|---|---:|---:|---:|",
    ]
    for rep in HEBREW_REPS:
        for kind in ("hebrew", "glyph"):
            for lane in ("holdout", "control"):
                d = result["lanes"][lane][rep][kind]["distanceDiagnostics"]
                lines.append(
                    f'| {rep} | {kind} | {lane} | {d["meanStepsToFirstDeparture"]:.3f} | '
                    f'{d["medianStepsToFirstDeparture"]:.3f} | {d["unitEndNoDepartureFraction"]:.3f} |'
                )

    lines += [
        "",
        "## Cross-system anonymous first-passage profile alignment",
        "",
        "No Hebrew↔glyph operator matching is used. Comparison is over identical anonymous S0 -> S1 -> F structural cells.",
        "",
        "| Hebrew representation | lane | common trajectory cells | Pearson r | row-wise permutation p | pass |",
        "|---|---|---:|---:|---:|---|",
    ]
    for rep in HEBREW_REPS:
        for lane in ("holdout", "control"):
            r = result["crossSystemFirstPassageProfiles"][rep][lane]
            lines.append(
                f'| {rep} | {lane} | {len(r["commonTransitionCells"])} | '
                f'{r["correlation"]:+.5f} | {r["permutationP"]:.5f} | {r["pass"]} |'
            )

lines += ["", f'Result SHA-256: `{result["resultSha256"]}`']
out.mkdir(parents=True, exist_ok=True)
(out / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
print("\n".join(lines))
