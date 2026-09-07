# V41 — Center-Blind Hebrew Positional Trajectory

**Experiment ID:** `mark:hebrew-positional-trajectory:v41`  
**Date:** 2026-09-07  
**Status:** preregistered before V41 Hebrew holdout outcomes and before any V41 Masoretic witness query

## Motivation

V40 found a weak but reproducible center-blind Hebrew context effect. On unseen center skeletons, the bidirectional surrounding field beat frequency and both one-sided ablations, and real context beat all 20 right-context destruction nulls. But V40 pooled much of the eight-token neighborhood into means/rates and failed its strict full-set criterion because right-only narrowly beat the full model.

V41 tests whether the surviving signal is carried by the **ordered trajectory of the surrounding positions** rather than by unordered neighborhood composition.

The Masoretic layer remains an external witness and is sealed throughout Hebrew-only Phase A.

## Sealed during Phase A

No V41 Phase-A feature, threshold, model, holdout, or endpoint may use:

- `draft.canon_masoretic_marks`
- cantillation or niqqud
- center-token consonants as predictors
- center intrinsic state as predictor
- lemma, morphology, Strong IDs
- translation, semantic labels, grammatical labels, accent names

The center consonantal skeleton is allowed only as the hidden target source and for anti-lookup subset membership.

## Holdout

Five-chapter blocks use `block_index=floor((chapter-1)/5)`.

Rank by `md5('v41-hebrew-position-field|' || book || ':' || block_index), book, block_index`; take the lowest 41 of 201.

Frozen holdout blocks in rank order:

1. Amo 1–5
2. 2Ch 31–35
3. Lev 1–5
4. 1Sa 26–30
5. 2Sa 16–20
6. Exo 26–30
7. 1Ki 21–22
8. Deu 26–30
9. Psa 11–15
10. Eze 6–10
11. Jer 1–5
12. Psa 76–80
13. Eze 26–30
14. Neh 11–13
15. Exo 21–25
16. Psa 91–95
17. Jdg 6–10
18. Jos 6–10
19. 2Ki 16–20
20. 2Ki 1–5
21. Deu 6–10
22. 1Ki 6–10
23. Psa 61–65
24. 1Ch 21–25
25. Eze 46–48
26. Gen 21–25
27. Psa 86–90
28. Eze 16–20
29. Job 31–35
30. Gen 36–40
31. Isa 41–45
32. Job 1–5
33. Neh 1–5
34. Psa 71–75
35. Jer 36–40
36. Jer 31–35
37. Jer 6–10
38. Psa 66–70
39. Psa 6–10
40. Zec 6–10
41. Num 26–30

## Eligible window

Center must have four previous and four following canonical tokens inside the same block/split:

`[-4,-3,-2,-1, CENTER, +1,+2,+3,+4]`

Center contributes no predictor feature.

## Target

V38 identity-blind center intrinsic class:

`length | equality_pattern | terminal_final_form`

Target alphabet = 64 most frequent training-window target classes + `OTHER`, selected before holdout scoring.

## Neighbor microfeatures

For each of the eight neighbor positions derive three identity-blind categorical features:

1. `L`: consonantal length, categories `1..8,9+`.
2. `R`: repeated-consonant excess = `length - distinct_consonant_count`, categories `0,1,2+`.
3. `F`: terminal-final-form boolean.

Consonant identities are never retained.

## Neighbor trajectory features

For each of the six true within-side adjacencies (-4→-3, -3→-2, -2→-1, +1→+2, +2→+3, +3→+4):

4. `DL`: signed length change, clipped categories `<=-3,-2,-1,0,+1,+2,>=+3`.
5. `DR`: signed repeated-excess change, categories `<=-2,-1,0,+1,>=+2`.

For the cross-center visible boundary (-1,+1), which is not treated as canonical adjacency:

6. `Xshared`: number of distinct consonant identities shared by -1 and +1, categories `0,1,2,3+`.
7. `Xboundary`: final consonant(-1) equals first consonant(+1), boolean.

These equality operations discard consonant identity after comparison.

## Models

All use empirical target prior and symmetric Dirichlet alpha=0.5 categorical emissions. Scores normalize over the frozen 65 target categories.

### P0 — unigram

Training target frequency only.

### P1 — ordered positional trajectory (primary)

Naive Bayes with separate emission tables for each position/feature:

- L, R, F at each of 8 offsets (24 positional emissions)
- DL and DR at each of 6 within-side adjacency positions (12 trajectory emissions)
- Xshared and Xboundary (2 cross-gap emissions)

Total 38 frozen categorical observations per eligible center.

### P2 — position-erased neighborhood control

Uses the same L/R/F observations but pools all eight offsets during training and scoring; each observed neighbor contributes to the same family-specific emission table regardless of position.

Uses the same six DL/DR observations but pools the six adjacency positions similarly.

Xshared/Xboundary are retained because they have a unique structural role.

Thus P2 has the same raw information and observation count as P1 while erasing where within the eight-token field each observation occurred.

### P3 — ordered left-only

P1 restricted to offsets -4..-1 and the three left DL/DR transitions. No cross-gap features.

### P4 — ordered right-only

P1 restricted to offsets +1..+4 and the three right DL/DR transitions. No cross-gap features.

## Phase-A endpoints

On all heldout eligible centers and on unseen-center-skeleton centers report:

- cross-entropy nats/token
- bits/token
- perplexity
- top-1, top-5, top-10
- MRR

Primary V41 success criterion:

1. P1 CE < P0 on full holdout;
2. P1 CE < P2 on full holdout (ordered trajectory beats same-information position-erased control);
3. P1 CE < P3 and P4 on unseen-center-skeleton subset;
4. P1 CE < P0 on unseen-center-skeleton subset.

## Order nulls

Using the frozen P1 model, evaluate 20 deterministic holdout-only permutations of the eight visible neighbor positions. For null k, order the eight offsets by `md5('v41-position-null-XX|' || offset)` and assign the observed neighbor microfeature bundles to those frozen permuted positions. Recompute the six within-side trajectory feature values from the permuted bundles occupying the left/right positions. Xshared/Xboundary use the bundles placed at -1/+1.

No refitting occurs. Real P1 should outperform the null distribution.

## Phase-A witness-opening boundary

Before V41 reads `draft.canon_masoretic_marks`, commit preregistration, exact feature coding, training target inventory/count hashes, Phase-A results, null results, and a witness-opening SHA.

## Phase B external witness

Only after that boundary, repeat the frozen ordered-vs-position-erased comparison against anonymous single-cantillation witness identities:

- Q0 witness frequency
- Q1 ordered positional trajectory, center-blind, same 38 observations
- Q2 position-erased witness control using same observations
- Q3 center intrinsic comparison
- Q4 frozen 0.5/0.5 normalized combination Q1 + Q3
- Q5 exact center skeleton upper bound

Report full, unseen-center-skeleton, and variable-witness-skeleton endpoints. Primary witness criterion: Q1 must beat Q0 and Q2 in unseen-center-skeleton cross-entropy. Q4 is secondary evidence for complementarity with center intrinsic state.

## Interpretation ceiling

Even a positive V41 would establish only a generalizable, ordered, center-blind Hebrew contextual field and possible correspondence with an external witness. It would not by itself identify the authentic historical mark system, historical priority, causal generation, semantics, direct Masoretic descent, or theological meaning.