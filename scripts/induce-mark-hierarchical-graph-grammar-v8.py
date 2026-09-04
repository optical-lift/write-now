#!/usr/bin/env python3
import json
import os
from pathlib import Path

from mark_graph_compression_v8_core import (
    canonical_sha,
    sha256_file,
    build_primitive_graph,
    induce_grammar,
    serialize_grammar,
    grammar_bits,
    synthetic_roundtrip_tests,
)

protocol_path = Path(os.environ.get(
    "MARK_COMPRESSION_PROTOCOL",
    "research/mark/discovery-experiments/hierarchical-graph-compression-v8.protocol.json",
))
v5_dir = Path(os.environ.get("MARK_V5_PACKET", "artifact-staging/v5"))
out_dir = Path(os.environ.get("MARK_COMPRESSION_GRAMMAR_OUT", "artifacts/mark-hierarchical-graph-compression-v8/grammar"))


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def locate(name):
    hits = list(v5_dir.rglob(name))
    if len(hits) != 1:
        raise RuntimeError(f"expected one V5 {name}, found {len(hits)}")
    return hits[0]


def load_train_graphs(projector_path, eligible, variant):
    graphs = []
    with projector_path.open("r", encoding="utf-8") as handle:
        for line_no, raw in enumerate(handle, 1):
            if not raw.strip():
                continue
            row = json.loads(raw)
            if row["observationId"] not in eligible or row["lane"] != "train":
                continue
            graphs.append(build_primitive_graph(row, variant, track_members=False))
            if len(graphs) % 50 == 0:
                print(f"loaded_train_graphs variant={variant} count={len(graphs)} line={line_no}")
    return graphs


protocol = load_json(protocol_path)
if protocol.get("schema") != "mark_hierarchical_graph_compression_protocol_v8":
    raise RuntimeError("unexpected V8 protocol schema")
parent = protocol["parentV5"]
cfg = protocol["grammarFamily"]

manifest = load_json(locate("edge-pair-manifest.json"))
world = load_json(locate("critical-edge-world.json"))
projector_path = locate("critical-edge-observations.jsonl")
# Deliberately do not locate or open role-pair-labels.jsonl in this induction process.

manifest_sha = manifest.get("edgePairManifestSha256")
world_sha = world.get("criticalEdgeWorldSha256")
if canonical_sha({k: v for k, v in manifest.items() if k != "edgePairManifestSha256"}) != manifest_sha:
    raise RuntimeError("V5 edge pair manifest SHA mismatch")
if canonical_sha({k: v for k, v in world.items() if k != "criticalEdgeWorldSha256"}) != world_sha:
    raise RuntimeError("V5 critical edge world SHA mismatch")
if manifest_sha != parent["expectedEdgePairManifestSha256"]:
    raise RuntimeError("wrong parent V5 edge pair manifest")
if world_sha != parent["expectedCriticalEdgeWorldSha256"]:
    raise RuntimeError("wrong parent V5 critical edge world")
if sha256_file(projector_path) != world["projectorRowsSha256"]:
    raise RuntimeError("V5 projector row hash mismatch")

if not synthetic_roundtrip_tests():
    raise RuntimeError("synthetic lossless grammar round-trip failed")

eligible = set(world["pairEligibleObservationIds"])
models = {}
for variant in ("lengthAware", "topology"):
    models[variant] = {}
    for model_name, allow_nonterminals in (("flat", False), ("hierarchical", True)):
        print(f"induction_start variant={variant} model={model_name}")
        graphs = load_train_graphs(projector_path, eligible, variant)
        if not graphs:
            raise RuntimeError(f"no Cleveland induction graphs for {variant}/{model_name}")
        result = induce_grammar(graphs, cfg, allow_nonterminals=allow_nonterminals)
        packet = serialize_grammar(result)
        packet["model"] = model_name
        packet["variant"] = variant
        packet["allowNonterminalChildren"] = allow_nonterminals
        packet["grammarSha256"] = canonical_sha(packet)
        models[variant][model_name] = packet
        print(
            f"induction_done variant={variant} model={model_name} rules={len(packet['rules'])} "
            f"raw={packet['rawDataBits']} data={packet['trainDataBits']} model_bits={packet['modelBits']} "
            f"total={packet['trainTotalBits']} sha={packet['grammarSha256']}"
        )

for variant in models:
    raw_values = {models[variant][name]["rawDataBits"] for name in models[variant]}
    if len(raw_values) != 1:
        raise RuntimeError(f"raw training code drift across models for {variant}")

core = {
    "schema": "mark_hierarchical_graph_grammar_freeze_v8",
    "experimentId": protocol["experimentId"],
    "parentV5RunId": int(parent["expectedRunId"]),
    "parentEdgePairManifestSha256": manifest_sha,
    "parentCriticalEdgeWorldSha256": world_sha,
    "parentProjectorRowsSha256": world["projectorRowsSha256"],
    "parentRolePairRowsSha256ExpectedButNotOpened": manifest["parentRolePairRowsSha256"],
    "grammarInductionLane": "train",
    "roleLabelsOpenedDuringInduction": False,
    "radiusBoundaryUsed": False,
    "v7VocabularyConsumed": False,
    "models": models,
    "rawTrainTotalBits": {
        variant: next(iter({models[variant][name]["rawDataBits"] for name in models[variant]})) + grammar_bits([])
        for variant in models
    },
    "contract": {
        "frozenBeforeRoleLabels": True,
        "sourcePixelsConsumed": False,
        "topologyReprojected": False,
        "residualGeometryConsumed": False,
        "sourceGroupUsedOnlyForCrossSourceCandidateSupport": True,
        "preservedBrokenLabelsConsumed": False,
        "syntheticLosslessRoundTripPassed": True,
    },
}
digest = canonical_sha(core)
packet = {**core, "grammarFreezeSha256": digest}
out_dir.mkdir(parents=True, exist_ok=True)
(out_dir / "hierarchical-graph-grammar-freeze.json").write_text(json.dumps(packet, indent=2) + "\n", encoding="utf-8")
summary = [
    f"grammar_freeze_sha256={digest}",
    f"parent_v5_edge_world_sha256={world_sha}",
    "role_labels_opened=false",
    "radius_boundary_used=false",
]
for variant in ("lengthAware", "topology"):
    for model_name in ("flat", "hierarchical"):
        model = models[variant][model_name]
        summary.append(
            f"variant={variant};model={model_name};rules={len(model['rules'])};"
            f"raw_data_bits={model['rawDataBits']};train_data_bits={model['trainDataBits']};"
            f"model_bits={model['modelBits']};train_total_bits={model['trainTotalBits']};"
            f"grammar_sha256={model['grammarSha256']}"
        )
(out_dir / "summary.txt").write_text("\n".join(summary) + "\n", encoding="utf-8")
print("\n".join(summary))
