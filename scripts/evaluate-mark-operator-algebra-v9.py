#!/usr/bin/env python3
import json
import os
from collections import Counter, defaultdict
from pathlib import Path

from mark_operator_algebra_v9_core import (
    build_graph, build_probability_functions, canonical_sha, iter_compositions,
    map_state, safe_log2_probability,
)

protocol_path = Path(os.environ.get("MARK_V9_PROTOCOL", "research/mark/discovery-experiments/operator-composition-algebra-v9.protocol.json"))
freeze_path = Path(os.environ.get("MARK_V9_FREEZE_FILE", "artifacts/mark-operator-composition-algebra-v9-freeze/operator-algebra-freeze.json"))
holdout_path = Path(os.environ.get("MARK_V9_HOLDOUT", "artifact-staging/v9-split/holdout.jsonl"))
control_path = Path(os.environ.get("MARK_V9_CONTROL", "artifact-staging/v9-split/control.jsonl"))
out_dir = Path(os.environ.get("MARK_V9_OUT", "artifacts/mark-operator-composition-algebra-v9"))


def load_json(path): return json.loads(Path(path).read_text(encoding="utf-8"))

def verify_freeze(packet):
    claimed = packet.get("operatorAlgebraFreezeSha256")
    core = {k:v for k,v in packet.items() if k != "operatorAlgebraFreezeSha256"}
    actual = canonical_sha(core)
    if actual != claimed:
        raise RuntimeError("operator algebra freeze hash mismatch")
    return actual


