#!/usr/bin/env python3
import hashlib
import json
import math
from collections import Counter, defaultdict


def canonical_json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def canonical_sha(value):
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def degree_class(value, cap):
    value = int(value)
    return f"{cap}+" if value >= cap else str(value)


def multiplicity_class(value, cap):
    value = int(value)
    return f"{cap}+" if value >= cap else str(value)


def node_class(center, cfg):
    return f"{center['kind']}|D{degree_class(center['degree'], int(cfg['degreeCap']))}"


def length_bin(value, width):
    return int(math.floor(max(0.0, float(value)) / float(width) + 1e-12))


def build_graph(row, cfg, variant):
    centers = {c["eventId"]: c for c in row["centers"]}
    grouped = defaultdict(list)
    self_loops = Counter()
    for edge in row["edges"]:
        a, b = edge["a"], edge["b"]
        if edge.get("selfLoop") or a == b:
            if a in centers:
                self_loops[a] += 1
            continue
        if a not in centers or b not in centers:
            continue
        grouped[tuple(sorted((a, b)))].append(edge)
    diagonal = math.hypot(float(row["region"]["width"]), float(row["region"]["height"]))
    adjacency = defaultdict(dict)
    edge_labels = {}
    for (a, b), edges in grouped.items():
        mult = multiplicity_class(len(edges), int(cfg["multiplicityCap"]))
        label = f"M{mult}"
        if variant == "lengthAware":
            mean_steps = sum(float(e["pathSteps"]) for e in edges) / len(edges)
            normalized = mean_steps / max(1.0, diagonal)
            label += f"|L{length_bin(normalized, float(cfg['normalizedLengthBinWidth']))}"
        elif variant != "topology":
            raise RuntimeError(f"unknown variant {variant}")
        adjacency[a][b] = label
        adjacency[b][a] = label
        edge_labels[(a, b)] = label
    classes = {event_id: node_class(center, cfg) for event_id, center in centers.items()}
    return {
        "observationId": row["observationId"],
        "sourceGroupId": row["sourceGroupId"],
        "lane": row["lane"],
        "centers": centers,
        "classes": classes,
        "adjacency": adjacency,
        "selfLoops": self_loops,
        "edgeLabels": edge_labels,
        "stateCache": {},
        "operatorCache": {},
    }


def state_token(graph, origin, destination):
    key = (origin, destination)
    cached = graph["stateCache"].get(key)
    if cached is not None:
        return cached
    edge = graph["adjacency"][origin][destination]
    token = f"{edge}|FROM:{graph['classes'][origin]}|TO:{graph['classes'][destination]}"
    graph["stateCache"][key] = token
    return token


def operator_descriptor(graph, incoming_neighbor, center, outgoing_neighbor, cfg):
    side = []
    for neighbor, edge in graph["adjacency"].get(center, {}).items():
        if neighbor in (incoming_neighbor, outgoing_neighbor):
            continue
        side.append({"edge": edge, "neighbor": graph["classes"][neighbor]})
    side.sort(key=canonical_json)
    return {
        "center": graph["classes"][center],
        "inPortNeighbor": graph["classes"][incoming_neighbor],
        "outPortNeighbor": graph["classes"][outgoing_neighbor],
        "selfLoops": multiplicity_class(graph["selfLoops"].get(center, 0), int(cfg["multiplicityCap"])),
        "sideBranches": side,
    }


def operator_id_from_descriptor(descriptor):
    return "OP" + canonical_sha(descriptor)[:24]


def reverse_operator_descriptor(descriptor):
    return {
        "center": descriptor["center"],
        "inPortNeighbor": descriptor["outPortNeighbor"],
        "outPortNeighbor": descriptor["inPortNeighbor"],
        "selfLoops": descriptor["selfLoops"],
        "sideBranches": descriptor["sideBranches"],
    }


def operator_occurrence(graph, incoming_neighbor, center, outgoing_neighbor, cfg):
    key = (incoming_neighbor, center, outgoing_neighbor)
    cached = graph["operatorCache"].get(key)
    if cached is not None:
        return cached
    desc = operator_descriptor(graph, incoming_neighbor, center, outgoing_neighbor, cfg)
    result = {
        "operatorId": operator_id_from_descriptor(desc),
        "reverseOperatorId": operator_id_from_descriptor(reverse_operator_descriptor(desc)),
        "descriptor": desc,
        "inputState": state_token(graph, incoming_neighbor, center),
        "outputState": state_token(graph, center, outgoing_neighbor),
    }
    graph["operatorCache"][key] = result
    return result


def iter_transitions(graph, cfg):
    for center in sorted(graph["adjacency"]):
        neighbors = sorted(graph["adjacency"][center])
        for incoming in neighbors:
            for outgoing in neighbors:
                if incoming == outgoing:
                    continue
                yield operator_occurrence(graph, incoming, center, outgoing, cfg)


def iter_compositions(graph, cfg):
    # Every oriented simple four-center path u-v-w-x appears once for that orientation.
    for v in sorted(graph["adjacency"]):
        for u in sorted(graph["adjacency"][v]):
            for w in sorted(graph["adjacency"][v]):
                if u == w:
                    continue
                A = operator_occurrence(graph, u, v, w, cfg)
                for x in sorted(graph["adjacency"].get(w, {})):
                    if x in (u, v, w):
                        continue
                    B = operator_occurrence(graph, v, w, x, cfg)
                    yield {
                        "operatorA": A["operatorId"],
                        "operatorB": B["operatorId"],
                        "state0": A["inputState"],
                        "state1": A["outputState"],
                        "state2": B["outputState"],
                    }


