#!/usr/bin/env python3
import hashlib
import json
import os
import statistics
from collections import Counter, defaultdict, deque
from pathlib import Path

from mark_graph_compression_v8_core import (
    canonical_sha,
    sha256_file,
    build_primitive_graph,
    clone_graph,
    graph_bits,
    apply_grammar,
)

PROTO = Path(os.environ.get(
    "MARK_TYPED_RELATIONAL_PROTOCOL",
    "research/mark/discovery-experiments/typed-relational-intervention-v2.protocol.json",
))
V5 = Path(os.environ.get("MARK_TYPED_RELATIONAL_V5", "artifact-staging/typed-relational/v5"))
V8 = Path(os.environ.get("MARK_TYPED_RELATIONAL_V8", "artifact-staging/typed-relational/v8"))
OUT = Path(os.environ.get("MARK_TYPED_RELATIONAL_OUT", "artifacts/mark-typed-relational-intervention-v2"))


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def locate(root, name):
    hits = list(Path(root).rglob(name))
    if len(hits) != 1:
        raise RuntimeError(f"expected one {name} under {root}, found {len(hits)}")
    return hits[0]


def endpoint_pair(edge):
    return tuple(sorted((int(edge["u"]), int(edge["v"]))))


def component_count(graph):
    adjacency = defaultdict(set)
    for edge in graph["edges"]:
        u, v = int(edge["u"]), int(edge["v"])
        if u == v:
            raise RuntimeError("primitive intervention graph unexpectedly contains self-edge")
        adjacency[u].add(v)
        adjacency[v].add(u)
    seen = set()
    count = 0
    for node in graph["nodes"]:
        if node in seen:
            continue
        count += 1
        seen.add(node)
        q = deque([node])
        while q:
            cur = q.popleft()
            for nxt in adjacency.get(cur, ()):
                if nxt not in seen:
                    seen.add(nxt)
                    q.append(nxt)
    return count


def graph_degrees(graph):
    degree = Counter({int(node): 0 for node in graph["nodes"]})
    for edge in graph["edges"]:
        degree[int(edge["u"])] += 1
        degree[int(edge["v"])] += 1
    return dict(sorted(degree.items()))


def invariant_signature(graph):
    comps = component_count(graph)
    return {
        "nodeSymbols": tuple(sorted((int(k), int(v)) for k, v in graph["nodes"].items())),
        "nodeCount": len(graph["nodes"]),
        "edgeCount": len(graph["edges"]),
        "perNodeDegree": tuple(graph_degrees(graph).items()),
        "edgeLabels": tuple(sorted(edge["label"] for edge in graph["edges"])),
        "components": comps,
        "cycleRank": len(graph["edges"]) - len(graph["nodes"]) + comps,
        "rawBits": graph_bits(graph),
    }


def clone_and_rewire(base, pair_a, pair_b, new_a, new_b):
    graph = clone_graph(base)
    by_pair = {endpoint_pair(edge): i for i, edge in enumerate(graph["edges"])}
    ia, ib = by_pair[pair_a], by_pair[pair_b]
    for index, pair in ((ia, new_a), (ib, new_b)):
        graph["edges"][index]["u"] = int(pair[0])
        graph["edges"][index]["v"] = int(pair[1])
        graph["edges"][index]["pu"] = ""
        graph["edges"][index]["pv"] = ""
    return graph


def typed_pair(graph, pair):
    u, v = pair
    return tuple(sorted((int(graph["nodes"][u]), int(graph["nodes"][v]))))


def selected_typed_signature(graph, pairs, label):
    return tuple(sorted((label, typed_pair(graph, pair)) for pair in pairs))


def deterministic_edge_pool(graph, observation_id, cap):
    by_label = defaultdict(list)
    for edge in graph["edges"]:
        pair = endpoint_pair(edge)
        label = edge["label"]
        token = f"{observation_id}|{pair[0]}|{pair[1]}|{label}"
        by_label[label].append((hashlib.sha256(token.encode()).hexdigest(), pair))
    out = {}
    for label, rows in sorted(by_label.items()):
        out[label] = [pair for _, pair in sorted(rows)[:int(cap)]]
    return out


