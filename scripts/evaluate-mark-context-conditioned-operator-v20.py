#!/usr/bin/env python3
import os
from pathlib import Path
from mark_context_conditioned_operator_v20_core import (
    adjudicate, compare_profiles, evaluate_system,
    read_json, read_jsonl, sha256_json, write_json,
)

protocol = read_json(os.environ["MARK_V20_PROTOCOL"])
freeze = read_json(Path(os.environ["MARK_V20_FREEZE"]) / "freeze.json")
hd = Path(os.environ["MARK_V20_HEBREW_EVAL"])
gd = Path(os.environ["MARK_V20_GLYPH_EVAL"])
out = Path(os.environ["MARK_V20_RESULT_OUT"])

if freeze.get("freezeAdjudication") != "FEASIBLE":
    result = {
        "schema": "mark_context_conditioned_operator_result_v20",
        "freezeSha256": freeze.get("freezeSha256"),
        "adjudication": "INSUFFICIENT_CONTEXT_SUPPORT",
    }
else:
    lanes = {}
    profiles = {}
    for lane in ("holdout", "control"):
        h = evaluate_system(read_jsonl(hd / f"{lane}.jsonl"), "hebrew", freeze, protocol, lane)
        g = evaluate_system(read_jsonl(gd / f"{lane}.jsonl"), "glyph", freeze, protocol, lane)
        lanes[lane] = {"hebrew": h, "glyph": g}
        profiles[lane] = compare_profiles(h, g, protocol, lane)
    result = {
        "schema": "mark_context_conditioned_operator_result_v20",
        "freezeSha256": freeze["freezeSha256"],
        "lanes": lanes,
        "crossSystemContextProfiles": profiles,
        "adjudication": adjudicate(lanes, profiles, freeze, protocol),
    }

result["resultSha256"] = sha256_json({k: v for k, v in result.items() if k != "resultSha256"})
write_json(out / "result.json", result)

lines = [
    "# Mark context-conditioned operator experiment v20",
    "",
    f'Adjudication: **{result["adjudication"]}**',
    "",
]
if "lanes" in result:
    lines += [
        "## Same operator, different structural context",
        "",
        "| system | lane | evaluable operators | context gain bits/event | positive operators | permutation p | pass |",
        "|---|---|---:|---:|---:|---:|---|",
    ]
    for kind in ("hebrew", "glyph"):
        for lane in ("holdout", "control"):
            r = result["lanes"][lane][kind]
            lines.append(
                f'| {kind} | {lane} | {r["evaluableOperators"]}/{r["frozenOperators"]} | '
                f'{r["operatorBalancedContextGainBitsPerEvent"]:+.5f} | '
                f'{r["positiveOperatorFraction"]:.3f} | {r["permutationP"]:.5f} | {r["pass"]} |'
            )
    lines += [
        "",
        "## Cross-system structural-context modulation profile",
        "",
        "No Hebrew↔glyph operator matching is used here. The comparison is only across the same anonymous structural state labels.",
        "",
        "| lane | common states | Pearson r | state-permutation p | pass |",
        "|---|---:|---:|---:|---|",
    ]
    for lane in ("holdout", "control"):
        r = result["crossSystemContextProfiles"][lane]
        lines.append(
            f'| {lane} | {len(r["commonStates"])} | {r["correlation"]:+.5f} | '
            f'{r["permutationP"]:.5f} | {r["pass"]} |'
        )
lines += ["", f'Result SHA-256: `{result["resultSha256"]}`']
out.mkdir(parents=True, exist_ok=True)
(out / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
print("\n".join(lines))
