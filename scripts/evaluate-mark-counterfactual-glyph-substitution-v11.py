#!/usr/bin/env python3
import hashlib
import json
import math
import os
import statistics
from collections import Counter, defaultdict
from pathlib import Path

from mark_glyph_transition_v10_core import (
    canonical_sha,
    map_state,
    probability_functions,
    read_jsonl,
    sequence_stream,
    thaw_variant,
    is_operator,
)

PROTO = Path(os.environ.get("MARK_V11_PROTOCOL", "research/mark/discovery-experiments/counterfactual-glyph-substitution-v11.protocol.json"))
V10_FREEZE = Path(os.environ.get("MARK_V11_V10_FREEZE", "artifact-staging/v11-parent/freeze/glyph-transition-code-freeze.json"))
V10_EVAL = Path(os.environ.get("MARK_V11_V10_EVAL", "artifact-staging/v11-parent/evaluation"))
OUT = Path(os.environ.get("MARK_V11_OUT", "artifacts/mark-counterfactual-glyph-substitution-v11"))


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def canonical_freeze_sha(packet):
    core = dict(packet)
    claimed = core.pop("freezeSha256", None)
    return claimed, canonical_sha(core)


def input_counts(operator):
    totals = Counter()
    for (glyph, incoming, _outgoing), count in operator.items():
        totals[(glyph, incoming)] += count
    return totals


def kernel_tv(g, h, incoming, states, pop):
    return 0.5 * sum(abs(pop(g, incoming, out) - pop(h, incoming, out)) for out in states)


def choose_panel(model_variant, protocol):
    states = list(model_variant["states"])
    base, operator, _class_tab, _class_totals = thaw_variant(model_variant)
    _p0, pop = probability_functions(states, base, operator, {
        "globalAdditiveAlpha": 0.5,
        "operatorBackoffPseudoCount": 12.0,
    })
    support = input_counts(operator)
    min_support = int(protocol["counterfactualPanel"]["minimumTrainOccurrencesPerGlyphIncomingState"])
    min_tv = float(protocol["counterfactualPanel"]["minimumFrozenKernelTotalVariation"])
    eligible = set(model_variant["eligibleGlyphs"])
    by_state = defaultdict(list)
    for (glyph, incoming), count in support.items():
        if glyph in eligible and count >= min_support:
            by_state[incoming].append(glyph)

    mapping = {}
    rows = []
    variant = model_variant["variant"]
    for incoming in sorted(by_state):
        glyphs = sorted(set(by_state[incoming]))
        if len(glyphs) < 2:
            continue
        for glyph in glyphs:
            n_g = support[(glyph, incoming)]
            candidates = []
            for substitute in glyphs:
                if substitute == glyph:
                    continue
                n_h = support[(substitute, incoming)]
                tv = kernel_tv(glyph, substitute, incoming, states, pop)
                if tv + 1e-15 < min_tv:
                    continue
                mismatch = abs(math.log2((n_h + 1.0) / (n_g + 1.0)))
                tie = hashlib.sha256(f"{variant}|{incoming}|{glyph}|{substitute}".encode("utf-8")).hexdigest()
                candidates.append((mismatch, tie, substitute, n_h, tv))
            if not candidates:
                continue
            candidates.sort()
            mismatch, tie, substitute, n_h, tv = candidates[0]
            mapping[(glyph, incoming)] = substitute
            rows.append({
                "variant": variant,
                "inputState": incoming,
                "actualGlyph": glyph,
                "substituteGlyph": substitute,
                "actualTrainSupport": int(n_g),
                "substituteTrainSupport": int(n_h),
                "absoluteLog2SupportRatio": mismatch,
                "frozenKernelTv": tv,
                "selectionTieSha256": tie,
            })
    return mapping, rows, pop


def signflip_p(values, lane, variant, protocol):
    if not values:
        return None
    observed = statistics.mean(values.values())
    iterations = int(protocol["null"]["iterations"])
    salt = protocol["null"]["seedSalt"]
    null_at_least = 0
    ordered = sorted(values.items())
    for iteration in range(iterations):
        total = 0.0
        for doc, value in ordered:
            digest = hashlib.sha256(f"{salt}|{variant}|{lane}|{iteration}|{doc}".encode("utf-8")).digest()
            sign = 1.0 if (digest[0] & 1) == 0 else -1.0
            total += sign * value
        null_mean = total / len(ordered)
        if null_mean >= observed - 1e-15:
            null_at_least += 1
    return (null_at_least + 1.0) / (iterations + 1.0)


