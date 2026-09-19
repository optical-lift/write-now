# Source-Level Disaggregation and Independence Certification v1 — Assessment

Status: **COMPLETE — PRIMARY OVERLAP GRAPH GATED**
Date: **2026-09-18**
Parent local-catalogue freeze: `b5d0562212c5767f161c22aaae164b66af796f94`

## Purpose

Frozen Local Law Catalogues v1 exposed a real source-independence problem:

> V36, V38 and V40 are distinct experiments, but they reuse overlapping biblical books/blocks and shared training models.

This checkpoint asked how far the historical evidence can be disaggregated without pretending that repeated measurements of one corpus are independent discovery.

## Core result

The historical evidence contains strong source-local transfer and recurrence.

It does **not** contain independently discovered local laws under the project's strict whole-system standard.

Therefore two statements must remain separate:

1. a **descriptive provenance overlap graph** can now be drawn safely if it carries model-dependence metadata;
2. the **primary independent-discovery overlap graph** required for whole-system reconstruction remains gated.

The next scientific checkpoint is independent source-local discovery, not global assembly.

## Overlap audit

V36 held out four whole books:

- Deuteronomy
- Judges
- Psalms
- Job

V38 held out 41 deterministic five-chapter blocks.

V40 held out 41 deterministic five-chapter blocks.

V38 and V40 share **10 exact holdout blocks**.

V38 contains **11 holdout blocks** inside the four V36 books.

V40 contains **11 holdout blocks** inside the four V36 books.

Therefore:

> experiment boundaries are not source-independence boundaries.

## Certification classes

The frozen certification language distinguishes:

- `INDEPENDENT_LOCAL_DISCOVERY`
- `WHOLE_SOURCE_HELDOUT_TRANSFER`
- `NONOVERLAPPING_UNIT_SHARED_TRAINING`
- `UNRESOLVED_SOURCE_UNIT`

Only `INDEPENDENT_LOCAL_DISCOVERY` may contribute to an independent recurrence count.

No historical V36/V38/V40 source unit qualifies.

## V36 / EQC-001

The frozen published V36 result already localizes the order effect by whole book.

### Deuteronomy

n = 94 supported paths.

- real median rank: 64
- reversed: 122.5
- shuffled: 108
- real top-10: 6.38%
- reversed: 3.19%
- shuffled: 2.13%

### Judges

n = 43.

- real median rank: 40
- reversed: 230
- shuffled: 138
- real top-10: 6.98%
- reversed: 0%
- shuffled: 0%

Both qualify as:

`WHOLE_SOURCE_HELDOUT_TRANSFER`

for `EQC-001`.

Psalms (n=7) and Job (n=1) remain unresolved for sparsity.

This is strong whole-source transfer because the complete heldout book was excluded from V36 fitting.

It is not independent discovery because the law/test was defined outside those books.

## V38 / EQC-002

The aggregate V38 A1 endpoint was replayed block by block under a protocol frozen before local outcomes were opened.

Frozen replay protocol:

`0b49e2cd54ce7320c5dacbd8ab5ce12dd306d0d1`

The replay preserves the original state representation, deterministic split, training set, support threshold, destination alphabet, first-order transition model, alpha 0.5 smoothing and unigram baseline.

Only the final aggregation unit changes.

### Replay verification

The 41 block rows recombine to the published V38 result:

- transitions: **58,691**, exact;
- replay conditional CE: **2.8360684584**;
- published conditional CE: **2.836068**;
- replay unigram CE: **2.8437660829**;
- published unigram CE: **2.843770**.

The difference is rounding-scale only.

### Source-local result

Under the frozen rule `transitions >= 100 && conditional CE < unigram CE`:

- **24 SOURCE_LOCAL_SUPPORT** blocks;
- **17 UNRESOLVED_BY_SHARED_MODEL** blocks;
- support spans **18 books**.

Supporting blocks qualify as:

`NONOVERLAPPING_UNIT_SHARED_TRAINING`

The exact block is held out, but other material from the same book may occur in training.

