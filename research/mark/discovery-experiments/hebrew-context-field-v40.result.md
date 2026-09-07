# V40 — Hebrew Context/Cadence Field — Complete Result

**Experiment ID:** `mark:hebrew-context-field:v40`  
**Date:** 2026-09-07

Custody chain:

- preregistration: `9d1b7ab463708129a818ed884b1fc57a7e5f7fb7`
- pre-outcome implementation freeze: `b7ad6a8843dcf2cd0282b25890b478f00560924b`
- null-index freeze: `26e4926ef08ba5bc3ff8706c3b3194ac20fd6d49`
- Phase-A Hebrew-only result: `369b2078e2587af7db88c3703c0a4277be41b083`
- witness-opening boundary: `1366952688ac0b16114019e1c84e78d11ae684a6`

## Bottom line

V40 does **not** satisfy its full preregistered Phase-A success criterion because full bidirectional C1 does not beat right-only C3 on complete heldout Hebrew cross-entropy. That failure is retained.

Nevertheless, V40 establishes three narrower observations:

1. Center-blind surrounding Hebrew cadence contains heldout information about the center intrinsic structure, particularly when the center consonantal skeleton was absent from training.
2. All 20 preregistered right-context destruction nulls are worse than the real center-blind context.
3. After the Hebrew-only field was frozen and the Masoretic layer opened solely as an external witness, center-blind cadence contains a small amount of witness information on its own and contributes complementary information when combined with the center intrinsic state, including on unseen center skeletons.

The appropriate interpretation is **partial center-blind structural correspondence**, not recovery of the authentic historical mark system.

---

# Phase A — Hebrew only

Eligible heldout centers: **67,962**.

| Model | CE nats | bits | perplexity | top-1 | top-5 | top-10 | MRR |
|---|---:|---:|---:|---:|---:|---:|---:|
| C0 unigram | 2.862013979 | 4.129013375 | 17.496730 | 16.8947% | 61.6344% | 80.0874% | 0.366520 |
| C1 full center-blind | **2.859429105** | 4.125284190 | 17.451561 | **17.3862%** | 61.5403% | **80.4803%** | **0.368935** |
| C2 left-only | 2.859962596 | 4.126053855 | 17.460874 | 17.2258% | 61.6109% | 80.3184% | 0.368098 |
| C3 right-only | **2.859391168** | **4.125229457** | **17.450899** | 17.0919% | **61.6462%** | 80.3302% | 0.367586 |

C1 beats C0 but misses the literal preregistered criterion because C3 is lower by ~0.00003794 nats/token.

## Phase-A unseen-center-skeleton subset

N = **6,943** heldout center tokens whose exact consonantal skeleton has zero V40 training occurrences.

| Model | CE nats | top-1 | top-5 | top-10 | MRR |
|---|---:|---:|---:|---:|---:|
| C0 | 3.662970332 | **12.8907%** | 37.4334% | 57.6408% | **0.242291** |
| C1 | **3.623982245** | 9.9237% | **39.3346%** | **61.5584%** | 0.237050 |
| C2 | 3.636550594 | 9.8372% | 38.1247% | 59.8300% | 0.230557 |
| C3 | 3.644738520 | 11.0327% | 37.9375% | 60.3918% | 0.238853 |

C1 improves C0 by **0.038988087 nats/token** and beats both one-sided models on cross-entropy. Ranking endpoints remain mixed.

## Phase-A context destruction

Real C1 CE: **2.859429105**.

Twenty mismatched-right-context nulls:

`2.872256, 2.870996, 2.870249, 2.870959, 2.871579, 2.871778, 2.872856, 2.872383, 2.872949, 2.872461, 2.873454, 2.872834, 2.873363, 2.872808, 2.872898, 2.873299, 2.872927, 2.874260, 2.875547363, 2.873637605`

- best null: **2.870248992**
- mean null: **2.872674674**
- worst null: **2.875547363**
- real beats **20/20** nulls.

Thus actual local right-context placement contains information that is destroyed by the deterministic mismatch control.

---

# Phase B — Masoretic layer as external witness

The witness was not opened until after commit `1366952688ac0b16114019e1c84e78d11ae684a6`.

Witness inventory:

- 29 anonymous cantillation identities
- 177,962 V40-eligible training witness centers
- 51,648 V40-eligible heldout witness centers

Models:

- M0 = training-wide witness frequency
- M1 = center-blind cadence Naive Bayes using the same frozen 14 V40 bins
- M2 = center intrinsic state categorical witness model
- M3 = frozen equal-weight 0.5/0.5 combination of M1 normalized log posterior and M2 log probability
- M4 = exact center consonantal skeleton upper bound

## Full heldout witness set

