# Source-Level Disaggregation v1 — V38 Block Replay Protocol

Status: **FROZEN BEFORE PER-BLOCK OUTCOME QUERY**
Date: **2026-09-18**
Parent experiment: `mark:hebrew-latent-structural-field:v38`
Original Phase-A freeze: `41648536d194a8e7676665a9f6a93c3822d5ca87`

## Purpose

Disaggregate the already-frozen aggregate V38 A1 result into non-overlapping heldout five-chapter blocks without changing the V38 representation, training set, transition model, smoothing, destination alphabet, or baseline.

This is a **post-hoc source-local replay of a frozen endpoint**, not a new discovery model.

## Source unit

One frozen V38 holdout block:

`book + block_index=floor((chapter-1)/5)`

There are 41 heldout blocks, fixed by the original V38 hash split.

Blocks do not overlap in token observations.

Blocks from the same biblical book are still treated as sharing a higher-level source group and must not be counted as fully independent book-level replications.

## Frozen model

Reproduce V38 A1 exactly:

- primary identity-blind state = `length | equality_pattern | terminal_final_form`;
- support threshold = 100 training tokens;
- supported source states remain distinct even when outside the top-64 destination alphabet;
- destination alphabet = training top 64 supported states + `OTHER`;
- training-only first-order transition model `P(next_dim | current_supported_state)`;
- alpha = 0.5;
- training unigram next-destination baseline over the same 65-category destination alphabet with alpha = 0.5;
- consecutive transitions may not cross book or five-chapter block boundaries.

## Per-block endpoint

For every holdout block report:

- heldout transition count;
- conditional cross-entropy;
- unigram cross-entropy;
- delta = conditional CE - unigram CE.

Negative delta means the frozen state-conditioned model predicts the block better than the frozen global next-state frequency baseline.

## Local presence rule

A block may be marked:

`SOURCE_LOCAL_SUPPORT`

only when:

- heldout transitions >= 100; and
- delta < 0.

This is evidence that the already-frozen V38 state/consequence relation transfers to that local block.

It is sufficient for a provisional `PRESENT` catalogue entry with an evidence ceiling recording that the model and training corpus are shared.

## Failure rule

If delta >= 0, or transitions < 100:

- do **not** assign `OPPORTUNITY_PRESENT_NO_INSTANCE`;
- do **not** assign `STRUCTURALLY_INCOMPATIBLE`;
- mark the local law status `UNRESOLVED_BY_SHARED_MODEL`.

Reason:

A globally trained transition model can fail in a block even if that block has its own state-dependent transition law with different local probabilities.

A negative transfer score is therefore not a clean absence test.

## Independence rule

For recurrence counting:

- different holdout blocks are non-overlapping evaluation observations;
- blocks in different books may be treated as distinct raw-source groups;
- all blocks share the same V38 training-derived model and are therefore **not statistically independent model fits**.

Certification label:

`NONOVERLAPPING_EVALUATION_SHARED_TRAINING`

No later analysis may call them fully independent experiments.

## No tuning

The threshold, sign criterion, source unit, and scoring formula may not change after block outcomes are queried.
