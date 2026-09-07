# V40 — Hebrew Context/Cadence Field — Phase A Result

**Experiment ID:** `mark:hebrew-context-field:v40`  
**Date:** 2026-09-07  
**Preregistration commit:** `9d1b7ab463708129a818ed884b1fc57a7e5f7fb7`  
**Pre-outcome implementation freeze:** `b7ad6a8843dcf2cd0282b25890b478f00560924b`  
**Null-index freeze:** `26e4926ef08ba5bc3ff8706c3b3194ac20fd6d49`  
**Status:** Phase A complete; Masoretic witness still unopened for V40 at the time of this result commit.

## Verdict

V40 does **not** satisfy its full preregistered primary success criterion because the full bidirectional center-blind model C1 does not beat both one-sided ablations on full heldout cross-entropy: right-only C3 is narrowly better than C1.

However, V40 shows a nontrivial center-blind effect that survives the anti-lookup subset and all 20 preregistered context-destruction nulls:

1. C1 improves over the center-state unigram C0 on the full heldout set.
2. On center consonantal skeletons absent from V40 training, C1 beats C0, C2, and C3 on cross-entropy.
3. All 20 deterministic mismatched-right-context nulls have worse cross-entropy than the real C1 context.

This is evidence for contextual information in the Hebrew-only surrounding field, but it is not sufficient to declare V40 a full recovery success under the frozen criterion.

## Full heldout set

Eligible heldout centers: **67,962**.

| Model | CE nats | bits | perplexity | top-1 | top-5 | top-10 | MRR |
|---|---:|---:|---:|---:|---:|---:|---:|
| C0 unigram | 2.862013979 | 4.129013375 | 17.496730 | 16.8947% | 61.6344% | 80.0874% | 0.366520 |
| C1 full center-blind | **2.859429105** | 4.125284190 | 17.451561 | **17.3862%** | 61.5403% | **80.4803%** | **0.368935** |
| C2 left-only | 2.859962596 | 4.126053855 | 17.460874 | 17.2258% | 61.6109% | 80.3184% | 0.368098 |
| C3 right-only | **2.859391168** | **4.125229457** | **17.450899** | 17.0919% | **61.6462%** | 80.3302% | 0.367586 |

Cross-entropy deltas versus C0:

- C1: **−0.002584874 nats/token**
- C2: **−0.002051383 nats/token**
- C3: **−0.002622812 nats/token**

C3 beats C1 by only **0.000037938 nats/token**, but the preregistered criterion is literal: C1 was required to be lower than both C2 and C3. It is not.

## Anti-lookup subset: unseen center skeletons

Heldout centers whose exact consonantal skeleton has zero V40 training occurrences: **6,943**.

The center skeleton is used only to define subset membership and was not available to C1–C3 as a predictor.

| Model | CE nats | bits | perplexity | top-1 | top-5 | top-10 | MRR |
|---|---:|---:|---:|---:|---:|---:|---:|
| C0 unigram | 3.662970332 | 5.284549133 | 38.976946 | **12.8907%** | 37.4334% | 57.6408% | **0.242291** |
| C1 full center-blind | **3.623982245** | **5.228301213** | **37.486552** | 9.9237% | **39.3346%** | **61.5584%** | 0.237050 |
| C2 left-only | 3.636550594 | 5.246433508 | 37.960669 | 9.8372% | 38.1247% | 59.8300% | 0.230557 |
| C3 right-only | 3.644738520 | 5.258246187 | 38.272764 | 11.0327% | 37.9375% | 60.3918% | 0.238853 |

Cross-entropy deltas versus C0:

- C1: **−0.038988087 nats/token**
- C2: **−0.026419738 nats/token**
- C3: **−0.018231813 nats/token**

On this anti-lookup subset, C1 is the best cross-entropy model and also has the best top-5/top-10. Top-1 and MRR are worse than C0, so the correct interpretation is improved probability allocation over the hidden structural state, not improved exact-state classification at every ranking endpoint.

## Context-destruction nulls

Frozen null rule: holdout left context and center target remain fixed; the four-token right context is replaced by the deterministic offset context defined in the preregistration/null-index note. The frozen C1 training model is not refit.

Real C1 cross-entropy: **2.859429105 nats/token**.

| Null | CE nats |
|---:|---:|
| 1 | 2.872256 |
| 2 | 2.870996 |
| 3 | 2.870249 |
| 4 | 2.870959 |
| 5 | 2.871579 |
| 6 | 2.871778 |
| 7 | 2.872856 |
| 8 | 2.872383 |
| 9 | 2.872949 |
| 10 | 2.872461 |
| 11 | 2.873454 |
| 12 | 2.872834 |
| 13 | 2.873363 |
| 14 | 2.872808 |
| 15 | 2.872898 |
| 16 | 2.873299 |
| 17 | 2.872927 |
| 18 | 2.874260 |
| 19 | 2.875547363 |
| 20 | 2.873637605 |

Null summary:

- best null: **2.870248992**
- mean null: **2.872674674**
- worst null: **2.875547363**
- real C1: **2.859429105**
- real beats all 20/20 nulls.

The real-vs-best-null margin is approximately **0.01082 nats/token**, considerably larger than C1's full-set improvement over C0. This indicates that the actual right context carries information that is lost by mismatching the right side, even though the frozen Naive Bayes combination is not globally better than the right-only ablation.

## Phase-A interpretation

The frozen primary criterion fails, so V40 must not be labeled a full Hebrew-only recovery success.

The strongest permitted statement is:

> A center-blind field derived from the surrounding Hebrew consonantal cadence carries heldout information about the hidden center structural class. The effect is especially visible on center words absent from training and is degraded by all preregistered right-context destruction nulls. However, the full bidirectional model does not beat the right-only ablation on the complete heldout set, so V40 does not satisfy its full preregistered success criterion.

This does **not** establish that V40's field is the authentic/original mark system, historical priority, causal generation, semantic meaning, or direct relationship to the Masoretic witness.

## Witness custody

At the time this file was committed, no V40 Phase-B query had read `draft.canon_masoretic_marks`. Phase B may begin only after a separate repository commit explicitly marks the witness-opening boundary.