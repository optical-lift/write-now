#!/usr/bin/env python3
import json
import os
from collections import Counter
from pathlib import Path

from mark_glyph_transition_v10_core import (
    canonical_sha,
    is_operator,
    read_jsonl,
    score_events,
    sequence_stream,
    thaw_variant,
)

PROTOCOL_PATH = Path(os.environ.get(
    "MARK_V10_PROTOCOL",
    "research/mark/discovery-experiments/glyph-transition-code-v10.protocol.json",
))
FREEZE_PATH = Path(os.environ.get(
    "MARK_V10_FREEZE_FILE",
    "artifacts/mark-glyph-transition-code-v10-freeze/glyph-transition-code-freeze.json",
))
HOLDOUT_PATH = Path(os.environ.get("MARK_V10_HOLDOUT", "artifact-staging/v10-sealed/holdout.jsonl"))
CONTROL_PATH = Path(os.environ.get("MARK_V10_CONTROL", "artifact-staging/v10-sealed/control.jsonl"))
MANIFEST_PATH = Path(os.environ.get("MARK_V10_MANIFEST", "artifact-staging/v10-sealed/split-manifest.json"))
OUT_DIR = Path(os.environ.get("MARK_V10_OUT", "artifacts/mark-glyph-transition-code-v10"))


def eval_eligible_glyphs(rows, variant, frozen_glyphs, minimum):
    counts = Counter()
    frozen = set(frozen_glyphs)
    for row in rows:
        for token in sequence_stream(row["words"], variant)[1:-1]:
            if is_operator(token) and token in frozen:
                counts[token] += 1
    return {glyph for glyph, count in counts.items() if count >= minimum}, counts


def gates(metrics, protocol, include_class=True):
    cfg = protocol["primaryGates"]
    checks = {
        "coverage": metrics["coveredFraction"] >= float(cfg["minimumEvaluationCoveredFraction"]),
        "inscriptions": metrics["distinctCoveredInscriptions"] >= int(cfg["minimumEvaluationDistinctInscriptions"]),
        "operatorGain": (metrics["operatorGainBitsPerEvent"] or -999) >= float(cfg["minimumOperatorGainBitsPerEvent"]),
        "inscriptionWins": (metrics["inscriptionFractionOperatorBeatsBaseline"] or 0) >= float(cfg["minimumInscriptionFractionOperatorBeatsBaseline"]),
    }
    if include_class:
        checks["classGain"] = (metrics["classGainBitsPerEvent"] or -999) >= float(cfg["minimumClassGainBitsPerEvent"])
        checks["classRetention"] = (metrics["classRetentionOfOperatorGain"] or 0) >= float(cfg["minimumClassRetentionOfOperatorGain"])
    return checks, all(checks.values())


def evaluate_lane(rows, lane, variant_model, variant, protocol):
    frozen_glyphs = variant_model["eligibleGlyphs"]
    eval_glyphs, raw_counts = eval_eligible_glyphs(
        rows,
        variant,
        frozen_glyphs,
        int(protocol["eligibility"]["minimumEvaluationGlyphOccurrences"]),
    )
    membership = {
        glyph: class_id
        for glyph, class_id in variant_model["classMembership"].items()
        if glyph in eval_glyphs
    }
    base, operator, class_tab, class_totals = thaw_variant(variant_model)
    metrics = score_events(
        rows=rows,
        variant=variant,
        common_states=set(variant_model["commonStates"]),
        eligible_glyphs=eval_glyphs,
        states=variant_model["states"],
        base=base,
        operator=operator,
        membership=membership,
        class_tab=class_tab,
        class_totals=class_totals,
        model_cfg=protocol["model"],
    )
    metrics["lane"] = lane
    metrics["variant"] = variant
    metrics["evaluationEligibleGlyphCount"] = len(eval_glyphs)
    metrics["evaluationEligibleGlyphs"] = sorted(eval_glyphs)
    metrics["frozenGlyphRawEvaluationCounts"] = {
        glyph: raw_counts[glyph] for glyph in sorted(raw_counts)
    }
    op_checks, op_pass = gates(metrics, protocol, include_class=False)
    full_checks, full_pass = gates(metrics, protocol, include_class=True)
    metrics["operatorGateChecks"] = op_checks
    metrics["operatorGatePass"] = op_pass
    metrics["finiteClassGateChecks"] = full_checks
    metrics["finiteClassGatePass"] = full_pass
    return metrics


