#!/usr/bin/env python3
import networkx as nx

from mark_graph_compression_v8_core import (
    TERMINAL_COUNT,
    clone_graph,
    contract_pair,
    expand_state,
    index_graph,
    rule_from_key,
)


def to_multigraph(nodes, edges):
    graph = nx.MultiGraph()
    for node, symbol in nodes.items():
        graph.add_node(str(node), symbol=int(symbol))
    for index, edge in enumerate(edges):
        if isinstance(edge, dict):
            a, b, label = str(edge["u"]), str(edge["v"]), edge["label"]
        else:
            a, b, label = str(edge[0]), str(edge[1]), edge[2]
        graph.add_edge(a, b, key=index, label=label)
    return graph


def assert_multigraph_roundtrip(original, contracted, rules):
    expanded_nodes, expanded_edges = expand_state(contracted, rules)
    left = to_multigraph(original["nodes"], original["edges"])
    right = to_multigraph(expanded_nodes, expanded_edges)
    node_match = nx.algorithms.isomorphism.categorical_node_match("symbol", None)
    edge_match = nx.algorithms.isomorphism.categorical_multiedge_match("label", None)
    if not nx.is_isomorphic(left, right, node_match=node_match, edge_match=edge_match):
        raise AssertionError("lossless multigraph round-trip failed")
    left_labels = sorted(data["label"] for _, _, _, data in left.edges(keys=True, data=True))
    right_labels = sorted(data["label"] for _, _, _, data in right.edges(keys=True, data=True))
    if left_labels != right_labels:
        raise AssertionError("parallel-edge label multiset changed during round-trip")
    if left.number_of_edges() != right.number_of_edges():
        raise AssertionError("parallel-edge multiplicity changed during round-trip")


def main():
    graph = {
        "observationId": "synthetic-multigraph",
        "sourceGroupId": "synthetic",
        "lane": "train",
        "nodes": {0: 0, 1: 0, 2: 1, 3: 2, 4: 3},
        "edges": [
            {"u": 0, "v": 1, "label": "L0|M1", "pu": "", "pv": ""},
            {"u": 0, "v": 1, "label": "L1|M1", "pu": "", "pv": ""},
            {"u": 1, "v": 2, "label": "L0|M2", "pu": "", "pv": ""},
            {"u": 0, "v": 3, "label": "L2|M1", "pu": "", "pv": ""},
            {"u": 2, "v": 3, "label": "L0|M1", "pu": "", "pv": ""},
            {"u": 2, "v": 4, "label": "L3|M3+", "pu": "", "pv": ""},
            {"u": 3, "v": 4, "label": "L1|M1", "pu": "", "pv": ""},
        ],
        "nextNode": 5,
    }
    original = clone_graph(graph)

    occurrences, _ = index_graph(graph)
    first = next(occ for occ in occurrences if {occ["u"], occ["v"]} == {0, 1})
    rule1 = rule_from_key(first["key"], TERMINAL_COUNT, 1)
    contract_pair(graph, first, rule1)
    assert_multigraph_roundtrip(original, graph, [rule1])

    occurrences, _ = index_graph(graph)
    nested = next(
        occ for occ in occurrences
        if TERMINAL_COUNT in (graph["nodes"][occ["u"]], graph["nodes"][occ["v"]])
    )
    rule2 = rule_from_key(nested["key"], TERMINAL_COUNT + 1, 2)
    contract_pair(graph, nested, rule2)
    assert_multigraph_roundtrip(original, graph, [rule1, rule2])

    occurrences, _ = index_graph(graph)
    nested2 = next(
        occ for occ in occurrences
        if TERMINAL_COUNT + 1 in (graph["nodes"][occ["u"]], graph["nodes"][occ["v"]])
    )
    rule3 = rule_from_key(nested2["key"], TERMINAL_COUNT + 2, 3)
    contract_pair(graph, nested2, rule3)
    assert_multigraph_roundtrip(original, graph, [rule1, rule2, rule3])

    print("multigraph_parallel_nested_roundtrip=passed")


if __name__ == "__main__":
    main()