def map_state(state, common_states):
    return state if state in common_states else "OTHER"


def nested_counts_to_rows(counts, key_names):
    rows = []
    for key, count in counts.items():
        if not isinstance(key, tuple):
            key = (key,)
        row = {name: value for name, value in zip(key_names, key)}
        row["count"] = int(count)
        rows.append(row)
    rows.sort(key=lambda row: tuple(str(row[name]) for name in key_names))
    return rows


def rows_to_counts(rows, key_names):
    return Counter({tuple(row[name] for name in key_names): int(row["count"]) for row in rows})


def build_probability_functions(model_variant):
    states = list(model_variant["states"])
    state_set = set(states)
    alpha = float(model_variant["smoothing"]["globalAdditiveAlpha"])
    op_lambda = float(model_variant["smoothing"]["operatorBackoffPseudoCount"])
    pair_lambda = float(model_variant["smoothing"]["baselineBackoffPseudoCount"])
    base1 = rows_to_counts(model_variant["counts"]["baseOneStep"], ("inputState", "outputState"))
    base2 = rows_to_counts(model_variant["counts"]["baseTwoStep"], ("inputState", "outputState"))
    op_counts = rows_to_counts(model_variant["counts"]["operatorOneStep"], ("operatorId", "inputState", "outputState"))
    a2 = rows_to_counts(model_variant["counts"]["firstOperatorTwoStep"], ("operatorId", "inputState", "outputState"))
    b2 = rows_to_counts(model_variant["counts"]["secondOperatorTwoStep"], ("operatorId", "inputState", "outputState"))
    pair2 = rows_to_counts(model_variant["counts"]["directPairTwoStep"], ("operatorA", "operatorB", "inputState", "outputState"))

    base1_totals = Counter()
    base2_totals = Counter()
    op_totals = Counter()
    a2_totals = Counter()
    b2_totals = Counter()
    pair2_totals = Counter()
    for (i, o), count in base1.items(): base1_totals[i] += count
    for (i, o), count in base2.items(): base2_totals[i] += count
    for (a, i, o), count in op_counts.items(): op_totals[(a, i)] += count
    for (a, i, o), count in a2.items(): a2_totals[(a, i)] += count
    for (b, i, o), count in b2.items(): b2_totals[(b, i)] += count
    for (a, b, i, o), count in pair2.items(): pair2_totals[(a, b, i)] += count

    nstates = max(1, len(states))

    def p1(i, o):
        if i not in state_set: i = "OTHER"
        if o not in state_set: o = "OTHER"
        return (base1[(i, o)] + alpha) / (base1_totals[i] + alpha * nstates)

    def p2(i, o):
        if i not in state_set: i = "OTHER"
        if o not in state_set: o = "OTHER"
        return (base2[(i, o)] + alpha) / (base2_totals[i] + alpha * nstates)

    def pop(a, i, o):
        if i not in state_set: i = "OTHER"
        if o not in state_set: o = "OTHER"
        total = op_totals[(a, i)]
        back = p1(i, o)
        return (op_counts[(a, i, o)] + op_lambda * back) / (total + op_lambda) if total else back

    comp_cache = {}
    def pcomp(a, b, i, o):
        if i not in state_set: i = "OTHER"
        if o not in state_set: o = "OTHER"
        key = (a, b, i, o)
        if key not in comp_cache:
            comp_cache[key] = sum(pop(a, i, middle) * pop(b, middle, o) for middle in states)
        return comp_cache[key]

    def pone(tab, totals, op, i, o, back):
        if i not in state_set: i = "OTHER"
        if o not in state_set: o = "OTHER"
        total = totals[(op, i)]
        return (tab[(op, i, o)] + pair_lambda * back) / (total + pair_lambda) if total else back

    def pa2(a, i, o):
        return pone(a2, a2_totals, a, i, o, p2(i, o))

    def pb2(b, i, o):
        return pone(b2, b2_totals, b, i, o, p2(i, o))

    def ppair(a, b, i, o):
        if i not in state_set: i = "OTHER"
        if o not in state_set: o = "OTHER"
        total = pair2_totals[(a, b, i)]
        back = pcomp(a, b, i, o)
        return (pair2[(a, b, i, o)] + pair_lambda * back) / (total + pair_lambda) if total else back

    return {
        "states": states,
        "p1": p1,
        "p2": p2,
        "pop": pop,
        "pcomp": pcomp,
        "pa2": pa2,
        "pb2": pb2,
        "ppair": ppair,
    }


def weighted_tv(prob_a, prob_b, states, input_weights):
    total_weight = sum(input_weights.values())
    if total_weight <= 0:
        return None
    total = 0.0
    for state_in, weight in input_weights.items():
        tv = 0.5 * sum(abs(prob_a(state_in, out) - prob_b(state_in, out)) for out in states)
        total += weight * tv
    return total / total_weight


def safe_log2_probability(value):
    return -math.log2(max(float(value), 1e-300))
