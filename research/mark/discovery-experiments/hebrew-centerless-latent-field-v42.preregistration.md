# V42 preregistration — centerless latent Hebrew field

Experiment ID: `mark:hebrew-centerless-latent-field:v42`
Date: 2026-09-07
Status: preregistered before any V42 outcome query and before any Masoretic witness query.

## Motivation

V41 showed that an identity-blind surrounding Hebrew field generalized to unseen center skeletons, while preserving absolute positional order did not improve prediction and in the preregistered comparisons made cross-entropy worse than a position-erased field. V42 therefore stops treating a designated center or local trajectory as privileged.

The hypothesis tested here is stronger and different: a local span may occupy a shared latent structural condition such that one anonymous subset of its Hebrew structural members predicts a disjoint anonymous subset from the same span better than frequency-only or mismatched-window controls.

## Phase-A seal

V42 is Hebrew-only. Until the Phase-A verdict is committed, no V42 query may read or derive from `draft.canon_masoretic_marks`, niqqud, cantillation, accent names, translations, lemmas, morphology, Strong IDs, semantic labels, grammatical labels, or any other external witness.

Exact consonant identities may be used only inside already-frozen identity-blind intrinsic/equality operations inherited from the V38–V41 pipeline and for anti-lookup subset membership. Raw token identity, exact center identity, lexical labels, or token strings are not model predictors.

## Source split and lexical anti-lookup

Reuse the frozen V41 five-chapter-block train/holdout assignment without modification.

A V42 holdout span is `lexically unseen` only when every consonantal skeleton occurring in that span is absent from V42 training. The full holdout remains the primary population; the all-unseen-span subset is the preregistered anti-lookup population.

## Span construction

Use nine consecutive canonical Hebrew tokens wholly contained within one frozen block and one split. Unlike V41, there is no designated predictive center and no signed offset feature.

For each token, construct only the inherited identity-blind intrinsic state:

`length | equality_pattern | terminal_final_form`

Map token intrinsic states to the same frozen 65-state alphabet used by V41: the 64 training-selected states plus `OTHER`. This alphabet is not reselected for V42.

A span is therefore represented as a multiset of nine anonymous intrinsic states. Token positions and canonical order are discarded before modeling.

## Deterministic reveal/missing partition

Each nine-token span is partitioned into an observed multiset A of four tokens and a held-out multiset B of five tokens.

The partition is deterministic and outcome-independent. Rank the nine token members by:

`md5('v42-reveal|' || book || ':' || chapter || ':' || verse || ':' || position)`

with canonical token identity used only to define stable membership before predictor construction. The lowest four hashes form A; the remaining five form B. Hash values and canonical positions are not predictors.

Because the model is permutation-invariant, A and B are used only as multisets of intrinsic-state categories.

## Models

### F0 — independent frequency baseline

Predict each missing B member independently from the empirical 65-state token frequency estimated on V42 training spans. Span log-probability is the sum over the five missing members.

### F1 — same-window anonymous field model (primary)

Estimate a permutation-invariant Dirichlet-multinomial conditional field from training spans.

For each training span, form the count vector of the four observed A states. The conditioning signature is the sorted multiset of A categories, represented canonically as a 65-dimensional sparse count vector.

For each conditioning signature, accumulate counts of missing B states across matching training spans. Use symmetric Dirichlet smoothing `alpha = 0.5` over the 65 target categories.

At holdout, predict each B state from the smoothed conditional distribution for its exact A multiset signature. If a holdout A signature was unseen in training, back off once to the global F0 distribution. No partial-signature or learned rescue backoff is permitted in V42.

The span score is the sum of the five missing-token log probabilities.

### F2 — matched-window control

For each holdout span, keep its observed A multiset fixed but replace the true B multiset with B from a different holdout span selected deterministically subject to the same five-token B length and no shared canonical token IDs.

The donor span is selected by ordering eligible donor spans by:

`md5('v42-matched-control|' || recipient_span_id || '|' || donor_span_id)`

and taking the first eligible donor.

Score the donor B under the recipient span's F1 predictive distribution. No refitting occurs.

This asks whether A predicts its own field partners better than equally sized structural material drawn from another real Hebrew field.

### F3 — shuffled-membership nulls

Run 20 deterministic membership nulls. For null `k = 01..20`, pool the nine real token-state bundles from each holdout span, rank members by:

`md5('v42-membership-null-XX|' || canonical_token_id)`

and assign the lowest four to A and the remaining five to B. Recompute F1 scoring using the same frozen training model and no refitting.

These nulls test whether the preregistered A/B partition has any special predictive relation beyond arbitrary membership splits of the same field.

## Primary endpoints

Report on the full holdout and the lexically-unseen-span subset:

- cross-entropy in nats per missing token
- bits per missing token
- perplexity
- mean missing-token log probability

Because B is a multiset and the primary hypothesis concerns conditional field information rather than exact ordered recovery, top-k and sequence-ranking metrics are not primary V42 endpoints.

## Primary V42 success criterion

V42 is positive only if all of the following hold:

1. F1 cross-entropy < F0 on the full holdout.
2. F1 cross-entropy < F0 on the lexically-unseen-span subset.
3. True same-window F1 mean missing-token log probability > F2 matched-window control on the full holdout.
4. True same-window F1 outperforms at least 19 of 20 F3 membership nulls on full-holdout cross-entropy.

Failure of any condition is a negative V42 result. No endpoint, threshold, alpha, alphabet, partition rule, span width, backoff, or subset definition may be changed after V42 outcomes are inspected; such changes require V43 or an explicitly labeled robustness analysis.

## Supporting diagnostics frozen before outcomes

Report:

- number and fraction of holdout A signatures seen in training
- endpoint values separately for seen-A and unseen-A/backoff spans
- performance by span vocabulary diversity (number of distinct intrinsic states among nine)
- performance by number of repeated intrinsic states among nine
- performance with one observed A member removed at a time, averaged over the four removals, using only an explicitly labeled robustness analysis after the primary verdict

The last item is supporting only and cannot rescue the primary result.

## Interpretation ceiling

A positive V42 would establish only that anonymous identity-blind Hebrew structural states within a local nine-token span exhibit generalizable mutual dependence consistent with a shared local field. It would not establish a historical mark system, semantics, grammar, causation, theological meaning, Masoretic descent, or that the inferred dependence is generated by a single literal latent variable.

A negative V42 would weigh against the proposed centerless local-field interpretation at this span width and frozen representation.

## Witness-opening boundary

Before any V42 Masoretic witness query, commit:

- this preregistration
- exact implementation note and hashes/counts needed to reproduce the V42 training model
- all Phase-A Hebrew endpoints
- matched-window control
- 20 membership nulls
- Phase-A verdict
- witness-opening SHA

Only after that SHA exists may a separate Phase-B witness analysis be designed or opened.
