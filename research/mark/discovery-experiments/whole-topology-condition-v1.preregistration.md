# Whole-Topology Condition Test v1 — Preregistration

Status: **FROZEN BEFORE 705-SOURCE OUTCOMES**  
Date: **2026-09-19**

## Why this experiment exists

Independent Source Law Discovery v1 recovered the same local destination-matching law in eight anonymous sources and a contradictory junction-conditioned relation in a ninth.

Only after that blind result was frozen did provenance show the contradictory source was a Genoese openwork lace edging with unusually low observed relational pair weight per detected center.

This test asks whether that whole-source quantity is actually the missing condition or merely a story suggested by one exception.

## Untouched test universe

Use all **705 source objects** from the original sealed 714-source corpus that were not among the nine independent-discovery sources.

The nine hypothesis-generating sources are excluded from every confirmatory statistic.

For the 705:

- provenance remains sealed;
- institution remains sealed;
- object type remains sealed;
- prior source-rule incidence remains sealed;
- canon labels are unavailable to scoring.

The only retained grouping variable is the original blind lane (`train`, `holdout`, `control`) for permutation stratification and replication diagnostics.

## Frozen whole-source predictor

For source S:

`pair_density(S) = observedPairWeight(S) / detectedCenters(S)`

No alternative topology predictor may be opened before the primary result is frozen.

## Frozen local outcomes

Compile each source alone with the same physical Mark compiler and **64 source-local null worlds**.

### Junction matching lift — primary

Context:

`CENTER:JUNCTION|ARM:PATH_TO_JUNCTION`

Matching outcome:

`PATH_TO_JUNCTION`

For an eligible source:

`junction_match_lift = observed match accuracy - mean(null match accuracy)`

Eligibility:

- detected centers > 0;
- observed junction-context count >= 30.

### Endpoint matching lift — secondary

Context:

`CENTER:JUNCTION|ARM:PATH_TO_ENDPOINT`

Matching outcome:

`PATH_TO_ENDPOINT`

Same lift definition and >=30 context-count gate.

## Primary prediction

If whole-source relational density is the omitted condition suggested by the lace exception:

> **the lowest-density sources should show weaker or reversed junction matching than the rest of the untouched corpus.**

The primary low-density group is defined without seeing outcomes:

- rank eligible sources by `pair_density` ascending;
- break ties by anonymous sourceGroupId;
- select the lowest `ceil(N/10)`.

Primary statistic:

`median junction lift(lowest decile) - median junction lift(other 90%)`

Predicted sign: **negative**.

## Primary null test

Use **20,000 deterministic permutations**.

Within each original blind lane independently:

- keep source pair density fixed;
- shuffle junction matching lift among eligible sources.

One-sided p-value:

`(1 + # permuted statistics <= observed statistic) / 20001`

This preserves lane-level distributions while breaking the source-level density/outcome relation.

## Monotonic companion

Also compute pooled Spearman correlation:

`rho(pair_density, junction_match_lift)`

Predicted sign: **positive**.

Its one-sided p-value uses the same 20,000 lane-stratified permutations.

## Frozen verdict language

### SUPPORTS_DENSITY_CONDITION

Require both:

- low-density median contrast < 0 with p <= 0.01;
- Spearman rho > 0 with p <= 0.05.

### LOW_DENSITY_EFFECT_NONMONOTONIC

Use when:

- low-density contrast < 0 with p <= 0.01;
- monotonic companion does not pass.

This would mean low density matters, but not as one simple monotonic continuum.

### NO_DENSITY_SUPPORT

Use when neither preregistered primary contrast supports the predicted direction.

The lace-based pair-density explanation is then rejected as the missing condition.

## Secondary diagnostics

After the primary statistic is computed but before provenance opening, report:

- endpoint matching tail contrast and Spearman rho;
- negative-lift prevalence in bottom decile versus remaining sources;
- train/holdout/control lane-specific primary statistics.

These cannot rescue a failed primary result by post-hoc threshold changes.

## Scientific guard

The purpose is not to prove the current whole/member hypothesis.

It is to give the lace exception a chance to **falsify the proposed missing condition** on 705 untouched sources.

Only after the blind result is frozen may provenance be rejoined.
