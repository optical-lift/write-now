#!/usr/bin/env python3
import hashlib
import json
import os
import statistics
from collections import Counter, defaultdict, deque
from pathlib import Path

from mark_graph_compression_v8_core import (
    TERMINAL_COUNT,
    apply_grammar,
    build_primitive_graph,
    canonical_sha,
    clone_graph,
    contract_pair,
    expand_state,
    expand_symbol,
    find_rule_occurrences,
    graph_bits,
    sha256_file,
)

PROTO = Path(os.environ.get(
    "MARK_RECURSIVE_V3_PROTOCOL",
    "research/mark/discovery-experiments/recursive-composition-intervention-v3.protocol.json",
))
V5 = Path(os.environ.get("MARK_RECURSIVE_V3_V5", "artifact-staging/recursive-v3/v5"))
V8 = Path(os.environ.get("MARK_RECURSIVE_V3_V8", "artifact-staging/recursive-v3/v8"))
OUT = Path(os.environ.get("MARK_RECURSIVE_V3_OUT", "artifacts/mark-recursive-composition-intervention-v3"))
MODE = os.environ.get("MARK_RECURSIVE_V3_MODE", "shard")
SHARDS = Path(os.environ.get("MARK_RECURSIVE_V3_SHARDS", "artifact-staging/recursive-v3/shards"))


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def locate(root, name):
    hits = list(Path(root).rglob(name))
    if len(hits) != 1:
        raise RuntimeError(f"expected one {name} under {root}, found {len(hits)}")
    return hits[0]


def component_count(graph):
    adjacency = defaultdict(set)
    for edge in graph["edges"]:
        u, v = int(edge["u"]), int(edge["v"])
        if u == v:
            raise RuntimeError("self-edge is not permitted")
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


def typed_edge_inventory(graph):
    return tuple(sorted(
        (
            edge["label"],
            tuple(sorted((int(graph["nodes"][edge["u"]]), int(graph["nodes"][edge["v"]])))),
        )
        for edge in graph["edges"]
    ))


def local_invariant_signature(graph):
    comps = component_count(graph)
    half_edges = []
    for edge in graph["edges"]:
        half_edges.append((int(edge["u"]), edge["pu"], edge["label"]))
        half_edges.append((int(edge["v"]), edge["pv"], edge["label"]))
    return {
        "nodeSymbols": tuple(sorted((int(k), int(v)) for k, v in graph["nodes"].items())),
        "nodeCount": len(graph["nodes"]),
        "edgeCount": len(graph["edges"]),
        "perNodeDegree": tuple(graph_degrees(graph).items()),
        "edgeLabels": tuple(sorted(edge["label"] for edge in graph["edges"])),
        "halfEdgeInventory": tuple(sorted(half_edges)),
        "components": comps,
        "cycleRank": len(graph["edges"]) - len(graph["nodes"]) + comps,
        "rawBits": graph_bits(graph),
    }


def primitive_invariant_signature(graph):
    comps = component_count(graph)
    return {
        "nodeSymbols": tuple(sorted((int(k), int(v)) for k, v in graph["nodes"].items())),
        "nodeCount": len(graph["nodes"]),
        "edgeCount": len(graph["edges"]),
        "perNodeDegree": tuple(graph_degrees(graph).items()),
        "edgeLabels": tuple(sorted(edge["label"] for edge in graph["edges"])),
        "typedEdgeInventory": typed_edge_inventory(graph),
        "components": comps,
        "cycleRank": len(graph["edges"]) - len(graph["nodes"]) + comps,
        "rawBits": graph_bits(graph),
    }


def apply_depth1_closure(base, rules):
    graph = clone_graph(base)
    for rule in rules:
        if int(rule["depth"]) != 1:
            continue
        selected = find_rule_occurrences(graph, rule)
        for occurrence in selected:
            contract_pair(graph, occurrence, rule)
    return graph


def upper_grammar_bits(base, rules):
    graph = clone_graph(base)
    for rule in rules:
        if int(rule["depth"]) < 2:
            continue
        selected = find_rule_occurrences(graph, rule)
        for occurrence in selected:
            contract_pair(graph, occurrence, rule)
    return int(graph_bits(graph))


def grammar_bits_for(graph, grammar):
    work = clone_graph(graph)
    return int(apply_grammar(work, grammar, track_members=False)["dataBits"])


