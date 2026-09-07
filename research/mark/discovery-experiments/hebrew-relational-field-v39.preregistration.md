# V39 — Hebrew Relational Structural Field

**Experiment ID:** `mark:hebrew-relational-field:v39`  
**Date:** 2026-09-07  
**Status:** preregistered before V39 Hebrew holdout outcomes and before any V39 Masoretic witness query

## Governing stance

V39 continues the source/witness correction introduced in V38.

The Masoretic notation is an external witness layer. It is not the target definition, label source, or discovery carrier for V39.

V39 asks whether the Hebrew consonantal text contains a richer identity-blind relational field than the V38 token-intrinsic field, and only after that field is frozen whether the Masoretic witness corresponds to it.

## Sealed information during Hebrew discovery

The following may not enter V39 feature construction, model selection, thresholds, support rules, holdout scoring, or lane choice before the witness-opening freeze:

- `draft.canon_masoretic_marks`
- cantillation codepoints
- niqqud / vowel points
- `lemma_raw`
- `morph`
- Strong identifiers
- translations
- conventional accent names
- inherited grammatical categories
- semantic labels

Only consonantal Hebrew letters U+05D0–U+05EA from `draft.ot_canonical_tokens_stage.hebrew_surface`, token order, and provenance coordinates may be used.

## Holdout

Five-chapter blocks use `block_index=floor((chapter-1)/5)`.

Rank blocks by:

`md5('v39-hebrew-relational-holdout|' || book || ':' || block_index), book, block_index`

Take the lowest 41 of 201 blocks.

Frozen V39 holdout blocks in rank order:

1. Psa 126–130
2. 1Sa 1–5
3. Isa 26–30
4. Gen 41–45
5. 2Ch 11–15
6. Est 1–5
7. 2Ki 11–15
8. 2Ch 16–20
9. Job 21–25
10. 1Ch 26–29
11. Jer 46–50
12. 2Ch 21–25
13. Psa 26–30
14. Jon 1–4
15. Gen 1–5
16. Isa 16–20
17. Jdg 11–15
18. 2Sa 11–15
19. Num 16–20
20. Psa 96–100
21. Num 11–15
22. Job 11–15
23. Ezr 1–5
24. Job 36–40
25. Jdg 6–10
26. Neh 11–13
27. 2Ch 31–35
28. Exo 1–5
29. Exo 36–40
30. Psa 56–60
31. Psa 66–70
32. Pro 21–25
33. Psa 86–90
34. Jos 1–5
35. Est 6–10
36. Eze 31–35
37. Psa 111–115
38. Psa 11–15
39. 2Ki 21–25
40. Num 26–30
41. 1Sa 31

No V39 holdout outcome may alter the representation after this preregistration.

## Consonantal token carrier

For each canonical token, strip every non-U+05D0–U+05EA character. The result is `skeleton`.

The V38 intrinsic identity-blind state is retained as a baseline:

`intrinsic = length | equality_pattern | terminal_final_form`

where `equality_pattern` relabels consonants by order of first occurrence within the token and discards consonant identity.

## Pairwise relational representation

For adjacent canonical tokens A→B wholly inside the same five-chapter block, derive two identity-blind representations.

### Coarse relation `Rcoarse(A,B)`

Concatenate the following categorical features:

1. `lenA_bin`: exact length 1–8, `9+` otherwise.
2. `lenB_bin`: exact length 1–8, `9+` otherwise.
3. `delta_len_bin`: `lenB-lenA`, clipped to `[-3,3]` with `LT-3` and `GT3` overflow bins.
4. `shared_distinct_bin`: number of distinct consonant identities appearing in both A and B, clipped to `0,1,2,3+`.
5. `same_first`: first(A)=first(B).
6. `same_last`: last(A)=last(B).
7. `boundary_continuity`: last(A)=first(B).
8. `exact_repeat`: A=B.
9. `A_terminal_final_form`.
10. `B_terminal_final_form`.