def main():
    protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    freeze = json.loads(FREEZE_PATH.read_text(encoding="utf-8"))
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))

    if protocol.get("schema") != "mark_glyph_transition_code_protocol_v10":
        raise RuntimeError("unexpected V10 protocol schema")
    if freeze.get("schema") != "mark_glyph_transition_code_freeze_v10":
        raise RuntimeError("unexpected V10 freeze schema")
    if freeze.get("protocolSha256") != canonical_sha(protocol):
        raise RuntimeError("freeze/protocol SHA mismatch")
    freeze_core = {k: v for k, v in freeze.items() if k != "freezeSha256"}
    if canonical_sha(freeze_core) != freeze.get("freezeSha256"):
        raise RuntimeError("immutable V10 freeze SHA does not verify")
    if manifest.get("sourceGitBlobSha1") != freeze.get("sourceGitBlobSha1"):
        raise RuntimeError("sealed evaluation source differs from frozen train source")
    if manifest.get("laneFileSha256", {}).get("holdout") is None or manifest.get("laneFileSha256", {}).get("control") is None:
        raise RuntimeError("evaluation packet missing sealed lane hashes")
    if any(freeze.get(field) is not False for field in (
        "semanticFieldsConsumed", "transliterationsConsumed", "translationsConsumed", "provenanceConsumed"
    )):
        raise RuntimeError("freeze reports forbidden information consumption")

    holdout_rows = read_jsonl(HOLDOUT_PATH, expected_lane="holdout")
    control_rows = read_jsonl(CONTROL_PATH, expected_lane="control")
    lane_rows = {"holdout": holdout_rows, "control": control_rows}

    results = {}
    for variant, variant_model in freeze["variants"].items():
        results[variant] = {}
        for lane, rows in lane_rows.items():
            result = evaluate_lane(rows, lane, variant_model, variant, protocol)
            results[variant][lane] = result
            print(
                f"[{variant}/{lane}] covered={result['coveredEvents']}/{result['allEvents']} "
                f"opGain={result['operatorGainBitsPerEvent']} "
                f"classGain={result['classGainBitsPerEvent']} "
                f"classRetention={result['classRetentionOfOperatorGain']}",
                flush=True,
            )

    primary = protocol["sequence"]["primaryVariant"]
    primary_holdout = results[primary]["holdout"]
    primary_control = results[primary]["control"]
    both_operator = primary_holdout["operatorGatePass"] and primary_control["operatorGatePass"]
    both_finite = primary_holdout["finiteClassGatePass"] and primary_control["finiteClassGatePass"]

    if both_finite:
        adjudication = "finiteOperationalCodeTransfers"
    elif both_operator:
        adjudication = "operatorCodeWithoutFiniteQuotient"
    elif primary_holdout["operatorGatePass"] or primary_control["operatorGatePass"]:
        adjudication = "sequenceIdentityWithoutTransfer"
    else:
        adjudication = "noResidualGlyphCodeUnderV10"

    ablation = protocol["sequence"]["ablationVariant"]
    ablation_both_operator = (
        results[ablation]["holdout"]["operatorGatePass"]
        and results[ablation]["control"]["operatorGatePass"]
    )
    boundary_dependence = both_operator and not ablation_both_operator

    core = {
        "schema": "mark_glyph_transition_code_result_v10",
        "experimentId": protocol["experimentId"],
        "protocolSha256": canonical_sha(protocol),
        "freezeSha256": freeze["freezeSha256"],
        "adjudication": adjudication,
        "boundaryDependence": boundary_dependence,
        "results": results,
        "functionalClasses": {
            variant: {
                "selectedClassCount": freeze["variants"][variant]["classSelection"]["selectedClassCount"],
                "classes": freeze["variants"][variant]["classes"],
            }
            for variant in freeze["variants"]
        },
        "semanticFieldsConsumed": False,
        "transliterationsConsumed": False,
        "translationsConsumed": False,
        "provenanceConsumed": False,
        "modelRefitAfterHoldout": False,
        "holdoutChangedClassMembership": False,
    }
    result_sha = canonical_sha(core)
    packet = {**core, "resultSha256": result_sha}
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "glyph-transition-code-result.json").write_text(
        json.dumps(packet, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    lines = [
        "# Mark glyph transition code v10",
        "",
        f"Adjudication: **{adjudication}**",
        f"Boundary dependence: **{str(boundary_dependence).lower()}**",
        "",
    ]
    for variant in (primary, ablation):
        lines.append(f"## {variant}")
        lines.append("")
        lines.append(
            f"Frozen functional classes: **{freeze['variants'][variant]['classSelection']['selectedClassCount']}** "
            f"across **{freeze['variants'][variant]['trainInventory']['eligibleGlyphCount']}** eligible train glyphs."
        )
        for lane in ("holdout", "control"):
            r = results[variant][lane]
            lines.append(
                f"- {lane}: coverage {r['coveredEvents']}/{r['allEvents']}={r['coveredFraction']:.3f}; "
                f"inscriptions={r['distinctCoveredInscriptions']}; baseline={r['baselineBitsPerEvent']:.4f} bits/event; "
                f"glyph={r['operatorBitsPerEvent']:.4f}; class={r['classBitsPerEvent']:.4f}; "
                f"glyph gain={r['operatorGainBitsPerEvent']:+.4f}; class gain={r['classGainBitsPerEvent']:+.4f}; "
                f"retention={r['classRetentionOfOperatorGain']:.3f}; inscription win fraction={r['inscriptionFractionOperatorBeatsBaseline']:.3f}; "
                f"operatorGate={r['operatorGatePass']}; finiteClassGate={r['finiteClassGatePass']}"
            )
        lines.append("")
    lines.extend([
        "The model was frozen from the train lane before holdout/control were opened. The blind packet contained raw `words` sequences, anonymous inscription IDs, and lane assignment only. No transliteration, translation, site, scribe, findspot, support, or proposed meaning was available to induction or evaluation.",
        "",
        f"Result SHA-256: `{result_sha}`",
    ])
    (OUT_DIR / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