def valid_new_pairs(existing, pair_a, pair_b, new_a, new_b):
    if new_a == new_b:
        return False
    if new_a[0] == new_a[1] or new_b[0] == new_b[1]:
        return False
    forbidden = existing - {pair_a, pair_b}
    if new_a in forbidden or new_b in forbidden:
        return False
    return True


def find_intervention(base, observation_id, cap):
    """Choose the deterministic minimum-SHA valid matched typed intervention.

    Both candidate counterfactuals are degree-preserving two-edge rewires over the
    same two primitive edges. One must preserve the selected endpoint-symbol
    relation signature while changing exact node adjacency; the other must break
    that signature. Realization labels never move and both rewires must preserve
    connected-component count and all frozen low-order invariants.
    """
    original_sig = invariant_signature(base)
    existing = {endpoint_pair(edge) for edge in base["edges"]}
    pools = deterministic_edge_pool(base, observation_id, cap)
    specs = []

    for label, pairs in sorted(pools.items()):
        for i in range(len(pairs)):
            pair_a = pairs[i]
            for j in range(i + 1, len(pairs)):
                pair_b = pairs[j]
                if len(set(pair_a + pair_b)) != 4:
                    continue
                u, v = pair_a
                x, y = pair_b
                alternatives = [
                    (tuple(sorted((u, x))), tuple(sorted((v, y)))),
                    (tuple(sorted((u, y))), tuple(sorted((v, x)))),
                ]
                if not all(valid_new_pairs(existing, pair_a, pair_b, a, b) for a, b in alternatives):
                    continue

                original_typed = selected_typed_signature(base, (pair_a, pair_b), label)
                classified = []
                for alt_index, (new_a, new_b) in enumerate(alternatives):
                    sig = selected_typed_signature(base, (new_a, new_b), label)
                    classified.append((alt_index, new_a, new_b, sig == original_typed))

                preservers = [row for row in classified if row[3]]
                breakers = [row for row in classified if not row[3]]
                if len(preservers) != 1 or len(breakers) != 1:
                    continue

                _, identity_a, identity_b, _ = preservers[0]
                _, breaking_a, breaking_b, _ = breakers[0]
                key = hashlib.sha256(
                    f"{observation_id}|{label}|{pair_a}|{pair_b}|{identity_a}|{identity_b}|{breaking_a}|{breaking_b}".encode()
                ).hexdigest()
                specs.append((
                    key, label, pair_a, pair_b,
                    identity_a, identity_b, breaking_a, breaking_b,
                    original_typed,
                ))

    for (
        _, label, pair_a, pair_b,
        identity_a, identity_b, breaking_a, breaking_b,
        original_typed,
    ) in sorted(specs):
        identity = clone_and_rewire(base, pair_a, pair_b, identity_a, identity_b)
        breaking = clone_and_rewire(base, pair_a, pair_b, breaking_a, breaking_b)
        if component_count(identity) != original_sig["components"]:
            continue
        if component_count(breaking) != original_sig["components"]:
            continue

        identity_sig = invariant_signature(identity)
        breaking_sig = invariant_signature(breaking)
        if identity_sig != original_sig:
            raise RuntimeError(f"identity rewire invariant drift for {observation_id}")
        if breaking_sig != original_sig:
            raise RuntimeError(f"type-breaking rewire invariant drift for {observation_id}")

        if selected_typed_signature(base, (identity_a, identity_b), label) != original_typed:
            raise RuntimeError(f"typed-preserving classification drift for {observation_id}")
        if selected_typed_signature(base, (breaking_a, breaking_b), label) == original_typed:
            raise RuntimeError(f"typed-breaking classification drift for {observation_id}")

        return {
            "label": label,
            "pairA": pair_a,
            "pairB": pair_b,
            "identityNewA": identity_a,
            "identityNewB": identity_b,
            "breakingNewA": breaking_a,
            "breakingNewB": breaking_b,
            "originalTypedSignature": original_typed,
            "identity": identity,
            "breaking": breaking,
            "invariants": original_sig,
        }
    return None


def grammar_bits_for(graph, grammar):
    work = clone_graph(graph)
    return int(apply_grammar(work, grammar, track_members=False)["dataBits"])