def expand_to_primitive(local_graph, all_rules):
    nodes_by_path, expanded_edges = expand_state(local_graph, all_rules)
    ordered_paths = sorted(nodes_by_path)
    path_to_node = {path: index for index, path in enumerate(ordered_paths)}
    graph = {
        "observationId": local_graph["observationId"],
        "sourceGroupId": local_graph["sourceGroupId"],
        "lane": local_graph["lane"],
        "nodes": {path_to_node[path]: int(nodes_by_path[path]) for path in ordered_paths},
        "edges": [
            {
                "u": path_to_node[a],
                "v": path_to_node[b],
                "label": label,
                "pu": "",
                "pv": "",
            }
            for a, b, label in expanded_edges
        ],
        "nextNode": len(ordered_paths),
    }
    return graph


def rule_leaf_maps(rules):
    rule_by_lhs = {int(rule["lhs"]): rule for rule in rules}
    cache = {}

    def leaves(symbol):
        symbol = int(symbol)
        if symbol not in cache:
            node_map, _ = expand_symbol(symbol, rule_by_lhs)
            cache[symbol] = {path: int(sym) for path, sym in node_map.items()}
        return cache[symbol]

    return leaves


def half_edge(graph, edge, side, leaves):
    if side == "u":
        node, port = int(edge["u"]), edge["pu"]
    else:
        node, port = int(edge["v"]), edge["pv"]
    symbol = int(graph["nodes"][node])
    leaf_symbol = int(leaves(symbol)[port])
    return (node, port, leaf_symbol)


def primitive_boundary_key(label, a, b):
    return (label, tuple(sorted((int(a[2]), int(b[2])))))


def recursive_pair_key(graph, label, a, b):
    sa, sb = int(graph["nodes"][a[0]]), int(graph["nodes"][b[0]])
    uv = (sa, sb, ((label, a[1], b[1]),))
    vu = (sb, sa, ((label, b[1], a[1]),))
    return min(uv, vu)


def selected_signature(fn, graph, label, pairs):
    if fn is primitive_boundary_key:
        return tuple(sorted(fn(label, a, b) for a, b in pairs))
    return tuple(sorted(fn(graph, label, a, b) for a, b in pairs))


def deterministic_edge_pool(graph, observation_id, cap, depth_by_symbol, leaves):
    pair_count = Counter(tuple(sorted((int(e["u"]), int(e["v"])))) for e in graph["edges"])
    by_label = defaultdict(list)
    for index, edge in enumerate(graph["edges"]):
        u, v = int(edge["u"]), int(edge["v"])
        su, sv = int(graph["nodes"][u]), int(graph["nodes"][v])
        if su < TERMINAL_COUNT or sv < TERMINAL_COUNT:
            continue
        if depth_by_symbol.get(su) != 1 or depth_by_symbol.get(sv) != 1:
            continue
        if pair_count[tuple(sorted((u, v)))] != 1:
            continue
        a = half_edge(graph, edge, "u", leaves)
        b = half_edge(graph, edge, "v", leaves)
        canonical_halves = tuple(sorted(((a[0], a[1], a[2]), (b[0], b[1], b[2]))))
        token = repr((observation_id, edge["label"], canonical_halves, index))
        by_label[edge["label"]].append((hashlib.sha256(token.encode()).hexdigest(), index, a, b))
    out = {}
    for label, values in sorted(by_label.items()):
        out[label] = [(index, a, b) for _, index, a, b in sorted(values)[:int(cap)]]
    return out


def existing_node_pairs(graph, removed_indices):
    pairs = Counter()
    for index, edge in enumerate(graph["edges"]):
        if index in removed_indices:
            continue
        pairs[tuple(sorted((int(edge["u"]), int(edge["v"]))))] += 1
    return pairs


def canonical_alternatives(a, b, c, d):
    return [
        ((a, c), (b, d)),
        ((a, d), (b, c)),
    ]


def valid_alternative(pairs, existing):
    node_pairs = []
    for a, b in pairs:
        if a[0] == b[0]:
            return False
        pair = tuple(sorted((int(a[0]), int(b[0]))))
        if existing.get(pair, 0):
            return False
        node_pairs.append(pair)
    return len(set(node_pairs)) == len(node_pairs)


def rewire_local_graph(base, index_a, index_b, pairs, label):
    graph = clone_graph(base)
    for index, (left, right) in zip((index_a, index_b), pairs):
        graph["edges"][index] = {
            "u": int(left[0]),
            "v": int(right[0]),
            "label": label,
            "pu": left[1],
            "pv": right[1],
        }
    return graph


