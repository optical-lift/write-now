# V40 — Hebrew Context/Cadence Field

**Experiment ID:** `mark:hebrew-context-field:v40`  
**Date:** 2026-09-07  
**Status:** preregistered before V40 Hebrew holdout outcomes and before any V40 Masoretic witness query

## Why V40 exists

V38 found only a weak generalizable Hebrew-only intrinsic-state signal. V39 showed that adding local categorical pair relations fragments the state space and overfits: H2–H4 all worsened held-out Hebrew prediction, even though some of the same contexts predicted the Masoretic witness on familiar words. On unseen skeletons, those witness gains disappeared.

V40 therefore changes the recovery route rather than adding more local categorical detail.

The primary V40 representation is **center-blind**: it attempts to infer the structural character of a Hebrew token from the cadence and shape of the surrounding consonantal sequence while excluding the center token’s consonants, skeleton identity, intrinsic state, lemma, morphology, and Masoretic mark from feature construction.

If this field generalizes, it is harder to explain as exact-word lookup.

## Sealed witness rule

Until the V40 Phase-A freeze, V40 may not query or use:

- `draft.canon_masoretic_marks`
- cantillation identities
- niqqud
- center-token consonantal identity in primary context features
- center-token intrinsic state as an input feature
- `lemma_raw`
- `morph`
- Strong IDs
- translations
- conventional accent names
- inherited grammatical labels
- semantics

The center token’s consonantal surface is allowed only as the **Phase-A target** (its V38 intrinsic class) and for defining the anti-lookup subset after the model is frozen.

## Holdout

Five-chapter blocks use `block_index=floor((chapter-1)/5)`.

Rank by:

`md5('v40-hebrew-context-field|' || book || ':' || block_index), book, block_index`

Take the lowest 41 of 201 blocks.

Frozen holdout blocks in rank order:

1. Neh 11–13
2. Isa 26–30
3. Psa 71–75
4. Gen 16–20
5. Eze 21–25
6. Lev 21–25
7. Gen 6–10
8. Deu 16–20
9. Exo 6–10
10. Psa 21–25
11. Neh 6–10
12. Zec 11–14
13. Hag 1–2
14. 2Ch 1–5
15. Deu 21–25
16. 1Ki 16–20
17. Psa 31–35
18. 1Ch 26–29
19. Job 1–5
20. Psa 86–90
21. Num 11–15
22. Exo 11–15
23. Dan 6–10
24. Gen 46–50
25. Job 11–15
26. Isa 51–55
27. Sng 1–5
28. Job 16–20
29. Gen 1–5
30. Jer 26–30
31. Jer 51–52
32. Deu 26–30
33. 1Ch 21–25
34. 1Ch 1–5
35. Dan 11–12
36. Lev 16–20
37. 1Sa 1–5
38. Num 26–30
39. Deu 1–5
40. Eze 36–40
41. 1Ch 16–20

## Token-intrinsic target

For the center token only, derive the V38 identity-blind intrinsic target:

`length | equality_pattern | terminal_final_form`

This target is never an input to the primary V40 context model.

Destination alphabet: 64 most frequent **training** center intrinsic classes plus `OTHER`, frequency descending with state-key ascending tie break.

## Eligible center windows

A center token is eligible when four previous and four next canonical tokens all exist inside the same five-chapter block and split side.

Window:

`[-4,-3,-2,-1, CENTER, +1,+2,+3,+4]`

The center token contributes no primary input feature.

## Neighbor-only raw features

For each neighbor token independently derive:

- consonantal length
- terminal-final-form boolean
- equality complexity = distinct consonants / consonantal length
- intrinsic class (used only for distinct-count summaries, not as a positional categorical identity)

Exact neighbor skeleton identities may be used only for equality comparisons among **neighbors**. Their strings/codepoints are not retained.

From the four left and four right neighbors derive the following frozen numerical/context features:

1. `left_mean_len`
2. `right_mean_len`
3. `left_sd_len`
4. `right_sd_len`
5. `left_final_rate`
6. `right_final_rate`
7. `left_mean_equality_complexity`
8. `right_mean_equality_complexity`
9. `left_mean_abs_len_delta` across the three within-left adjacencies
10. `right_mean_abs_len_delta` across the three within-right adjacencies
11. `left_distinct_intrinsic_count`
12. `right_distinct_intrinsic_count`
13. `cross_side_same_skeleton_pairs` = number of equal-skeleton pairs among the 4×4 left/right comparisons, clipped at 4+
14. `boundary_bridge` = whether the final consonant of token -1 equals the first consonant of token +1

None of these features observes the center consonants.

## Training-only discretization

Features 1–10 are discretized using training-only quintile cutpoints at 20%, 40%, 60%, 80%. Ties use the lowest bin whose upper cutpoint is >= value. Features 11–13 use their integer categories with 13 clipped to `4+`. Feature 14 is boolean.

