#!/usr/bin/env python3
import hashlib
import json
import os
from pathlib import Path

PROTOCOL_PATH = Path(os.environ.get(
    "MARK_V10_PROTOCOL",
    "research/mark/discovery-experiments/glyph-transition-code-v10.protocol.json",
))
SOURCE_PATH = Path(os.environ.get("MARK_V10_SOURCE", "artifact-staging/v10-source/LinearAInscriptions.js"))
OUT_DIR = Path(os.environ.get("MARK_V10_SPLIT", "artifact-staging/v10-split"))


def canonical_json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def git_blob_sha1(data):
    header = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(header + data).hexdigest()


def strip_trailing_commas(js_text):
    """Remove JS-only trailing commas outside quoted strings.

    The pinned source is generated as JavaScript data. Most of the first Map is
    JSON-compatible, but a few newly-added arrays legally retain a comma before
    their closing bracket. We normalize only that syntax; no values are
    evaluated and no JavaScript is executed.
    """
    out = []
    in_string = False
    escaped = False
    i = 0
    while i < len(js_text):
        ch = js_text[i]
        if in_string:
            out.append(ch)
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
            i += 1
            continue
        if ch == '"':
            in_string = True
            out.append(ch)
            i += 1
            continue
        if ch == ",":
            j = i + 1
            while j < len(js_text) and js_text[j].isspace():
                j += 1
            if j < len(js_text) and js_text[j] in "]}":
                i += 1
                continue
        out.append(ch)
        i += 1
    return "".join(out)


def parse_inscription_map(data):
    text = data.decode("utf-8")
    marker = "var inscriptions = new Map("
    start = text.find(marker)
    if start < 0:
        raise RuntimeError("could not locate inscriptions Map")
    start += len(marker)
    payload = strip_trailing_commas(text[start:].lstrip())
    decoder = json.JSONDecoder()
    value, _consumed = decoder.raw_decode(payload)
    if not isinstance(value, list):
        raise RuntimeError("inscriptions Map payload is not an array")
    return value


def lane_for(key, lanes):
    digest = hashlib.sha256(key.encode("utf-8")).digest()
    bucket = int.from_bytes(digest[:8], "big") % 10
    if bucket in lanes["trainBuckets"]:
        return "train", bucket
    if bucket in lanes["holdoutBuckets"]:
        return "holdout", bucket
    if bucket in lanes["controlBuckets"]:
        return "control", bucket
    raise RuntimeError(f"unassigned split bucket {bucket}")


def main():
    protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    if protocol.get("schema") != "mark_glyph_transition_code_protocol_v10":
        raise RuntimeError("unexpected V10 protocol schema")

    raw = SOURCE_PATH.read_bytes()
    actual_blob = git_blob_sha1(raw)
    expected_blob = protocol["source"]["expectedGitBlobSha1"]
    if actual_blob != expected_blob:
        raise RuntimeError(f"source blob drift: expected {expected_blob}, got {actual_blob}")

    entries = parse_inscription_map(raw)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    handles = {
        lane: (OUT_DIR / f"{lane}.jsonl").open("w", encoding="utf-8")
        for lane in ("train", "holdout", "control")
    }
    lane_counts = {lane: 0 for lane in handles}
    word_counts = {lane: 0 for lane in handles}
    seen_anon = set()

    try:
        for entry in entries:
            if not isinstance(entry, list) or len(entry) != 2:
                raise RuntimeError("malformed inscriptions Map entry")
            key, obj = entry
            if not isinstance(key, str) or not isinstance(obj, dict):
                raise RuntimeError("malformed inscription key/object")
            words = obj.get("words")
            if not isinstance(words, list) or not all(isinstance(x, str) for x in words):
                raise RuntimeError(f"inscription {key!r} has invalid words array")

            lane, bucket = lane_for(key, protocol["lanes"])
            anonymous_id = "I" + hashlib.sha256(key.encode("utf-8")).hexdigest()[:20]
            if anonymous_id in seen_anon:
                raise RuntimeError("anonymous inscription id collision")
            seen_anon.add(anonymous_id)

            row = {
                "schema": "mark_glyph_transition_blind_inscription_v10",
                "anonymousInscriptionId": anonymous_id,
                "lane": lane,
                "splitBucket": bucket,
                "words": words,
            }
            serialized = canonical_json(row)
            forbidden = protocol["custody"]["forbiddenInBlindPacket"]
            leaked = [field for field in forbidden if f'"{field}"' in serialized]
            if leaked:
                raise RuntimeError(f"forbidden fields leaked into blind row: {leaked}")
            handles[lane].write(serialized + "\n")
            lane_counts[lane] += 1
            word_counts[lane] += sum(1 for x in words if x != "\n")
    finally:
        for handle in handles.values():
            handle.close()

    if min(lane_counts.values()) <= 0:
        raise RuntimeError(f"empty lane after deterministic split: {lane_counts}")

    file_hashes = {
        lane: sha256_bytes((OUT_DIR / f"{lane}.jsonl").read_bytes())
        for lane in lane_counts
    }
    manifest = {
        "schema": "mark_glyph_transition_split_manifest_v10",
        "experimentId": protocol["experimentId"],
        "protocolSha256": sha256_bytes(canonical_json(protocol).encode("utf-8")),
        "sourceRepository": protocol["source"]["repository"],
        "sourceCommit": protocol["source"]["commit"],
        "sourcePath": protocol["source"]["path"],
        "sourceGitBlobSha1": actual_blob,
        "sourceSha256": sha256_bytes(raw),
        "inscriptionCounts": lane_counts,
        "rawWordCounts": word_counts,
        "laneFileSha256": file_hashes,
        "semanticFieldsPresentInBlindPacket": False,
    }
    (OUT_DIR / "split-manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