def evaluate_lane(path, lane, protocol, freeze):
    cfg = protocol["primitiveGraph"]
    results = {}
    raw_observations = 0
    for variant, model in freeze["variants"].items():
        probs = build_probability_functions(model)
        states = set(model["states"]); common = states - {"OTHER"}
        eligible = {row["operatorId"] for row in model["operators"]}
        totals = Counter(); by_source = defaultdict(Counter)
        raw_paths = 0; covered = 0; sources = set()
        # Law evidence aggregators exist only for the primary variant.
        laws = model.get("candidateLaws")
        idem_rows = defaultdict(lambda: Counter())
        cancel_rows = defaultdict(lambda: Counter())
        order_rows = defaultdict(lambda: Counter())
        cond_rows = defaultdict(lambda: Counter())

        with path.open("r", encoding="utf-8") as handle:
            for raw in handle:
                row = json.loads(raw)
                if row.get("lane") != lane:
                    raise RuntimeError(f"{lane} evaluator received {row.get('lane')}")
                if variant == protocol["primitiveGraph"]["primaryVariant"]:
                    raw_observations += 1
                graph = build_graph(row, cfg, variant)
                source = row["sourceGroupId"]
                for seq in iter_compositions(graph, cfg):
                    raw_paths += 1
                    A,B = seq["operatorA"], seq["operatorB"]
                    if A not in eligible or B not in eligible:
                        continue
                    covered += 1; sources.add(source)
                    i = map_state(seq["state0"], common); o = map_state(seq["state2"], common)
                    q = {
                        "inputOnly": probs["p2"](i,o),
                        "firstOperatorOnly": probs["pa2"](A,i,o),
                        "secondOperatorOnly": probs["pb2"](B,i,o),
                        "composition": probs["pcomp"](A,B,i,o),
                        "directPair": probs["ppair"](A,B,i,o),
                    }
                    for name, value in q.items():
                        bits = safe_log2_probability(value)
                        totals[name] += bits; by_source[source][name] += bits
                    by_source[source]["paths"] += 1
                    if laws:
                        pair = (A,B)
                        for idx, cand in enumerate(laws["idempotence"]):
                            if pair == (cand["operatorA"], cand["operatorB"]):
                                idem_rows[idx]["n"] += 1
                                idem_rows[idx]["bitsAA"] += safe_log2_probability(probs["pcomp"](A,B,i,o))
                                idem_rows[idx]["bitsA"] += safe_log2_probability(probs["pop"](A,i,o))
                        for idx, cand in enumerate(laws["cancellation"]):
                            if pair == (cand["operatorA"], cand["operatorB"]):
                                cancel_rows[idx]["n"] += 1
                                cancel_rows[idx]["return"] += int(i == o)
                                cancel_rows[idx]["baseReturnExpected"] += probs["p2"](i,i)
                        for idx, cand in enumerate(laws["orderSensitivity"]):
                            A0,B0 = cand["operatorA"], cand["operatorB"]
                            if pair == (A0,B0):
                                order_rows[idx]["nAB"] += 1
                                order_rows[idx]["ownAB"] += safe_log2_probability(probs["pcomp"](A0,B0,i,o))
                                order_rows[idx]["swapAB"] += safe_log2_probability(probs["pcomp"](B0,A0,i,o))
                            elif pair == (B0,A0):
                                order_rows[idx]["nBA"] += 1
                                order_rows[idx]["ownBA"] += safe_log2_probability(probs["pcomp"](B0,A0,i,o))
                                order_rows[idx]["swapBA"] += safe_log2_probability(probs["pcomp"](A0,B0,i,o))
                        for idx, cand in enumerate(laws["conditionalComposition"]):
                            if pair != (cand["operatorA"], cand["operatorB"]): continue
                            frozen = {m["inputState"]: m["dominantOutputState"] for m in cand["frozenInputOutcomes"]}
                            if i in frozen:
                                cond_rows[(idx,i)]["n"] += 1
                                cond_rows[(idx,i)]["correct"] += int(o == frozen[i])

        if covered:
            avg = {name: totals[name] / covered for name in totals}
        else:
            avg = {name: None for name in ("inputOnly","firstOperatorOnly","secondOperatorOnly","composition","directPair")}
        source_rows = []
        for source, rec in sorted(by_source.items()):
            n = rec["paths"]
            source_rows.append({
                "sourceGroupId": source,
                "paths": n,
                **{f"{name}BitsPerPath": rec[name]/n for name in ("inputOnly","firstOperatorOnly","secondOperatorOnly","composition","directPair")}
            })
        source_comp_beats_input = sum(r["compositionBitsPerPath"] < r["inputOnlyBitsPerPath"] for r in source_rows) / max(1,len(source_rows))
        result = {
            "variant": variant,
            "observations": raw_observations if variant == protocol["primitiveGraph"]["primaryVariant"] else None,
            "rawCompositionPaths": raw_paths,
            "coveredCompositionPaths": covered,
            "coveredPathFraction": covered / max(1,raw_paths),
            "coveredDistinctSources": len(sources),
            "bitsPerPath": avg,
            "gainsBitsPerPath": {
                "compositionOverInputOnly": None if not covered else avg["inputOnly"] - avg["composition"],
                "compositionOverFirstOperatorOnly": None if not covered else avg["firstOperatorOnly"] - avg["composition"],
                "compositionOverSecondOperatorOnly": None if not covered else avg["secondOperatorOnly"] - avg["composition"],
                "directPairAdvantageOverComposition": None if not covered else avg["composition"] - avg["directPair"],
            },
            "sourceFractionCompositionBeatsInputOnly": source_comp_beats_input,
            "sourceScores": source_rows,
        }
        if laws:
            law_cfg = protocol["lawDiscovery"]
            idem = []
            for idx,cand in enumerate(laws["idempotence"]):
                rec=idem_rows[idx]; n=rec["n"]
                delta = None if not n else abs(rec["bitsAA"]-rec["bitsA"])/n
                idem.append({**cand,"evaluationOccurrences":n,"absoluteLogLossDifferenceBitsPerPath":delta,"transfers":bool(n and delta <= float(law_cfg["idempotence"]["transferMaximumAbsoluteLogLossDifferenceBitsPerPath"]))})
            cancel=[]
            for idx,cand in enumerate(laws["cancellation"]):
                rec=cancel_rows[idx];n=rec["n"]
                emp=None if not n else rec["return"]/n; base=None if not n else rec["baseReturnExpected"]/n
                gain=None if not n else emp-base
                cancel.append({**cand,"evaluationOccurrences":n,"empiricalIdentityReturn":emp,"inputOnlyExpectedIdentityReturn":base,"identityGainOverInputOnly":gain,"transfers":bool(n and gain >= float(law_cfg["cancellation"]["transferMinimumIdentityGainOverInputOnly"]))})
            order=[]
            for idx,cand in enumerate(laws["orderSensitivity"]):
                rec=order_rows[idx];nab=rec["nAB"];nba=rec["nBA"]
                adv_ab=None if not nab else (rec["swapAB"]-rec["ownAB"])/nab
                adv_ba=None if not nba else (rec["swapBA"]-rec["ownBA"])/nba
                threshold=float(law_cfg["orderSensitivity"]["transferMinimumOwnOrderLogLossAdvantageBitsPerPath"])
                order.append({**cand,"evaluationOccurrencesAB":nab,"evaluationOccurrencesBA":nba,"ownOrderAdvantageAB":adv_ab,"ownOrderAdvantageBA":adv_ba,"transfers":bool(nab and nba and adv_ab>=threshold and adv_ba>=threshold)})
            cond=[]
            bycand=defaultdict(list)
            for (idx,i),rec in cond_rows.items():
                if rec["n"]:
                    bycand[idx].append({"inputState":i,"evaluationOccurrences":rec["n"],"accuracy":rec["correct"]/rec["n"]})
            threshold=float(law_cfg["conditionalComposition"]["transferMinimumAccuracyPerFrozenInputOutcome"])
            for idx,cand in enumerate(laws["conditionalComposition"]):
                evals=sorted(bycand[idx],key=lambda r:r["inputState"])
                successful=[r for r in evals if r["accuracy"]>=threshold]
                outputs={m["dominantOutputState"] for m in cand["frozenInputOutcomes"] if any(r["inputState"]==m["inputState"] and r["accuracy"]>=threshold for r in evals)}
                cond.append({**cand,"evaluationInputs":evals,"successfulFrozenInputs":len(successful),"transfers":len(successful)>=2 and len(outputs)>=2})
            result["lawEvaluation"]={
                "idempotence":idem,
                "cancellation":cancel,
                "orderSensitivity":order,
                "conditionalComposition":cond,
                "transferCounts":{
                    "idempotence":sum(r["transfers"] for r in idem),
                    "cancellation":sum(r["transfers"] for r in cancel),
                    "orderSensitivity":sum(r["transfers"] for r in order),
                    "conditionalComposition":sum(r["transfers"] for r in cond),
                }
            }
        results[variant]=result
    return {"lane":lane,"variants":results,"observations":raw_observations}

