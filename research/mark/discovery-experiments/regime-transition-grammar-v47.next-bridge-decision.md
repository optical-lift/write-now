# Mark V47 next-bridge decision

**Experiment:** `mark:regime-transition-grammar:v47`  
**Status:** NEXT BRIDGE SELECTED AFTER BLIND CONFIRMATION  
**Date:** 2026-09-18

## Primary next bridge — REGIME BOUNDARY DYNAMICS

V47 shows that RG-001, RG-002, and RG-004 are robustly persistent across scale, while RG-003 fails the final persistence gate.

This matches an independent V46 residual: RG-003 had the weakest centroid-margin character among the five regimes.

V46 also preserved an orthogonal, internally stable source-relative representation (R4) that was not absorbed into the global five-regime atlas.

Together those results point to a new question:

> **Can continuous structural position, boundary proximity, and within-source displacement predict when a cross-scale child remains in the same regime versus changes regime?**

This is a different problem from discovering more discrete regime sequences.

## Why not continue adding discrete history?

V47 already tested length-3 and length-4 regime histories.

They did not add matched-null-surviving predictive information beyond the immediate prior state.

Adding longer strings at the same representation would therefore be a weak next move.

## Why boundary dynamics is higher-value

The five regime labels throw away continuous information.

For every observation, the frozen V46 model already contains or can deterministically recover:

- distance to assigned centroid;
- distance to second-nearest centroid;
- centroid margin;
- full 12-dimensional PCA position;
- source-relative offsets under the preserved R4 feature view.

Those observables can ask whether a regime transition occurs because a structure is near a boundary, moves in a particular direction through feature space, or changes relative to its own source baseline.

## Smallest next experiment

Build a new source-blind edge record from the already-frozen V46/V47 artifacts.

For each child -> parent edge, record without semantics:

- child RG and parent RG;
- child and parent frozen R3 PCA coordinates;
- child and parent nearest-centroid distance;
- child and parent nearest/second-nearest margin;
- displacement vector and magnitude in frozen PCA space;
- child and parent R4 source-relative coordinates;
- scale pair;
- source ID.

Primary target:

`P(persist vs change | child continuous state, displacement, scale pair)`

Compare against:

1. child RG alone;
2. scale pair alone;
3. child RG + scale pair;
4. source-preserving nulls.

A useful result would identify a continuous transition surface or displacement rule that transfers to unseen sources.

A null result would tell us the five-regime topology atlas is missing the physical observable that governs regime change.

## Fresh-evidence strategy

Do not reuse V47 confirmation as confirmation for the new boundary hypothesis.

The new experiment should make a fresh source split before outcomes are inspected.

Because the 431 original V46 discovery sources were never used in V47 transition scoring, they can provide a large fresh transition-outcome pool, although their regime coordinates are in-sample to the V46 clustering and that limitation must be explicitly controlled.

One clean design is:

- develop the boundary model on the 283 V47 sources whose transition outcomes are already known;
- freeze the model;
- confirm only on a source-separated subset of the 431 V46-discovery sources whose transition outcomes have never been inspected;
- include an explicit sensitivity analysis for the fact that those sources participated in fitting the V46 centroids.

If that in-sample-coordinate limitation is unacceptable under implementation audit, the experiment should instead rebuild a fixed equivalent regime model on a source-separated basis before outcome scoring.

## Secondary retained directions

### Restore exact V45 operator ecology
Still valuable, but deferred until the exact V5/V45 projector can be restored under an equivalence contract.

### Improve field -> object identifiability
The current matched null cannot identify many object-scale transitions because object strata are often singleton. A later experiment may need a different source-preserving null or multiple object-level observations.

### Source-relative organization
R4 remains an independent clue and should be incorporated into boundary dynamics rather than discarded.

## Decision

The next bridge should study **where structural state changes happen in continuous structural space**, not ask what the regimes mean.

Inference direction:

`stable regime atlas -> continuous boundary/displacement dynamics -> reproducible change rule -> next layer`

not:

`semantic expectation -> choose a regime transition that resembles it`.
