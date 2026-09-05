#!/usr/bin/env python3
import os
from pathlib import Path
from mark_operator_selection_grammar_v28_core import (
    REPRESENTATIONS, adjudicate, read_json, read_jsonl, sha256_json, write_json,
)
from mark_operator_selection_grammar_v28_fast import evaluate_all_fast

protocol = read_json(os.environ["MARK_V28_PROTOCOL"])
freeze = read_json(Path(os.environ["MARK_V28_FREEZE"]) / "freeze.json")
hd = Path(os.environ["MARK_V28_HEBREW_EVAL"])
gd = Path(os.environ["MARK_V28_GLYPH_EVAL"])
out = Path(os.environ["MARK_V28_RESULT_OUT"])
if freeze.get("freezeAdjudication") != "FEASIBLE":
    result={"schema":"mark_operator_selection_grammar_result_v28","freezeSha256":freeze.get("freezeSha256"),"adjudication":"INSUFFICIENT_SELECTION_SUPPORT"}
else:
    hebrew_eval={lane:read_jsonl(hd / f"{lane}.jsonl") for lane in ("holdout","control")}
    glyph_eval={lane:read_jsonl(gd / f"{lane}.jsonl") for lane in ("holdout","control")}
    lanes, glyph = evaluate_all_fast(hebrew_eval, glyph_eval, freeze, protocol)
    result={"schema":"mark_operator_selection_grammar_result_v28","freezeSha256":freeze["freezeSha256"],"lanes":lanes,"glyph":glyph,"adjudication":adjudicate(lanes,glyph)}
result["resultSha256"] = sha256_json({k:v for k,v in result.items() if k != "resultSha256"})
out.mkdir(parents=True, exist_ok=True)
write_json(out / "result.json", result)
lines=["# Mark operator-selection grammar experiment v28","",f'Adjudication: **{result["adjudication"]}**',""]
if "lanes" in result:
    lines += ["## Operator selection beyond prefix position","","| system | representation | lane | events | eval ops | state-selection gain | gain over global | +ops | residual-null p | actual>matched substitute | pass |","|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|"]
    for lane in ("holdout","control"):
        g=result["glyph"][lane]
        lines.append(f'| glyph | identity | {lane} | {g["evaluationEvents"]} | {g["evaluableOperators"]}/{g["frozenOperators"]} | {g["operatorBalancedSelectionGainBits"]:+.5f} | {g["operatorBalancedGainOverGlobalBits"]:+.5f} | {g["positiveOperatorFraction"]:.3f} | {g["residualReassignmentP"]:.5f} | {g["counterfactualActualPreference"]:.3f} | {g["pass"]} |')
        for rep in REPRESENTATIONS:
            h=result["lanes"][lane][rep]["hebrew"]
            lines.append(f'| Hebrew | {rep} | {lane} | {h["evaluationEvents"]} | {h["evaluableOperators"]}/{h["frozenOperators"]} | {h["operatorBalancedSelectionGainBits"]:+.5f} | {h["operatorBalancedGainOverGlobalBits"]:+.5f} | {h["positiveOperatorFraction"]:.3f} | {h["residualReassignmentP"]:.5f} | {h["counterfactualActualPreference"]:.3f} | {h["pass"]} |')
    lines += ["","## Cross-system anonymous state-selection profiles","","No Hebrew operator is paired with any glyph. Correlation is over anonymous state-level selection gain only.","","| Hebrew representation | lane | shared states | Pearson r | permutation p | pass |","|---|---|---:|---:|---:|---|"]
    for rep in REPRESENTATIONS:
        for lane in ("holdout","control"):
            c=result["lanes"][lane][rep]["cross"]
            lines.append(f'| {rep} | {lane} | {c["sharedStates"]} | {c["pearsonR"]:+.5f} | {c["permutationP"]:.5f} | {c["pass"]} |')
lines += ["",f'Result SHA-256: `{result["resultSha256"]}`']
(out / "summary.md").write_text("\n".join(lines)+"\n", encoding="utf-8")
print("\n".join(lines))
