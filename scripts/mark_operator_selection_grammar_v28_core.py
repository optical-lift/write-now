#!/usr/bin/env python3
import hashlib
import itertools
import math
import random
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from pathlib import Path

from mark_hebrew_glyph_annotation_competition_v19_io import (
    NS, canonical_json, read_json, read_jsonl, sha256_json, write_json, write_jsonl,
)
from mark_hebrew_glyph_annotation_competition_v19_projector import glyph_segments, hist
from mark_hebrew_operator_representation_v21_core import _target_lemma_and_morph
from mark_verse_boundary_continuity_v25_core import _anon

EPS = 1e-300
REPRESENTATIONS = ("lemma", "lemmaCoarseMorph", "lemmaFullMorph")


def _book_lane_map(book_ids, protocol):
    split = protocol["hebrewSplit"]
    ordered = sorted(set(book_ids), key=lambda b: hashlib.sha256((split["salt"] + ":" + b).encode()).hexdigest())
    residues = {
        "train": set(split["trainRankResidues"]),
        "holdout": set(split["holdoutRankResidues"]),
        "control": set(split["controlRankResidues"]),
    }
    mapping = {}
    for rank, book in enumerate(ordered):
        r = rank % 5
        mapping[book] = next(k for k, vals in residues.items() if r in vals)
    return mapping, ordered


def parse_hebrew_books(wlc_dir, protocol):
    raw, books = [], []
    for path in sorted(Path(wlc_dir).glob("*.xml")):
        root = ET.parse(path).getroot()
        for chapter in root.findall(".//osis:chapter", NS):
            cid = chapter.attrib.get("osisID")
            if not cid:
                continue
            book = cid.split(".")[0]
            books.append(book)
            verses = []
            for verse in chapter.findall(".//osis:verse", NS):
                vid = verse.attrib.get("osisID")
                if not vid:
                    continue
                lemma, coarse, full = [], [], []
                for w in verse.findall(".//osis:w", NS):
                    parsed = _target_lemma_and_morph(w)
                    if parsed is None:
                        continue
                    lem, c, f = parsed
                    lemma.append(lem)
                    coarse.append(f"{lem}|M={c}")
                    full.append(f"{lem}|M={f}")
                if lemma:
                    verses.append({
                        "anonymousVerseId": _anon("V", vid),
                        "tokens": lemma,
                        "lemmaCoarseMorph": coarse,
                        "lemmaFullMorph": full,
                    })
            if verses:
                raw.append((book, cid, verses))
    lane_map, ordered = _book_lane_map(books, protocol)
    lanes = {"train": [], "holdout": [], "control": []}
    for book, cid, verses in raw:
        lane = lane_map[book]
        lanes[lane].append({
            "anonymousChapterId": _anon("C", cid),
            "anonymousBookId": _anon("B", book),
            "lane": lane,
            "verses": verses,
        })
    for lane in lanes:
        lanes[lane].sort(key=lambda x: x["anonymousChapterId"])
    lane_books = {lane: sorted({r["anonymousBookId"] for r in rows}) for lane, rows in lanes.items()}
    assert not (set(lane_books["train"]) & set(lane_books["holdout"]))
    assert not (set(lane_books["train"]) & set(lane_books["control"]))
    assert not (set(lane_books["holdout"]) & set(lane_books["control"]))
    manifest = {
        "schema": "mark_operator_selection_hebrew_packets_v28",
        "bookCounts": {k: len(v) for k, v in lane_books.items()},
        "chapterCounts": {k: len(v) for k, v in lanes.items()},
        "verseCounts": {k: sum(len(c["verses"]) for c in v) for k, v in lanes.items()},
        "tokenCounts": {k: sum(len(z["tokens"]) for c in v for z in c["verses"]) for k, v in lanes.items()},
        "bookDisjointAcrossLanes": True,
        "bookAssignmentDigest": hashlib.sha256("|".join(f"{_anon('B', b)}:{lane_map[b]}" for b in ordered).encode()).hexdigest(),
    }
    return lanes, manifest


