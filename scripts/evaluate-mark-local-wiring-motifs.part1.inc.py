
def build_graph(row, motif_cfg):
    centers = {c["eventId"]: c for c in row["centers"]}
    diag = math.hypot(float(row["region"]["width"]), float(row["region"]["height"]))
    grouped = defaultdict(list)
    for edge in row["edges"]:
        grouped[tuple(sorted((edge["a"], edge["b"])))].append(edge)
    adjacency = defaultdict(set)
    edge_attrs = {}
    for key, edges in grouped.items():
        a, b = key
        if a not in centers or b not in centers:
            continue
        if a != b:
            adjacency[a].add(b)
            adjacency[b].add(a)
        mean_norm_length = statistics.mean(float(e["pathSteps"]) for e in edges) / max(1.0, diag)
        edge_attrs[key] = {
            "multiplicity": multiplicity_class(len(edges), int(motif_cfg["multiplicityCap"])),
            "lengthBin": length_bin(mean_norm_length, float(motif_cfg["normalizedLengthBinWidth"])),
        }
    return {
        "observationId": row["observationId"],
        "sourceGroupId": row["sourceGroupId"],
        "lane": row["lane"],
        "centers": centers,
        "adjacency": adjacency,
        "edgeAttrs": edge_attrs,
        "motifCache": {},
    }


def edge_label(attrs, variant):
    token = f"M{attrs['multiplicity']}"
    if variant == "lengthAware":
        token += f"|L{attrs['lengthBin']}"
    return token


def motif_signature(graph, root, radius, variant, motif_cfg):
    cache_key = (root, int(radius), variant)
    cached = graph["motifCache"].get(cache_key)
    if cached is not None:
        return cached
    centers = graph["centers"]
    if root not in centers:
        raise RuntimeError(f"unknown motif root {root}")
    radius = int(radius)
    depths = {root: 0}
    queue = deque([root])
    while queue:
        current = queue.popleft()
        depth = depths[current]
        if depth >= radius:
            continue
        for neighbor in sorted(graph["adjacency"].get(current, ())):
            if neighbor not in depths:
                depths[neighbor] = depth + 1
                queue.append(neighbor)
    nodes = set(depths)
    induced_edges = []
    for (a, b), attrs in graph["edgeAttrs"].items():
        if a in nodes and b in nodes:
            induced_edges.append((a, b, edge_label(attrs, variant)))
    induced_edges.sort(key=lambda x: (x[0], x[1], x[2]))

    degree_cap = int(motif_cfg["degreeCap"])
    base = {}
    for node in nodes:
        center = centers[node]
        base[node] = f"{'ROOT' if node == root else 'NODE'}|{center['kind']}|D{degree_class(center['degree'], degree_cap)}"
    labels = {node: short_hash(base[node]) for node in nodes}
    incident = defaultdict(list)
    for a, b, label in induced_edges:
        incident[a].append((b, label, a == b))
        if a != b:
            incident[b].append((a, label, False))
    for _ in range(radius + 2):
        nxt = {}
        for node in sorted(nodes):
            neighbors = []
            for other, elabel, self_loop in incident.get(node, ()):
                prefix = "LOOP" if self_loop else "EDGE"
                neighbors.append(f"{prefix}|{elabel}|{labels[other]}")
            neighbors.sort()
            nxt[node] = short_hash(f"{base[node]}||{labels[node]}||{'||'.join(neighbors)}")
        labels = nxt

    final_edge_tokens = []
    for a, b, elabel in induced_edges:
        endpoint_labels = sorted((labels[a], labels[b]))
        final_edge_tokens.append(f"{endpoint_labels[0]}|{elabel}|{endpoint_labels[1]}")
    strict_payload = (
        f"R{radius}|{variant}|ROOT:{labels[root]}|"
        f"N:{'|'.join(sorted(labels.values()))}|E:{'|'.join(sorted(final_edge_tokens))}"
    )
    fingerprint = hashlib.sha256(strict_payload.encode()).hexdigest()

    tokens = Counter()
    node_base_no_root = {}
    for node in nodes:
        center = centers[node]
        node_base_no_root[node] = f"{center['kind']}|D{degree_class(center['degree'], degree_cap)}"
        tokens[f"N|Z{depths[node]}|{'R' if node == root else 'N'}|{node_base_no_root[node]}"] += 1
    for a, b, elabel in induced_edges:
        da, db = depths[a], depths[b]
        left = f"Z{da}|{node_base_no_root[a]}"
        right = f"Z{db}|{node_base_no_root[b]}"
        if right < left:
            left, right = right, left
        loop = "LOOP" if a == b else "EDGE"
        tokens[f"E|{loop}|{left}|{elabel}|{right}"] += 1

    result = {
        "fingerprint": fingerprint,
        "tokens": tokens,
        "nodes": len(nodes),
        "edges": len(induced_edges),
    }
    graph["motifCache"][cache_key] = result
    return result


