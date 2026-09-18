# Mark Regime Boundary Dynamics v48 — preimplementation freeze

**Experiment:** `mark:regime-boundary-dynamics:v48`  
**Status:** PREREGISTERED / CHECKPOINT ARCHITECTURE FROZEN / NO V48 OUTCOMES OPENED  
**Date:** 2026-09-18  
**Parent V47 closure:** `88bad42d5610aa97e01e97d2605647eb392f280c`

## Frozen governance blobs

- preregistration: `f0f3c139c083537cfc525d733246d86b07b6756b`
- protocol: `274278c5007fd0c58be293259f11bb3b7ff346be`
- START_HERE: `9b053a059ad6ec86434588b9c49c3373431a917c`
- execution checkpoint contract: `32d24c6f639d487d582cae9f943872882a93127d`

## Frozen source roles

### Coordinate-fit
- V47 discovery sources: 171
- observations: 5,305
- source-list SHA-256: `b77f4f48353764d42888a0de4fb6f1027c78d11565b69ecefe88dd74dffbddbc`
- observation-list SHA-256: `c219978ab6ad8e81bf3ce55634ea9c167c00d4d666e214c43bef093dd2b13795`

### Boundary development
- V47 validation sources: 59
- observations: 2,332
- source-list SHA-256: `daa2f0e62f0925ad3ebf7cd533ce3ceb9a27f68585d3209fbf5de9066e3b34e4`
- observation-list SHA-256: `d1a5a58178866bd61fc4f671e8c08d30e09f225da010c485a46640d20a19d91c`

### Boundary validation
- V47 confirmation sources: 53
- observations: 1,607
- source-list SHA-256: `4d947806cb30d62785165a75b2b718da750e476b719711a0a8fa8abc9bd99599`
- observation-list SHA-256: `9652f6d2411e6dc975466bddfe8ba1cd98b69affaec012168e550d51cba387e2`

### Fresh final confirmation
- original V46 discovery sources: 431
- observations: 13,482
- source-list SHA-256: `a36f428e48c0fcfb70a81c3f6c6aa743740985046928c3d8bb8c4a648fb302df`
- observation-list SHA-256: `a79d274f4b747359aaa891d8d1a8901a2702bce1856b8bed4fb0cc55d0a8f93e`

No source appears in more than one V48 role.

## Frozen equivalent-coordinate requirement

V48 will not use the original V46 fitted coordinates for final confirmation.

Checkpoint 1 must rebuild the exact V46 R3 representation on the 171 coordinate-fit sources only and align its five clusters to canonical RG-001..RG-005 by a one-to-one permutation maximizing agreement.

Minimum equivalence gates:

- aligned ARI >= 0.85;
- >=50 coordinate-fit observations per aligned regime;
- >=20 coordinate-fit sources per aligned regime.

Failure closes V48 without boundary modeling.

R4 source-relative coordinates are also fitted only from the coordinate-fit sources.

## Frozen boundary target

For every later geometric child -> parent edge:

`persist = aligned child RG == aligned parent RG`

Predictors may use the preregistered R3/R4 continuous state, displacement, and scale context only.

## Frozen model attempt set

- B0 — scale pair
- B1 — child RG
- B2 — child RG + scale pair
- C1 — B2 + child R3 continuous state
- C2 — C1 + R3 displacement
- C3 — C2 + R4 source-relative state/displacement

Model family:

L2 logistic regression.

Development-only C grid:

`0.01, 0.1, 1.0, 10.0`

Selection occurs only on the 59 development sources with source-grouped cross-validation.

Primary statistic:

held-out log-loss gain in bits/edge over B2.

## Frozen null

100 target permutations.

Within each:

`sourceGroupId × scalePair × childRG`

stratum, permute persist/change labels where possible.

Observed selected-model gain must exceed the matched null 99th percentile on validation and final confirmation.

## Frozen checkpoint architecture

The experiment is deliberately split so a timeout never requires restarting completed science.

- CP1 coordinate models
- CP2 development edge features
- CP3 development model selection
- CP4 validation edge features
- CP5 validation observed score
- CP6.0–CP6.9 validation null batches, exactly 10 iterations each
- CP7 validation adjudication
- CP8 final-confirmation edge features
- CP9 final-confirmation observed score
- CP10.0–CP10.9 final-confirmation null batches
- CP11 final confirmation adjudication
- CP12 context rejoin

Every checkpoint receives an immutable artifact hash.

Completed checkpoints and null batches are never recomputed merely because a chat or tool session times out.

## Boundary

No V48 continuous coordinate outcome, persist/change target, model score, validation result, confirmation result, or null result has been inspected before this freeze.

The only permitted next action is **CP1**:

rebuild and freeze the source-separated equivalent R3/R4 coordinate models.

Do not compile boundary targets or run nulls in the same turn.
