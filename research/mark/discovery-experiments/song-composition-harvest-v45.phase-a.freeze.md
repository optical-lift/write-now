# Mark V45 Phase-A final freeze

**Experiment:** `mark:song-composition-harvest:v45`  
**Phase:** A  
**Status:** CLOSED / FROZEN  
**Date:** 2026-09-18

## Closure commits and immutable identities

- V45 implementation SHA: `c6d51f22357ddbc457c886965a79d30a913b0b1b`
- Pre-execution freeze SHA: `f561a17386c2a292db2c0dae245ef78ee4ca1ac6`
- Bound pre-outcome branch head: `b5b37209e5644d0a3366d0dc060603db72089f6b`
- Candidate closure commit: `fba0965e11253f9b66ac68c4a591a0964f1892f3`
- Candidate closure blob: `f5b4908cb28939ac2b044628a903c3ff8d7e6d99`
- Summary commit: `e1b99dfbf13b4f9830c8ddc529b6cce803ad51db`
- Summary blob: `08caaabb9caea7c62c5710cd7635c82cdb5c27fc`
- Result commit: `73d39d9d243ce4826cd79e5b7a42bc0d1853cd77`
- Result blob: `53c49d6270b032422d4b29e34f3ae22695f655f8`

The exact runner-produced candidate packet is bound by SHA-256:

`4701952d164c21dd39105d74f1fe4441e423c80259d3f6887f9f6697ad690ed6`

The exact runner-produced summary is bound by SHA-256:

`1af05d7fadad125ae8c9996682fd9ed42e9161dc2e44236db206c9590d1b3cf7`

## Engine custody

- Primary train freeze SHA-256: `1d4a15ccb08fc27137695504a865c1cbd8d36954e07d0552a151582fcee9b0f3`
- Primary result SHA-256: `06e9d515dc898dd330d962c304c1ad0e61631a058a6191ffa10ed87a06ca05e3`
- Topology train freeze SHA-256: `7b4280663a593a3860fec5b9fe5c02740117d8b701831a7d51a3bd04581a20ac`
- Topology result SHA-256: `86e3d0d5ddb21a4008eb9b04123882aa19170952eb63742d7c6718b1440f6625`

The V44/V45 pre-holdout train-freeze comparison passed byte-for-byte for both primary and topology protocols before holdout opened.

## Frozen corpus

No new source was acquired during V45.

- pair-eligible observations: 433
- train: 84 observations / 43 distinct sources
- holdout: 230 / 154
- control: 119 / 63

Frozen lane hashes remain those recorded in the pre-execution config.

## Frozen Phase-A statuses

- **CR-001 — HARVESTED_RULE:** factorized sequential operator composition.
- **CR-002 — HARVESTED_RULE:** supported operator repetition / idempotence.
- **CR-003 — HARVESTED_RULE:** supported ordered-pair operational cancellation.
- **CR-004 — INSUFFICIENT_CONTRAST:** order sensitivity / noncommutativity.
- **CR-005 — INSUFFICIENT_CONTRAST:** input-conditional composition.

These statuses may not be retroactively changed after Song semantics are opened.

## First compiler handoff

The first compiler handoff is **CR-001**.

The compiler should first test whether two independently identified physical operators can be composed using their already-learned consequence relations, without inventing a special semantic relation for the pair.

CR-002 and CR-003 are retained as additional harvested constraints/laws.

The direct-pair residual advantage over first-order composition remains an explicit residual. It is not permission to refit Phase A after seeing semantics.

## Semantic boundary

Up to and including this freeze:

- Song ontology files were not opened;
- Song relation-family names were not used;
- translations were not used;
- named glyph meanings were not used;
- historical/theological semantic assignments were not used to construct, select, tune, or adjudicate V45.

**This commit closes the Phase-A blind boundary.**

Only after this freeze commit exists may the research process read the governed Song ontology handoff and ask whether the already-frozen physical rules correspond to compiler-level semantic structures.

The first post-freeze task must preserve the direction of inference:

`frozen physical rule -> Song compiler test`

not:

`Song semantic expectation -> reinterpret or retune Mark evidence`.
