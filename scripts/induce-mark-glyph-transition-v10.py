#!/usr/bin/env python3
import json
import os
from pathlib import Path

from mark_glyph_transition_v10_core import canonical_sha, freeze_variant, read_jsonl

PROTOCOL_PATH = Path(os.environ.get(
    "MARK_V10_PROTOCOL",
    "research/mark/discovery-experiments/glyph-transition-code-v10.protocol.json",
))
TRAIN_PATH = Path(os.environ.get("MARK_V10_TRAIN", "artifact-staging/v10-split/train.jsonl"))
MANIFEST_PATH = Path(os.environ.get("MARK_V10_MANIFEST", "artifact-staging/v10-split/split-manifest.json"))
OUT_DIR = Path(os.environ.get("MARK_V10_FREEZE", "artifacts/mark-glyph-transition-code-v10-freeze"))


def main():
    protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    if protocol.get("schema") != "mark_glyph_transition_code_protocol_v10":
        raise RuntimeError("unexpected V10 protocol schema")
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    if manifest.get("experimentId") != protocol["experimentId"]:
        raise RuntimeError("V10 manifest experiment mismatch")
    if manifest.get("protocolSha256") != canonical_sha(protocol):
        raise RuntimeError("V10 manifest/protocol hash mismatch")
    if manifest.get("semanticFieldsPresentInBlindPacket") is not False:
        raise RuntimeError("blind packet semantic leakage flag is not false")

    # This process is allowed to see train only. The workflow also asserts the
    # holdout/control files are physically absent in this job.
    train_rows = read_jsonl(TRAIN_PATH, expected_lane="train")
    variants = {}
    for variant in (protocol["sequence"]["primaryVariant"], protocol["sequence"]["ablationVariant"]):
        variants[variant] = freeze_variant(train_rows, protocol, variant)
        print(
            f"[{variant}] inscriptions={len(train_rows)} "
            f"eligibleGlyphs={variants[variant]['trainInventory']['eligibleGlyphCount']} "
            f"classes={variants[variant]['classSelection']['selectedClassCount']}",
            flush=True,
        )

    core = {
        "schema": "mark_glyph_transition_code_freeze_v10",
        "experimentId": protocol["experimentId"],
        "protocolSha256": canonical_sha(protocol),
        "sourceCommit": manifest["sourceCommit"],
        "sourceGitBlobSha1": manifest["sourceGitBlobSha1"],
        "sourceSha256": manifest["sourceSha256"],
        "trainPacketSha256": manifest["laneFileSha256"]["train"],
        "trainInscriptionCount": manifest["inscriptionCounts"]["train"],
        "semanticFieldsConsumed": False,
        "transliterationsConsumed": False,
        "translationsConsumed": False,
        "provenanceConsumed": False,
        "variants": variants,
    }
    freeze_sha = canonical_sha(core)
    packet = {**core, "freezeSha256": freeze_sha}

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "glyph-transition-code-freeze.json").write_text(
        json.dumps(packet, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    primary = variants[protocol["sequence"]["primaryVariant"]]
    summary = [
        "Mark glyph transition code v10 — pre-holdout freeze",
        f"protocolSha256={packet['protocolSha256']}",
        f"freezeSha256={freeze_sha}",
        f"trainInscriptions={packet['trainInscriptionCount']}",
        f"primaryEligibleGlyphs={primary['trainInventory']['eligibleGlyphCount']}",
        f"primaryFunctionalClasses={primary['classSelection']['selectedClassCount']}",
        "semanticFieldsConsumed=false",
        "holdoutOpened=false",
        "controlOpened=false",
    ]
    (OUT_DIR / "summary.txt").write_text("\n".join(summary) + "\n", encoding="utf-8")
    print("\n".join(summary))


if __name__ == "__main__":
    main()
