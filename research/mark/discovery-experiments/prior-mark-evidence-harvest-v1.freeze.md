# Prior-Mark Evidence and Constraint Harvest v1 — Freeze

Status: **FROZEN**
Date: **2026-09-18**
Branch: `mark-prior-evidence-harvest-v1`
Instrument freeze: `be94c2c36fa6510b299f989fd6eb5252816f0718`

## Freeze boundary

This freeze closes the **Prior-Mark Evidence and Constraint Harvest** checkpoint in `WHOLE_SYSTEM_RECONSTRUCTION_ROADMAP.md`.

The next governed checkpoint is **Law-Equivalence Adjudication Language**.

The frozen harvest may be read and compared by that later checkpoint, but the harvest itself must not be silently rewritten to fit candidate equivalences discovered later.

## Pre-freeze branch head

`ce07cd4e2f25c913b9f9a1d1f9e617a98351ac20`

## Packet inventory

The branch contains:

- **90 total packets**, `RLOP-001` through `RLOP-090`;
- **84 canonical active packets**, `RLOP-007` through `RLOP-090`;
- **6 superseded instrument-pilot history packets**, `RLOP-001` through `RLOP-006`.

The six superseded packets remain byte-preserved as history. Their direct frozen-result replacements are identified in the manifest.

## Frozen harvest artifacts

| Artifact | Git blob SHA |
|---|---|
| `prior-mark-evidence-harvest-v1.artifact-ledger.json` | `83d2d143350a0bbae7eddc4cb802a18c82b0686f` |
| `prior-mark-evidence-harvest-v1.part1.jsonl` | `8c18de5c611c5d6b50417422b189514bc598fc8a` |
| `prior-mark-evidence-harvest-v1.part2.jsonl` | `53abae435ddd90c01f9c688bdc740a5c0ebe8edd` |
| `prior-mark-evidence-harvest-v1.part3.jsonl` | `fe13f99fe831681a1149e9e31e9f508e5aef3f11` |
| `prior-mark-evidence-harvest-v1.part4.jsonl` | `b19703808a62ffb29c3abb14292aba5c70152c40` |
| `prior-mark-evidence-harvest-v1.part5.jsonl` | `c38d00f2379d0e8daaf15f094f7f44935d3e24fe` |
| `prior-mark-evidence-harvest-v1.part6.jsonl` | `59ea73ce7b339ad5cb487d0520ac078010954102` |
| `prior-mark-evidence-harvest-v1.manifest.json` | `d49f8b68261bab452ad8f9d2be7286854591be70` |
| `prior-mark-evidence-harvest-v1.assessment.md` | `7810429bc98b86c54260b55d160b00038b51cec3` |
| `scripts/validate-prior-mark-evidence-harvest-v1.py` | `34701d5ca501bd81927998546896992241a09d40` |
| `WHOLE_SYSTEM_RECONSTRUCTION_ROADMAP.md` | `c8896ea28536272cb536e6acc30b9d051f68dfba` |

## Validation at freeze

The exact committed packet set was reread before this freeze.

Validation passed:

- exactly 90 packets;
- unique and continuous IDs from `RLOP-001` through `RLOP-090`;
- all result statuses valid;
- all evidence provenance classes valid;
- all packets retain source references;
- all packets retain epistemic ceilings;
- all packet construction is marked independent;
- no new cross-source matching was performed;
- no universal-law labels were assigned;
- no candidate equivalence classes were created;
- no external semantic labels were imported.

## Scientific coverage

The harvest preserves recovered outcome-bearing Mark evidence from:

- earliest blind-world / conveyor recurrence and family-transfer tests;
- V5 real-corpus challenge;
- source-rule, relational-state, local-state and transition-grammar experiments;
- masked substitution, topology, vertex, edge, wiring and hierarchy experiments;
- relationship and recursive-composition interventions;
- V9–V30 operator/state/composition and Hebrew-glyph experiments;
- white-paint calibration, glyph-transfer and physical-witness tests;
- V35-P through the frozen V36 preregistration reading;
- V36;
- V38–V40;
- V42;
- V45–V48.

The harvest does not invent outcomes where none were recovered.

Explicit no-outcome/non-scientific-test custody remains for:

- V31–V34: no result lineage recovered;
- V37: preregistered/pre-outcome only;
- V41: preregistered/pre-outcome only;
- V43: execution blocked;
- V44: execution failure;
- V7 sparse compiler: engineering equivalence/scale validation only;
- white-paint candidate projector v4: no distinct scientific adjudication recovered.

## Canonical comparison rule

Future law-equivalence work should use `RLOP-007..RLOP-090` as the active packet corpus.

By default, direct `frozen_result` packets should be preferred for equivalence adjudication.

Post-result syntheses may be consulted only with their provenance visible. They must not silently become equivalent to direct frozen experimental endpoints.

## Preserved scientific asymmetries

The freeze intentionally retains tensions rather than resolving them.

Examples include:

- partial family transfer **and** large abstention;
- exact-identity signal **and** coarse-form signal;
- strong hierarchical compression **and** failed recursive-protection intervention;
- strong factorized composition **and** small residual higher-order information;
- V15 cross-system fingerprint signal **and** V16 stress failure;
- Hebrew operator main effect **and** failed Hebrew context interaction;
- stable fixed V46 atlas **and** failed V48 independently rebuilt coordinate equivalence.

These are constraints for the next experiment, not inconsistencies to erase.

## Next checkpoint

Design and freeze the **Law-Equivalence Adjudication Language** before opening candidate cross-source matches.

That language must decide, in substrate-neutral terms, when two independently discovered packets may count as:

- the same law;
- a specialization/generalization relation;
- an inverse;
- a composition;
- a contextual variant;
- or unrelated.

The comparison rules must be frozen before the candidate matches are inspected.

No global grammar is built at this freeze.
