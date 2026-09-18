# Relational Law Observation Packet v1 — Instrument Freeze

Status: **FROZEN FOR PRIOR-MARK EVIDENCE HARVEST**
Date: **2026-09-18**
Branch: `mark-relational-law-observation-packet-v1`

## Freeze boundary

This freeze closes the instrument-construction checkpoint described in `WHOLE_SYSTEM_RECONSTRUCTION_ROADMAP.md`.

The next governed checkpoint is **Prior-Mark Evidence and Constraint Harvest**.

The harvest may use this packet format, but it must not silently modify the frozen v1 instrument. Any required schema change discovered during harvest becomes an explicit v1.x/v2 amendment or a new instrument checkpoint.

## Pre-freeze branch head

`7a0d76df530baaaf14bf1b45a6e89d14dab90dee`

## Frozen artifacts

| Artifact | Git blob SHA |
|---|---|
| `research/mark/discovery-experiments/relational-law-observation-packet-v1.schema.json` | `38d9420ef195efce9357a139e6b173a122391ea1` |
| `research/mark/discovery-experiments/relational-law-observation-packet-v1.spec.md` | `ee94c0d104f1c849c25c8a58cd2dddc122360520` |
| `research/mark/discovery-experiments/relational-law-observation-packet-v1.pilot.part1.jsonl` | `fae8bff6a7984594263cee1319c8d35ed06c7a20` |
| `research/mark/discovery-experiments/relational-law-observation-packet-v1.pilot.part2.jsonl` | `844a8ccb7943899309719cdeb0960a88af31b7e5` |
| `research/mark/discovery-experiments/relational-law-observation-packet-v1.pilot.part3.jsonl` | `b358b0df99906c9ad94a2f5178e19b71be5c1ec7` |
| `research/mark/discovery-experiments/relational-law-observation-packet-v1.pilot-manifest.json` | `91a2cfc887eaedfc7338194cb102944ec95c085c` |
| `research/mark/discovery-experiments/relational-law-observation-packet-v1.pilot-assessment.md` | `71a657842cc89c9c6d2f4512c73ea5d4a79c51f1` |
| `scripts/validate-mark-relational-law-observation-v1.py` | `4c5ad5caa2d66fd8fce50041410b1439773315f0` |
| `research/mark/discovery-experiments/WHOLE_SYSTEM_RECONSTRUCTION_ROADMAP.md` | `3f3a1748aa4b2116c9c467dd764521badc5bf1f4` |

## Pilot coverage

The frozen pilot contains **27 packets**, `RLOP-001` through `RLOP-027`.

It deliberately spans:

- supported findings;
- negative constraints;
- diagnostics;
- source-local experiments;
- blind multi-source experiments;
- cross-system tests;
- external-witness comparisons;
- sequence behavior;
- representation failure;
- composition;
- repetition;
- cancellation;
- field structure;
- scale persistence;
- population-sensitive coordinate failure.

The pilot is a stress test of the instrument, not an exhaustive V1–V48 harvest.

## Freeze validation

Exact committed pilot artifacts were reread after the final schema refinement.

Validation passed:

- 27 packets parse;
- IDs are complete and unique from `RLOP-001` through `RLOP-027`;
- every packet records evidence provenance;
- every packet records historical experiment scope;
- every packet affirms independent packet construction;
- every packet has `cross_source_matching_performed = false`;
- every packet has no external semantic labels;
- every packet has `universal_law_label = null`;
- every packet has no candidate equivalences.

## Scientific role

The instrument is allowed to record:

- observed transformations;
- relational constraints;
- representation dependencies;
- failed models;
- nulls and negative findings;
- field-level organization;
- observation boundaries;
- unresolved residuals.

It is not allowed to assign the larger grammar.

The frozen order remains:

> **independent discovery first → abstract comparison second → global grammar last**

## Next checkpoint

Begin the **Prior-Mark Evidence and Constraint Harvest**.

That work should:

1. walk the Mark history experiment by experiment;
2. prefer direct frozen result artifacts over synthesis notes wherever recoverable;
3. create one or more RLOP packets for every materially distinct supported, negative, diagnostic, unresolved, or insufficient-contrast finding;
4. preserve source/container boundaries as discovery custody, not ontology;
5. perform no cross-source equivalence matching;
6. reserve law comparison for the later equivalence-adjudication checkpoint.

No global reconstruction begins at this freeze.