def find_intervention(local, observation_id, cap, rules):
    depth_by_symbol = {int(rule["lhs"]): int(rule["depth"]) for rule in rules}
    leaves = rule_leaf_maps(rules)
    pools = deterministic_edge_pool(local, observation_id, cap, depth_by_symbol, leaves)
    original_local_sig = local_invariant_signature(local)
    original_primitive = expand_to_primitive(local, rules)
    original_primitive_sig = primitive_invariant_signature(original_primitive)
    specs = []

    for label, candidates in sorted(pools.items()):
        for i in range(len(candidates)):
            index_a, a, b = candidates[i]
            for j in range(i + 1, len(candidates)):
                index_b, c, d = candidates[j]
                if len({a[0], b[0], c[0], d[0]}) != 4:
                    continue
                existing = existing_node_pairs(local, {index_a, index_b})
                alternatives = canonical_alternatives(a, b, c, d)
                if not all(valid_alternative(pairs, existing) for pairs in alternatives):
                    continue

                original_pairs = ((a, b), (c, d))
                primitive_signature = selected_signature(primitive_boundary_key, local, label, original_pairs)
                if not all(
                    selected_signature(primitive_boundary_key, local, label, pairs) == primitive_signature
                    for pairs in alternatives
                ):
                    continue

                recursive_signature = selected_signature(recursive_pair_key, local, label, original_pairs)
                classified = []
                for pairs in alternatives:
                    sig = selected_signature(recursive_pair_key, local, label, pairs)
                    classified.append((pairs, sig == recursive_signature))
                preservers = [pairs for pairs, preserved in classified if preserved]
                breakers = [pairs for pairs, preserved in classified if not preserved]
                if len(preservers) != 1 or len(breakers) != 1:
                    continue

                preserving = preservers[0]
                breaking = breakers[0]
                key = hashlib.sha256(repr((
                    observation_id, label, index_a, index_b,
                    preserving, breaking, primitive_signature, recursive_signature,
                )).encode()).hexdigest()
                specs.append((
                    key, label, index_a, index_b,
                    preserving, breaking,
                    primitive_signature, recursive_signature,
                ))

    for (
        key, label, index_a, index_b,
        preserving_pairs, breaking_pairs,
        primitive_signature, recursive_signature,
    ) in sorted(specs):
        preserving = rewire_local_graph(local, index_a, index_b, preserving_pairs, label)
        breaking = rewire_local_graph(local, index_a, index_b, breaking_pairs, label)

        if component_count(preserving) != original_local_sig["components"]:
            continue
        if component_count(breaking) != original_local_sig["components"]:
            continue
        if local_invariant_signature(preserving) != original_local_sig:
            raise RuntimeError(f"local preserving invariant drift for {observation_id}")
        if local_invariant_signature(breaking) != original_local_sig:
            raise RuntimeError(f"local breaking invariant drift for {observation_id}")

        preserving_primitive = expand_to_primitive(preserving, rules)
        breaking_primitive = expand_to_primitive(breaking, rules)
        if primitive_invariant_signature(preserving_primitive) != original_primitive_sig:
            raise RuntimeError(f"expanded primitive preserving invariant drift for {observation_id}")
        if primitive_invariant_signature(breaking_primitive) != original_primitive_sig:
            raise RuntimeError(f"expanded primitive breaking invariant drift for {observation_id}")

        return {
            "candidateSha256": key,
            "label": label,
            "edgeIndexA": index_a,
            "edgeIndexB": index_b,
            "preservingPairs": preserving_pairs,
            "breakingPairs": breaking_pairs,
            "primitiveBoundarySignature": primitive_signature,
            "recursiveRelationSignature": recursive_signature,
            "originalLocal": local,
            "preservingLocal": preserving,
            "breakingLocal": breaking,
            "originalPrimitive": original_primitive,
            "preservingPrimitive": preserving_primitive,
            "breakingPrimitive": breaking_primitive,
            "localRawBits": original_local_sig["rawBits"],
        }
    return None