Consonant identities are used only for equality tests and shared-count computation; their names/codepoints are never retained in the representation.

### Exact identity-blind pair fingerprint `Rpair(A,B)`

Let C be the character sequence `A || B`. For each character position j in C, replace the character with the 1-based position of its first occurrence in C. Preserve the A/B boundary.

Example schematic: if A has pattern `x y` and B has `y z`, the pair fingerprint is `1.2|2.4`.

This preserves the complete equality topology within and across the adjacent words while erasing consonant identity.

## Hebrew-only predictive lanes

Target for all Phase-A lanes is the next token’s **V38 intrinsic state**. Destination alphabet is the 64 most frequent training intrinsic states plus `OTHER`, selected by training frequency descending, state key ascending tie break. Symmetric Dirichlet smoothing `alpha=0.5`.

### H0 — unigram

Training-wide next-intrinsic distribution.

### H1 — V38 intrinsic baseline

`P(next_intrinsic | current_intrinsic)`.

### H2 — coarse left-relation context

Context key:

`current_intrinsic || Rcoarse(previous,current)`

A context is supported at >=50 training occurrences. Unsupported H2 contexts back off to H1.

### H3 — exact pair-topology context

Context key:

`current_intrinsic || Rpair(previous,current)`

A context is supported at >=50 training occurrences. Unsupported H3 contexts back off to H2, then H1.

### H4 — relation-delta context

Context key:

`current_intrinsic || Rcoarse(prev2,previous) || Rcoarse(previous,current)`

A context is supported at >=50 training occurrences. Unsupported H4 contexts back off to H2, then H1.

This is the preregistered sequence-delta lane.

## Phase-A primary endpoints

On heldout transitions wholly inside V39 holdout blocks report for H0–H4:

- cross-entropy in nats/token
- bits/token
- perplexity
- delta nats versus H0
- delta nats versus H1 for H2–H4
- supported-context coverage

Primary success criterion for richer relational structure: at least one of H2–H4 has lower heldout cross-entropy than H1 without lower than 50% supported-context coverage.

## Phase-A order control

For heldout 4-token windows wholly inside one holdout block, compare H4 score under:

- real order `[0,1,2,3]`
- reverse `[3,2,1,0]`
- deterministic rotation `[1,2,3,0]`

Report mean log score and fraction real > control. This is descriptive; the primary criterion remains heldout cross-entropy.

## Phase-A adjacency null

Run 20 deterministic within-block predecessor-offset nulls for H2.

For null k=2…21, replace the actual predecessor used to compute `Rcoarse(previous,current)` with the token k positions earlier in the same block when available. The target next token and current token remain unchanged. This preserves the corpus and marginal token-form distribution but destroys true immediate adjacency.

Report the 20 null H2 cross-entropies. Real H2 should outperform the null distribution if immediate Hebrew relational adjacency is informative.

## Phase-A anti-lookup subset

Evaluate H1–H4 separately on transitions where the current exact consonantal skeleton has zero occurrences in V39 training.

This tests whether relational structure generalizes when exact current-word lookup is impossible.

## Phase-A freeze boundary

Before any V39 query reads `draft.canon_masoretic_marks`, commit to GitHub:

- this preregistration
- a machine-readable protocol
- state/context inventory hashes and support counts
- Phase-A results
- reproducible SQL or extraction script
- a commit SHA explicitly designated as the V39 witness-opening boundary

After that boundary no V39 holdout, representation, threshold, smoothing, backoff, lane, endpoint, or witness scoring rule may change.

## Phase B — external Masoretic witness only

After the witness-opening boundary, read the Masoretic witness exactly as an external comparison layer.

Primary witness-eligible token: exactly one cantillation codepoint U+0591–U+05AF attached to the token. Conventional accent names are not used.

All emission parameters are training-block only with `alpha=5` shrinkage toward training-wide witness frequency.

### W0 — witness frequency

