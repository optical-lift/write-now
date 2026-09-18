# Mark Regime Boundary Dynamics v48 — preregistration

**Experiment ID:** `mark:regime-boundary-dynamics:v48`  
**Parent:** V47 final closure `88bad42d5610aa97e01e97d2605647eb392f280c`  
**Status:** preregistered before any V48 boundary outcome is scored

## Purpose

V47 established a reproducible first-order persistence grammar for RG-001, RG-002, and RG-004, rejected RG-003 neighborhood -> field persistence on confirmation, and found no additional length-3/4 discrete-state program.

V48 therefore asks a different question:

> Can continuous structural position, boundary proximity, and cross-scale displacement predict whether a child remains in the same structural regime or changes regime?

This experiment is not a longer discrete-state grammar test and is not a semantic interpretation experiment.

## Core scientific change

The V46/V47 regime labels compress a continuous physical feature space.

V48 reopens the continuous representation while preserving the already-discovered five-regime topology as a reference frame.

Primary target:

`P(persist vs change | continuous structural state, displacement, scale pair)`

where:

`persist = aligned child regime == aligned parent regime`.

## Source-separated architecture

V48 uses all 714 existing sources, but assigns them different roles.

### Coordinate-fit lane

Use the **171 V47 discovery sources / 5,305 observations** only to fit a source-separated equivalent of the V46 R3 five-regime coordinate system.

Source-list SHA-256:

`b77f4f48353764d42888a0de4fb6f1027c78d11565b69ecefe88dd74dffbddbc`

Observation-list SHA-256:

`c219978ab6ad8e81bf3ce55634ea9c167c00d4d666e214c43bef093dd2b13795`

### Boundary-development lane

Use the **59 V47 validation sources / 2,332 observations** only after the coordinate model is frozen.

Source-list SHA-256:

`daa2f0e62f0925ad3ebf7cd533ce3ceb9a27f68585d3209fbf5de9066e3b34e4`

Observation-list SHA-256:

`d1a5a58178866bd61fc4f671e8c08d30e09f225da010c485a46640d20a19d91c`

### Boundary-validation lane

Use the **53 V47 confirmation sources / 1,607 observations** only after the boundary model and thresholds are frozen.

Source-list SHA-256:

`4d947806cb30d62785165a75b2b718da750e476b719711a0a8fa8abc9bd99599`

Observation-list SHA-256:

`9652f6d2411e6dc975466bddfe8ba1cd98b69affaec012168e550d51cba387e2`

### Fresh final-confirmation lane

Use the **431 original V46 discovery sources / 13,482 observations** only after boundary validation is frozen.

These sources fitted the original V46 atlas, but **their cross-scale transition outcomes were never scored in V47**.

V48 does not use their original fitted coordinates. They are projected through the new source-separated equivalent coordinate model trained only on the 171 coordinate-fit sources.

Source-list SHA-256:

`a36f428e48c0fcfb70a81c3f6c6aa743740985046928c3d8bb8c4a648fb302df`

Observation-list SHA-256:

`a79d274f4b747359aaa891d8d1a8901a2702bce1856b8bed4fb0cc55d0a8f93e`

No source is used in more than one V48 role.

## Equivalent regime coordinate model

Rebuild the exact V46 R3 feature representation:

- same R3 feature list;
- StandardScaler;
- PCA retaining >=95% variance;
- KMeans K=5;
- random state 4601;
- n_init=20;
- max_iter=500;
- Lloyd algorithm.

Fit only on the 171 coordinate-fit sources.

Align the resulting five clusters to canonical RG-001..RG-005 using only the frozen canonical V46 assignments for those same 171 sources.

Alignment must maximize total observation agreement under a one-to-one cluster permutation.

Before downstream outcome scoring, freeze:

- fitted scaler;
- PCA;
- centroids;
- cluster-to-RG alignment;
- agreement with canonical V46 assignments;
- exact model SHA.

The equivalent model is usable only if:

- aligned ARI vs canonical assignments >= **0.85**;
- every aligned regime has >= **50** coordinate-fit observations;
- every aligned regime appears in >= **20** coordinate-fit sources.

Failure ends V48 without boundary modeling.

## Continuous predictors

For every geometric child -> parent edge, derive from the frozen equivalent coordinate model:

### Child state
- 12-or-model-determined PCA coordinates;
- squared distance to assigned centroid;
- squared distance to second-nearest centroid;
- normalized nearest-vs-second margin;
- aligned child RG.