def position_bucket(i, protocol):
    for (lo, hi), label in zip(protocol["positionBuckets"]["buckets"], protocol["positionBuckets"]["labels"]):
        if int(lo) <= int(i) <= int(hi):
            return label
    raise ValueError(i)


def _seq(verse, rep):
    return verse["tokens"] if rep == "lemma" else verse[rep]


def hebrew_events(chapters, rep, protocol):
    out = []
    for ch in chapters:
        for verse in ch["verses"]:
            seq = _seq(verse, rep)
            for i, op in enumerate(seq):
                out.append({"state": hist(seq, i), "pos": position_bucket(i, protocol), "operator": op})
    return out


def glyph_events(rows, protocol):
    out = []
    for _, seq in glyph_segments(rows):
        for i, op in enumerate(seq):
            out.append({"state": hist(seq, i), "pos": position_bucket(i, protocol), "operator": op})
    return out


def _normalize(d, ops):
    z = sum(d.get(o, 0.0) for o in ops)
    if z <= 0:
        return {o: 1.0 / len(ops) for o in ops}
    return {o: d.get(o, 0.0) / z for o in ops}


def build_model(events, protocol):
    cfg = protocol["training"]
    support = Counter(e["operator"] for e in events)
    eligible = [(o, n) for o, n in support.items() if n >= int(cfg["minimumOperatorEvents"])]
    eligible.sort(key=lambda x: (-x[1], x[0]))
    ops = [o for o, _ in eligible[:int(cfg["maximumOperatorsPerSystem"])]]
    opset = set(ops)
    kept = [e for e in events if e["operator"] in opset]
    state_support = Counter(e["state"] for e in kept)
    states = sorted(s for s, n in state_support.items() if n >= int(cfg["minimumStateEvents"]))
    stateset = set(states)
    kept = [e for e in kept if e["state"] in stateset]

    g = Counter(e["operator"] for e in kept)
    alpha = float(cfg["globalAlpha"])
    total = sum(g.values())
    pglobal = {o: (g[o] + alpha) / (total + alpha * len(ops)) for o in ops}

    pos_counts = defaultdict(Counter)
    sp_counts = defaultdict(Counter)
    for e in kept:
        pos_counts[e["pos"]][e["operator"]] += 1
        sp_counts[(e["state"], e["pos"])][e["operator"]] += 1
    ppos = {}
    pb = float(cfg["positionBackoffPseudoCount"])
    for p, cnt in pos_counts.items():
        n = sum(cnt.values())
        ppos[p] = {o: (cnt[o] + pb * pglobal[o]) / (n + pb) for o in ops}
    psel = {}
    sb = float(cfg["statePositionBackoffPseudoCount"])
    mincell = int(cfg["minimumStatePositionEventsForConditional"])
    for (s, p), cnt in sp_counts.items():
        base = ppos[p]
        n = sum(cnt.values())
        if n >= mincell:
            psel[canonical_json([s, p])] = {o: (cnt[o] + sb * base[o]) / (n + sb) for o in ops}
        else:
            psel[canonical_json([s, p])] = dict(base)

    substitutes = {}
    for op in ops:
        candidates = [x for x in ops if x != op]
        substitutes[op] = min(candidates, key=lambda x: (abs(g[x] - g[op]), x)) if candidates else op
    return {
        "operators": ops,
        "operatorSupport": {o: int(g[o]) for o in ops},
        "states": states,
        "stateSupport": {s: int(state_support[s]) for s in states},
        "pGlobal": pglobal,
        "pPos": ppos,
        "pSel": psel,
        "substitutes": substitutes,
        "trainEvents": len(kept),
    }


def freeze_models(hebrew_train, glyph_train, protocol):
    systems = {rep: build_model(hebrew_events(hebrew_train, rep, protocol), protocol) for rep in REPRESENTATIONS}
    glyph = build_model(glyph_events(glyph_train, protocol), protocol)
    return {"hebrew": systems, "glyph": glyph}


def _dist(model, state, pos, source_state=None):
    base = model["pPos"].get(pos, model["pGlobal"])
    s = state if source_state is None else source_state
    sel = model["pSel"].get(canonical_json([s, pos]), base)
    return base, sel


