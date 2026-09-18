# Mark Regime Transition Grammar v47 — final result

**Experiment:** `mark:regime-transition-grammar:v47`  
**Parent:** V46 Structural Regime Atlas  
**Status:** CLOSED — CONFIRMATION RESIDUAL  
**Date:** 2026-09-18

## Question

Do the five already-confirmed V46 structural regimes form a reproducible grammar as observations expand from local to neighborhood to field to object scale?

## Geometry

A regime-blind deterministic parent graph was frozen before regime labels were joined.

Across the 283 V47 sources:

- observations: 9,244
- discovery: 5,305 observations / 171 sources
- validation: 2,332 / 59
- confirmation: 1,607 / 53

More than 96% of observations in every lane link to a larger-scale parent.

Discovery contains 1,838 four-level chains.

## Pairwise discovery

Seven rules survive the source×scale-preserving matched null.

All seven are same-regime persistence rules.

No cross-regime rule satisfies all discovery gates.

The discovered rules are:

- RG-001 local -> neighborhood
- RG-001 neighborhood -> field
- RG-002 local -> neighborhood
- RG-002 neighborhood -> field
- RG-003 neighborhood -> field
- RG-004 local -> neighborhood
- RG-004 neighborhood -> field

## Higher-order discovery

Length-3 chains tested: 3,708.

Length-4 chains tested: 1,838.

Harvested higher-order programs: **0**.

Longer history does not add matched-null-surviving predictive information beyond the immediate prior regime at the current five-regime representation.

## Validation

All seven pairwise rules transfer on 59 unseen sources.

- transferred: 7
- rejected: 0
- insufficient contrast: 0

## Confirmation

Six of seven pairwise rules transfer on the final 53 unseen sources.

Confirmed:

- RG-001 local -> neighborhood
- RG-001 neighborhood -> field
- RG-002 local -> neighborhood
- RG-002 neighborhood -> field
- RG-004 local -> neighborhood
- RG-004 neighborhood -> field

Rejected under the frozen gate:

`RG-003 neighborhood -> field RG-003`

Its confirmation conditional probability is 11/23 = **0.4783**, below the frozen 0.50 threshold.

The same rule still has:

- lift = **13.0137**
- target support across 5 confirmation sources
- frozen predictive gain = **+1.2550 bits/edge**

Therefore the rejection is narrow but real under the preregistered contract.

## Final structural verdict

V47 supports a **reproducible first-order persistence grammar for RG-001, RG-002, and RG-004 across local -> neighborhood -> field scales**.

It does not support:

- a universal persistence rule for all five regimes;
- a reproducible cross-regime jump grammar under the discovery gates;
- an additional length-3/4 regime-program layer at the current representation;
- a field -> object rule distinguishable under the current null.

The field -> object question is partly underidentified because many source×object strata are singletons, preventing the matched null from changing object labels.

## What V47 taught us

The important result is not merely that some states persist.

It is the asymmetry:

- some structural regimes behave like stable scale-persistent states;
- at least one regime, RG-003, behaves more like a boundary/residual state;
- the current discrete regime label is sufficient for persistence but insufficient to explain transition/break behavior;
- longer discrete state history adds no robust information.

This indicates that the next useful observable is likely **continuous position relative to regime boundaries and source-relative structural displacement**, rather than a longer discrete symbol string.

## Semantic boundary

No Song meaning, glyph meaning, language, OCR, or source provenance entered V47 scoring.

The result is structural only.
