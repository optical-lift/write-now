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
    parse_edge_label,
)

PROTO = Path(os.environ.get(
    "MARK_RELATIONAL_PROTOCOL",
    "research/mark/discovery-experiments/relational-intervention-v1.protocol.json",
))
V5 = Path(os.environ.get("MARK_RELATIONAL_V5", "artifact-staging/relational/v5"))
V8 = Path(os.environ.get("MARK_RELATIONAL_V8", "artifact-staging/relational/v8"))
OUT = Path(os.environ.get("MARK_RELATIONAL_OUT", "artifacts/mark-relational-intervention-v1"))


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


def clone_and_attribute_swap(base, pair_a, pair_b):
    graph = clone_graph(base)
    by_pair = {endpoint_pair(edge): i for i, edge in enumerate(graph["edges"])}
    ia, ib = by_pair[pair_a], by_pair[pair_b]
    graph["edges"][ia]["label"], graph["edges"][ib]["label"] = (
        graph["edges"][ib]["label"], graph["edges"][ia]["label"]
    )
    return graph


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


def deterministic_edge_pool(graph, observation_id, cap):
    by_mult = defaultdict(list)
    for edge in graph["edges"]:
        mult, length_bin = parse_edge_label(edge["label"])
        if length_bin is None:
            continue
        pair = endpoint_pair(edge)
        token = f"{observation_id}|{pair[0]}|{pair[1]}|{edge['label']}"
        by_mult[mult].append((hashlib.sha256(token.encode()).hexdigest(), pair, int(length_bin)))
    out = []
    for mult, rows in sorted(by_mult.items()):
        for item in sorted(rows)[:int(cap)]:
            out.append((mult, *item))
    return out


def find_intervention(base, observation_id, cap):
    """Selection-equivalent optimization of the frozen minimum-SHA rule.

    The first implementation tested connectivity for every candidate and only then
    took the minimum candidate SHA. Here we enumerate the identical candidate
    specifications, sort by the identical SHA, and test connectivity in that
    order. The first connectivity-valid item is therefore exactly the same
    minimum-SHA valid candidate, without repeated full-graph walks for candidates
    that cannot win.
    """
    original_sig = invariant_signature(base)
    existing = {endpoint_pair(edge) for edge in base["edges"]}
    pool = deterministic_edge_pool(base, observation_id, cap)
    specs = []
    for i in range(len(pool)):
        mult_a, _, pair_a, len_a = pool[i]
        for j in range(i + 1, len(pool)):
            mult_b, _, pair_b, len_b = pool[j]
            if mult_a != mult_b or len_a == len_b:
                continue
            if len(set(pair_a + pair_b)) != 4:
                continue
            u, v = pair_a
            x, y = pair_b
            alternatives = [
                (tuple(sorted((u, x))), tuple(sorted((v, y)))),
                (tuple(sorted((u, y))), tuple(sorted((v, x)))),
            ]
            for alt_index, (new_a, new_b) in enumerate(alternatives):
                if new_a == new_b or new_a in existing - {pair_a, pair_b} or new_b in existing - {pair_a, pair_b}:
                    continue
                if new_a[0] == new_a[1] or new_b[0] == new_b[1]:
                    continue
                key = hashlib.sha256(
                    f"{observation_id}|{pair_a}|{pair_b}|{new_a}|{new_b}|{alt_index}".encode()
                ).hexdigest()
                specs.append((key, pair_a, pair_b, new_a, new_b, len_a, len_b, mult_a))
    for _, pair_a, pair_b, new_a, new_b, len_a, len_b, mult in sorted(specs):
        rewire = clone_and_rewire(base, pair_a, pair_b, new_a, new_b)
        if component_count(rewire) != original_sig["components"]:
            continue
        attr = clone_and_attribute_swap(base, pair_a, pair_b)
        attr_sig = invariant_signature(attr)
        rewire_sig = invariant_signature(rewire)
        if attr_sig != original_sig:
            raise RuntimeError(f"attribute intervention invariant drift for {observation_id}")
        if rewire_sig != original_sig:
            raise RuntimeError(f"relationship intervention invariant drift for {observation_id}")
        return {
            "pairA": pair_a,
            "pairB": pair_b,
            "newA": new_a,
            "newB": new_b,
            "lengthBinA": len_a,
            "lengthBinB": len_b,
            "multiplicityClass": mult,
            "attribute": attr,
            "rewire": rewire,
            "invariants": original_sig,
        }
    return None


def grammar_bits_for(graph, grammar):
    work = clone_graph(graph)
    return int(apply_grammar(work, grammar, track_members=False)["dataBits"])