def topology_counterfactuals_from_spec(row, spec):
    base = build_primitive_graph(row, "topology", track_members=False)
    identity = clone_and_rewire(
        base,
        tuple(spec["pairA"]), tuple(spec["pairB"]),
        tuple(spec["identityNewA"]), tuple(spec["identityNewB"]),
    )
    breaking = clone_and_rewire(
        base,
        tuple(spec["pairA"]), tuple(spec["pairB"]),
        tuple(spec["breakingNewA"]), tuple(spec["breakingNewB"]),
    )
    sig = invariant_signature(base)
    if invariant_signature(identity) != sig:
        raise RuntimeError(f"topology identity rewire invariant drift for {row['observationId']}")
    if invariant_signature(breaking) != sig:
        raise RuntimeError(f"topology type-breaking rewire invariant drift for {row['observationId']}")
    return base, identity, breaking


def signflip_p(values, iterations, salt):
    ids = [item[0] for item in values]
    nums = [item[1] for item in values]
    observed = statistics.mean(nums)
    nulls = []
    for iteration in range(int(iterations)):
        signed = []
        for oid, value in zip(ids, nums):
            h = hashlib.sha256(f"{salt}|{iteration}|{oid}".encode()).digest()
            sign = 1.0 if (h[0] & 1) else -1.0
            signed.append(sign * value)
        nulls.append(statistics.mean(signed))
    p = (1 + sum(x >= observed for x in nulls)) / (1 + len(nulls))
    return observed, p, {
        "iterations": len(nulls),
        "mean": statistics.mean(nulls),
        "min": min(nulls),
        "max": max(nulls),
        "nullAtLeastObserved": sum(x >= observed for x in nulls),
    }


def lane_summary(rows, null_cfg):
    values = [(r["observationId"], r["hierarchicalNormalizedTypedSelectivePenalty"]) for r in rows]
    observed, p, null = signflip_p(values, null_cfg["iterations"], null_cfg["seedSalt"])
    gaps = [r["hierarchicalTypedSelectivePenaltyBits"] for r in rows]
    return {
        "eligibleObservations": len(rows),
        "meanNormalizedTypedSelectivePenalty": observed,
        "medianTypedSelectivePenaltyBits": statistics.median(gaps),
        "meanTypedSelectivePenaltyBits": statistics.mean(gaps),
        "positiveFraction": sum(x > 0 for x in gaps) / len(gaps),
        "zeroFraction": sum(x == 0 for x in gaps) / len(gaps),
        "signFlipP": p,
        "null": null,
        "meanIdentityRewirePenaltyBits": statistics.mean(r["hierarchicalIdentityRewirePenaltyBits"] for r in rows),
        "meanTypeBreakingRewirePenaltyBits": statistics.mean(r["hierarchicalTypeBreakingRewirePenaltyBits"] for r in rows),
        "meanFlatTypedSelectivePenaltyBits": statistics.mean(r["flatTypedSelectivePenaltyBits"] for r in rows),
        "meanTopologyTypedSelectivePenaltyBits": statistics.mean(r["topologyTypedSelectivePenaltyBits"] for r in rows),
    }


protocol = load_json(PROTO)
if protocol.get("schema") != "mark_typed_relational_intervention_protocol_v2":
    raise RuntimeError("wrong typed relational intervention protocol")

manifest = load_json(locate(V5, "edge-pair-manifest.json"))
world = load_json(locate(V5, "critical-edge-world.json"))
projector = locate(V5, "critical-edge-observations.jsonl")
grammar_path = locate(V8, "hierarchical-graph-grammar-freeze.json")
grammar_packet = load_json(grammar_path)

if manifest.get("edgePairManifestSha256") != protocol["parentV5"]["expectedEdgePairManifestSha256"]:
    raise RuntimeError("V5 manifest parent drift")
if world.get("criticalEdgeWorldSha256") != protocol["parentV5"]["expectedCriticalEdgeWorldSha256"]:
    raise RuntimeError("V5 world parent drift")
if sha256_file(projector) != protocol["parentV5"]["expectedProjectorRowsSha256"]:
    raise RuntimeError("V5 projector rows drift")
freeze_sha = grammar_packet.get("grammarFreezeSha256")
if canonical_sha({k: v for k, v in grammar_packet.items() if k != "grammarFreezeSha256"}) != freeze_sha:
    raise RuntimeError("V8 grammar internal hash mismatch")
if freeze_sha != protocol["parentV8"]["expectedGrammarFreezeSha256"]:
    raise RuntimeError("wrong V8 grammar freeze")
