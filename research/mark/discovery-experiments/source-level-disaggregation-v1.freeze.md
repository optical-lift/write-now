# Source-Level Disaggregation and Independence Certification v1 — Freeze

Status: **FROZEN**
Date: **2026-09-18**
Branch: `source-level-disaggregation-v1`
Parent local-catalogue freeze: `b5d0562212c5767f161c22aaae164b66af796f94`

## Final correction

Experiment names are not independent source nodes.

The historical Mark evidence can be localized into heldout books and non-overlapping heldout blocks, but those local outcomes inherit shared models and law tests.

Therefore:

> **non-overlapping evaluation is not independent discovery.**

This checkpoint preserves both facts.

## Historical source-local evidence

### EQC-001

V36 whole-book heldout transfer:

- Deuteronomy — supported
- Judges — supported
- Psalms — unresolved for sparsity
- Job — unresolved for sparsity

V40 block replay:

- 41 heldout blocks
- 29 source-local-support blocks
- 12 unresolved blocks
- 18 support books

### EQC-002

V38 block replay:

- 41 heldout blocks
- 24 source-local-support blocks
- 17 unresolved blocks
- 18 support books

## Replay verification

### V38

The block decomposition recombines to the published aggregate:

- transitions: **58,691**, exact
- conditional CE: **2.8360684584**
- published: **2.836068**
- unigram CE: **2.8437660829**
- published: **2.843770**

### V40

The reconstructed replay reproduces the frozen experiment:

- total tokens: **306,785**
- training windows: **237,215**
- heldout windows: **67,962**
- model targets: **65**
- training OTHER targets: **6,022**

Real C1:

- replay: **2.85942910519731**
- published: **2.859429105**

All 20 context-destruction null aggregate CEs reproduce the published series to numerical precision.

## Strict certification census

Authoritative source-level record:

`source-level-disaggregation-v1.source-units.jsonl`

Total units: **86**

- `WHOLE_SOURCE_HELDOUT_TRANSFER`: **2**
- `NONOVERLAPPING_UNIT_SHARED_TRAINING`: **53**
- `UNRESOLVED_SOURCE_UNIT`: **31**
- `INDEPENDENT_LOCAL_DISCOVERY`: **0**

### EQC-001

- independent discovery count: **0**
- whole-source heldout transfer: **2**
- shared-training local support: **29**
- unresolved units: **14**
- distinct support books: **19**

### EQC-002

- independent discovery count: **0**
- whole-source heldout transfer: **0**
- shared-training local support: **24**
- unresolved units: **17**
- distinct support books: **18**

## Same-source co-occurrence

V38 and V40 share ten exact holdout blocks.

Six exact blocks support both current strict law signatures:

- `Zec:2`
- `Deu:3`
- `Dan:1`
- `Gen:1`
- `Isa:10`
- `2Ch:0`

This is same-source co-occurrence evidence.

It is not independent recurrence and does not establish composition.

## Superseded descriptive layer

The earlier 23-book raw-book registry/catalogues are preserved as historical provenance.

They predate the completed V40 disaggregation and are therefore **superseded for scientific counting** by the strict 86-unit certification record.

They may not be used to claim independent discovery.

## Graph readiness

A descriptive provenance graph is allowed if it preserves dependence classes.

The primary Step-8 cross-source overlap graph required for whole-system reconstruction remains gated because:

`independent_discovery_count = 0`

for both current strict law clusters.

## Governing next step

**Independent Source Law Discovery v1**

Each source container must be selected and sealed before discovery and must recover its own local law catalogue without importing:

- EQC labels;
- MCR labels;
- another source's state inventory;
- another source's operator vocabulary;
- a global model trained on comparison sources.

Only after several `INDEPENDENT_LOCAL_DISCOVERY` catalogues are frozen may strict cross-source equivalence reopen.

## Scratch-state cleanup

All temporary V40 replay tables and scoring functions created in Noel/Supabase for this checkpoint were dropped after the frozen results were committed.

No scratch research tables remain.

## Frozen artifact blobs

- certification spec: `5b256db903e30348f674cbc6604066edaa3d4c9a`
- V36 book localization: `f5d223377b5049cca1e59eb488426994360ba342`
- V38 replay protocol: `6bb50aabcc3728c5a4fb32d2e799ec770951e679`
- V38 replay result: `5a3b43b86e640e2b49c536fd6f7f2d66097e1c93`
- V40 replay protocol: `f645d64a4ded72dba0df9bad1cc5210039874527`
- V40 replay result: `4961f13ec28b74b413833604971936f5bcb63178`
- certified source units: `719ab643c350df91fd5819896e4d496ebc2d642d`
- co-occurrence record: `f88ab4b733b1cd70bf71b500194ae8938b27521e`
- strict summary: `365aa78e9c1c0a8a3dae51da8271c645736e987a`
- assessment: `b033ddc288b0d14030b1c68de68738e70d5af40b`
- manifest: `b701621f65039aa480f5f0b23ecb80f08e083197`
- validator: `cc3f1c73e528dd764e679539659f4135fd2ed801`
- roadmap: `f90b0a30aeb28679ecc304da0077058591ea141b`

## Pre-freeze head

`3a31a2ca0779734790763aed8ba34216ce8f74e4`

## Next checkpoint

**Independent Source Law Discovery v1**

Do not promote heldout transfer counts into independent discovery counts.