def topology_rewire_from_spec(row, spec):
    base = build_primitive_graph(row, "topology", track_members=False)
    rewired = clone_and_rewire(base, tuple(spec["pairA"]), tuple(spec["pairB"]), tuple(spec["newA"]), tuple(spec["newB"]))
    if invariant_signature(rewired) != invariant_signature(base):
        raise RuntimeError(f"topology rewire invariant drift for {row['observationId']}")
    return base, rewired


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
    values = [(r["observationId"], r["hierarchicalNormalizedSelectivePenalty"]) for r in rows]
    observed, p, null = signflip_p(values, null_cfg["iterations"], null_cfg["seedSalt"])
    gaps = [r["hierarchicalSelectivePenaltyBits"] for r in rows]
    return {
        "eligibleObservations": len(rows),
        "meanNormalizedSelectivePenalty": observed,
        "medianSelectivePenaltyBits": statistics.median(gaps),
        "meanSelectivePenaltyBits": statistics.mean(gaps),
        "positiveFraction": sum(x > 0 for x in gaps) / len(gaps),
        "zeroFraction": sum(x == 0 for x in gaps) / len(gaps),
        "signFlipP": p,
        "null": null,
        "meanFlatSelectivePenaltyBits": statistics.mean(r["flatSelectivePenaltyBits"] for r in rows),
        "meanTopologyRelationshipPenaltyBits": statistics.mean(r["topologyRelationshipPenaltyBits"] for r in rows),
    }


protocol = load_json(PROTO)
if protocol.get("schema") != "mark_relational_intervention_protocol_v1":
    raise RuntimeError("wrong relational intervention protocol")

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
cap = protocol["matchedIntervention"]["candidateEdgeLimitPerMultiplicityClass"]

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
            continue
        original_bits = grammar_bits_for(base, primary_grammar)
        attr_bits = grammar_bits_for(spec["attribute"], primary_grammar)
        rewire_bits = grammar_bits_for(spec["rewire"], primary_grammar)
        flat_original = grammar_bits_for(base, flat_grammar)
        flat_attr = grammar_bits_for(spec["attribute"], flat_grammar)
        flat_rewire = grammar_bits_for(spec["rewire"], flat_grammar)
        topo_base, topo_rewire = topology_rewire_from_spec(row, spec)
        topo_original = grammar_bits_for(topo_base, topology_grammar)
        topo_rewire_bits = grammar_bits_for(topo_rewire, topology_grammar)
        selective = rewire_bits - attr_bits
        rows.append({
            "observationId": row["observationId"],
            "sourceGroupId": row["sourceGroupId"],
            "lane": row["lane"],
            "intervention": {
                "pairA": list(spec["pairA"]),
                "pairB": list(spec["pairB"]),
                "newA": list(spec["newA"]),
                "newB": list(spec["newB"]),
                "lengthBinA": spec["lengthBinA"],
                "lengthBinB": spec["lengthBinB"],
                "multiplicityClass": spec["multiplicityClass"],
            },
            "rawBits": spec["invariants"]["rawBits"],
            "hierarchicalOriginalBits": original_bits,
            "hierarchicalAttributeSwapBits": attr_bits,
            "hierarchicalRelationshipRewireBits": rewire_bits,
            "hierarchicalAttributePenaltyBits": attr_bits - original_bits,
            "hierarchicalRelationshipPenaltyBits": rewire_bits - original_bits,
            "hierarchicalSelectivePenaltyBits": selective,
            "hierarchicalNormalizedSelectivePenalty": selective / max(1, original_bits),
            "flatOriginalBits": flat_original,
            "flatAttributeSwapBits": flat_attr,
            "flatRelationshipRewireBits": flat_rewire,
            "flatSelectivePenaltyBits": flat_rewire - flat_attr,
            "topologyOriginalBits": topo_original,
            "topologyRelationshipRewireBits": topo_rewire_bits,
            "topologyRelationshipPenaltyBits": topo_rewire_bits - topo_original,
        })
        if seen % 20 == 0:
            print(f"observations_seen={seen};eligible_interventions={len(rows)}", flush=True)

if not rows:
    raise RuntimeError("no eligible interventions")

summaries = {}
for lane in sorted(lanes):
    lane_rows = [r for r in rows if r["lane"] == lane]
    summaries[lane] = lane_summary(lane_rows, protocol["null"]) if lane_rows else None

