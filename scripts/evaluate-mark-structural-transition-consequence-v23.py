#!/usr/bin/env python3
import os
from pathlib import Path

from mark_structural_transition_consequence_v23_core import (
    HEBREW_REPS, adjudicate, compare_transition_profiles,
    read_json, read_jsonl, sha256_json, write_json,
)
from mark_structural_transition_consequence_v23_fast import evaluate_system_fast

protocol = read_json(os.environ["MARK_V23_PROTOCOL"])
freeze = read_json(Path(os.environ["MARK_V23_FREEZE"]) / "freeze.json")
hd = Path(os.environ["MARK_V23_HEBREW_EVAL"])
gd = Path(os.environ["MARK_V23_GLYPH_EVAL"])
out = Path(os.environ["MARK_V23_RESULT_OUT"])

if freeze.get("freezeAdjudication") != "FEASIBLE":
    result = {
        "schema": "mark_structural_transition_consequence_result_v23",
        "freezeSha256": freeze.get("freezeSha256"),
        "adjudication": "INSUFFICIENT_STRUCTURAL_SUPPORT",
    }
else:
    results = {"holdout": {}, "control": {}}
    profiles = {rep: {} for rep in HEBREW_REPS}
    for lane in ("holdout", "control"):
        hrows = read_jsonl(hd / f"{lane}.jsonl")
        grows = read_jsonl(gd / f"{lane}.jsonl")
        for rep in HEBREW_REPS:
            pair = freeze["systems"][rep]
            h = evaluate_system_fast(hrows, "hebrew", rep, pair, protocol, lane)
            g = evaluate_system_fast(grows, "glyph", rep, pair, protocol, lane)
            results[lane][rep] = {"hebrew": h, "glyph": g}
            profiles[rep][lane] = compare_transition_profiles(h, g, protocol, lane, rep)

    result = {
        "schema": "mark_structural_transition_consequence_result_v23",
        "freezeSha256": freeze["freezeSha256"],
        "lanes": results,
        "crossSystemTransitionProfiles": profiles,
        "adjudication": adjudicate(results, profiles, freeze, protocol),
    }

result["resultSha256"] = sha256_json({k: v for k, v in result.items() if k != "resultSha256"})
write_json(out / "result.json", result)

lines = [
    "# Mark structural-transition consequence experiment v23",
    "",
    f'Adjudication: **{result["adjudication"]}**',
    "",
]
if "lanes" in result:
    lines += [
        "## Immediate anonymous relational-state transformation",
        "",
        "The outcome is the outgoing four-history equality pattern immediately after the current operator is inserted. No next-token recurrence outcome is used.",
        "",
        "| relational representation | system | lane | evaluable ops | interaction gain bits/event | total gain over state-only | positive ops | permutation p | pass |",
        "|---|---|---|---:|---:|---:|---:|---:|---|",
    ]
    for rep in HEBREW_REPS:
        for kind in ("hebrew", "glyph"):
            for lane in ("holdout", "control"):
                r = result["lanes"][lane][rep][kind]
                lines.append(
                    f'| {rep} | {kind} | {lane} | {r["evaluableOperators"]}/{r["frozenOperators"]} | '
                    f'{r["operatorBalancedInteractionGainBitsPerEvent"]:+.5f} | '
                    f'{r["operatorBalancedTotalGainOverStateOnlyBitsPerEvent"]:+.5f} | '
                    f'{r["positiveInteractionOperatorFraction"]:.3f} | {r["permutationP"]:.5f} | {r["pass"]} |'
                )
    lines += [
        "",
        "## Cross-system anonymous transition-profile alignment",
        "",
        "No Hebrew↔glyph operator matching is used. The comparison is across identical anonymous incoming-state -> outgoing-state transition labels.",
        "",
        "| Hebrew relational representation | lane | common transition cells | Pearson r | row-wise permutation p | pass |",
        "|---|---|---:|---:|---:|---|",
    ]
    for rep in HEBREW_REPS:
        for lane in ("holdout", "control"):
            r = result["crossSystemTransitionProfiles"][rep][lane]
            lines.append(
                f'| {rep} | {lane} | {len(r["commonTransitionCells"])} | '
                f'{r["correlation"]:+.5f} | {r["permutationP"]:.5f} | {r["pass"]} |'
            )
lines += ["", f'Result SHA-256: `{result["resultSha256"]}`']
out.mkdir(parents=True, exist_ok=True)
(out / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
print("\n".join(lines))