def score_observation(row, grammar_packet, cap):
    hierarchical = grammar_packet["models"]["lengthAware"]["hierarchical"]
    flat = grammar_packet["models"]["lengthAware"]["flat"]
    rules = hierarchical["rules"]

    primitive = build_primitive_graph(row, "lengthAware", track_members=False)
    local = apply_depth1_closure(primitive, rules)
    spec = find_intervention(local, row["observationId"], cap, rules)
    if spec is None:
        return None

    h_original = grammar_bits_for(spec["originalPrimitive"], hierarchical)
    h_preserving = grammar_bits_for(spec["preservingPrimitive"], hierarchical)
    h_breaking = grammar_bits_for(spec["breakingPrimitive"], hierarchical)
    f_original = grammar_bits_for(spec["originalPrimitive"], flat)
    f_preserving = grammar_bits_for(spec["preservingPrimitive"], flat)
    f_breaking = grammar_bits_for(spec["breakingPrimitive"], flat)
    u_original = upper_grammar_bits(spec["originalLocal"], rules)
    u_preserving = upper_grammar_bits(spec["preservingLocal"], rules)
    u_breaking = upper_grammar_bits(spec["breakingLocal"], rules)

    hierarchical_selective = h_breaking - h_preserving
    flat_selective = f_breaking - f_preserving
    hierarchy_increment = hierarchical_selective - flat_selective
    upper_selective = u_breaking - u_preserving

    return {
        "observationId": row["observationId"],
        "sourceGroupId": row["sourceGroupId"],
        "lane": row["lane"],
        "intervention": {
            "candidateSha256": spec["candidateSha256"],
            "completeEdgeLabel": spec["label"],
            "edgeIndexA": spec["edgeIndexA"],
            "edgeIndexB": spec["edgeIndexB"],
            "preservingPairs": spec["preservingPairs"],
            "breakingPairs": spec["breakingPairs"],
            "primitiveBoundarySignature": spec["primitiveBoundarySignature"],
            "recursiveRelationSignature": spec["recursiveRelationSignature"],
        },
        "localRawBits": spec["localRawBits"],
        "localRawSelectivePenaltyBits": 0,
        "fullHierarchicalOriginalBits": h_original,
        "fullHierarchicalPreservingBits": h_preserving,
        "fullHierarchicalBreakingBits": h_breaking,
        "fullHierarchicalPreservingPenaltyBits": h_preserving - h_original,
        "fullHierarchicalBreakingPenaltyBits": h_breaking - h_original,
        "fullHierarchicalSelectivePenaltyBits": hierarchical_selective,
        "flatOriginalBits": f_original,
        "flatPreservingBits": f_preserving,
        "flatBreakingBits": f_breaking,
        "flatSelectivePenaltyBits": flat_selective,
        "hierarchyIncrementBits": hierarchy_increment,
        "normalizedHierarchyIncrement": hierarchy_increment / max(1, h_original),
        "upperOriginalBits": u_original,
        "upperPreservingBits": u_preserving,
        "upperBreakingBits": u_breaking,
        "upperOnlySelectivePenaltyBits": upper_selective,
    }


def validate_parents(protocol):
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
    return manifest, world, projector, grammar_packet, freeze_sha


def shard_for(observation_id, count):
    digest = hashlib.sha256(str(observation_id).encode()).digest()
    return int.from_bytes(digest[:8], "big") % int(count)