g = protocol["gates"]
holdout = summaries.get("holdout")
control = summaries.get("control")
if holdout is None or control is None or holdout["eligibleObservations"] < g["minimumEligibleHoldoutObservations"] or control["eligibleObservations"] < g["minimumEligibleControlObservations"]:
    adjudication = "INFEASIBLE"
    passed = False
else:
    passed = bool(
        holdout["positiveFraction"] >= g["holdoutPositiveFractionMinimum"]
        and control["positiveFraction"] >= g["controlPositiveFractionMinimum"]
        and holdout["meanNormalizedSelectivePenalty"] > g["holdoutMeanNormalizedSelectivePenaltyMinimum"]
        and control["meanNormalizedSelectivePenalty"] > g["controlMeanNormalizedSelectivePenaltyMinimum"]
        and holdout["signFlipP"] <= g["holdoutSignFlipPMaximum"]
        and control["signFlipP"] <= g["controlSignFlipPMaximum"]
    )
    adjudication = "RELATIONSHIP_CODE_SUPPORTED" if passed else "RELATIONSHIP_EFFECT_NOT_DISTINGUISHED"

core = {
    "schema": "mark_relational_intervention_result_v1",
    "experimentId": protocol["experimentId"],
    "grammarFreezeSha256": freeze_sha,
    "parentEdgePairManifestSha256": manifest["edgePairManifestSha256"],
    "parentCriticalEdgeWorldSha256": world["criticalEdgeWorldSha256"],
    "projectorRowsSha256": sha256_file(projector),
    "candidatePopulationSeen": seen,
    "eligibleInterventions": len(rows),
    "laneSummaries": summaries,
    "passed": passed,
    "adjudication": adjudication,
    "contract": {
        "grammarFrozenBeforeIntervention": True,
        "grammarRefitAfterIntervention": False,
        "trainLaneExcludedFromPrimaryAdjudication": True,
        "attributeAndRelationshipInterventionsUseSameTwoEdges": True,
        "lowOrderGraphInvariantsExact": True,
        "rawCodeLengthExact": True,
        "roleLabelsConsumed": False,
        "sourcePixelsConsumed": False,
        "optimizedSelectorIsMinimumShaEquivalentToFrozenSelector": True,
    }
}
digest = canonical_sha(core)
packet = {**core, "relationalInterventionSha256": digest}
OUT.mkdir(parents=True, exist_ok=True)
(OUT / "result.json").write_text(json.dumps(packet, indent=2) + "\n", encoding="utf-8")
with (OUT / "interventions.jsonl").open("w", encoding="utf-8") as out:
    for row in sorted(rows, key=lambda x: x["observationId"]):
        out.write(json.dumps(row, separators=(",", ":")) + "\n")

summary = [
    "# Mark relational intervention v1",
    "",
    f"Adjudication: **{adjudication}**",
    f"Eligible matched interventions: **{len(rows)}** from {seen} pair-eligible heldout/control observations.",
    "",
]
for lane in ("holdout", "control"):
    s = summaries.get(lane)
    if not s:
        summary.append(f"- {lane}: no eligible observations")
    else:
        summary.append(
            f"- {lane}: n={s['eligibleObservations']}; mean normalized relationship-minus-attribute penalty={s['meanNormalizedSelectivePenalty']:+.8f}; "
            f"median bits={s['medianSelectivePenaltyBits']:+.1f}; positive fraction={s['positiveFraction']:.3f}; sign-flip p={s['signFlipP']:.6f}; "
            f"flat mean gap={s['meanFlatSelectivePenaltyBits']:+.2f} bits; topology rewire penalty={s['meanTopologyRelationshipPenaltyBits']:+.2f} bits"
        )
summary += [
    "",
    "Both interventions use the same two edges and exactly preserve node labels, node/edge count, per-node degree, complete edge-label multiset, connected components, cycle rank, and raw V8 code length. The attribute intervention preserves relationships and swaps length realization assignment; the relationship intervention preserves the labels and degree budget but rewires which nodes are connected.",
    "",
    "The selector optimization is scientifically identical to the frozen minimum-SHA rule: candidate specifications are sorted by the same SHA first, then connectivity is checked in that order, so the first accepted candidate is exactly the minimum-SHA connectivity-valid candidate the exhaustive implementation would select.",
    "",
    "A pass supports a causal distinction inside the current Mark representation between relationship organization and edge-realization assignment under a grammar learned before this test. It does not establish historical semantics or prove conscious machine encoding.",
    "",
    f"Result SHA-256: `{digest}`",
]
(OUT / "summary.md").write_text("\n".join(summary) + "\n", encoding="utf-8")
print("\n".join(summary))
