# V38 Phase A Result — Hebrew-Only Latent Structural Field

**Experiment:** `mark:hebrew-latent-structural-field:v38`  
**Date:** 2026-09-07  
**Witness status during all results below:** SEALED — no V38 query of `draft.canon_masoretic_marks` had been made.

## Source-role correction

V38 does not treat the Masoretic marks as the target system. Phase A asks whether a structural field can be recovered and validated from the Hebrew consonantal carrier alone. The Masoretic layer remains an external witness until the freeze boundary represented by the commit containing this file.

## Frozen carrier and representation

- canonical tokens: 306,785
- exact consonantal skeleton types: 39,956
- identity-blind primary shape classes before support filtering: 739
- primary state: `length | equality_pattern | terminal_final_form`
- training support threshold: 100 tokens
- supported states: 74
- top profile dimensions: 64 states + `OTHER`
- supported inventory MD5: `1b60fb1eb8b1408e0c00fb4ffb4d2b67`
- top-64 MD5: `e48ff566723f05257e4bc75b1871b90c`
- 5-NN graph edges: 370
- graph MD5: `409afff01e748bfd19242fd2600c05a0`
- graph mean retained-neighbor JS distance: 0.0283534023
- graph minimum retained-neighbor distance: 0.0022478045
- graph maximum fifth-neighbor distance: 0.0718362474

The full supported inventory and profile dimensions are in `hebrew-latent-structural-field-v38.inventory.json`. The graph is reproducible with `hebrew-latent-structural-field-v38.extract.sql`.

## Implementation correction before interpretation

The first A1 SQL pass mistakenly collapsed supported source states that were not in the top-64 destination alphabet into `OTHER`. The frozen protocol defines the top-64 restriction for destination/profile dimensions, not for supported source-state identity. This was corrected in implementation without changing the protocol, split, threshold, smoothing, state definition, or endpoint. The corrected A1 values below are the reportable primary result. The erroneous pass was 2.835990 vs 2.843770 nats and is preserved here for custody rather than hidden.

## A1 — heldout next-state cross-entropy

Heldout consecutive-token transitions: **58,691**.

Primary identity-blind state:

| metric | transition model | unigram baseline |
|---|---:|---:|
| cross-entropy, nats/token | **2.836068** | 2.843770 |
| bits/token | **4.091582** | 4.102693 |
| perplexity | **17.0486** | 17.1804 |

Delta transition minus unigram: **-0.007701 nats/token**.

Training supported-state coverage: **97.94%**.  
Heldout supported-state coverage: **97.54%**.

Interpretation: the Hebrew-only primary state has a small but positive heldout sequential predictive advantage over unigram. The effect is real in sign under this frozen endpoint but small in magnitude.

## A2 — order sensitivity

Heldout triples: **58,650**.

Mean log transition score:

- real order: **-5.671965**
- reverse: **-5.731011**
- deterministic rotation: **-5.699265**

Pairwise triple fractions:

- real > reverse: **45.87%**
- real = reverse: **10.56%**
- real > rotation: **51.75%**
- real = rotation: **1.47%**

Interpretation: real order has the best mean heldout score against both controls, but it does not beat reversal on a majority of individual triples. Therefore V38 Phase A supports only **weak directional organization**, not a strong path-level order discriminator.

## A3 — recurrence and coverage

- supported states: **74**
- training supported-state token coverage: **97.94%**
- holdout supported-state token coverage: **97.54%**
- observed training source→destination edges: **3,146**
- heldout transition previously observed in training: **99.666%**

This is a dense recurrent state field rather than a sparse collection of one-off types. However, the high seen-transition rate also means A1 is testing generalization of transition probabilities across heldout passages more than discovery of wholly novel transition types.

## A4 — final-form ablation

Removing `terminal_final_form` reduces supported states from 74 to **55**.

Heldout A1:

- conditional: **2.392135 nats/token**
- unigram: **2.397704 nats/token**
- delta: **-0.005570 nats/token**

Heldout A2 means:

- real: **-4.784023**
- reverse: **-4.827584**
- rotation: **-4.804007**

Fractions:

- real > reverse: **43.01%**
- real > rotation: **50.25%**

Because the ablated alphabet differs, absolute cross-entropies are not directly comparable to the primary state. The relevant comparison is the advantage over each lane's own unigram: the primary state gains about 0.00770 nats versus about 0.00557 without final-form information. Final-form orthography therefore contributes some of the Hebrew-only sequential signal under this representation.

## A5 — exact consonantal skeleton upper-bound / lexical control

Training support threshold: 20 occurrences.

- supported exact skeletons: **1,619**
- training token coverage: **65.45%**
- holdout token coverage: **59.43%**
- heldout transitions: **58,691**
- conditional cross-entropy: **4.496937 nats/token**
- unigram cross-entropy: **4.447066 nats/token**
- delta: **+0.049871 nats/token**
- conditional perplexity: **89.74**
- unigram perplexity: **85.38**

Exact consonantal identity performs **worse** than unigram on this heldout next-state task. Therefore the modest primary-state generalization is not explained by simply memorizing consonantal word identity under this frozen control.

## Phase A verdict

Phase A does **not** justify saying that the authentic underlying mark system has been recovered.

What it does justify saying is narrower:

> An identity-blind structural partition derived solely from the Hebrew consonantal surface shows a small heldout sequential advantage over unigram, preserves a weak real-order advantage in mean path score, and generalizes better than an exact consonantal-identity transition model under the frozen controls.

This is enough to proceed to the preregistered external-witness test, because Phase A did recover a measurable Hebrew-only structural signal. It is not strong enough to identify that signal with a historical mark system.

## Witness-opening boundary

After this file is committed, the V38 Phase A representation, holdout, support thresholds, smoothing, graph rule, endpoints, inventory hashes, profile dimensions, and graph hash are frozen. Only after that commit may V38 read the Masoretic witness for Phase B.

No Phase B outcome may retroactively alter Phase A. Any changed representation becomes robustness or V39.
