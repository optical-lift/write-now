# Source-Local Law Expansion v1 — Assessment

Status: **COMPLETE — READY TO FREEZE**
Date: **2026-09-18**
Parent overlap-graph freeze: `67ff6a734b208b46a9ec175ba8dcf60ebc273700`

## Purpose

Cross-Source Overlap Graph v1 was source-honest but law-thin: 23 book sources and only two shared law nodes.

This checkpoint asks:

> Which additional already-supported Mark laws can be localized to raw sources from frozen evidence without changing the scientific rule?

## Admission rule

A law is source-localizable only if frozen evidence provides at least one of:

1. a source-level adjudication of the law contrast;
2. a direct positive local witness satisfying the frozen law criterion;
3. a frozen executable protocol that can be replayed source-locally without changing the representation, split, thresholds or model.

A source row alone is not enough.

A per-source accuracy without the law's null/control is not enough.

## V45 / V9 composition lineage

The strongest expansion comes from the operator-composition lineage.

A critical custody fact was recovered:

- frozen V9 evaluator result SHA-256:
  `06e9d515dc898dd330d962c304c1ad0e61631a058a6191ffa10ed87a06ca05e3`
- V45 recorded primary evaluator result SHA-256:
  `06e9d515dc898dd330d962c304c1ad0e61631a058a6191ffa10ed87a06ca05e3`

The files are byte-identical.

Therefore V9 and V45 are **one evidence lineage** for graph purposes.

They must not create duplicate law nodes or duplicate source recurrences.

## Three atomic Mark-local laws admitted

### MLAW-COMP-001 — factorized sequential composition

Historical anchors:

- MCR-020
- MCR-056
- CR-001

Law statement:

> For supported paths, the ordered consequence of A then B is constrained by composition of the independently learned one-step consequence relations and cannot be reduced to input state or either one-sided operator alone.

The exact frozen evaluator preserves a `sourceScores` row for every covered holdout source group.

Result:

- covered holdout source groups: **151**
- source groups where composition beats input-only: **151 / 151**
- minimum covered paths in a source: **2**
- maximum covered paths in a source: **63,522**

These are source-local directional transfer results under one shared frozen training model.

Evidence ceiling:

> A source edge says the frozen factorized model beats input-only in that source. Edge precision differs sharply by path count, and the 151 edges are not 151 independent model fits.

### MLAW-IDEM-001 — repetition stability

Historical anchors:

- MCR-021
- repetition half of MCR-057
- CR-002

The committed V45 candidate closure contains direct positive holdout witness records in:

- S000CD9B9CDAB347F
- S08D2070B1CF8C96A

Those two source groups receive conservative `PRESENT` evidence.

No other source group is inferred positive in v1.

A custody inconsistency is preserved:

- the V45 narrative/summary says six positive physical witnesses;
- the frozen candidate closure blob `f5b4908c...` contains two committed positive witness records.

v1 uses only the witness records actually present in the frozen closure.

### MLAW-CANCEL-001 — ordered cancellation

Historical anchors:

- MCR-022
- cancellation half of MCR-057
- CR-003

Direct positive holdout witness records are preserved in:

- S000CD9B9CDAB347F
- S0B6FA01FD1099102

Those two source groups receive conservative `PRESENT` evidence.

Again, no broader source distribution is inferred from aggregate transfer alone.

## Physical raw source nodes

The V45 holdout lane contains:

- 230 observations
- 154 distinct `sourceGroupId` values
- 151 source groups covered by CR-001

For v1 expansion, the 151 covered source groups may become graph source nodes with:

`DISTINCT_SOURCE_GROUP_IDS_WITH_NONOVERLAPPING_GROUP_MEMBERSHIP`

They retain shared model dependence:

`V9_V45_SHARED_TRAINING_MODEL`

They are not independent model fits.

## What was not localized

Several artifacts preserve per-source rows but not the source-local law contrast.

Examples:

### MCR-028 / MCR-029

The source-rule atlas preserves per-source context counts and accuracies for the blind attraction/exclusion rules.

It does **not** preserve a per-source matched-null expectation.

Therefore aggregate attraction/exclusion cannot be converted into hundreds of source-local law edges.

### MCR-034

Source-local state mixtures are preserved.

The spatial-destruction contrast itself is aggregate.

No source-local spatial-law edge is created.

### MCR-036 / MCR-037

Source transition profiles preserve local transition/program and commitment/return counts.

The frozen null-relative deviation/asymmetry test is not source-adjudicated.

Counts alone do not establish the law.

### MCR-038 / MCR-083 / MCR-087

These are intrinsically cross-source organization/recurrence laws.

They remain valid global-support evidence but are not single-source occurrence laws.

## Replay-capable bridge candidates

The branch audit found a high-value set whose frozen protocols and evaluators survive:

- MCR-069 — V20 context-conditioned operator
- MCR-072 — V23 glyph structural transition interaction
- MCR-089 — V23 Hebrew operator main effect
- MCR-078 — V29 temporal footprint
- MCR-015 / MCR-016 — V40 center/context field

These are the priority next targets because they can potentially connect:

- physical/glyph source-group nodes;
- Hebrew book nodes.

V20, V23 and V29 all retain frozen protocols, cores, evaluators and workflows.

V29 additionally uses a frozen whole-book Hebrew split, making book-local replay especially tractable.

## Current graph implication

If the V45 tranche is added to the existing graph without bridge replay, the primary graph contains:

### Source families

- 23 Hebrew book nodes
- 151 physical source-group nodes

### Law dimensions

Existing:

- EQC-001
- EQC-002

New:

- MLAW-COMP-001
- MLAW-IDEM-001
- MLAW-CANCEL-001

### Positive physical edges

- composition: 151
- idempotence: 2
- cancellation: 2

Existing book positive edges:

- EQC-001: 2
- EQC-002: 18

Total positive edges would be:

**175**

But the graph would have two disconnected evidence-family components:

1. book-state/order component;
2. physical operator-composition component.

That disconnectedness is not evidence for two ontologies.

It is first a **measurement-bridge problem**.

## Checkpoint verdict

`LAW_BREADTH_EXPANDED__CROSS_FAMILY_BRIDGE_NOT_YET_LOCALIZED`

The project should not yet compare whole-system reconstruction models.

The next checkpoint should explicitly recover bridge-law source distributions from the frozen cross-system experiments.

## Next checkpoint

**Cross-Family Bridge Localization v1**

Priority order:

1. V23: MCR-072 + MCR-089
2. V20: MCR-069
3. V29: MCR-078
4. V40: MCR-015 + MCR-016

The goal is not to make the graph connected.

The goal is to discover whether the already-frozen evidence actually supplies local law occurrences on both sides of the current component boundary.