def multiset_jaccard_distance(a, b):
    keys = set(a) | set(b)
    if not keys:
        return 0.0
    intersection = sum(min(a.get(k, 0), b.get(k, 0)) for k in keys)
    union = sum(max(a.get(k, 0), b.get(k, 0)) for k in keys)
    return 0.0 if union == 0 else 1.0 - intersection / union


def pair_motif_metrics(pair, A, B, graph_a, graph_b, observables, motif_cfg, kcand):
    mapping, best = center_mapping(A, B, kcand)
    if not mapping:
        return None
    values = {item["id"]: [] for item in observables}
    motif_cache_a = {}
    motif_cache_b = {}
    for aid, bid in mapping.items():
        for item in observables:
            signature_key = (int(item["radius"]), item["variant"])
            ma = motif_cache_a.get((aid, signature_key))
            if ma is None:
                ma = motif_signature(graph_a, aid, signature_key[0], signature_key[1], motif_cfg)
                motif_cache_a[(aid, signature_key)] = ma
            mb = motif_cache_b.get((bid, signature_key))
            if mb is None:
                mb = motif_signature(graph_b, bid, signature_key[0], signature_key[1], motif_cfg)
                motif_cache_b[(bid, signature_key)] = mb
            if item["kind"] == "graded":
                values[item["id"]].append(multiset_jaccard_distance(ma["tokens"], mb["tokens"]))
            else:
                values[item["id"]].append(0.0 if ma["fingerprint"] == mb["fingerprint"] else 1.0)
    return {
        "pairId": f"{pair['observationA']}::{pair['observationB']}",
        "observationA": pair["observationA"],
        "observationB": pair["observationB"],
        "lane": pair["lane"],
        "label": pair["label"],
        "occupantFamilyA": pair["occupantFamilyA"],
        "occupantFamilyB": pair["occupantFamilyB"],
        "mappedRoots": len(mapping),
        "bestD4Transform": best,
        "motifMutation": {key: statistics.mean(xs) if xs else None for key, xs in values.items()},
    }


def auc_smaller(pos, neg):
    if not pos or not neg:
        return None
    score = 0.0
    total = 0
    for p in pos:
        for n in neg:
            total += 1
            if p < n: score += 1
            elif p == n: score += 0.5
    return 2 * (score / total) - 1


def balanced_effect(rows, feature, label_override=None):
    by_family = defaultdict(lambda: {"preserved": [], "broken": []})
    for row in rows:
        value = row["motifMutation"].get(feature)
        if value is None:
            continue
        label = label_override.get(row["pairId"], row["label"]) if label_override else row["label"]
        by_family[(row["occupantFamilyA"], row["occupantFamilyB"])][label].append(float(value))
    family_effects = []
    details = []
    for (a, b), labels in sorted(by_family.items()):
        effect = auc_smaller(labels["preserved"], labels["broken"])
        if effect is None:
            continue
        family_effects.append(effect)
        details.append({
            "occupantFamilyA": a,
            "occupantFamilyB": b,
            "effect": effect,
            "preservedPairs": len(labels["preserved"]),
            "brokenPairs": len(labels["broken"]),
        })
    return {
        "balancedEffect": statistics.mean(family_effects) if family_effects else None,
        "supportedFamilies": len(family_effects),
        "familyEffects": details,
        "pairsWithValue": sum(row["motifMutation"].get(feature) is not None for row in rows),
    }