Training-wide codepoint frequency.

### W1 — V38 intrinsic baseline

`P(mark | current_intrinsic)`.

### W2L — coarse left relation

`P(mark | current_intrinsic, Rcoarse(previous,current))`, support >=50, backoff W1.

### W2R — coarse right relation

`P(mark | current_intrinsic, Rcoarse(current,next))`, support >=50, backoff W1.

### W3 — bidirectional coarse relational state

`P(mark | current_intrinsic, Rcoarse(previous,current), Rcoarse(current,next))`, support >=50.

Unsupported W3 contexts use the arithmetic mean of W2L and W2R probabilities; if either side is unsupported it has already backed off to W1.

### W4 — exact identity-blind pair topology

Compute left and right exact-pair emission models independently:

- `P(mark | current_intrinsic, Rpair(previous,current))`
- `P(mark | current_intrinsic, Rpair(current,next))`

Each exact-pair context requires support >=50 and otherwise backs off to its corresponding coarse W2 model.

W4 probability is the arithmetic mean of the left and right exact-pair probabilities.

### W5 — relation-delta witness context

`P(mark | current_intrinsic, Rcoarse(previous,current), Rcoarse(current,next), delta_len_left, delta_len_right)` with support >=50; unsupported contexts back off to W3.

### W6 — exact consonantal skeleton upper bound

`P(mark | exact_skeleton)` with the same alpha=5 smoothing. This is a lexical/control ceiling and is not the latent-field result.

## Phase-B endpoints

On witness-eligible V39 holdout tokens report W0–W6:

- cross-entropy / log loss
- top-1
- top-3
- top-5
- mean reciprocal rank
- delta cross-entropy versus W0
- delta cross-entropy versus W1 for W2–W5

Primary V39 witness criterion: one or more relational lanes W2–W5 must improve heldout cross-entropy over W1.

## Phase-B anti-lookup subsets

Report the same metrics on:

1. unseen current skeletons: exact consonantal skeleton absent from V39 training
2. variable-witness skeletons: current skeleton observed with >=2 witness codepoints across training and/or holdout

A relational effect that survives unseen skeletons is stronger evidence of structural generalization than exact-word lookup.

## Phase-B witness nulls

Reuse the 20 frequency-stratified witness-label permutations defined conceptually in V38, with salts `v39-witness-scramble-00` through `v39-witness-scramble-19`. Real relational alignment must be compared with the null distribution; the Hebrew representation itself remains fixed.

## Interpretation matrix

### A. H2–H4 improve Hebrew prediction and W2–W5 improve witness prediction, including unseen skeletons

Preferred statement:

> Identity-blind relations between neighboring Hebrew consonantal forms carry generalizable sequential structure and independently predict part of the external Masoretic witness. This strengthens the hypothesis that both may reflect a deeper structural organization not reducible to exact word identity.

This does not establish that V39 has recovered the original historical mark system.

### B. Hebrew relational lanes improve H1 but do not improve W1

> The richer Hebrew relational field is real under the predictive test but does not substantially correspond to the Masoretic witness under this representation.

### C. Witness relational lanes improve W1 but Hebrew-only H2–H4 do not improve H1

> Apparent witness gains may be context-conditioned lookup rather than evidence of an independently stable Hebrew structural field. Treat cautiously.

### D. Only exact skeleton W6 is strong

> Current evidence remains dominated by lexical/consonantal identity; V39 has not isolated the deeper identity-blind relation sought.

### E. Neither Hebrew nor witness relational lanes improve

> This V39 representation fails. That does not falsify an underlying authentic mark system; it falsifies only this representation as a useful recovery route.

## Epistemic ceiling

No V39 result by itself establishes:

- the authentic/original historical mark system
- historical priority or provenance
- causal generation of the Hebrew text
- direct descent of Masoretic notation from the recovered field
- semantic meanings of latent states
- theological claims

V39 is a blind structural recovery test followed by an external witness comparison.