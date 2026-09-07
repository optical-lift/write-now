# V38 Phase B Result — External Masoretic Witness Test

**Experiment:** `mark:hebrew-latent-structural-field:v38`  
**Date:** 2026-09-07  
**Phase-A witness-opening boundary:** `41648536d194a8e7676665a9f6a93c3822d5ca87`

## Governing role

The Masoretic layer is evaluated here only as an external historical witness. It does not define the V38 Hebrew latent states, graph, support, split, smoothing, or Phase-A endpoints.

The witness was not queried for V38 until after the Phase-A freeze boundary above.

## Witness inventory

Primary witness eligibility: exactly one U+0591–U+05AF cantillation codepoint attached to a token in `mt_noel_current`.

- training witness-eligible tokens: **186,351**
- holdout witness-eligible tokens: **44,384**
- observed anonymous witness identities: **29**

No conventional accent names were used in scoring.

## Primary models

- **W0 frequency:** training-wide witness frequency
- **W1 blind Hebrew state:** `P(mark | primary identity-blind Hebrew state)`, alpha=5 shrinkage to W0
- **W2 graph-smoothed state:** 0.5 W1 + 0.5 mean W1 over the five frozen Hebrew-graph neighbors
- **W3 exact consonantal skeleton:** `P(mark | exact consonantal skeleton)`, same smoothing; lexical upper-bound control

A first W1 query used witness-eligible token counts to determine whether a Hebrew state was supported. That does not match the frozen Phase-A support inventory, which is defined from all Hebrew training tokens. The reportable W1 values below use the frozen 74-state Phase-A inventory. The earlier discrepant W1 cross-entropy was 2.457705 nats versus the corrected 2.458024 nats; it is preserved here for custody.

## Full holdout results

| metric | W0 frequency | W1 blind state | W2 graph-smoothed | W3 exact skeleton |
|---|---:|---:|---:|---:|
| cross-entropy, nats | 2.481724 | **2.458024** | **2.457015** | **2.365328** |
| top-1 | 17.98% | **19.41%** | **19.41%** | **21.12%** |
| top-3 | 47.49% | **48.51%** | 48.30% | **52.62%** |
| top-5 | 67.14% | **67.47%** | 67.30% | **71.71%** |
| MRR | 0.3874 | **0.3995** | 0.3986 | **0.4235** |

Entropy reduction versus frequency:

- W1: **0.02370 nats/token** = 0.03419 bits/token
- W2: **0.02471 nats/token** = 0.03565 bits/token
- W3: **0.11640 nats/token** = 0.16792 bits/token

### Primary reading

The independently recovered Hebrew state predicts part of the Masoretic witness better than raw witness frequency. The graph neighborhood adds only a very small further cross-entropy improvement and does not improve most rank endpoints. Exact consonantal identity remains substantially stronger than the current identity-blind state.

Therefore the present result is **partial correspondence**, not recovery of the witness from the latent state and not evidence that the Masoretic layer is the authentic underlying system.

## Anti-lookup subset 1 — unseen consonantal skeletons

Heldout witness-eligible tokens whose exact consonantal skeleton had zero training occurrences: **6,177**.

| metric | W0 | W1 | W3 |
|---|---:|---:|---:|
| cross-entropy, nats | **2.436023** | 2.436496 | **2.436023** |
| top-1 | 15.35% | **19.75%** | 15.35% |
| top-5 | **69.61%** | 69.18% | **69.61%** |
| MRR | 0.3783 | **0.4026** | 0.3783 |

W3 necessarily falls back to W0 here.

This subset is mixed: W1 substantially improves top-1 and MRR, but slightly worsens cross-entropy and top-5. The blind state therefore carries some ranking information beyond exact-word lookup, but the unseen-skeleton result is not a clean probabilistic win.

## Anti-lookup subset 2 — variable-mark skeletons

Heldout tokens whose exact consonantal skeleton participates in at least two distinct witness identities across the eligible corpus: **39,574**.

| metric | W0 | W1 | W3 |
|---|---:|---:|---:|
| cross-entropy, nats | 2.494422 | **2.467910** | **2.363880** |
| top-1 | 18.22% | **19.33%** | **21.74%** |
| top-5 | 66.35% | **66.81%** | **71.47%** |
| MRR | 0.3868 | **0.3976** | **0.4273** |

Exact consonantal identity remains strongly informative even where the same skeleton can take more than one witness identity. That means lexical identity is not merely functioning as a one-word/one-mark lookup; it captures contextual distributions that the present blind state does not.

## Witness-label nulls

The preregistration specified 20 deterministic frequency-stratified witness-label permutations. The operational null used here permutes **training witness labels within five training-frequency strata while leaving heldout witness labels observed**, thereby breaking the Hebrew-state↔witness-label association while approximately preserving frequency class. A simultaneous train+holdout relabel would be mathematically label-invariant and would not constitute a null test.

W1 cross-entropy under the 20 null assignments:

`2.6892, 2.6113, 2.6713, 2.7032, 2.7123, 2.6498, 2.7133, 2.6385, 2.6941, 2.6646, 2.6666, 2.7364, 2.6877, 2.7201, 2.6651, 2.6561, 2.6396, 2.6815, 2.6983, 2.6843`

- null mean: **2.67917 nats**
- null minimum: **2.61130 nats**
- null maximum: **2.73643 nats**
- real W1: **2.45802 nats**

Real alignment outperforms all 20 deterministic nulls on this endpoint.

Because the preregistration did not explicitly say whether witness-label permutations were applied to training only or simultaneously to evaluation labels, this operational interpretation is documented rather than hidden. It should be repeated as an explicitly specified robustness test if the null becomes central to a later claim.

## Phase B verdict

The strongest warranted statement from V38 so far is:

> A structural partition recovered from the Hebrew consonantal surface without using Masoretic information has a small but reproducible relationship to the later Masoretic witness. The relationship beats raw mark frequency on the full heldout set and beats all 20 frequency-stratified training-label nulls, but exact consonantal identity explains substantially more of the witness distribution, and the unseen-skeleton test is mixed.

This supports treating the Masoretic layer as a **partial or transformed witness to structure present in the Hebrew carrier**, rather than treating it as the source definition of that structure.

It does **not** establish that the V38 state field is the authentic original mark system.

## What changed relative to the V36/V37 framing

V36/V37 asked how Masoretic glyph identity/form predicts Hebrew operators. V38 shows why those results must not be read as though the Masoretic system were automatically upstream.

A Hebrew-only field can be built and validated before the Masoretic witness is opened, and that independent field later shows non-random correspondence with the witness. This makes the scientifically cleaner causal/source-role diagram:

`Hebrew carrier structure ↔ unknown latent/upstream system ? ↔ Masoretic witness`

rather than:

`Masoretic marks = target system → Hebrew`

The question mark remains intentional.

## Next scientific move

The present primary state is deliberately austere: consonantal length, identity-blind repetition topology, and terminal final-form status. It finds only a small Hebrew-only signal. The next experiment should expand the **Hebrew-derived** latent representation itself—still without Masoretic access—using local consonantal transformations, positional recurrence, repeated-root-shape relations without lexical labels, and longer-range sequence structure. That should be preregistered as V39 rather than tuned inside V38.