A failing block is not converted into a negative law edge because failure of the shared transition model is not equivalent to failure of every possible local state-dependent law.

## V40 / EQC-001

V40 had no published per-block table, so a source-local replay protocol was frozen before block outcomes were queried:

`1e0a1e8756eb98a50cee2e1f0a24e921076c0c2f`

The support criterion was intentionally strict:

- eligible centers >= 100; and
- real C1 CE must beat **all 20** frozen context-destruction nulls in that block.

### Replay identity verification

The reconstruction reproduces the original frozen V40 endpoint:

- total tokens: **306,785**
- training windows: **237,215**
- heldout windows: **67,962**
- training OTHER targets: **6,022**
- target classes: **65**

Real C1:

- replay: **2.85942910519731**
- published: **2.859429105**

All 20 null aggregate CEs reproduce the published series to numerical precision, including the published minimum and maximum.

Therefore the local replay is a faithful decomposition of the frozen V40 endpoint, not a new model.

### Source-local result

- **29 SOURCE_LOCAL_SUPPORT** blocks;
- **12 UNRESOLVED_BY_SHARED_MODEL** blocks;
- support spans **18 books**.

Supporting blocks qualify as:

`NONOVERLAPPING_UNIT_SHARED_TRAINING`.

## Exact same-source law co-occurrence

V38 and V40 have ten identical heldout blocks.

Among them:

- **6 support both EQC-002 and EQC-001**
- 2 support EQC-001 only under the frozen shared-model replay
- 2 remain unresolved in both

The six dual-support raw blocks are:

- Zec:2
- Deu:3
- Dan:1
- Gen:1
- Isa:10
- 2Ch:0

This is not independent recurrence.

It is direct **same-source co-occurrence evidence**:

> two separately frozen law tests succeed in the same raw source region.

That fact should be preserved for later system-composition work.

## Certification census

Across V36, V38 and V40 there are **86 source units**:

- `WHOLE_SOURCE_HELDOUT_TRANSFER`: **2**
- `NONOVERLAPPING_UNIT_SHARED_TRAINING`: **53**
- `UNRESOLVED_SOURCE_UNIT`: **31**
- `INDEPENDENT_LOCAL_DISCOVERY`: **0**

### EQC-001

- independent discovery count: **0**
- whole-source heldout transfer: **2**
- shared-training local supports: **29**
- unresolved source units: **14**
- distinct books with support: **19**

### EQC-002

- independent discovery count: **0**
- whole-source heldout transfer: **0**
- shared-training local supports: **24**
- unresolved source units: **17**
- distinct books with support: **18**

## What is now certified

The evidence supports these claims:

- the current laws are not artifacts of one aggregate score only;
- EQC-001 transfers into multiple non-overlapping heldout regions and two completely heldout books;
- EQC-002 transfers into 24 non-overlapping heldout blocks across 18 books;
- two current law signatures coexist in six exact raw source blocks;
- experiment-name nodes must never be counted as independent source nodes.

The evidence does **not** support:

- 53 independent discoveries;
- 18 independently trained source grammars;
- universality from book count;
- negative-law claims from unresolved blocks;
- composition merely from co-presence.

## Graph readiness distinction

A provenance-preserving descriptive graph is now possible.

It may display:

- book/block nodes;
- PRESENT transfer/support edges;
- unresolved/open cells;
- dependence groups;
- same-source co-occurrence.

But it may not be used as the Step-8 independent-discovery graph or as a universality count.

The primary reconstruction gate remains:

> at least several source containers must independently discover and freeze their own local law catalogues before cross-source equivalence is opened.

Historical disaggregation cannot manufacture that condition after the fact.

## Next checkpoint

**Independent Source Law Discovery v1**

The next experiment must select and seal genuinely isolated source containers before discovery.

Each source must recover its own local relational laws without receiving:

- EQC labels;
- MCR labels;
- another source's state inventory;
- another source's operator vocabulary;
- a global model fitted on the comparison sources.

Only after those local catalogues are frozen may the existing Law-Equivalence Adjudication language compare them.

That is the next legitimate route toward the whole-system reconstruction.
