# Mark Regime Transition Grammar v47 — preregistration

**Experiment ID:** `mark:regime-transition-grammar:v47`  
**Parent:** V46 next-bridge decision `f4b338e37b8323166feb7669569889b85637f52b`  
**Status:** preregistered before any cross-scale transition outcome is scored

## Purpose

V47 asks what V46 taught us to ask next:

> Do the already-confirmed anonymous structural regimes transform across local -> neighborhood -> field -> object scales according to recurrent, source-independent rules?

The goal is not to recover a predetermined semantic category. The goal is to determine whether the five confirmed structural modes form a larger grammar when observations are connected across scale.

## Frozen alphabet

V47 may use only the five V46 regime identities:

- RG-001
- RG-002
- RG-003
- RG-004
- RG-005

Their definitions, centroids, assignments, and support radii are immutable.

V47 may not rename them from context or refit the V46 atlas.

## Source pool

To avoid learning transition rules on sources that fitted the regime centroids, V47 excludes all 431 original V46 discovery sources from transition-rule learning.

The V47 pool is the union of V46 validation + confirmation sources:

- **283 source objects**
- **9,244 untouched V46 observations**
- canonical source-list SHA-256: `b9cc1accbca97380178d8408e7c4d38f9b18ad22c64a785c5f5a8e835c82c729`
- canonical fixed regime-assignment mapping SHA-256: `633918a3bad435adfdef9859a33743b9fa88bfcf59a79a4ed8a59b71141d9d90`

No new image acquisition is required for V47.

## New source-separated partitions

Partition each source by:

`bucket = first_32_bits(SHA256("mark-v47-regime-transition-grammar|" + sourceGroupId)) mod 100`

- 0–59: discovery
- 60–79: validation
- 80–99: confirmation

Frozen inventory:

- discovery: **171 sources / 5,305 observations**
- validation: **59 sources / 2,332 observations**
- confirmation: **53 sources / 1,607 observations**

No source may appear in more than one V47 lane.

## Geometric scale graph

Proposal scales have fixed rank:

1. `local`
2. `neighborhood`
3. `field`
4. `object`

For each observation A, candidate parent B must:

- belong to the same `sourceGroupId`;
- have strictly greater scale rank;
- cover at least **95% of A's rectangular area**, measured as intersection(A,B) / area(A).

Parent selection is deterministic:

1. choose the **lowest higher scale rank** for which at least one eligible parent exists;
2. within that scale, choose greatest child-containment fraction;
3. then smallest parent area;
4. then lexicographically smallest parent observation ID.

Each observation has at most one parent.

Repeated parent links yield source-local chains of length 2–4.

Observations with no eligible parent remain roots/unlinked and are preserved in coverage reporting.

This graph is purely geometric. Regime labels must not participate in parent selection.

## Phase A — pairwise transition discovery

On V47 discovery sources only, count transitions:

`(child scale, child RG) -> (parent scale, parent RG)`

Preserve:

- occurrence count;
- distinct-source support;
- conditional probability;
- lift over the scale-pair marginal;
- source-win/support distribution.

### Null

Use deterministic source- and scale-preserving permutations:

- within each source and each proposal scale, permute frozen RG labels among observations;
- preserve region geometry, parent edges, source identity, scale counts, and per-source-per-scale regime marginals;
- use **100 deterministic permutations**, seeds derived from SHA-256 of experiment ID + iteration.

This null asks whether cross-scale transitions contain organization beyond source/media composition and scale-specific regime frequencies.

### Candidate harvest

Discovery may harvest up to 15 pairwise candidate rules.

A candidate must have:

- >= 20 discovery occurrences;
- >= 10 distinct discovery sources;
- observed conditional probability >= 0.50;
- lift over discovery scale-pair marginal >= 1.25;
- observed lift above the 99th percentile of its matched permutation-null lift distribution.

Candidates are ranked by:

1. distinct-source support;
2. permutation-null excess;
3. occurrence count;

with deterministic tie-breaking by transition key.

All harvested and failed candidate keys must remain in the discovery record.

## Phase B — higher-order transition programs

If Phase A yields at least one harvested pairwise rule, discovery may inspect source-local regime chains of lengths 3 and 4.

The purpose is to test **composition of confirmed regimes**, not to assign meaning.

For each chain template, compare:

- empirical next-regime predictability;
- first-order transition model;
- scale-only marginal baseline;
- source-and-scale-preserving permutation null.

A length-3/4 candidate may be frozen for validation only if it recurs in >=10 discovery sources and improves held-in discovery log loss over the first-order transition model.

Every attempted chain length and candidate must be preserved.

## Validation

Before validation opens, freeze:

- exact graph-builder implementation;
- discovery graph artifact SHA;
- pairwise candidates;
- any higher-order candidates;
- smoothing rules;
- probability tables;
- null seeds/results required for frozen thresholds.

Validation performs **no refit**.

Pairwise rule transfer is reported by exact rule key, source support, occurrence count, and log-likelihood/lift under the discovery-frozen model.

No failed candidate may be replaced after validation.

## Confirmation

Confirmation opens only after validation is frozen.

No model, candidate, threshold, or transition graph rule may change before confirmation.

## Blindness

Transition discovery/scoring may use:

- sourceGroupId;
- observationId;
- frozen V46 regime ID;
- proposal scale/kind;
- observation rectangle geometry.

It may not use:

- institution;
- title;
- provider;
- language;
- chronology;
- geography;
- OCR/transcription;
- writing/ornament/photo/art labels;
- Song ontology categories.

V46 context rejoin motivated the question, but context does not enter V47 scoring.

## Legitimate outcomes

V47 can support more than one next direction.

### Transition grammar found
Stable cross-scale transition rules transfer to unseen sources.

### Higher-order program found
Longer regime chains add predictive structure beyond pairwise transitions.

### Marginal-only structure
Apparent transitions disappear under source-and-scale-preserving nulls; regime mixtures matter but transition order does not.

### Geometry insufficient
Too few reliable parent links exist; build a better hierarchical observable rather than forcing a grammar.

Any of these is useful because each identifies the next bridge segment.
