#!/usr/bin/env python3
import hashlib
import json
import math
import os
import statistics
from collections import Counter, defaultdict, deque
from pathlib import Path

from scipy.spatial import cKDTree

protocol_path = Path(os.environ.get(
    "MARK_MOTIF_PROTOCOL",
    "research/mark/discovery-experiments/local-wiring-motif-correspondence-v7.protocol.json",
))
v5_dir = Path(os.environ.get("MARK_V5_PACKET", "artifact-staging/v5"))
out_dir = Path(os.environ.get("MARK_MOTIF_OUT", "artifacts/mark-local-wiring-motif-correspondence-v7"))


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def canonical_sha(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()


def short_hash(text):
    return hashlib.sha256(text.encode()).hexdigest()[:24]


def locate(name):
    hits = list(v5_dir.rglob(name))
    if len(hits) != 1:
        raise RuntimeError(f"expected one v5 {name}, found {len(hits)}")
    return hits[0]


def transform_point(u, v, name):
    if name == "IDENTITY": return u, v
    if name == "ROT90": return 1 - v, u
    if name == "ROT180": return 1 - u, 1 - v
    if name == "ROT270": return v, 1 - u
    if name == "MIRROR_X": return 1 - u, v
    if name == "MIRROR_Y": return u, 1 - v
    if name == "MIRROR_DIAGONAL": return v, u
    if name == "MIRROR_ANTIDIAGONAL": return 1 - v, 1 - u
    raise RuntimeError(name)


TRANSFORMS = [
    "IDENTITY", "ROT90", "ROT180", "ROT270",
    "MIRROR_X", "MIRROR_Y", "MIRROR_DIAGONAL", "MIRROR_ANTIDIAGONAL",
]


def normalized_points(rows, region, transform):
    w = max(1.0, float(region["width"]))
    h = max(1.0, float(region["height"]))
    x0 = float(region["x"])
    y0 = float(region["y"])
    return [
        transform_point((float(c["x"]) - x0) / w, (float(c["y"]) - y0) / h, transform)
        for c in rows
    ]


def symmetric_distance(a, b, ra, rb, transform):
    if not a or not b:
        return None
    A = normalized_points(a, ra, transform)
    B = normalized_points(b, rb, "IDENTITY")
    ta, tb = cKDTree(A), cKDTree(B)
    dab = tb.query(A, k=1, workers=1)[0]
    dba = ta.query(B, k=1, workers=1)[0]
    return (float(dab.sum()) + float(dba.sum())) / (len(A) + len(B))


def sparse_match(a, b, ra, rb, transform, kcand):
    if not a or not b:
        return []
    A = normalized_points(a, ra, transform)
    B = normalized_points(b, rb, "IDENTITY")
    swapped = False
    left, right = A, B
    if len(left) > len(right):
        left, right = right, left
        swapped = True
    k = max(1, min(int(kcand), len(right)))
    tree = cKDTree(right)
    dists, idxs = tree.query(left, k=k, workers=1)
    if k == 1:
        dists = [[float(x)] for x in dists]
        idxs = [[int(x)] for x in idxs]
    candidates = []
    for i in range(len(left)):
        for q in range(k):
            candidates.append((float(dists[i][q]), i, int(idxs[i][q])))
    candidates.sort(key=lambda x: (x[0], x[1], x[2]))
    used_l, used_r, pairs = set(), set(), []
    for distance, i, j in candidates:
        if i in used_l or j in used_r:
            continue
        used_l.add(i); used_r.add(j)
        pairs.append((j, i, distance) if swapped else (i, j, distance))
    return pairs


def center_mapping(A, B, kcand):
    by_a, by_b = defaultdict(list), defaultdict(list)
    for center in A["centers"]: by_a[center["kind"]].append(center)
    for center in B["centers"]: by_b[center["kind"]].append(center)
    scored = []
    for order, transform in enumerate(TRANSFORMS):
        numerator = 0.0
        denominator = 0
        for kind in ("ENDPOINT", "JUNCTION"):
            distance = symmetric_distance(by_a[kind], by_b[kind], A["region"], B["region"], transform)
            if distance is not None:
                weight = len(by_a[kind]) + len(by_b[kind])
                numerator += distance * weight
                denominator += weight
        scored.append((float("inf") if denominator == 0 else numerator / denominator, order, transform))
    best = min(scored)[2]
    mapping = {}
    for kind in ("ENDPOINT", "JUNCTION"):
        aa, bb = by_a[kind], by_b[kind]
        for ia, ib, _ in sparse_match(aa, bb, A["region"], B["region"], best, kcand):
            mapping[aa[ia]["eventId"]] = bb[ib]["eventId"]
    return mapping, best


def degree_class(value, cap):
    value = int(value)
    return f"{cap}+" if value >= cap else str(value)


def multiplicity_class(value, cap):
    value = int(value)
    return f"{cap}+" if value >= cap else str(value)


def length_bin(value, width):
    return int(math.floor(max(0.0, float(value)) / float(width) + 1e-12))