if grammar_packet.get("roleLabelsOpenedDuringInduction") is not False:
    raise RuntimeError("V8 grammar label-custody contract violated")
if grammar_packet.get("parentProjectorRowsSha256") != protocol["parentV5"]["expectedProjectorRowsSha256"]:
    raise RuntimeError("V8/V5 projector lineage mismatch")

eligible = set(world["pairEligibleObservationIds"])
lanes = {protocol["population"]["primaryLane"], protocol["population"]["replicationLane"]}
primary_grammar = grammar_packet["models"]["lengthAware"]["hierarchical"]
flat_grammar = grammar_packet["models"]["lengthAware"]["flat"]
topology_grammar = grammar_packet["models"]["topology"]["hierarchical"]
cap = protocol["matchedIntervention"]["candidateEdgeLimitPerCompleteLabel"]

rows = []
seen = 0
with projector.open("r", encoding="utf-8") as handle:
    for raw in handle:
        if not raw.strip():
            continue
        row = json.loads(raw)
        if row["observationId"] not in eligible or row["lane"] not in lanes:
            continue
        seen += 1
        base = build_primitive_graph(row, "lengthAware", track_members=False)
        spec = find_intervention(base, row["observationId"], cap)
        if spec is None:
            if seen % 20 == 0:
                print(f"observations_seen={seen};eligible_interventions={len(rows)}", flush=True)
            continue

        original_bits = grammar_bits_for(base, primary_grammar)
        identity_bits = grammar_bits_for(spec["identity"], primary_grammar)
        breaking_bits = grammar_bits_for(spec["breaking"], primary_grammar)

        flat_original = grammar_bits_for(base, flat_grammar)
        flat_identity = grammar_bits_for(spec["identity"], flat_grammar)
        flat_breaking = grammar_bits_for(spec["breaking"], flat_grammar)

        topo_base, topo_identity, topo_breaking = topology_counterfactuals_from_spec(row, spec)
        topo_original = grammar_bits_for(topo_base, topology_grammar)
        topo_identity_bits = grammar_bits_for(topo_identity, topology_grammar)
        topo_breaking_bits = grammar_bits_for(topo_breaking, topology_grammar)

        selective = breaking_bits - identity_bits
        rows.append({
            "observationId": row["observationId"],
            "sourceGroupId": row["sourceGroupId"],
            "lane": row["lane"],
            "intervention": {
                "completeEdgeLabel": spec["label"],
                "pairA": list(spec["pairA"]),
                "pairB": list(spec["pairB"]),
                "identityNewA": list(spec["identityNewA"]),
                "identityNewB": list(spec["identityNewB"]),
                "breakingNewA": list(spec["breakingNewA"]),
                "breakingNewB": list(spec["breakingNewB"]),
                "originalTypedSignature": spec["originalTypedSignature"],
            },
            "rawBits": spec["invariants"]["rawBits"],
            "hierarchicalOriginalBits": original_bits,
            "hierarchicalIdentityRewireBits": identity_bits,
            "hierarchicalTypeBreakingRewireBits": breaking_bits,
            "hierarchicalIdentityRewirePenaltyBits": identity_bits - original_bits,
            "hierarchicalTypeBreakingRewirePenaltyBits": breaking_bits - original_bits,
            "hierarchicalTypedSelectivePenaltyBits": selective,
            "hierarchicalNormalizedTypedSelectivePenalty": selective / max(1, original_bits),
            "flatOriginalBits": flat_original,
            "flatIdentityRewireBits": flat_identity,
            "flatTypeBreakingRewireBits": flat_breaking,
            "flatTypedSelectivePenaltyBits": flat_breaking - flat_identity,
            "topologyOriginalBits": topo_original,
            "topologyIdentityRewireBits": topo_identity_bits,
            "topologyTypeBreakingRewireBits": topo_breaking_bits,
            "topologyTypedSelectivePenaltyBits": topo_breaking_bits - topo_identity_bits,
        })
        if seen % 20 == 0:
            print(f"observations_seen={seen};eligible_interventions={len(rows)}", flush=True)

if not rows:
    raise RuntimeError("no eligible typed relational interventions")

summaries = {}
for lane in sorted(lanes):
    lane_rows = [r for r in rows if r["lane"] == lane]
    summaries[lane] = lane_summary(lane_rows, protocol["null"]) if lane_rows else None