### Parent state
- same continuous quantities for parent.

### Displacement
- parent minus child PCA vector;
- Euclidean displacement magnitude;
- signed displacement along the child-to-centroid direction;
- signed displacement toward/away from the nearest competing centroid;
- change in centroid margin.

### Source-relative structure
Rebuild the preserved V46 R4 source-relative normalized representation with:

- within-source median centering before global scaling;
- fit global StandardScaler/PCA only on coordinate-fit sources;
- project all later lanes without refit.

Include child R4 coordinates, parent R4 coordinates, and R4 displacement magnitude/vector.

### Context
- scale pair;
- aligned child RG.

No provenance or semantic class enters the predictors.

## Boundary-model attempt set

Development may compare a small preserved model set:

1. **B0:** scale pair only;
2. **B1:** child RG only;
3. **B2:** child RG + scale pair;
4. **C1:** B2 + child continuous R3 state;
5. **C2:** C1 + R3 displacement features;
6. **C3:** C2 + R4 source-relative state/displacement.

Primary model family: L2-regularized logistic regression.

Allowed C grid on development only:

`[0.01, 0.1, 1.0, 10.0]`

All attempts and source-fold scores must be retained.

Selection uses source-grouped cross-validation on the 59 development sources only.

Primary selection metric:

mean held-out **log-loss gain in bits/edge over B2**.

Tie-breakers:

1. greater fraction of held-out sources with positive log-loss gain;
2. lower Brier score;
3. simpler model;
4. lower C.

No validation outcome may alter feature groups or C.

## Null model

The primary null asks whether continuous edge structure adds predictive information beyond source, scale pair, and child-RG composition.

For each null iteration:

- preserve every edge and all continuous predictor values;
- permute the persist/change target within each `sourceGroupId × scalePair × childRG` stratum where permutation is possible;
- singleton strata remain unchanged.

Use **100 deterministic null iterations**.

The observed selected-model gain over B2 must exceed the matched null 99th percentile on validation and confirmation.

## Frozen validation gate

A V48 boundary rule is **VALIDATION_SUPPORTED** only if all are true on the 53-source boundary-validation lane:

1. selected continuous model log loss < frozen B2 log loss;
2. gain over B2 > **0 bits/edge**;
3. gain exceeds matched null Q99;
4. >= **55%** of validation sources with >=5 scored edges have positive source-level gain;
5. both persistence and change outcomes are present.

No validation repair is allowed.

## Final confirmation gate

Reuse the validation gate unchanged on the 431-source fresh final-confirmation lane.

No model, C, feature group, null definition, or threshold may change.

## Checkpointed execution architecture

V48 must never require one monolithic long-running process.

Every stage emits immutable sufficient-statistics/checkpoint artifacts.

### Checkpoint 1 — equivalent coordinate model
Fit and freeze R3/R4 coordinate models and alignment.

### Checkpoint 2 — edge feature corpora
Compile development, validation, and final-confirmation edge predictors separately.
Each lane gets its own SHA and may be resumed independently.

### Checkpoint 3 — development model attempts
Run and freeze source-grouped CV sufficient statistics before selecting a model.

### Checkpoint 4 — null batches
Run the 100 nulls as exactly **10 batches of 10 iterations**.

Batch identities are fixed:

- batch 0 = iterations 0–9;
- ...
- batch 9 = iterations 90–99.

Each batch emits only the metric sufficient statistics required for final adjudication and receives its own SHA.

Completed batches are never recomputed because a later chat/tool session times out.

### Checkpoint 5 — validation
Combine only the frozen model + frozen validation features + all ten frozen validation-null batches.

### Checkpoint 6 — confirmation
Same architecture on final confirmation.

## Semantic boundary

V48 remains structural and source-blind through final confirmation.

Forbidden before final confirmation freeze:

- institution;
- title;
- language;
- chronology;
- OCR/transcription;
- writing/ornament/photo/art labels;
- named glyph identity;
- Song ontology labels.

## Legitimate outcomes

### Continuous boundary rule
Continuous state/displacement predicts persist/change beyond discrete RG + scale pair and survives validation/confirmation.

### Source-relative rule
R4 source-relative features add transferable information beyond global R3 coordinates.

### Discrete sufficiency
Continuous predictors do not improve over B2; the five-regime discrete state is sufficient at this level.

### Missing observable
Development gains do not transfer, indicating the current R3/R4 physical representation is missing the variable controlling regime change.

Any outcome determines where to build next.
