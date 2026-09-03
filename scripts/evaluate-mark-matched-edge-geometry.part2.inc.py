
    return {
        "pairId": f"{pair['observationA']}::{pair['observationB']}",
        "lane": pair["lane"],
        "label": pair["label"],
        "occupantFamilyA": pair["occupantFamilyA"],
        "occupantFamilyB": pair["occupantFamilyB"],
        "bestD4Transform": best,
        "mappedCenters": len(mapping),
        "v5Metrics": {
            "preservedEdgeMeanTurnRateMutation": mean(v5_turn),
            "preservedEdgeMeanTortuosityMutation": mean(v5_tort),
        },
        "matchedCells": cells,
        "matchedEdgeBuckets": sum(cell["edgeBucketCount"] for cell in cells),
    }


def aggregate_pair_key(rows, feature):
    cells = []
    raw_units = 0
    for row in rows:
        for cell in row["matchedCells"]:
            value = cell.get(feature)
            if value is None:
                continue
            count = int(cell["edgeBucketCount"])
            raw_units += count
            cells.append({
                "pairId": row["pairId"],
                "structuralKey": cell["structuralKey"],
                "value": float(value),
                "unitCount": count,
                "lane": row["lane"],
                "label": row["label"],
                "occupantFamilyA": row["occupantFamilyA"],
                "occupantFamilyB": row["occupantFamilyB"],
            })
    return cells, raw_units


def conditioned_effect(rows, feature, minimum_pairs_per_label, label_override=None):
    cells, raw_units = aggregate_pair_key(rows, feature)
    by_stratum = defaultdict(lambda: {"preserved": [], "broken": []})
    for cell in cells:
        label = label_override.get(cell["pairId"], cell["label"]) if label_override else cell["label"]
        family = (cell["occupantFamilyA"], cell["occupantFamilyB"])
        by_stratum[(family, cell["structuralKey"])][label].append(cell)

    family_effects = defaultdict(list)
    supported_strata = 0
    supported_pairs = set()
    supported_cells = 0
    supported_units = 0
    for (family, key), labels in sorted(by_stratum.items()):
        preserved = labels["preserved"]
        broken = labels["broken"]
        if len(preserved) < minimum_pairs_per_label or len(broken) < minimum_pairs_per_label:
            continue
        effect = auc_smaller([x["value"] for x in preserved], [x["value"] for x in broken])
        if effect is None:
            continue
        family_effects[family].append(effect)
        supported_cells += len(preserved) + len(broken)
        supported_units += sum(x["unitCount"] for x in preserved) + sum(x["unitCount"] for x in broken)
        supported_pairs.update(x["pairId"] for x in preserved)
        supported_pairs.update(x["pairId"] for x in broken)
        supported_strata += 1

    family_summary = []
    for family, effects in sorted(family_effects.items()):
        family_summary.append({
            "occupantFamilyA": family[0],
            "occupantFamilyB": family[1],
            "effect": statistics.mean(effects),
            "supportedStructuralStrata": len(effects),
        })
    overall = statistics.mean(x["effect"] for x in family_summary) if family_summary else None
    return {
        "balancedEffect": overall,
        "supportedFamilies": len(family_summary),
        "supportedStructuralStrata": supported_strata,
        "supportedPairs": len(supported_pairs),
        "supportedPairKeyCells": supported_cells,
        "supportedEdgeBuckets": supported_units,
        "allEdgeBuckets": raw_units,
        "edgeBucketSupportFraction": supported_units / max(1, raw_units),
        "familyEffects": family_summary,
    }


def shuffled_labels(rows, iteration):
    by_family = defaultdict(list)
    for row in rows:
        by_family[(row["occupantFamilyA"], row["occupantFamilyB"])].append(row)
    override = {}
    for (family_a, family_b), family_rows in sorted(by_family.items()):
        preserved_count = sum(row["label"] == "preserved" for row in family_rows)
        ordered = sorted(
            family_rows,
            key=lambda row: (
                hashlib.sha256(
                    f"matched-edge-v6-null|{iteration}|{family_a}|{family_b}|{row['pairId']}".encode()
                ).hexdigest(),
                row["pairId"],
            ),
        )
        for index, row in enumerate(ordered):
            override[row["pairId"]] = "preserved" if index < preserved_count else "broken"
    return override


def add_null(result, rows, feature, minimum_pairs_per_label, iterations):
    observed = result["balancedEffect"]
    if observed is None:
        result["null"] = None
        return
    null_values = []
    for iteration in range(iterations):
        override = shuffled_labels(rows, iteration)
        null_result = conditioned_effect(rows, feature, minimum_pairs_per_label, override)
        value = null_result["balancedEffect"]
        if value is not None:
            null_values.append(value)
    if not null_values:
        result["null"] = None
        return
    result["null"] = {
        "iterationsRequested": iterations,
        "iterationsWithSupport": len(null_values),
        "mean": statistics.mean(null_values),
        "min": min(null_values),
        "max": max(null_values),
        "absoluteNullAtLeastObserved": sum(abs(x) >= abs(observed) for x in null_values),
        "nullAtLeastObserved": sum(x >= observed for x in null_values),
        "nullAtMostObserved": sum(x <= observed for x in null_values),
    }


protocol = load_json(protocol_path)
if protocol.get("schema") != "mark_matched_edge_geometry_protocol_v6":
    raise RuntimeError("unexpected v6 protocol")
parent = protocol["parentV5"]
matching = protocol["matching"]
discovery = protocol["discovery"]

manifest = load_json(locate("edge-pair-manifest.json"))
world = load_json(locate("critical-edge-world.json"))
role_pair_path = locate("role-pair-labels.jsonl")
projector_path = locate("critical-edge-observations.jsonl")

manifest_sha = manifest.get("edgePairManifestSha256")
world_sha = world.get("criticalEdgeWorldSha256")
if canonical_sha({k: v for k, v in manifest.items() if k != "edgePairManifestSha256"}) != manifest_sha:
    raise RuntimeError("v5 edge pair manifest SHA mismatch")
if canonical_sha({k: v for k, v in world.items() if k != "criticalEdgeWorldSha256"}) != world_sha:
    raise RuntimeError("v5 critical edge world SHA mismatch")
if manifest_sha != parent["expectedEdgePairManifestSha256"]:
    raise RuntimeError("wrong parent v5 edge pair manifest")
if world_sha != parent["expectedCriticalEdgeWorldSha256"]:
    raise RuntimeError("wrong parent v5 critical edge world")
projector_bytes = projector_path.read_bytes()
if hashlib.sha256(projector_bytes).hexdigest() != world["projectorRowsSha256"]:
    raise RuntimeError("v5 projector rows SHA mismatch")
role_bytes = role_pair_path.read_bytes()
if hashlib.sha256(role_bytes).hexdigest() != manifest["parentRolePairRowsSha256"]:
    raise RuntimeError("v5 role pair rows SHA mismatch")

pairs = [json.loads(raw) for raw in role_bytes.splitlines() if raw.strip()]
eligible_obs = set(world["pairEligibleObservationIds"])
