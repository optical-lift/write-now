# Component-Placement Junction Law Test v1 — Preregistration

Status: **FROZEN BEFORE PLACEMENT/LAW JOIN OUTCOMES**  
Date: **2026-09-19**

## Why this test exists

Degree is a real condition, but it is not sufficient. The completed degree-conditioned test left **18 train → holdout → control matching sublaws**, while the same degree/arm condition still produced strict matching and strict reversal across independent sources in every lane.

The prior frozen checkpoint specified the next move if that happened: move upward to **component placement**.

This test does not invent a new placement representation. It reuses the already-frozen masked structural slot instrument from run **33794464849**.

## Placement condition

For each observation that sits inside a larger observation, the prior instrument already froze an exact masked slot key consisting only of:

- parent proposal scale;
- target position inside the parent;
- target area contraction inside the parent;
- target aspect relation to the parent;
- capped immediate-sibling count.

The target's own topology was removed from the context. Occupant tokens, substitution-family IDs, provenance, institution, culture, language, object type and chronology are forbidden here.

## Only measurement change

The previous grammar was:

`CENTER:JUNCTION|DEGREE:<d>|ARM:<state>`

This test uses:

`CENTER:JUNCTION|DEGREE:<d>|PLACEMENT:<p>|ARM:<state>`

Physical extraction is unchanged. The 64 source-local null worlds are unchanged. Placement is constant for an observation, so it is constant in the observed world and every null world.

## Sequential test

Train discovers degree + placement + arm laws and freezes them before the relationship is evaluated in holdout. Holdout validates without refit. Control confirms holdout survivors without refit.

The strict gate remains unchanged: observed matching must lie above every one of 64 null matching accuracies for STRICT_MATCH, below every null for STRICT_REVERSE, otherwise unresolved.

## Falsifier

If the same degree + exact masked placement + arm condition still contains both strict matching and strict reversal across independent sources, this placement coordinate is not sufficient.

## Custody note

Both source datasets already existed before this test: the degree-law outcomes and the masked-slot placement atlas. Their **cross-relationship has not been computed before this preregistration**. This experiment therefore protects the join and the lane-by-lane transfer test rather than claiming that the marginal datasets are newly unseen.
