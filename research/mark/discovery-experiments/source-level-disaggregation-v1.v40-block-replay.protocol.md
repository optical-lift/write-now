# Source-Level Disaggregation v1 — V40 Block Replay Protocol

Status: **FROZEN BEFORE PER-BLOCK OUTCOME QUERY**
Date: **2026-09-18**
Parent experiment: `mark:hebrew-context-field:v40`
Original complete result: `292e853991d1f1c5b544531aae687d8aaedff8c7`
Pre-outcome implementation freeze: `b7ad6a8843dcf2cd0282b25890b478f00560924b`

## Purpose

Localize the already-frozen V40 relational-placement result to non-overlapping heldout five-chapter blocks.

This replay changes only the final aggregation unit.

It does not alter:

- V40 holdout blocks;
- center-blind window definition;
- intrinsic target;
- 14 context features;
- training-only cutpoints;
- target alphabet;
- Naive Bayes alpha;
- context-destruction offsets;
- real/null scoring rule.

## Source unit

One V40 heldout five-chapter block.

Different blocks are non-overlapping evaluation observations.

Blocks in the same biblical book share a higher-level source group.

All blocks share one V40 training-derived model.

Certification class:

`NONOVERLAPPING_EVALUATION_SHARED_TRAINING`

## Frozen law target

Local anchor:

`MCR-016`

Shared strict-equivalence target:

`EQC-001 — Component inventory cannot substitute for relational placement/order.`

The local evidence is the V40 context-destruction contrast: actual positional context carries information that is lost when the right-context placement is deterministically mismatched.

## Frozen model

Use the original V40 Phase-A C1 model exactly:

- center target = V38 intrinsic class `length | equality_pattern | terminal_final_form`;
- destination alphabet = 64 most frequent training targets + `OTHER`;
- eligible window = four left + hidden center + four right tokens inside one frozen block/split;
- 14 neighbor-only features exactly as preregistered;
- features 1–10 use frozen training quintile cutpoints from the pre-outcome implementation note;
- features 11–13 use frozen integer categories;
- feature 14 is boolean;
- Naive Bayes alpha = 0.5;
- empirical training target prior;
- posterior normalized over 65 targets.

## Frozen nulls

For null `k=1..20`:

- keep the left context and center target fixed;
- replace the four-token right context using the original deterministic offset rule `10+k`;
- remain inside the same heldout block;
- use the corresponding negative offset when required by the frozen protocol;
- score with the same already-frozen training model.

## Per-block endpoint

For every block report:

- eligible center count;
- real C1 cross-entropy;
- each of the 20 null cross-entropies;
- number of nulls beaten by the real context;
- mean null CE;
- real-minus-mean-null delta.

## Local presence rule

A block earns:

`SOURCE_LOCAL_SUPPORT`

only when:

1. eligible centers >= 100; and
2. real C1 CE is lower than **all 20** deterministic context-destruction null CEs.

This is intentionally stricter than a sign-only criterion and directly mirrors the strongest published V40 placement result.

## Failure rule

Any other block is:

`UNRESOLVED_BY_SHARED_MODEL`

It does **not** become a negative law edge.

Failure of a globally trained C1 model or one null contrast in one block does not establish that the block lacks its own relational-placement dependence.

## No tuning

This threshold and all scoring rules are frozen before block outcomes are queried.