protocol = load_json(protocol_path)
freeze = load_json(freeze_path)
freeze_sha = verify_freeze(freeze)
if freeze["protocolSha256"] != canonical_sha(protocol):
    raise RuntimeError("protocol changed after model freeze")
if freeze.get("holdoutOpenedDuringInduction") is not False or freeze.get("roleLabelsOpened") is not False:
    raise RuntimeError("invalid custody flags in freeze")

holdout = evaluate_lane(holdout_path, "holdout", protocol, freeze)
control = evaluate_lane(control_path, "control", protocol, freeze)
primary = protocol["primitiveGraph"]["primaryVariant"]
gate = protocol["predictiveTransferGate"]
hr = holdout["variants"][primary]
g = hr["gainsBitsPerPath"]
coverage_ok = hr["coveredPathFraction"] >= float(gate["minimumCoveredPathFraction"]) and hr["coveredDistinctSources"] >= int(gate["minimumCoveredDistinctSources"])
input_ok = g["compositionOverInputOnly"] is not None and g["compositionOverInputOnly"] >= float(gate["minimumGainOverInputOnlyBitsPerPath"]) and hr["sourceFractionCompositionBeatsInputOnly"] >= float(gate["minimumSourceFractionCompositionBeatsInputOnly"])
one_sided_ok = g["compositionOverFirstOperatorOnly"] is not None and g["compositionOverFirstOperatorOnly"] >= float(gate["minimumGainOverEachOneSidedBaselineBitsPerPath"]) and g["compositionOverSecondOperatorOnly"] >= float(gate["minimumGainOverEachOneSidedBaselineBitsPerPath"])
direct_ok = g["directPairAdvantageOverComposition"] is not None and g["directPairAdvantageOverComposition"] <= float(gate["maximumDirectPairAdvantageOverCompositionBitsPerPath"])
operator_signal = input_ok
if coverage_ok and input_ok and one_sided_ok and direct_ok:
    adjudication = "first_order_operator_algebra_transfers"
elif coverage_ok and operator_signal and (not one_sided_ok or not direct_ok):
    adjudication = "contextual_or_higher_order_operator_state_required"
elif coverage_ok and operator_signal:
    adjudication = "operator_consequence_without_first_order_composition"
else:
    adjudication = "no_transferable_operator_consequence_under_v9"

def variant_gate(result):
    gains=result["gainsBitsPerPath"]
    return bool(
        result["coveredPathFraction"] >= float(gate["minimumCoveredPathFraction"])
        and result["coveredDistinctSources"] >= int(gate["minimumCoveredDistinctSources"])
        and gains["compositionOverInputOnly"] is not None
        and gains["compositionOverInputOnly"] >= float(gate["minimumGainOverInputOnlyBitsPerPath"])
        and gains["compositionOverFirstOperatorOnly"] >= float(gate["minimumGainOverEachOneSidedBaselineBitsPerPath"])
        and gains["compositionOverSecondOperatorOnly"] >= float(gate["minimumGainOverEachOneSidedBaselineBitsPerPath"])
        and gains["directPairAdvantageOverComposition"] <= float(gate["maximumDirectPairAdvantageOverCompositionBitsPerPath"])
        and result["sourceFractionCompositionBeatsInputOnly"] >= float(gate["minimumSourceFractionCompositionBeatsInputOnly"])
    )