def _qualify(events, model, protocol):
    ec = protocol["evaluation"]
    opset, stateset = set(model["operators"]), set(model["states"])
    kept = [e for e in events if e["operator"] in opset and e["state"] in stateset]
    oc = Counter(e["operator"] for e in kept)
    qualified = sorted(o for o, n in oc.items() if n >= int(ec["minimumEvaluationEventsPerOperator"]))
    return kept, qualified


def _mapping_for_perm(model, seed):
    rng = random.Random(seed)
    by_pos = defaultdict(list)
    for key in model["pSel"]:
        s, p = __import__("json").loads(key)
        by_pos[p].append(s)
    mapping = {}
    for p, states in by_pos.items():
        states = sorted(set(states))
        shuffled = list(states)
        rng.shuffle(shuffled)
        mapping[p] = dict(zip(states, shuffled))
    return mapping


def _score(events, qualified, model, mapping=None):
    q = set(qualified)
    byop = defaultdict(lambda: [0.0, 0, 0.0, 0, 0])
    bystate = defaultdict(lambda: [0.0, 0])
    for e in events:
        op = e["operator"]
        if op not in q:
            continue
        src = None
        if mapping is not None:
            src = mapping.get(e["pos"], {}).get(e["state"], e["state"])
        base, sel = _dist(model, e["state"], e["pos"], src)
        gain = math.log2(max(sel[op], EPS)) - math.log2(max(base[op], EPS))
        global_gain = math.log2(max(sel[op], EPS)) - math.log2(max(model["pGlobal"][op], EPS))
        sub = model["substitutes"][op]
        residual_actual = sel[op] / max(base[op], EPS)
        residual_sub = sel[sub] / max(base[sub], EPS)
        a = byop[op]
        a[0] += gain; a[1] += 1; a[2] += global_gain; a[3] += int(residual_actual > residual_sub); a[4] += 1
        bystate[e["state"]][0] += gain; bystate[e["state"]][1] += 1
    op_means = {o: vals[0] / vals[1] for o, vals in byop.items() if vals[1]}
    primary = sum(op_means.values()) / len(op_means) if op_means else 0.0
    secondary = sum(vals[2] / vals[1] for vals in byop.values() if vals[1]) / len(op_means) if op_means else 0.0
    positive = sum(v > 0 for v in op_means.values()) / len(op_means) if op_means else 0.0
    cf_byop = [vals[3] / vals[4] for vals in byop.values() if vals[4]]
    cf = sum(cf_byop) / len(cf_byop) if cf_byop else 0.0
    state_profile = {s: v[0] / v[1] for s, v in bystate.items() if v[1]}
    state_counts = {s: v[1] for s, v in bystate.items() if v[1]}
    return primary, secondary, positive, cf, op_means, state_profile, state_counts


def evaluate_system(events, model, protocol, lane, label, pthreshold):
    kept, qualified = _qualify(events, model, protocol)
    primary, secondary, positive, cf, opmeans, profile, profile_counts = _score(kept, qualified, model)
    perms = int(protocol["null"]["permutations"])
    ge = 0
    for i in range(perms):
        mapping = _mapping_for_perm(model, f"mark-v28:{label}:{lane}:{i}")
        null_primary = _score(kept, qualified, model, mapping)[0]
        ge += int(null_primary >= primary - 1e-15)
    p = (1 + ge) / (perms + 1)
    ec = protocol["evaluation"]
    sufficient = len(qualified) >= int(ec["minimumEvaluableOperators"])
    passed = sufficient and primary > 0 and p <= float(pthreshold) and positive >= float(ec["positiveOperatorFractionAtLeast"]) and cf > float(ec["counterfactualPreferenceAtLeast"])
    return {
        "lane": lane,
        "label": label,
        "evaluationEvents": len(kept),
        "evaluableOperators": len(qualified),
        "frozenOperators": len(model["operators"]),
        "operatorBalancedSelectionGainBits": primary,
        "operatorBalancedGainOverGlobalBits": secondary,
        "positiveOperatorFraction": positive,
        "counterfactualActualPreference": cf,
        "residualReassignmentP": p,
        "sufficient": sufficient,
        "pass": passed,
        "stateProfile": profile,
        "stateProfileCounts": profile_counts,
        "operatorMeans": opmeans,
    }