| Model | CE nats | top-1 | top-3 | top-5 | MRR |
|---|---:|---:|---:|---:|---:|
| M0 frequency | 2.475548073 | 16.6976% | 47.9515% | 67.5147% | 0.381654 |
| M1 center-blind cadence | 2.473702951 | 17.1585% | 47.8412% | 67.4024% | 0.383617 |
| M2 center intrinsic | 2.450737882 | 18.8836% | 49.1965% | 67.7471% | 0.398012 |
| M3 cadence + intrinsic | **2.446545135** | 19.1992% | 48.7550% | **67.8129%** | **0.398509** |
| M4 exact skeleton | **2.341605047** | **22.9244%** | **54.4939%** | **72.5236%** | **0.438974** |

M1 improves M0 by **0.001845123 nats/token**. M3 improves M2 by **0.004192747 nats/token**. Exact skeleton remains much stronger on familiar-word-dominated full evaluation.

## Unseen-center-skeleton witness subset

N = **6,124** witness-eligible heldout centers whose exact consonantal skeleton has zero witness-training occurrences.

M4 necessarily falls back to M0 on this subset.

| Model | CE nats | top-1 | top-3 | top-5 | MRR |
|---|---:|---:|---:|---:|---:|
| M0 frequency | 2.432932026 | 13.6022% | 48.7916% | **70.6238%** | 0.373748 |
| M1 center-blind cadence | **2.432908326** | 16.0843% | 48.9059% | 70.1012% | 0.383688 |
| M2 center intrinsic | 2.439224490 | 19.5950% | **50.0163%** | 69.4971% | 0.404364 |
| M3 cadence + intrinsic | **2.413657009** | **20.8197%** | 49.1672% | 70.3952% | **0.411119** |
| M4 exact skeleton fallback | 2.432932026 | 13.6022% | 48.7916% | **70.6238%** | 0.373748 |

Important distinctions:

- M1 technically improves M0 in the preregistered primary cross-entropy endpoint, but only by **0.000023700 nats/token**. This is too small to describe as a strong standalone cadence-to-witness effect.
- M1 nevertheless improves top-1 by ~2.48 percentage points and MRR by ~0.00994, while slightly worsening top-5.
- M2 alone is worse than M0 in cross-entropy on unseen skeletons despite better ranking metrics.
- The frozen M3 combination is materially better: **2.413657009**, improving M0 by **0.019275017 nats/token** and M2 by **0.025567481 nats/token**. This indicates that the weak center-blind cadence signal contains information complementary to the center intrinsic state.

## Variable-witness-skeleton subset

N = **46,522**.

| Model | CE nats | top-1 | top-3 | top-5 | MRR |
|---|---:|---:|---:|---:|---:|
| M0 | 2.484887408 | 16.9318% | 47.5968% | 66.8694% | 0.381014 |
| M1 | 2.482948925 | 17.1467% | 47.4851% | 66.7985% | 0.382064 |
| M2 | 2.457432893 | 18.6406% | 48.8608% | 67.2456% | **0.395531** |
| M3 | **2.455319142** | **18.8384%** | 48.4502% | 67.2220% | 0.395162 |
| M4 | **2.345854686** | **23.0085%** | **54.4517%** | **72.2647%** | **0.438929** |

Again, exact skeleton dominates where it is available. M3 provides a modest cross-entropy gain over M2.

---

# Scientific interpretation

## What V40 supports

The data support the following narrower statement:

> Structural cadence in the Hebrew consonantal neighborhood contains information about a hidden center token even when the center consonants are unavailable. On center words absent from training, the bidirectional center-blind field improves heldout structural-state cross-entropy and beats either side alone. Destroying the actual right context weakens this prediction in all 20 preregistered nulls. After this Hebrew-only result was frozen, the same center-blind cadence field showed weak standalone correspondence with the external Masoretic witness and contributed complementary witness information when combined with center intrinsic structure, including on unseen center skeletons.

## What V40 does not support

V40 does not support saying:

- that its 14-feature cadence field is the authentic/original mark system;
- that the Masoretic witness is the original system;
- that the underlying system has been fully recovered;
- that the Hebrew was causally generated by the recovered field;
- that the field has established historical priority or provenance;
- that latent states have known semantic/theological meanings.

The strict Phase-A criterion failed and must remain part of the result.

## Direction implied for the next experiment

V40 suggests that the useful carrier may be **distributed and relational rather than token-local**, but its handcrafted aggregate cadence features are weak and the full-set bidirectional model is not optimal.

A next experiment should therefore preserve center blindness while testing a representation that can recover **position-specific trajectory across the entire surrounding window without using center identity**. It should be designed and frozen without Masoretic information, and should test whether the unseen-center effect replicates on a new deterministic holdout before any witness comparison.