def run_shard(protocol, world, projector, grammar_packet):
    shard_index = int(os.environ["MARK_RECURSIVE_V3_SHARD_INDEX"])
    shard_count = int(os.environ["MARK_RECURSIVE_V3_SHARD_COUNT"])
    if shard_index < 0 or shard_index >= shard_count:
        raise RuntimeError("invalid shard index")
    eligible = set(world["pairEligibleObservationIds"])
    lanes = {protocol["population"]["primaryLane"], protocol["population"]["replicationLane"]}
    cap = int(protocol["matchedIntervention"]["candidateEdgeLimitPerCompleteLabel"])
    rows = []
    seen_ids = []

    with projector.open("r", encoding="utf-8") as handle:
        for raw in handle:
            if not raw.strip():
                continue
            row = json.loads(raw)
            oid = row["observationId"]
            if oid not in eligible or row["lane"] not in lanes:
                continue
            if shard_for(oid, shard_count) != shard_index:
                continue
            seen_ids.append(oid)
            scored = score_observation(row, grammar_packet, cap)
            if scored is not None:
                rows.append(scored)
            print(
                f"shard={shard_index};seen={len(seen_ids)};eligible_interventions={len(rows)};observation={oid}",
                flush=True,
            )

    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / "interventions.jsonl").open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n")
    worker = {
        "schema": "mark_recursive_composition_intervention_v3_worker",
        "protocolSha256": canonical_sha(protocol),
        "shardIndex": shard_index,
        "shardCount": shard_count,
        "seenObservationIds": seen_ids,
        "candidatePopulationSeen": len(seen_ids),
        "eligibleInterventions": len(rows),
    }
    (OUT / "worker.json").write_text(json.dumps(worker, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(worker, sort_keys=True), flush=True)


def signflip_p(values, iterations, salt):
    ids = [item[0] for item in values]
    nums = [item[1] for item in values]
    observed = statistics.mean(nums)
    nulls = []
    for iteration in range(int(iterations)):
        signed = []
        for oid, value in zip(ids, nums):
            h = hashlib.sha256(f"{salt}|{iteration}|{oid}".encode()).digest()
            signed.append((1.0 if (h[0] & 1) else -1.0) * value)
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
    normalized = [(r["observationId"], r["normalizedHierarchyIncrement"]) for r in rows]
    observed, p, null = signflip_p(normalized, null_cfg["iterations"], null_cfg["seedSalt"])
    increments = [r["hierarchyIncrementBits"] for r in rows]
    return {
        "eligibleObservations": len(rows),
        "meanNormalizedHierarchyIncrement": observed,
        "medianHierarchyIncrementBits": statistics.median(increments),
        "meanHierarchyIncrementBits": statistics.mean(increments),
        "positiveFraction": sum(x > 0 for x in increments) / len(increments),
        "zeroFraction": sum(x == 0 for x in increments) / len(increments),
        "signFlipP": p,
        "null": null,
        "meanFullHierarchicalSelectivePenaltyBits": statistics.mean(r["fullHierarchicalSelectivePenaltyBits"] for r in rows),
        "meanFlatSelectivePenaltyBits": statistics.mean(r["flatSelectivePenaltyBits"] for r in rows),
        "meanUpperOnlySelectivePenaltyBits": statistics.mean(r["upperOnlySelectivePenaltyBits"] for r in rows),
        "meanPreservingPenaltyBits": statistics.mean(r["fullHierarchicalPreservingPenaltyBits"] for r in rows),
        "meanBreakingPenaltyBits": statistics.mean(r["fullHierarchicalBreakingPenaltyBits"] for r in rows),
    }


def run_aggregate(protocol, manifest, world, projector, freeze_sha):
    shard_count = int(os.environ.get("MARK_RECURSIVE_V3_SHARD_COUNT", "20"))
    workers = [load_json(path) for path in sorted(SHARDS.rglob("worker.json"))]
    if len(workers) != shard_count:
        raise RuntimeError(f"expected {shard_count} worker packets, found {len(workers)}")
    expected_indices = list(range(shard_count))
    actual_indices = sorted(int(w["shardIndex"]) for w in workers)
    if actual_indices != expected_indices:
        raise RuntimeError(f"shard index coverage mismatch: {actual_indices}")
    protocol_sha = canonical_sha(protocol)
    for worker in workers:
        if worker.get("protocolSha256") != protocol_sha:
            raise RuntimeError("worker protocol drift")
        if int(worker.get("shardCount")) != shard_count:
            raise RuntimeError("worker shard-count drift")

    all_seen = []
    for worker in workers:
        all_seen.extend(worker["seenObservationIds"])
    if len(all_seen) != len(set(all_seen)):
        raise RuntimeError("duplicate observation ownership across shards")

    eligible = set(world["pairEligibleObservationIds"])
    lanes = {protocol["population"]["primaryLane"], protocol["population"]["replicationLane"]}
    expected_order = []
    with projector.open("r", encoding="utf-8") as handle:
        for raw in handle:
            if not raw.strip():
                continue
            row = json.loads(raw)
            if row["observationId"] in eligible and row["lane"] in lanes:
                expected_order.append(row["observationId"])
    if set(all_seen) != set(expected_order) or len(all_seen) != len(expected_order):
        raise RuntimeError("shards do not exactly cover the frozen evaluation population")

    rows_by_id = {}
    for path in sorted(SHARDS.rglob("interventions.jsonl")):
        with path.open("r", encoding="utf-8") as handle:
            for raw in handle:
                if not raw.strip():
                    continue
                row = json.loads(raw)
                oid = row["observationId"]
                if oid in rows_by_id:
                    raise RuntimeError(f"duplicate scored observation {oid}")
                rows_by_id[oid] = row
    if not set(rows_by_id).issubset(set(expected_order)):
        raise RuntimeError("scored row outside frozen population")
    order_index = {oid: index for index, oid in enumerate(expected_order)}
    rows = sorted(rows_by_id.values(), key=lambda row: order_index[row["observationId"]])

    if not rows:
        raise RuntimeError("no eligible recursive composition interventions")
    summaries = {}
    for lane in sorted(lanes):
        lane_rows = [row for row in rows if row["lane"] == lane]
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
            and holdout["meanNormalizedHierarchyIncrement"] > g["holdoutMeanNormalizedHierarchyIncrementMinimum"]
            and control["meanNormalizedHierarchyIncrement"] > g["controlMeanNormalizedHierarchyIncrementMinimum"]
            and holdout["meanUpperOnlySelectivePenaltyBits"] > g["holdoutMeanUpperOnlySelectivePenaltyMinimumBits"]
            and control["meanUpperOnlySelectivePenaltyBits"] > g["controlMeanUpperOnlySelectivePenaltyMinimumBits"]
            and holdout["signFlipP"] <= g["holdoutSignFlipPMaximum"]
            and control["signFlipP"] <= g["controlSignFlipPMaximum"]
        )
        adjudication = "RECURSIVE_COMPOSITION_SUPPORTED" if passes else "RECURSIVE_COMPOSITION_NOT_DISTINGUISHED"

    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / "interventions.jsonl").open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n")

    result = {
        "schema": "mark_recursive_composition_intervention_result_v3",
        "experimentId": protocol["experimentId"],
        "designContext": protocol["designContext"],
        "protocolSha256": protocol_sha,
        "grammarFreezeSha256": freeze_sha,
        "parentEdgePairManifestSha256": manifest.get("edgePairManifestSha256"),
        "parentCriticalEdgeWorldSha256": world.get("criticalEdgeWorldSha256"),
        "projectorRowsSha256": sha256_file(projector),
        "candidatePopulationSeen": len(expected_order),
        "eligibleInterventions": len(rows),
        "laneSummaries": summaries,
        "adjudication": adjudication,
    }
    result_sha = canonical_sha(result)
    result["resultSha256"] = result_sha
    (OUT / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    lines = [
        "# Mark recursive composition intervention v3",
        "",
        f"Adjudication: **{adjudication}**",
        f"Eligible matched interventions: **{len(rows)}** from {len(expected_order)} pair-eligible reused evaluation observations.",
        "",
    ]
    for lane in ("holdout", "control"):
        s = summaries.get(lane)
        if s is None:
            lines.append(f"- {lane}: no eligible interventions")
            continue
        lines.append(
            f"- {lane}: n={s['eligibleObservations']}; "
            f"mean normalized hierarchy increment={s['meanNormalizedHierarchyIncrement']:+.8f}; "
            f"median hierarchy increment={s['medianHierarchyIncrementBits']:+.1f} bits; "
            f"positive fraction={s['positiveFraction']:.3f}; "
            f"sign-flip p={s['signFlipP']:.6f}; "
            f"full hierarchical selective={s['meanFullHierarchicalSelectivePenaltyBits']:+.2f} bits; "
            f"flat selective={s['meanFlatSelectivePenaltyBits']:+.2f} bits; "
            f"upper-only selective={s['meanUpperOnlySelectivePenaltyBits']:+.2f} bits"
        )
    lines.extend([
        "",
        "Both counterfactuals re-pair the same four residual half-edges after frozen depth-1 closure. Both preserve the complete primitive boundary typed-edge signature and the full expanded primitive typed-edge inventory. The preserving edit changes module instances while retaining the exact selected frozen V8 residual pair-key multiset; the breaking edit changes that recursive relation signature.",
        "",
        "The primary outcome is a difference-in-differences: (full hierarchical breaking-minus-preserving penalty) minus (flat breaking-minus-preserving penalty). Positive values therefore isolate hierarchical selectivity beyond the frozen flat/local dictionary. The upper-only diagnostic applies only depth>=2 rules to the fixed depth-1 closure.",
        "",
        "V3 was designed after V1 and V2 had already opened holdout/control. These are reused mechanistic evaluation lanes, not fresh independent holdouts. Scientific failure is green.",
        "",
        f"Result SHA-256: `{result_sha}`",
    ])
    (OUT / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines), flush=True)


protocol = load_json(PROTO)
if protocol.get("schema") != "mark_recursive_composition_intervention_protocol_v3":
    raise RuntimeError("wrong recursive composition protocol")
manifest, world, projector, grammar_packet, freeze_sha = validate_parents(protocol)

if MODE == "shard":
    run_shard(protocol, world, projector, grammar_packet)
elif MODE == "aggregate":
    run_aggregate(protocol, manifest, world, projector, freeze_sha)
else:
    raise RuntimeError(f"unknown MARK_RECURSIVE_V3_MODE={MODE}")
