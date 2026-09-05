#!/usr/bin/env python3
import os
from pathlib import Path

from mark_hebrew_consequence_representation_v22_core import (
    PRIMARY, REPRESENTATIONS, adjudicate, cell_id, compare_profiles,
    evaluate_cell, evaluate_glyph, paired_axis, read_json, read_jsonl,
    reproduction_check, sha256_json, write_json,
)

protocol = read_json(os.environ["MARK_V22_PROTOCOL"])
baseline = read_json(os.environ["MARK_V22_BASELINE"])
freeze = read_json(Path(os.environ["MARK_V22_FREEZE"]) / "freeze.json")
hd = Path(os.environ["MARK_V22_HEBREW_EVAL"])
gd = Path(os.environ["MARK_V22_GLYPH_EVAL"])
out = Path(os.environ["MARK_V22_RESULT_OUT"])

if freeze.get("protocolSha256") != sha256_json(protocol):
    raise ValueError("V22 protocol SHA mismatch against freeze")
if freeze.get("baselineManifestSha256") != sha256_json(baseline):
    raise ValueError("V22 baseline manifest SHA mismatch against freeze")

if freeze.get("freezeAdjudication") != "FEASIBLE":
    result = {
        "schema": "mark_hebrew_consequence_representation_result_v22",
        "freezeSha256": freeze.get("freezeSha256"),
        "baselineReproduction": False,
        "adjudication": "INSUFFICIENT_CELL_SUPPORT",
    }
else:
    lanes = {}
    glyph = {}
    axes = {
        r: {"consequence": {}, "operator": {}}
        for r in PRIMARY
    }
    profiles = {r: {} for r in PRIMARY}

    for lane in ("holdout", "control"):
        hrows = read_jsonl(hd / f"{lane}.jsonl")
        grows = read_jsonl(gd / f"{lane}.jsonl")
        lane_cells = {}
        for op_rep in REPRESENTATIONS:
            for cons_rep in REPRESENTATIONS:
                cid = cell_id(op_rep, cons_rep)
                lane_cells[cid] = evaluate_cell(
                    hrows, op_rep, cons_rep, freeze["cells"][cid],
                    freeze, protocol, lane
                )
        lanes[lane] = lane_cells
        glyph[lane] = evaluate_glyph(
            grows, freeze["glyph"], freeze, protocol, lane
        )

        for r in PRIMARY:
            diag = lane_cells[cell_id(r, r)]
            cons_base = lane_cells[cell_id(r, "lemma")]
            op_base = lane_cells[cell_id("lemma", r)]
            axes[r]["consequence"][lane] = paired_axis(
                hrows, r, "consequence", diag, cons_base,
                freeze, protocol, lane
            )
            axes[r]["operator"][lane] = paired_axis(
                hrows, r, "operator", diag, op_base,
                freeze, protocol, lane
            )
            profiles[r][lane] = compare_profiles(
                diag, glyph[lane], protocol, lane
            )

    baseline_ok = reproduction_check(lanes, glyph, baseline)
    result = {
        "schema": "mark_hebrew_consequence_representation_result_v22",
        "freezeSha256": freeze["freezeSha256"],
        "baselineReproduction": baseline_ok,
        "lanes": lanes,
        "glyph": glyph,
        "pairedAxes": axes,
        "crossSystemContextProfiles": profiles,
        "adjudication": adjudicate(
            lanes, axes, profiles, glyph, freeze, baseline_ok, protocol
        ),
    }

result["resultSha256"] = sha256_json(
    {k: v for k, v in result.items() if k != "resultSha256"}
)
write_json(out / "result.json", result)

lines = [
    "# Mark Hebrew consequence representation experiment v22",
    "",
    f'Adjudication: **{result["adjudication"]}**',
    f'Inherited V20/V21 reproduction exact within frozen tolerance: **{result.get("baselineReproduction", False)}**',
    "",
]

if "lanes" in result:
    lines += [
        "## Frozen 3 x 3 operator / consequence matrix",
        "",
        "State is always the inherited anonymous four-history BASE-LEMMA state. Only current operator identity and the identity used to define SAME/REPEAT/SEEN/NEW vary.",
        "",
        "| operator | consequence | lane | evaluable ops | context gain bits/event | positive ops | permutation p | pass |",
        "|---|---|---|---:|---:|---:|---:|---|",
    ]
    for op_rep in REPRESENTATIONS:
        for cons_rep in REPRESENTATIONS:
            cid = cell_id(op_rep, cons_rep)
            for lane in ("holdout", "control"):
                r = result["lanes"][lane][cid]
                lines.append(
                    f'| {op_rep} | {cons_rep} | {lane} | '
                    f'{r["evaluableOperators"]}/{r["frozenOperators"]} | '
                    f'{r["operatorBalancedContextGainBitsPerEvent"]:+.5f} | '
                    f'{r["positiveOperatorFraction"]:.3f} | '
                    f'{r["permutationP"]:.5f} | {r["pass"]} |'
                )

    lines += [
        "",
        "## Primary matched-resolution axis tests",
        "",
        "A diagonal cell must beat both one-axis alternatives: same operator with lemma consequence, and lemma operator with the same refined consequence.",
        "",
        "| resolution | axis changed | lane | eligible ops | coverage | delta bits/event | positive ops | sign-flip p | pass |",
        "|---|---|---|---:|---:|---:|---:|---:|---|",
    ]
    for resolution in PRIMARY:
        for axis in ("consequence", "operator"):
            for lane in ("holdout", "control"):
                r = result["pairedAxes"][resolution][axis][lane]
                lines.append(
                    f'| {resolution} | {axis} | {lane} | '
                    f'{r["eligibleOperators"]}/{r["diagonalEvaluableOperators"]} | '
                    f'{r["coverageFraction"]:.3f} | '
                    f'{r["operatorBalancedDeltaBitsPerEvent"]:+.5f} | '
                    f'{r["positiveOperatorFraction"]:.3f} | '
                    f'{r["signFlipP"]:.5f} | {r["pass"]} |'
                )

    lines += [
        "",
        "## Inherited glyph reproduction",
        "",
        "| lane | evaluable glyphs | context gain bits/event | positive glyphs | permutation p | pass |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for lane in ("holdout", "control"):
        r = result["glyph"][lane]
        lines.append(
            f'| {lane} | {r["evaluableOperators"]}/{r["frozenOperators"]} | '
            f'{r["operatorBalancedContextGainBitsPerEvent"]:+.5f} | '
            f'{r["positiveOperatorFraction"]:.3f} | {r["permutationP"]:.5f} | {r["pass"]} |'
        )

    lines += [
        "",
        "## Secondary cross-system context-profile comparison",
        "",
        "No Hebrew↔glyph operator matching is used. This asks only whether the same anonymous structural states are where context adds predictive value.",
        "",
        "| matched Hebrew resolution | lane | common states | Pearson r | state-permutation p | pass |",
        "|---|---|---:|---:|---:|---|",
    ]
    for resolution in PRIMARY:
        for lane in ("holdout", "control"):
            r = result["crossSystemContextProfiles"][resolution][lane]
            lines.append(
                f'| {resolution} | {lane} | {len(r["commonStates"])} | '
                f'{r["correlation"]:+.5f} | {r["permutationP"]:.5f} | {r["pass"]} |'
            )

lines += ["", f'Result SHA-256: `{result["resultSha256"]}`']
out.mkdir(parents=True, exist_ok=True)
(out / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
print("\n".join(lines))
