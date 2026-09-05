#!/usr/bin/env python3
import os
from pathlib import Path

from mark_hebrew_operator_representation_v21_core import (
    adjudicate, compare_profiles, evaluate_glyph, evaluate_representation,
    paired_refinement, read_json, read_jsonl, sha256_json, write_json,
)

protocol = read_json(os.environ["MARK_V21_PROTOCOL"])
freeze = read_json(Path(os.environ["MARK_V21_FREEZE"]) / "freeze.json")
hd = Path(os.environ["MARK_V21_HEBREW_EVAL"])
gd = Path(os.environ["MARK_V21_GLYPH_EVAL"])
out = Path(os.environ["MARK_V21_RESULT_OUT"])

if freeze.get("freezeAdjudication") != "FEASIBLE":
    result = {
        "schema": "mark_hebrew_operator_representation_result_v21",
        "freezeSha256": freeze.get("freezeSha256"),
        "adjudication": "INSUFFICIENT_REFINED_SUPPORT",
    }
else:
    lanes = {}
    paired = {
        "lemmaCoarseMorph": {},
        "lemmaFullMorph": {},
    }
    profiles = {
        "lemma": {},
        "lemmaCoarseMorph": {},
        "lemmaFullMorph": {},
    }

    for lane in ("holdout", "control"):
        hrows = read_jsonl(hd / f"{lane}.jsonl")
        grows = read_jsonl(gd / f"{lane}.jsonl")

        lane_results = {}
        for rep in ("lemma", "lemmaCoarseMorph", "lemmaFullMorph"):
            lane_results[rep] = evaluate_representation(
                hrows, rep, freeze["systems"][rep], freeze, protocol, lane
            )
        lane_results["glyph"] = evaluate_glyph(
            grows, freeze["systems"]["glyph"], freeze, protocol, lane
        )
        lanes[lane] = lane_results

        for rep in ("lemmaCoarseMorph", "lemmaFullMorph"):
            paired[rep][lane] = paired_refinement(
                hrows, rep, lane_results["lemma"], lane_results[rep],
                freeze, protocol, lane
            )

        for rep in ("lemma", "lemmaCoarseMorph", "lemmaFullMorph"):
            profiles[rep][lane] = compare_profiles(
                lane_results[rep], lane_results["glyph"], protocol, lane
            )

    result = {
        "schema": "mark_hebrew_operator_representation_result_v21",
        "freezeSha256": freeze["freezeSha256"],
        "lanes": lanes,
        "pairedRefinement": paired,
        "crossSystemContextProfiles": profiles,
        "adjudication": adjudicate(lanes, paired, profiles, freeze, protocol),
    }

result["resultSha256"] = sha256_json(
    {k: v for k, v in result.items() if k != "resultSha256"}
)
write_json(out / "result.json", result)

lines = [
    "# Mark Hebrew operator representation experiment v21",
    "",
    f'Adjudication: **{result["adjudication"]}**',
    "",
]

if "lanes" in result:
    lines += [
        "## Context-conditioned effect by operator representation",
        "",
        "| representation | lane | evaluable operators | context gain bits/event | positive operators | permutation p | pass |",
        "|---|---|---:|---:|---:|---:|---|",
    ]
    for rep in ("lemma", "lemmaCoarseMorph", "lemmaFullMorph", "glyph"):
        for lane in ("holdout", "control"):
            r = result["lanes"][lane][rep]
            lines.append(
                f'| {rep} | {lane} | {r["evaluableOperators"]}/{r["frozenOperators"]} | '
                f'{r["operatorBalancedContextGainBitsPerEvent"]:+.5f} | '
                f'{r["positiveOperatorFraction"]:.3f} | {r["permutationP"]:.5f} | '
                f'{r["pass"]} |'
            )

    lines += [
        "",
        "## Paired morphology refinement over inherited lemma",
        "",
        "| representation | lane | eligible parent lemmas | parent coverage | delta bits/event | positive parents | sign-flip p | pass |",
        "|---|---|---:|---:|---:|---:|---:|---|",
    ]
    for rep in ("lemmaCoarseMorph", "lemmaFullMorph"):
        for lane in ("holdout", "control"):
            r = result["pairedRefinement"][rep][lane]
            lines.append(
                f'| {rep} | {lane} | {r["eligibleParentLemmas"]}/{r["baselineEvaluableLemmas"]} | '
                f'{r["parentCoverageFraction"]:.3f} | '
                f'{r["parentBalancedDeltaBitsPerEvent"]:+.5f} | '
                f'{r["positiveParentFraction"]:.3f} | {r["signFlipP"]:.5f} | '
                f'{r["pass"]} |'
            )

    lines += [
        "",
        "## Cross-system structural-context profile",
        "",
        "No Hebrew↔glyph operator matching is used. State and consequence labels remain the inherited V20 base-lemma/glyph structural labels.",
        "",
        "| Hebrew representation | lane | common states | Pearson r | state-permutation p | pass |",
        "|---|---|---:|---:|---:|---|",
    ]
    for rep in ("lemma", "lemmaCoarseMorph", "lemmaFullMorph"):
        for lane in ("holdout", "control"):
            r = result["crossSystemContextProfiles"][rep][lane]
            lines.append(
                f'| {rep} | {lane} | {len(r["commonStates"])} | '
                f'{r["correlation"]:+.5f} | {r["permutationP"]:.5f} | {r["pass"]} |'
            )

lines += ["", f'Result SHA-256: `{result["resultSha256"]}`']
out.mkdir(parents=True, exist_ok=True)
(out / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
print("\n".join(lines))