def evaluate(rows, lane, model_variant, protocol):
    variant = model_variant["variant"]
    common_states = set(model_variant["commonStates"])
    mapping, panel_rows, pop = choose_panel(model_variant, protocol)
    per_doc = defaultdict(lambda: [0.0, 0])
    total_sequence_operators = 0
    eligible_events = 0
    event_sum = 0.0
    event_wins = 0

    for row in rows:
        doc = row["anonymousInscriptionId"]
        stream = sequence_stream(row["words"], variant)
        for pos in range(1, len(stream) - 1):
            glyph = stream[pos]
            if not is_operator(glyph):
                continue
            total_sequence_operators += 1
            incoming = map_state(stream[pos - 1], common_states)
            substitute = mapping.get((glyph, incoming))
            if substitute is None:
                continue
            outgoing = map_state(stream[pos + 1], common_states)
            q_actual = max(pop(glyph, incoming, outgoing), 1e-300)
            q_sub = max(pop(substitute, incoming, outgoing), 1e-300)
            advantage = math.log2(q_actual) - math.log2(q_sub)
            eligible_events += 1
            event_sum += advantage
            event_wins += int(advantage > 0)
            per_doc[doc][0] += advantage
            per_doc[doc][1] += 1

    doc_means = {doc: total / n for doc, (total, n) in per_doc.items() if n > 0}
    values = list(doc_means.values())
    result = {
        "lane": lane,
        "variant": variant,
        "panelMappings": len(panel_rows),
        "panelSha256": canonical_sha(panel_rows),
        "totalSequenceOperatorEvents": total_sequence_operators,
        "eligibleEvents": eligible_events,
        "eligibleEventFraction": eligible_events / max(1, total_sequence_operators),
        "eligibleInscriptions": len(values),
        "meanInscriptionAdvantageBits": statistics.mean(values) if values else None,
        "medianInscriptionAdvantageBits": statistics.median(values) if values else None,
        "positiveInscriptionFraction": sum(v > 0 for v in values) / max(1, len(values)),
        "eventWeightedMeanAdvantageBits": event_sum / max(1, eligible_events),
        "eventActualKernelWinFraction": event_wins / max(1, eligible_events),
        "signFlipP": signflip_p(doc_means, lane, variant, protocol),
    }
    return result, panel_rows


def primary_gate(results, protocol):
    g = protocol["gates"]
    holdout = results["holdout"]
    control = results["control"]
    support = (
        holdout["eligibleInscriptions"] >= int(g["minimumEligibleHoldoutInscriptions"])
        and control["eligibleInscriptions"] >= int(g["minimumEligibleControlInscriptions"])
        and holdout["eligibleEvents"] >= int(g["minimumEligibleHoldoutEvents"])
        and control["eligibleEvents"] >= int(g["minimumEligibleControlEvents"])
    )
    if not support:
        return "INFEASIBLE", support
    passed = (
        holdout["meanInscriptionAdvantageBits"] > float(g["holdoutMeanInscriptionAdvantageMinimumBits"])
        and control["meanInscriptionAdvantageBits"] > float(g["controlMeanInscriptionAdvantageMinimumBits"])
        and holdout["positiveInscriptionFraction"] >= float(g["holdoutPositiveInscriptionFractionMinimum"])
        and control["positiveInscriptionFraction"] >= float(g["controlPositiveInscriptionFractionMinimum"])
        and holdout["signFlipP"] <= float(g["holdoutSignFlipPMaximum"])
        and control["signFlipP"] <= float(g["controlSignFlipPMaximum"])
    )
    return ("GLYPH_SPECIFIC_COUNTERFACTUAL_CONSEQUENCE_TRANSFERS" if passed else "COUNTERFACTUAL_CONSEQUENCE_NOT_DISTINGUISHED"), support


