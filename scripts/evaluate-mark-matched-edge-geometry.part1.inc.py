
def mean(values):
    return statistics.mean(values) if values else None


def auc_smaller(pos, neg):
    if not pos or not neg:
        return None
    score = 0.0
    total = 0
    for p in pos:
        for n in neg:
            total += 1
            if p < n:
                score += 1
            elif p == n:
                score += 0.5
    return 2 * (score / total) - 1


def v5_balanced_effect(rows, feature):
    by = defaultdict(lambda: {"preserved": [], "broken": []})
    for row in rows:
        value = row["v5Metrics"].get(feature)
        if value is not None:
            by[(row["occupantFamilyA"], row["occupantFamilyB"])][row["label"]].append(float(value))
    effects = []
    for _, values in sorted(by.items()):
        effect = auc_smaller(values["preserved"], values["broken"])
        if effect is not None:
            effects.append(effect)
    return statistics.mean(effects) if effects else None


def quant_bin(value, width):
    if value is None or not math.isfinite(value):
        return "NA"
    return int(math.floor(max(0.0, value) / width + 1e-12))


def degree_cap(value, cap):
    value = int(value)
    return f"{cap}+" if value >= cap else str(value)


def multiplicity_class(count, cap):
    count = int(count)
    return f"{cap}+" if count >= cap else str(count)


def midpoint_cell(a_center_1, a_center_2, b_center_1, b_center_2, A, B, transform, grid):
    au1, av1 = normalized_point(a_center_1, A["region"], transform)
    au2, av2 = normalized_point(a_center_2, A["region"], transform)
    bu1, bv1 = normalized_point(b_center_1, B["region"], "IDENTITY")
    bu2, bv2 = normalized_point(b_center_2, B["region"], "IDENTITY")
    u = ((au1 + au2) / 2 + (bu1 + bu2) / 2) / 2
    v = ((av1 + av2) / 2 + (bv1 + bv2) / 2) / 2
    gx = max(0, min(grid - 1, int(math.floor(u * grid))))
    gy = max(0, min(grid - 1, int(math.floor(v * grid))))
    return f"{gx}:{gy}"


def pair_analysis(pair, A, B, matching, kcand):
    mapping, best = center_mapping(A, B, kcand)
    inverse = {b: a for a, b in mapping.items()}
    matched_a = set(mapping)
    matched_b = set(mapping.values())
    ba = buckets(A, matched_a, mapping)
    bb = buckets(B, matched_b, None)
    center_a = {c["eventId"]: c for c in A["centers"]}
    center_b = {c["eventId"]: c for c in B["centers"]}
    diag_a = math.hypot(float(A["region"]["width"]), float(A["region"]["height"]))
    diag_b = math.hypot(float(B["region"]["width"]), float(B["region"]["height"]))

    # Exact V5 geometry statistic reproduction, including its geometry-informed
    # parallel-path ordering. This is only a validation baseline; V6 does not
    # use this ordering in the matched analysis.
    v5_turn = []
    v5_tort = []
    for key in sorted(set(ba) & set(bb)):
        xa = sorted(ba[key], key=lambda e: (e["pathSteps"], e["tortuosity"], e["turnRate"], e["pathSha256"]))
        xb = sorted(bb[key], key=lambda e: (e["pathSteps"], e["tortuosity"], e["turnRate"], e["pathSha256"]))
        for edge_a, edge_b in zip(xa, xb):
            v5_tort.append(abs(float(edge_a["tortuosity"]) - float(edge_b["tortuosity"])))
            v5_turn.append(abs(float(edge_a["turnRate"]) - float(edge_b["turnRate"])))

    unit_acc = defaultdict(lambda: {
        "turn": [], "tort": [], "edgeBuckets": 0
    })
    for key in sorted(set(ba) & set(bb)):
        edges_a = ba[key]
        edges_b = bb[key]
        # Detailed shape is only comparable when the connection survived with
        # the same parallel-path multiplicity. Multiplicity mutation remains a
        # graph edit, not a path-shape observation.
        if len(edges_a) != len(edges_b):
            continue
        if not edges_a:
            continue
        b1, b2 = key
        a1, a2 = inverse.get(b1), inverse.get(b2)
        if a1 is None or a2 is None:
            continue
        ca1, ca2 = center_a[a1], center_a[a2]
        cb1, cb2 = center_b[b1], center_b[b2]

        endpoint_profile = sorted([
            (
                ca1["kind"],
                degree_cap(ca1["degree"], int(matching["degreeCap"])),
                degree_cap(cb1["degree"], int(matching["degreeCap"])),
            ),
            (
                ca2["kind"],
                degree_cap(ca2["degree"], int(matching["degreeCap"])),
                degree_cap(cb2["degree"], int(matching["degreeCap"])),
            ),
        ])

        chord_a = float(edges_a[0]["chordPixels"]) / max(1.0, diag_a)
        chord_b = float(edges_b[0]["chordPixels"]) / max(1.0, diag_b)
        path_a = statistics.mean(float(edge["pathSteps"]) for edge in edges_a) / max(1.0, diag_a)
        path_b = statistics.mean(float(edge["pathSteps"]) for edge in edges_b) / max(1.0, diag_b)
        span_mean = (chord_a + chord_b) / 2
        span_delta = abs(chord_a - chord_b)
        path_mean = (path_a + path_b) / 2
        path_delta = abs(path_a - path_b)
        graph_size = math.sqrt(max(1, int(A["centerCount"])) * max(1, int(B["centerCount"])))
        graph_size_bin = int(math.floor(math.log2(graph_size + 1)))
        position = midpoint_cell(
            ca1, ca2, cb1, cb2, A, B, best, int(matching["broadPositionGrid"])
        )
        multiplicity = multiplicity_class(len(edges_a), int(matching["multiplicityCap"]))
        self_loop = bool(edges_a[0].get("selfLoop")) or bool(edges_b[0].get("selfLoop"))

        structural_descriptor = [
            endpoint_profile,
            multiplicity,
            int(self_loop),
            quant_bin(span_mean, float(matching['normalizedSpanMeanBinWidth'])),
            quant_bin(span_delta, float(matching['normalizedSpanDeltaBinWidth'])),
            quant_bin(path_mean, float(matching['normalizedPathMeanBinWidth'])),
            quant_bin(path_delta, float(matching['normalizedPathDeltaBinWidth'])),
            position,
            graph_size_bin,
        ]
        structural_key = hashlib.sha256(
            json.dumps(structural_descriptor, separators=(",", ":"), sort_keys=False).encode()
        ).hexdigest()[:24]

        # No path is paired to another path by residual geometry in V6.
        # Parallel paths are represented by their within-bucket means.
        turn_a = statistics.mean(float(edge["turnRate"]) for edge in edges_a)
        turn_b = statistics.mean(float(edge["turnRate"]) for edge in edges_b)
        tort_a = statistics.mean(float(edge["tortuosity"]) for edge in edges_a)
        tort_b = statistics.mean(float(edge["tortuosity"]) for edge in edges_b)
        acc = unit_acc[structural_key]
        acc["turn"].append(abs(turn_a - turn_b))
        acc["tort"].append(abs(tort_a - tort_b))
        acc["edgeBuckets"] += 1

    cells = [
        {
            "structuralKey": key,
            "meanTurnRateMutation": statistics.mean(values["turn"]),
            "meanTortuosityMutation": statistics.mean(values["tort"]),
            "edgeBucketCount": values["edgeBuckets"],
        }
        for key, values in sorted(unit_acc.items())
    ]