Cutpoints are frozen before V40 holdout scoring.

## Hebrew-only predictive models

### C0 — center-state unigram

Training-wide center intrinsic distribution.

### C1 — center-blind cadence Naive Bayes

For every target intrinsic category y and every feature j, estimate categorical `P(feature_j_bin | y)` from training center windows with symmetric Dirichlet alpha=0.5 across the observed training alphabet of that feature.

Score a candidate y for an evaluation center as:

`log P(y) + Σ_j log P(feature_j_bin | y)`

Normalize over the 65 target categories with log-sum-exp to obtain `P(y | context)`.

No feature interactions or context-key products are fit.

### C2 — left-only cadence ablation

Same as C1 but use only left-side features 1,3,5,7,9,11 plus no cross-side or boundary feature.

This tests whether bidirectional context is carrying information unavailable causally from the left.

### C3 — right-only cadence ablation

Same as C1 using only right-side features 2,4,6,8,10,12.

## Phase-A endpoints

On heldout eligible centers report C0–C3:

- cross-entropy nats/token
- bits/token
- perplexity
- top-1
- top-5
- top-10
- mean reciprocal rank

Primary V40 success criterion:

1. C1 heldout cross-entropy < C0, and
2. C1 heldout cross-entropy < both C2 and C3, and
3. C1 improves C0 on the unseen-center-skeleton subset defined below.

This is intentionally stricter than V38/V39.

## Anti-lookup subset

After model freeze, identify heldout center tokens whose exact consonantal skeleton has zero V40 training occurrences. The center skeleton is used only to assign membership in this evaluation subset; it was not available to C1–C3.

Report the same endpoints. The primary criterion requires C1 cross-entropy improvement over C0 on this subset.

## Context-destruction nulls

Run 20 deterministic nulls. Within each holdout block, replace the four-token right context of each eligible center with the four-token right context beginning at a deterministic offset 11–30 tokens later when it remains inside the same block; otherwise use the corresponding negative offset. Null k uses offset `10+k`, k=1…20.

The left context and center target remain fixed. Recompute C1 features using the mismatched right context but the already-frozen training cutpoints/model.

Real C1 should outperform the null distribution if cross-center cadence matters.

## Phase-A freeze boundary

Before any V40 query reads `draft.canon_masoretic_marks`, commit:

- preregistration
- machine-readable protocol
- training cutpoints
- top-64 target inventory
- model count hashes
- Phase-A results
- witness-opening boundary SHA

No Phase-B outcome may change V40’s representation or Phase-A verdict.

## Phase B — external witness comparison

After the freeze, primary witness-eligible center tokens carry exactly one U+0591–U+05AF cantillation codepoint.

### M0 — witness frequency

Training-wide witness frequency.

### M1 — center-blind cadence model

Use the same 14 frozen context features/bins. Fit training-only Naive Bayes `P(feature_bin | mark)` with alpha=0.5 and training mark prior. The center consonants/intrinsic state remain excluded.

### M2 — center intrinsic comparison

Categorical `P(mark | center_intrinsic)` with alpha=5 shrinkage toward witness frequency. This is the V38-style structural baseline and is not center-blind.

### M3 — cadence + intrinsic

Combine M1 log posterior score and M2 log probability with frozen equal weights 0.5/0.5 before normalization. This asks whether cadence adds information beyond center intrinsic state.

### M4 — exact center skeleton upper bound

Categorical `P(mark | exact_center_skeleton)` with alpha=5 shrinkage toward witness frequency. This is a lexical upper bound, not the recovered field.

## Phase-B endpoints

Report cross-entropy, top-1, top-3, top-5, MRR on:

- full heldout witness set
- unseen-center-skeleton subset
- variable-witness-skeleton subset

Primary witness interpretation requires M1 to outperform M0 on unseen center skeletons. If it does not, cadence-to-witness alignment is not considered generalizable.

## Interpretation

### Strong V40 pattern

If C1 beats C0/C2/C3, survives unseen center skeletons and context-destruction nulls, and M1 independently beats M0 on unseen witness skeletons:

> A center-blind structural field carried by surrounding Hebrew consonantal cadence generalizes to the hidden center structure and independently predicts part of the external Masoretic witness. This is stronger evidence for an underlying organization than V38/V39 because exact center-word identity was unavailable to the primary field.

This still does not prove historical identity with the authentic mark system.

### Hebrew-only success, witness failure

The Hebrew cadence field is real but does not correspond substantially to the Masoretic witness.

### Witness success without Hebrew success

Treat as witness-conditioned correlation, not recovery.

### Both fail

This context/cadence representation is rejected; investigate different carrier dimensions rather than adding features post hoc.

## Epistemic ceiling

V40 cannot alone establish historical provenance, causal generation, direct Masoretic descent, semantic meanings, or theological claims.