def _pearson(xs, ys):
    if len(xs) < 2:
        return 0.0
    mx, my = sum(xs)/len(xs), sum(ys)/len(ys)
    dx, dy = [x-mx for x in xs], [y-my for y in ys]
    den = math.sqrt(sum(x*x for x in dx) * sum(y*y for y in dy))
    return sum(x*y for x, y in zip(dx, dy)) / den if den else 0.0


def compare_profiles(hres, gres, protocol, rep, lane):
    min_n = int(protocol["evaluation"]["minimumEvaluationEventsPerState"])
    states = sorted(set(hres["stateProfile"]) & set(gres["stateProfile"]))
    states = [s for s in states if hres["stateProfileCounts"].get(s,0) >= min_n and gres["stateProfileCounts"].get(s,0) >= min_n]
    minimum = int(protocol["crossSystem"]["minimumSharedStates"])
    if len(states) < minimum:
        return {"sharedStates": len(states), "pearsonR": 0.0, "permutationP": 1.0, "sufficient": False, "pass": False}
    x = [hres["stateProfile"][s] for s in states]
    y = [gres["stateProfile"][s] for s in states]
    r = _pearson(x,y)
    rng = random.Random(f"mark-v28-cross:{rep}:{lane}")
    nperm = int(protocol["crossSystem"]["permutations"])
    ge = 0
    for _ in range(nperm):
        yp = list(y); rng.shuffle(yp)
        ge += int(_pearson(x,yp) >= r - 1e-15)
    p = (1+ge)/(nperm+1)
    passed = r > 0 and p <= float(protocol["crossSystem"]["pAtMost"])
    return {"sharedStates": len(states), "pearsonR": r, "permutationP": p, "sufficient": True, "pass": passed}


def evaluate_all(hebrew_eval, glyph_eval, freeze, protocol):
    lanes = {"holdout": {}, "control": {}}
    gresults = {}
    for lane in ("holdout","control"):
        grows = glyph_eval[lane]
        g = evaluate_system(glyph_events(grows, protocol), freeze["glyph"], protocol, lane, "glyph", protocol["evaluation"]["glyphPAtMost"])
        gresults[lane] = g
        for rep in REPRESENTATIONS:
            h = evaluate_system(hebrew_events(hebrew_eval[lane], rep, protocol), freeze["hebrew"][rep], protocol, lane, rep, protocol["evaluation"]["hebrewFamilywisePAtMost"])
            lanes[lane][rep] = {"hebrew": h, "cross": compare_profiles(h, g, protocol, rep, lane)}
    return lanes, gresults


def adjudicate(lanes, glyph):
    hpass = [rep for rep in REPRESENTATIONS if all(lanes[l][rep]["hebrew"]["pass"] for l in ("holdout","control"))]
    gpass = all(glyph[l]["pass"] for l in ("holdout","control"))
    cross = [rep for rep in hpass if gpass and all(lanes[l][rep]["cross"]["pass"] for l in ("holdout","control"))]
    if cross:
        return "CROSS_SYSTEM_STATE_SELECTION_PROFILE_ALIGNED"
    if len(hpass) > 1:
        return "MULTIPLE_HEBREW_REPRESENTATIONS_SUPPORT_OPERATOR_SELECTION"
    if len(hpass) == 1:
        return {"lemma":"LEMMA_SUPPORTS_OPERATOR_SELECTION","lemmaCoarseMorph":"COARSE_MORPH_SUPPORTS_OPERATOR_SELECTION","lemmaFullMorph":"FULL_MORPH_SUPPORTS_OPERATOR_SELECTION"}[hpass[0]]
    if gpass:
        return "GLYPH_ONLY_OPERATOR_SELECTION"
    sufficient = any(lanes[l][r]["hebrew"]["sufficient"] for l in ("holdout","control") for r in REPRESENTATIONS) or any(glyph[l]["sufficient"] for l in ("holdout","control"))
    return "NO_OPERATOR_SELECTION_GRAMMAR" if sufficient else "INSUFFICIENT_SELECTION_SUPPORT"