g = protocol["gates"]
holdout = summaries.get("holdout")
control = summaries.get("control")
if holdout is None or control is None:
    adjudication = "INFEASIBLE"
elif (
    holdout["eligibleObservations"] < g["minimumEligibleHoldoutObservations"]
    or control["eligibleObservations"] < g["minimumEligibleControlObservations"]
):
    adjudication = "INFEASIBLE"
else:
    passes = (
        holdout["positiveFraction"] >= g["holdoutPositiveFractionMinimum"]
        and control["positiveFraction"] >= g["controlPositiveFractionMinimum"]
        and holdout["meanNormalizedTypedSelectivePenalty"] > g["holdoutMeanNormalizedSelectivePenaltyMinimum"]
        and control["meanNormalizedTypedSelectivePenalty"] > g["controlMeanNormalizedSelectivePenaltyMinimum"]
        and holdout["signFlipP"] <= g["holdoutSignFlipPMaximum"]
        and control["signFlipP"] <= g["controlSignFlipPMaximum"]
    )
    adjudication = "TYPED_RELATION_CLASS_SUPPORTED" if passes else "TYPED_RELATION_CLASS_NOT_DISTINGUISHED"

OUT.mkdir(parents=True, exist_ok=True)
with (OUT / "interventions.jsonl").open("w", encoding="utf-8") as handle:
    for row in rows:
        handle.write(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n")

result = {
    "schema": "mark_typed_relational_intervention_result_v2",
    "experimentId": protocol["experimentId"],
    "designContext": protocol["designContext"],
    "grammarFreezeSha256": freeze_sha,
    "parentEdgePairManifestSha256": manifest.get("edgePairManifestSha256"),
    "parentCriticalEdgeWorldSha256": world.get("criticalEdgeWorldSha256"),
    "projectorRowsSha256": sha256_file(projector),
    "candidatePopulationSeen": seen,
    "eligibleInterventions": len(rows),
    "laneSummaries": summaries,
    "adjudication": adjudication,
}
result_sha = canonical_sha(result)
result["resultSha256"] = result_sha
(OUT / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")

lines = [
    "# Mark typed relational intervention v2",
    "",
    f"Adjudication: **{adjudication}**",
    f"Eligible matched interventions: **{len(rows)}** from {seen} pair-eligible heldout/control observations.",
    "",
]
for lane in ("holdout", "control"):
    s = summaries.get(lane)
    if s is None:
        lines.append(f"- {lane}: no eligible interventions")
        continue
    lines.append(
        f"- {lane}: n={s['eligibleObservations']}; "
        f"mean normalized type-breaking-minus-identity penalty={s['meanNormalizedTypedSelectivePenalty']:+.8f}; "
        f"median bits={s['medianTypedSelectivePenaltyBits']:+.1f}; "
        f"positive fraction={s['positiveFraction']:.3f}; "
        f"sign-flip p={s['signFlipP']:.6f}; "
        f"identity rewire penalty={s['meanIdentityRewirePenaltyBits']:+.2f} bits; "
        f"type-breaking rewire penalty={s['meanTypeBreakingRewirePenaltyBits']:+.2f} bits; "
        f"flat mean selective={s['meanFlatTypedSelectivePenaltyBits']:+.2f} bits; "
        f"topology mean selective={s['meanTopologyTypedSelectivePenaltyBits']:+.2f} bits"
    )
lines.extend([
    "",
    "Both counterfactuals change exact node adjacency using the same two edges. Both preserve node identities and terminal labels, node/edge count, per-node degree, complete edge-label inventory, connected components, cycle rank, and raw V8 code length. The identity rewire preserves the selected endpoint structural-type relation signature; the type-breaking rewire changes that signature.",
    "",
    "This test was designed after V1 returned RELATIONSHIP_EFFECT_NOT_DISTINGUISHED. It therefore does not rescue V1's literal node-identity claim; it tests a narrower representational claim aligned to what the frozen V8 grammar actually encodes.",
    "",
    "A pass supports typed structural relationship classes as a protected level in the frozen blind grammar. It does not establish historical semantics or prove conscious machine encoding.",
    "",
    f"Result SHA-256: `{result_sha}`",
])
(OUT / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
print("\n".join(lines), flush=True)
