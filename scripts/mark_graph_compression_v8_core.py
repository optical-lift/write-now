#!/usr/bin/env python3
import hashlib
import json
import math
import statistics
from collections import Counter, defaultdict

TERMINAL_LABELS = sorted(
    f"{kind}|D{deg}|S{loop}"
    for kind in ("ENDPOINT", "JUNCTION")
    for deg in ("0", "1", "2", "3", "4", "5", "6+")
    for loop in ("0", "1", "2", "3+")
)
TERMINAL_TO_ID = {label: i for i, label in enumerate(TERMINAL_LABELS)}
TERMINAL_COUNT = len(TERMINAL_LABELS)
MULT_TO_INDEX = {"1": 1, "2": 2, "3+": 3}


def canonical_sha(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()


def sha256_file(path, chunk=1024 * 1024):
    h = hashlib.sha256()
    with open(path, "rb") as handle:
        while True:
            data = handle.read(chunk)
            if not data:
                break
            h.update(data)
    return h.hexdigest()


def gamma_len(value):
    value = int(value)
    if value < 1:
        raise ValueError("gamma code requires integer >= 1")
    return 2 * int(math.floor(math.log2(value))) + 1


def count_bits(value):
    return gamma_len(int(value) + 1)


def symbol_bits(symbol):
    return gamma_len(int(symbol) + 1)


def port_bits(path):
    return gamma_len(len(path) + 1) + len(path)


def degree_class(value, cap=6):
    value = int(value)
    return f"{cap}+" if value >= cap else str(value)


def multiplicity_class(value, cap=3):
    value = int(value)
    return f"{cap}+" if value >= cap else str(value)


def terminal_symbol(kind, degree, self_loops):
    label = f"{kind}|D{degree_class(degree)}|S{multiplicity_class(self_loops)}"
    return TERMINAL_TO_ID[label]


def make_edge_label(multiplicity, length_bin=None):
    mult = multiplicity_class(multiplicity)
    return f"M{mult}" if length_bin is None else f"L{int(length_bin)}|M{mult}"


def parse_edge_label(label):
    if label.startswith("L"):
        lhs, rhs = label.split("|", 1)
        length_bin = int(lhs[1:])
        mult = rhs[1:]
        return mult, length_bin
    return label[1:], None


def edge_label_id(label):
    mult, length_bin = parse_edge_label(label)
    m = MULT_TO_INDEX[mult]
    if length_bin is None:
        return m - 1
    return int(length_bin) * 3 + (m - 1)


def edge_label_bits(label):
    return gamma_len(edge_label_id(label) + 1)


def edge_bits(edge):
    return 64 + edge_label_bits(edge["label"]) + port_bits(edge["pu"]) + port_bits(edge["pv"])


def graph_bits(graph):
    bits = count_bits(len(graph["nodes"])) + count_bits(len(graph["edges"]))
    bits += sum(symbol_bits(symbol) for symbol in graph["nodes"].values())
    bits += sum(edge_bits(edge) for edge in graph["edges"])
    return bits


def rule_bits(rule):
    bits = symbol_bits(rule["left"]) + symbol_bits(rule["right"])
    bits += count_bits(len(rule["internal"]))
    for item in rule["internal"]:
        bits += edge_label_bits(item["label"]) + port_bits(item["pLeft"]) + port_bits(item["pRight"])
    return bits


def grammar_bits(rules):
    return count_bits(len(rules)) + sum(rule_bits(rule) for rule in rules)


def graph_code_total(graphs, rules):
    return grammar_bits(rules) + sum(graph_bits(graph) for graph in graphs)


def build_primitive_graph(row, variant, track_members=False):
    centers = {c["eventId"]: c for c in row["centers"]}
    grouped = defaultdict(list)
    self_counts = Counter()
    for edge in row["edges"]:
        a, b = edge["a"], edge["b"]
        if a not in centers or b not in centers:
            continue
        if a == b:
            self_counts[a] += 1
        else:
            grouped[tuple(sorted((a, b)))].append(edge)

    event_ids = list(centers)
    event_to_node = {event_id: index for index, event_id in enumerate(event_ids)}
    nodes = {
        event_to_node[event_id]: terminal_symbol(
            centers[event_id]["kind"], centers[event_id]["degree"], self_counts[event_id]
        )
        for event_id in event_ids
    }
    diagonal = max(1.0, math.hypot(float(row["region"]["width"]), float(row["region"]["height"])))
    edges = []
    for (a, b), bundle in grouped.items():
        mean_norm = statistics.mean(float(edge["pathSteps"]) for edge in bundle) / diagonal
        length_bin = int(math.floor(max(0.0, mean_norm) / 0.05 + 1e-12)) if variant == "lengthAware" else None
        edges.append({
            "u": event_to_node[a],
            "v": event_to_node[b],
            "label": make_edge_label(len(bundle), length_bin),
            "pu": "",
            "pv": "",
        })
    graph = {
        "observationId": row["observationId"],
        "sourceGroupId": row["sourceGroupId"],
        "lane": row["lane"],
        "nodes": nodes,
        "edges": edges,
        "nextNode": len(nodes),
    }
    if track_members:
        graph["members"] = {event_to_node[eid]: [eid] for eid in event_ids}
        graph["ancestry"] = {eid: [] for eid in event_ids}
    return graph


def clone_graph(graph, track_members=False):
    out = {
        "observationId": graph["observationId"],
        "sourceGroupId": graph["sourceGroupId"],
        "lane": graph["lane"],
        "nodes": dict(graph["nodes"]),
        "edges": [dict(edge) for edge in graph["edges"]],
        "nextNode": graph["nextNode"],
    }
    if track_members:
        out["members"] = {node: list(members) for node, members in graph.get("members", {}).items()}
        out["ancestry"] = {eid: list(seq) for eid, seq in graph.get("ancestry", {}).items()}
    return out


def endpoint_port(edge, node):
    if edge["u"] == node:
        return edge["pu"]
    if edge["v"] == node:
        return edge["pv"]
    raise KeyError(node)


def oriented_bundle(graph, u, v, indices):
    su, sv = graph["nodes"][u], graph["nodes"][v]
    uv = tuple(sorted((graph["edges"][i]["label"], endpoint_port(graph["edges"][i], u), endpoint_port(graph["edges"][i], v)) for i in indices))
    vu = tuple(sorted((graph["edges"][i]["label"], endpoint_port(graph["edges"][i], v), endpoint_port(graph["edges"][i], u)) for i in indices))
    key_uv = (su, sv, uv)
    key_vu = (sv, su, vu)
    if key_vu < key_uv:
        return v, u, vu, key_vu
    return u, v, uv, key_uv


def key_hash(key):
    return hashlib.sha256(repr(key).encode()).hexdigest()


def index_graph(graph):
    pair_edges = defaultdict(list)
    incident = defaultdict(list)
    context = defaultdict(list)
    for index, edge in enumerate(graph["edges"]):
        u, v = edge["u"], edge["v"]
        if u == v:
            raise RuntimeError("residual self-edge is not permitted")
        pair_edges[(min(u, v), max(u, v))].append(index)
        incident[u].append(index)
        incident[v].append(index)
    occurrences = []
    for (u, v), indices in pair_edges.items():
        left, right, descriptors, key = oriented_bundle(graph, u, v, indices)
        occurrences.append({
            "u": u,
            "v": v,
            "left": left,
            "right": right,
            "indices": tuple(indices),
            "key": key,
        })
    for node, indices in incident.items():
        items = []
        for i in indices:
            edge = graph["edges"][i]
            other = edge["v"] if edge["u"] == node else edge["u"]
            items.append((graph["nodes"][other], edge["label"], endpoint_port(edge, node), len(endpoint_port(edge, other))))
        context[node] = hashlib.sha256(repr((graph["nodes"][node], tuple(sorted(items)))).encode()).hexdigest()
    for occurrence in occurrences:
        cu, cv = context[occurrence["u"]], context[occurrence["v"]]
        occurrence["sortKey"] = (min(cu, cv), max(cu, cv), min(occurrence["u"], occurrence["v"]), max(occurrence["u"], occurrence["v"]))
    return occurrences, incident


def enumerate_corpus_candidates(graphs, allow_nonterminals, symbol_depth):
    records = {}
    per_graph_incident = []
    for gi, graph in enumerate(graphs):
        occurrences, incident = index_graph(graph)
        per_graph_incident.append(incident)
        for occurrence in occurrences:
            left_symbol = occurrence["key"][0]
            right_symbol = occurrence["key"][1]
            if not allow_nonterminals and (left_symbol >= TERMINAL_COUNT or right_symbol >= TERMINAL_COUNT):
                continue
            depth = max(symbol_depth.get(left_symbol, 0), symbol_depth.get(right_symbol, 0)) + 1
            record = records.setdefault(occurrence["key"], {"sources": set(), "occurrences": [], "depth": depth})
            record["sources"].add(graph["sourceGroupId"])
            record["occurrences"].append((gi, occurrence))
    return records, per_graph_incident


def select_nonoverlap(record):
    by_graph = defaultdict(list)
    for gi, occurrence in record["occurrences"]:
        by_graph[gi].append(occurrence)
    selected = []
    for gi in sorted(by_graph):
        used = set()
        for occurrence in sorted(by_graph[gi], key=lambda x: x["sortKey"]):
            if occurrence["u"] in used or occurrence["v"] in used:
                continue
            used.add(occurrence["u"])
            used.add(occurrence["v"])
            selected.append((gi, occurrence))
    return selected


def rule_from_key(key, lhs, depth, support=0, occurrences=0, gain=0):
    left, right, descriptors = key
    return {
        "lhs": int(lhs),
        "left": int(left),
        "right": int(right),
        "depth": int(depth),
        "internal": [
            {"label": label, "pLeft": pleft, "pRight": pright}
            for label, pleft, pright in descriptors
        ],
        "distinctSourceSupport": int(support),
        "selectedOccurrences": int(occurrences),
        "gainBits": int(gain),
        "candidateHash": key_hash(key),
    }


def key_from_rule(rule):
    descriptors = tuple(sorted((item["label"], item["pLeft"], item["pRight"]) for item in rule["internal"]))
    return (int(rule["left"]), int(rule["right"]), descriptors)


def candidate_delta_bits(graphs, rules, key, selected, per_graph_incident):
    new_symbol = TERMINAL_COUNT + len(rules)
    temp_rule = rule_from_key(key, new_symbol, 0)
    model_delta = grammar_bits(rules + [temp_rule]) - grammar_bits(rules)
    graph_delta = 0
    selected_by_graph = defaultdict(list)
    for gi, occurrence in selected:
        selected_by_graph[gi].append(occurrence)
    for gi, occurrences in selected_by_graph.items():
        graph = graphs[gi]
        incident = per_graph_incident[gi]
        old_n = len(graph["nodes"])
        old_m = len(graph["edges"])
        local_delta = 0
        internal_indices_all = set()
        selected_nodes = {}
        for occurrence in occurrences:
            left, right = occurrence["left"], occurrence["right"]
            local_delta += symbol_bits(new_symbol) - symbol_bits(graph["nodes"][left]) - symbol_bits(graph["nodes"][right])
            selected_nodes[left] = "0"
            selected_nodes[right] = "1"
            internal_indices_all.update(occurrence["indices"])
        removed_edges = len(internal_indices_all)
        for edge_index in internal_indices_all:
            local_delta -= edge_bits(graph["edges"][edge_index])
        for node, prefix in selected_nodes.items():
            for edge_index in incident.get(node, ()):
                if edge_index in internal_indices_all:
                    continue
                edge = graph["edges"][edge_index]
                old_path = endpoint_port(edge, node)
                local_delta += port_bits(prefix + old_path) - port_bits(old_path)
        new_n = old_n - len(occurrences)
        new_m = old_m - removed_edges
        local_delta += count_bits(new_n) + count_bits(new_m) - count_bits(old_n) - count_bits(old_m)
        graph_delta += local_delta
    return model_delta + graph_delta


def contract_pair(graph, occurrence, rule):
    left, right = occurrence["left"], occurrence["right"]
    if left not in graph["nodes"] or right not in graph["nodes"]:
        raise RuntimeError("contraction endpoint disappeared")
    current_indices = [
        i for i, edge in enumerate(graph["edges"])
        if {edge["u"], edge["v"]} == {left, right}
    ]
    if not current_indices:
        raise RuntimeError("contraction lost internal edge bundle")
    check_left, check_right, _, current_key = oriented_bundle(graph, left, right, current_indices)
    expected_key = key_from_rule(rule)
    if current_key != expected_key:
        raise RuntimeError(f"rule mismatch expected={key_hash(expected_key)} got={key_hash(current_key)}")
    left, right = check_left, check_right
    new_node = graph["nextNode"]
    graph["nextNode"] += 1
    new_edges = []
    for edge in graph["edges"]:
        u, v = edge["u"], edge["v"]
        if {u, v} == {left, right}:
            continue
        out = dict(edge)
        if out["u"] == left:
            out["u"] = new_node
            out["pu"] = "0" + out["pu"]
        elif out["u"] == right:
            out["u"] = new_node
            out["pu"] = "1" + out["pu"]
        if out["v"] == left:
            out["v"] = new_node
            out["pv"] = "0" + out["pv"]
        elif out["v"] == right:
            out["v"] = new_node
            out["pv"] = "1" + out["pv"]
        if out["u"] == out["v"]:
            raise RuntimeError("unexpected residual self-edge after complete-bundle contraction")
        new_edges.append(out)
    graph["edges"] = new_edges
    graph["nodes"].pop(left)
    graph["nodes"].pop(right)
    graph["nodes"][new_node] = int(rule["lhs"])
    if "members" in graph:
        members = graph["members"].pop(left) + graph["members"].pop(right)
        graph["members"][new_node] = members
        for event_id in members:
            graph["ancestry"][event_id].append(int(rule["lhs"]))
    return new_node


def apply_selected(graphs, selected, rule):
    by_graph = defaultdict(list)
    for gi, occurrence in selected:
        by_graph[gi].append(occurrence)
    uses = 0
    for gi in sorted(by_graph):
        graph = graphs[gi]
        for occurrence in sorted(by_graph[gi], key=lambda x: x["sortKey"]):
            contract_pair(graph, occurrence, rule)
            uses += 1
    return uses


def induce_grammar(graphs, cfg, allow_nonterminals):
    rules = []
    symbol_depth = {i: 0 for i in range(TERMINAL_COUNT)}
    raw_bits = sum(graph_bits(graph) for graph in graphs)
    start_total = grammar_bits([]) + raw_bits
    max_rules = int(cfg["maxRules"])
    max_depth = int(cfg["maxDerivationDepth"])
    min_sources = int(cfg["minimumDistinctSourceGroups"])
    min_occ = int(cfg["minimumNonoverlappingOccurrences"])
    shortlist_n = int(cfg["candidateShortlist"])
    trace = []
    for iteration in range(max_rules):
        records, per_graph_incident = enumerate_corpus_candidates(graphs, allow_nonterminals, symbol_depth)
        candidates = [
            (key, record) for key, record in records.items()
            if len(record["sources"]) >= min_sources and record["depth"] <= max_depth
        ]
        candidates.sort(key=lambda item: (-len(item[1]["sources"]), -len(item[1]["occurrences"]), key_hash(item[0])))
        candidates = candidates[:shortlist_n]
        scored = []
        for key, record in candidates:
            selected = select_nonoverlap(record)
            if len(selected) < min_occ:
                continue
            delta = candidate_delta_bits(graphs, rules, key, selected, per_graph_incident)
            gain = -delta
            if gain <= 0:
                continue
            scored.append((gain, len(record["sources"]), len(selected), key_hash(key), key, record, selected))
        if not scored:
            trace.append({"iteration": iteration, "stop": "no_positive_supported_candidate"})
            break
        scored.sort(key=lambda row: (-row[0], -row[1], -row[2], row[3]))
        gain, support, selected_count, _, key, record, selected = scored[0]
        lhs = TERMINAL_COUNT + len(rules)
        rule = rule_from_key(key, lhs, record["depth"], support, selected_count, gain)
        uses = apply_selected(graphs, selected, rule)
        if uses != selected_count:
            raise RuntimeError("selected occurrence application drift")
        rules.append(rule)
        symbol_depth[lhs] = int(rule["depth"])
        current_data = sum(graph_bits(graph) for graph in graphs)
        current_total = grammar_bits(rules) + current_data
        trace.append({
            "iteration": iteration,
            "lhs": lhs,
            "depth": rule["depth"],
            "candidateHash": rule["candidateHash"],
            "gainBits": gain,
            "distinctSourceSupport": support,
            "selectedOccurrences": selected_count,
            "rules": len(rules),
            "dataBits": current_data,
            "modelBits": grammar_bits(rules),
            "totalBits": current_total,
        })
    final_data = sum(graph_bits(graph) for graph in graphs)
    final_model = grammar_bits(rules)
    return {
        "rules": rules,
        "rawDataBits": raw_bits,
        "initialTotalBits": start_total,
        "trainDataBits": final_data,
        "modelBits": final_model,
        "trainTotalBits": final_data + final_model,
        "trace": trace,
        "observationCount": len(graphs),
        "sourceGroupCount": len({g["sourceGroupId"] for g in graphs}),
    }


def find_rule_occurrences(graph, rule):
    target = key_from_rule(rule)
    occurrences, _ = index_graph(graph)
    matches = [occ for occ in occurrences if occ["key"] == target]
    used = set()
    selected = []
    for occurrence in sorted(matches, key=lambda x: x["sortKey"]):
        if occurrence["u"] in used or occurrence["v"] in used:
            continue
        used.add(occurrence["u"])
        used.add(occurrence["v"])
        selected.append(occurrence)
    return selected


def apply_grammar(graph, grammar, track_members=False):
    uses = Counter()
    for rule in grammar["rules"]:
        selected = find_rule_occurrences(graph, rule)
        for occurrence in selected:
            contract_pair(graph, occurrence, rule)
            uses[int(rule["lhs"])] += 1
    return {
        "dataBits": graph_bits(graph),
        "ruleUses": dict(sorted(uses.items())),
        "residualNodes": len(graph["nodes"]),
        "residualEdges": len(graph["edges"]),
        "ancestry": graph.get("ancestry") if track_members else None,
    }


def serialize_grammar(model):
    return {
        "terminalLabels": TERMINAL_LABELS,
        "rules": model["rules"],
        "rawDataBits": model["rawDataBits"],
        "trainDataBits": model["trainDataBits"],
        "modelBits": model["modelBits"],
        "trainTotalBits": model["trainTotalBits"],
        "observationCount": model["observationCount"],
        "sourceGroupCount": model["sourceGroupCount"],
        "trace": model["trace"],
    }


def levenshtein_normalized(a, b):
    a = list(a)
    b = list(b)
    if not a and not b:
        return 0.0
    prev = list(range(len(b) + 1))
    for i, xa in enumerate(a, 1):
        cur = [i]
        for j, xb in enumerate(b, 1):
            cur.append(min(cur[-1] + 1, prev[j] + 1, prev[j - 1] + (0 if xa == xb else 1)))
        prev = cur
    return prev[-1] / max(1, len(a), len(b))


def auc_smaller(pos, neg):
    if not pos or not neg:
        return None
    score = 0.0
    total = 0
    for p in pos:
        for n in neg:
            total += 1
            if p < n:
                score += 1.0
            elif p == n:
                score += 0.5
    return 2.0 * (score / total) - 1.0


def balanced_effect(rows, feature, label_override=None):
    by_family = defaultdict(lambda: {"preserved": [], "broken": []})
    for row in rows:
        value = row.get(feature)
        if value is None:
            continue
        label = label_override.get(row["pairId"], row["label"]) if label_override else row["label"]
        by_family[(row["occupantFamilyA"], row["occupantFamilyB"])][label].append(float(value))
    effects = []
    details = []
    for (fa, fb), labels in sorted(by_family.items()):
        effect = auc_smaller(labels["preserved"], labels["broken"])
        if effect is None:
            continue
        effects.append(effect)
        details.append({
            "occupantFamilyA": fa,
            "occupantFamilyB": fb,
            "effect": effect,
            "preservedPairs": len(labels["preserved"]),
            "brokenPairs": len(labels["broken"]),
        })
    return {
        "balancedEffect": statistics.mean(effects) if effects else None,
        "supportedFamilies": len(effects),
        "pairsWithValue": sum(row.get(feature) is not None for row in rows),
        "familyEffects": details,
    }


def shuffled_labels(rows, iteration, salt="hier-compression-v8-null"):
    by_family = defaultdict(list)
    for row in rows:
        by_family[(row["occupantFamilyA"], row["occupantFamilyB"])].append(row)
    override = {}
    for (fa, fb), family_rows in sorted(by_family.items()):
        preserved = sum(row["label"] == "preserved" for row in family_rows)
        ordered = sorted(
            family_rows,
            key=lambda row: (
                hashlib.sha256(f"{salt}|{iteration}|{fa}|{fb}|{row['pairId']}".encode()).hexdigest(),
                row["pairId"],
            ),
        )
        for index, row in enumerate(ordered):
            override[row["pairId"]] = "preserved" if index < preserved else "broken"
    return override


def add_null(result, rows, feature, iterations):
    observed = result["balancedEffect"]
    if observed is None:
        result["null"] = None
        return
    values = []
    for iteration in range(int(iterations)):
        effect = balanced_effect(rows, feature, shuffled_labels(rows, iteration))["balancedEffect"]
        if effect is not None:
            values.append(effect)
    result["null"] = None if not values else {
        "iterationsRequested": int(iterations),
        "iterationsWithSupport": len(values),
        "mean": statistics.mean(values),
        "min": min(values),
        "max": max(values),
        "absoluteNullAtLeastObserved": sum(abs(x) >= abs(observed) for x in values),
        "nullAtLeastObserved": sum(x >= observed for x in values),
        "nullAtMostObserved": sum(x <= observed for x in values),
    }


def expand_symbol(symbol, rule_by_lhs):
    if symbol < TERMINAL_COUNT:
        return {"": symbol}, []
    rule = rule_by_lhs[int(symbol)]
    left_nodes, left_edges = expand_symbol(int(rule["left"]), rule_by_lhs)
    right_nodes, right_edges = expand_symbol(int(rule["right"]), rule_by_lhs)
    nodes = {"0" + path: sym for path, sym in left_nodes.items()}
    nodes.update({"1" + path: sym for path, sym in right_nodes.items()})
    edges = [
        ("0" + a, "0" + b, label) for a, b, label in left_edges
    ] + [
        ("1" + a, "1" + b, label) for a, b, label in right_edges
    ]
    for item in rule["internal"]:
        a = "0" + item["pLeft"]
        b = "1" + item["pRight"]
        if a not in nodes or b not in nodes:
            raise RuntimeError("rule port path does not land on a terminal leaf")
        edges.append((a, b, item["label"]))
    return nodes, edges


def expand_state(graph, rules):
    rule_by_lhs = {int(rule["lhs"]): rule for rule in rules}
    node_maps = {}
    nodes = {}
    edges = []
    for top_index, node_id in enumerate(sorted(graph["nodes"])):
        prefix = f"T{top_index}:"
        local_nodes, local_edges = expand_symbol(int(graph["nodes"][node_id]), rule_by_lhs)
        node_maps[node_id] = {path: prefix + path for path in local_nodes}
        for path, sym in local_nodes.items():
            nodes[prefix + path] = sym
        for a, b, label in local_edges:
            edges.append((prefix + a, prefix + b, label))
    for edge in graph["edges"]:
        a = node_maps[edge["u"]][edge["pu"]]
        b = node_maps[edge["v"]][edge["pv"]]
        edges.append((a, b, edge["label"]))
    return nodes, edges


def nx_graph(nodes, edges):
    import networkx as nx
    graph = nx.Graph()
    for node, symbol in nodes.items():
        graph.add_node(node, symbol=int(symbol))
    for a, b, label in edges:
        graph.add_edge(a, b, label=label)
    return graph


def assert_isomorphic_primitive(original, contracted, rules):
    import networkx as nx
    original_nodes = {str(node): symbol for node, symbol in original["nodes"].items()}
    original_edges = [(str(edge["u"]), str(edge["v"]), edge["label"]) for edge in original["edges"]]
    expanded_nodes, expanded_edges = expand_state(contracted, rules)
    g1 = nx_graph(original_nodes, original_edges)
    g2 = nx_graph(expanded_nodes, expanded_edges)
    node_match = nx.algorithms.isomorphism.categorical_node_match("symbol", None)
    edge_match = nx.algorithms.isomorphism.categorical_edge_match("label", None)
    if not nx.is_isomorphic(g1, g2, node_match=node_match, edge_match=edge_match):
        raise RuntimeError("lossless contraction round-trip failed")


def synthetic_roundtrip_tests():
    graph = {
        "observationId": "synthetic",
        "sourceGroupId": "synthetic",
        "lane": "train",
        "nodes": {0: 0, 1: 0, 2: 1, 3: 2},
        "edges": [
            {"u": 0, "v": 1, "label": "L0|M1", "pu": "", "pv": ""},
            {"u": 0, "v": 1, "label": "L1|M1", "pu": "", "pv": ""},
            {"u": 1, "v": 2, "label": "L0|M2", "pu": "", "pv": ""},
            {"u": 0, "v": 3, "label": "L2|M1", "pu": "", "pv": ""},
            {"u": 2, "v": 3, "label": "L0|M1", "pu": "", "pv": ""},
        ],
        "nextNode": 4,
    }
    original = clone_graph(graph)
    occs, _ = index_graph(graph)
    first = next(occ for occ in occs if {occ["u"], occ["v"]} == {0, 1})
    rule1 = rule_from_key(first["key"], TERMINAL_COUNT, 1)
    contract_pair(graph, first, rule1)
    assert_isomorphic_primitive(original, graph, [rule1])
    occs, _ = index_graph(graph)
    nested = next(occ for occ in occs if TERMINAL_COUNT in (graph["nodes"][occ["u"]], graph["nodes"][occ["v"]]))
    rule2 = rule_from_key(nested["key"], TERMINAL_COUNT + 1, 2)
    contract_pair(graph, nested, rule2)
    assert_isomorphic_primitive(original, graph, [rule1, rule2])
    return True