def main():
    protocol = load_json(PROTO)
    if protocol.get("schema") != "mark_counterfactual_glyph_substitution_protocol_v11":
        raise RuntimeError("unexpected V11 protocol schema")
    freeze = load_json(V10_FREEZE)
    parent = protocol["parentV10"]
    if freeze.get("schema") != "mark_glyph_transition_code_freeze_v10":
        raise RuntimeError("unexpected parent V10 freeze schema")
    if freeze.get("protocolSha256") != parent["expectedProtocolSha256"]:
        raise RuntimeError("parent V10 protocol hash drift")
    claimed, computed = canonical_freeze_sha(freeze)
    if claimed != computed or claimed != parent["expectedFreezeSha256"]:
        raise RuntimeError("parent V10 freeze hash drift")
    if freeze.get("semanticFieldsConsumed") is not False or freeze.get("provenanceConsumed") is not False:
        raise RuntimeError("parent V10 freeze custody violation")

    lane_rows = {
        "holdout": read_jsonl(V10_EVAL / "holdout.jsonl", expected_lane="holdout"),
        "control": read_jsonl(V10_EVAL / "control.jsonl", expected_lane="control"),
    }
    variants = [protocol["representation"]["primaryVariant"], protocol["representation"]["replicationVariant"]]
    all_results = {}
    panels = {}
    for variant in variants:
        model_variant = freeze["variants"][variant]
        all_results[variant] = {}
        panel_ref = None
        for lane in ("holdout", "control"):
            result, panel = evaluate(lane_rows[lane], lane, model_variant, protocol)
            all_results[variant][lane] = result
            if panel_ref is None:
                panel_ref = panel
            elif canonical_sha(panel_ref) != canonical_sha(panel):
                raise RuntimeError("counterfactual panel changed across lanes")
        panels[variant] = panel_ref

    primary = protocol["representation"]["primaryVariant"]
    adjudication, support = primary_gate(all_results[primary], protocol)
    core = {
        "schema": "mark_counterfactual_glyph_substitution_result_v11",
        "experimentId": protocol["experimentId"],
        "protocolSha256": canonical_sha(protocol),
        "parentV10FreezeSha256": freeze["freezeSha256"],
        "parentV10ResultSha256": protocol["designContext"]["parentV10ResultSha256"],
        "freshIndependentHoldout": False,
        "adjudication": adjudication,
        "primarySupportSufficient": support,
        "results": all_results,
        "panelSha256": {variant: canonical_sha(panels[variant]) for variant in panels},
    }
    result_sha = canonical_sha(core)
    packet = {**core, "resultSha256": result_sha}

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "result.json").write_text(json.dumps(packet, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    for variant, panel in panels.items():
        (OUT / f"{variant}-counterfactual-panel.json").write_text(json.dumps(panel, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    lines = [
        "# Mark counterfactual glyph substitution v11",
        "",
        f"Adjudication: **{adjudication}**",
        "",
    ]
    for variant in variants:
        lines.append(f"## {variant}")
        lines.append("")
        for lane in ("holdout", "control"):
            r = all_results[variant][lane]
            lines.append(
                f"- {lane}: inscriptions={r['eligibleInscriptions']}; events={r['eligibleEvents']}; "
                f"coverage={r['eligibleEventFraction']:.3f}; mean inscription advantage={r['meanInscriptionAdvantageBits']:+.6f} bits; "
                f"median={r['medianInscriptionAdvantageBits']:+.6f}; positive fraction={r['positiveInscriptionFraction']:.3f}; "
                f"sign-flip p={r['signFlipP']:.6f}; event-weighted advantage={r['eventWeightedMeanAdvantageBits']:+.6f}; "
                f"event actual-kernel win fraction={r['eventActualKernelWinFraction']:.3f}"
            )
        lines.append("")
    lines.extend([
        "The incoming anonymous state is held fixed. Each actual glyph is compared with a different, train-matched glyph that was supported in the same incoming state and whose frozen V10 consequence kernel differed by at least the preregistered total-variation threshold. Substitute selection used V10 train counts/kernels only.",
        "",
        "This is a post-V10 mechanistic counterfactual prediction test on reused evaluation inscriptions, not a physical causal intervention or fresh independent holdout confirmation.",
        "",
        f"Result SHA-256: `{result_sha}`",
        "",
    ])
    (OUT / "summary.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