core={
    "schema":"mark_operator_composition_algebra_result_v9",
    "experimentId":protocol["experimentId"],
    "protocolSha256":canonical_sha(protocol),
    "operatorAlgebraFreezeSha256":freeze_sha,
    "parentV5RunId":freeze["parentV5RunId"],
    "laneResults":{"holdout":holdout,"control":control},
    "adjudication":{
        "primary":adjudication,
        "coverageGate":coverage_ok,
        "inputOnlyGate":input_ok,
        "oneSidedGate":one_sided_ok,
        "directPairSufficiencyGate":direct_ok,
        "lengthAwareFullGate":variant_gate(holdout["variants"]["lengthAware"]),
        "topologyFullGate":variant_gate(holdout["variants"]["topology"]),
        "semanticClaimLimit":"operational structure only; no lexical translation or historical semantic assignment"
    },
    "contract":{
        "roleLabelsConsumed":False,
        "sourcePixelsConsumed":False,
        "topologyReprojected":False,
        "v7ArtifactConsumed":False,
        "v8ArtifactConsumed":False,
        "modelRefitAfterHoldout":False,
        "holdoutReselection":False,
    }
}
result_sha=canonical_sha(core);packet={**core,"operatorCompositionAlgebraSha256":result_sha}
out_dir.mkdir(parents=True,exist_ok=True)
(out_dir/"operator-composition-algebra.json").write_text(json.dumps(packet,indent=2)+"\n",encoding="utf-8")
summary=[f"operator_composition_algebra_sha256={result_sha}",f"operator_algebra_freeze_sha256={freeze_sha}",f"adjudication={adjudication}"]
for lane_name,lane_result in (("holdout",holdout),("control",control)):
    for variant,result in lane_result["variants"].items():
        gains=result["gainsBitsPerPath"]
        summary.append(f"lane={lane_name};variant={variant};coverage={result['coveredPathFraction']:.6f};sources={result['coveredDistinctSources']};input_bits={result['bitsPerPath']['inputOnly']:.6f};A_bits={result['bitsPerPath']['firstOperatorOnly']:.6f};B_bits={result['bitsPerPath']['secondOperatorOnly']:.6f};composition_bits={result['bitsPerPath']['composition']:.6f};direct_bits={result['bitsPerPath']['directPair']:.6f};gain_input={gains['compositionOverInputOnly']:.6f};gain_A={gains['compositionOverFirstOperatorOnly']:.6f};gain_B={gains['compositionOverSecondOperatorOnly']:.6f};direct_advantage={gains['directPairAdvantageOverComposition']:.6f};source_win_fraction={result['sourceFractionCompositionBeatsInputOnly']:.6f}")
        if "lawEvaluation" in result:
            summary.append("law_transfers="+";".join(f"{k}:{v}" for k,v in result["lawEvaluation"]["transferCounts"].items()))
(out_dir/"summary.txt").write_text("\n".join(summary)+"\n",encoding="utf-8")
md=["### Mark operator composition algebra v9 — frozen result","",f"- Adjudication: **{adjudication}**",f"- Frozen train model: `{freeze_sha}`","","| Lane | Variant | Coverage | Sources | Input-only bits/path | A-only | B-only | A∘B | Direct A,B | Gain vs input | Gain vs A | Gain vs B | Direct advantage |","| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
for lane_name,lane_result in (("holdout",holdout),("control",control)):
    for variant,result in lane_result["variants"].items():
        b=result["bitsPerPath"];g=result["gainsBitsPerPath"]
        md.append(f"| {lane_name} | {variant} | {result['coveredPathFraction']:.3f} | {result['coveredDistinctSources']} | {b['inputOnly']:.4f} | {b['firstOperatorOnly']:.4f} | {b['secondOperatorOnly']:.4f} | {b['composition']:.4f} | {b['directPair']:.4f} | {g['compositionOverInputOnly']:.4f} | {g['compositionOverFirstOperatorOnly']:.4f} | {g['compositionOverSecondOperatorOnly']:.4f} | {g['directPairAdvantageOverComposition']:.4f} |")
if "lawEvaluation" in holdout["variants"][primary]:
    tc=holdout["variants"][primary]["lawEvaluation"]["transferCounts"]
    md += ["","Frozen Cleveland law candidates that transfer in Bavaria: "+", ".join(f"**{k} {v}**" for k,v in tc.items())+"."]
md += ["","This result tests anonymous structural consequences. It does not assign lexical meanings to operators or states."]
(out_dir/"summary.md").write_text("\n".join(md)+"\n",encoding="utf-8")
print("\n".join(summary))
