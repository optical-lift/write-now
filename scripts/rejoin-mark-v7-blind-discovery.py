#!/usr/bin/env python3
import hashlib
import json
import os
from pathlib import Path

blind_path = Path(os.environ.get("MARK_BLIND_DISCOVERY_PACKET", "artifact-staging/blind-discovery/blind-discovery/blind-discovery.json"))
rejoin_path = Path(os.environ.get("MARK_HARVEST_REJOIN", "artifact-staging/context-custody/mark-harvest-rejoin-v1/mark-harvest-custody-rejoin-v1.json"))
out_dir = Path(os.environ.get("MARK_DISCOVERY_REJOIN_OUT", "artifacts/mark-blind-discovery-context-rejoin-v1"))


def canonical_sha256(value) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


blind = json.loads(blind_path.read_text(encoding="utf-8"))
if blind.get("schema") != "mark_v7_blind_discovery_packet_v1":
    raise RuntimeError("unexpected blind discovery packet schema")
supplied = blind.get("blindDiscoverySha256")
blind_core = {key: value for key, value in blind.items() if key != "blindDiscoverySha256"}
computed = canonical_sha256(blind_core)
if not supplied or supplied != computed:
    raise RuntimeError("blind discovery packet SHA-256 verification failed before provenance rejoin")
if not blind.get("provenanceRejoinMayProceed"):
    raise RuntimeError("blind packet does not authorize provenance rejoin")

rejoin = json.loads(rejoin_path.read_text(encoding="utf-8"))
if rejoin.get("schema") != "mark_harvest_custody_rejoin_v1":
    raise RuntimeError("unexpected harvest rejoin schema")
if rejoin.get("sealedHarvestBlindSha256") != blind.get("sourceHarvestSha256"):
    raise RuntimeError("harvest rejoin does not belong to the frozen blind discovery packet")

lanes = {}
for lane in ["train", "holdout", "control"]:
    sources = [source for source in rejoin.get("sources", []) if source.get("challengeLane") == lane]
    institutions = sorted({str(source.get("institution")) for source in sources if source.get("institution")})
    rights = sorted({str(source.get("rightsBasis")) for source in sources if source.get("rightsBasis")})
    lanes[lane] = {
        "sourceObjects": len(sources),
        "institutions": institutions,
        "rightsBases": rights,
    }

contextual = {
    "schema": "mark_v7_blind_discovery_context_rejoin_v1",
    "sealedBlindDiscoverySha256": supplied,
    "sourceHarvestSha256": blind.get("sourceHarvestSha256"),
    "experimentId": blind.get("experimentId"),
    "laneContext": lanes,
    "blindRankingPreserved": True,
    "rules": blind.get("rules", []),
    "interpretationContract": {
        "whatRejoined": "institutional provenance for the already-frozen train holdout and control lanes",
        "whatDidNotChange": "rule definitions, blind rank, candidate tier, observed statistics, null statistics, and compiler custody",
        "semanticMeaningAssigned": False,
        "scientificClaimAuthorized": "only that the frozen anonymous relational statistics can now be inspected against their real source provenance; semantic or historical interpretation requires a separate evidentiary step"
    },
}
out_dir.mkdir(parents=True, exist_ok=True)
(out_dir / "context-rejoin.json").write_text(json.dumps(contextual, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
lines = [
    f"schema={contextual['schema']}",
    f"sealed_blind_discovery_sha256={supplied}",
    f"train_institutions={'|'.join(lanes['train']['institutions'])}",
    f"holdout_institutions={'|'.join(lanes['holdout']['institutions'])}",
    f"control_institutions={'|'.join(lanes['control']['institutions'])}",
    f"rules={len(contextual['rules'])}",
]
(out_dir / "summary.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
print(json.dumps({"sealedBlindDiscoverySha256": supplied, "laneContext": lanes, "rules": len(contextual["rules"])}, indent=2))
