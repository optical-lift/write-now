# Source-Level Disaggregation and Independence Certification v1 — Freeze

Status: **FROZEN**
Date: **2026-09-18**
Branch: `source-level-disaggregation-v1`
Parent local-catalogue freeze: `b5d0562212c5767f161c22aaae164b66af796f94`

## Core correction

Experiment surfaces are not source nodes.

V36, V38 and V40 reuse overlapping biblical evidence, including exact shared five-chapter holdout blocks.

For reconstruction purposes, the current primary raw source unit is therefore:

> **canonical biblical book**

## Certified raw source layer

- raw book nodes: **23**
- raw observation independence: `CERTIFIED_NONOVERLAPPING_BOOK`
- shared model dependence retained separately:
  - `V36_SHARED_TRAINING_MODEL`
  - `V38_SHARED_TRAINING_MODEL`

This means book observations are non-overlapping, but source edges are not independent model fits.

## EQC-001

Source-local `PRESENT`:

- BOOK-Deu
- BOOK-Jdg

Evidence comes from V36's already-published frozen book-level order-control results.

BOOK-Psa and BOOK-Job remain unresolved because V36 explicitly reported their strict-support samples as too sparse.

## EQC-002

A source-local replay of the frozen V38 A1 endpoint was preregistered before opening block outcomes.

Result:

- 41 holdout blocks
- 24 source-local-support blocks
- 17 unresolved blocks
- 18 distinct books with at least one source-local-support block

The replay recombines to the original V38 aggregate within rounding:

- transitions: 58,691 exactly
- conditional CE difference from published: < 5e-7
- unigram CE difference from published: < 4e-6

EQC-002 `PRESENT` books:

- BOOK-1Sa
- BOOK-2Ch
- BOOK-2Ki
- BOOK-Amo
- BOOK-Dan
- BOOK-Deu
- BOOK-Eze
- BOOK-Ezr
- BOOK-Gen
- BOOK-Isa
- BOOK-Jdg
- BOOK-Jer
- BOOK-Jon
- BOOK-Jos
- BOOK-Lev
- BOOK-Mal
- BOOK-Num
- BOOK-Zec

## Co-presence

Only:

- BOOK-Deu
- BOOK-Jdg

currently carry `PRESENT` entries for both EQC-001 and EQC-002.

This is descriptive co-presence only.

It is not evidence of composition.

## Negative-evidence custody

No failed shared-model transfer was promoted to a negative law edge.

Cells without positive local support remain `MEASUREMENT_UNRESOLVED`.

A global model may fail in a book even when the book has a source-specific realization of the law.

## Overlap-graph readiness

Verdict:

`READY_FOR_DESCRIPTIVE_OVERLAP_GRAPH_WITH_SHARED_MODEL_DEPENDENCE`

The first graph may describe where frozen laws are locally supported across non-overlapping raw source books.

It may not:

- count book edges as independent model replications;
- infer universality from edge frequency;
- infer composition from co-presence;
- use experiment-name nodes as independent sources;
- include canon in the primary Mark graph;
- turn unresolved cells into negative edges.

## Frozen artifact blobs

- overlap audit: `84dc54f390dfe8edf396c0aba3525765c0e278db`
- V36 retrospective localization: `c73798778bc2d5faaa61a7957ab9d12bd810d9c6`
- V38 block replay protocol: `6bb50aabcc3728c5a4fb32d2e799ec770951e679`
- V38 block replay result: `5a3b43b86e640e2b49c536fd6f7f2d66097e1c93`
- V38 replay verification: `14835d9d93701a945cfbb1c633b17df80e036777`
- raw book registry: `389fa30e3ba3194a2f5458152918e1f4154ec857`
- raw book catalogues: `304f638db88d23f29b447fc64171bac48848690e`
- raw book catalogue schema: `a538c680de5af6c39bb1919afe8cfc1d92061fa6`
- assessment: `ebabf6e069c0bb939a6ff2f94e68c6f54ee9d62a`
- manifest: `f38a962eb7562d404cd81e04c9895cd0fe024a61`
- validator: `4d0ff9ff20312b461b03b2ba108fe3497db0336a`
- roadmap: `6ab918d84ccfd3cb629d6e3263873db63318d459`

## Pre-freeze head

`589a288a216c92b057aa1433ffa7d097cccc999a`

## Next checkpoint

**Cross-Source Overlap Graph v1**

Use BOOK-* nodes and frozen source-law entries only.
