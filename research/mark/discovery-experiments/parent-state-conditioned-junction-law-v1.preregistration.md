# Parent-State Conditioned Junction Law Test v1 — Preregistration

Status: **FROZEN BEFORE PARENT-STATE LAW JOIN OUTCOMES**  
Date: **2026-09-19**

## Question

The component-placement experiment left **67 train cells MIXED** even after conditioning on degree and an independently frozen masked structural slot.

Does the frozen local state of the **smallest containing parent observation** separate any of those remaining collisions into direction-consistent laws?

## Why this coordinate is next

This coordinate was selected before the final placement control outcome in `relational-state-next-coordinate-audit-v1.md`.

The prior State Transition Grammar v1 already established, blind across train/holdout/control, that the containment hierarchy is stateful and directional: same-state persistence is enriched, specific cross-state transitions are suppressed, and short parent→child→grandchild programs depart strongly from null.

The current experiment uses only the **parent's frozen state ID**. It does not use the prior transition statistics as labels, and it does not use the target observation's local-state ID.

## Target

Primary analysis is limited to the exact **67 degree+placement+arm cells classified MIXED on the frozen placement train result**.

That target list must be deterministically extracted and hash-frozen before any parent-state-conditioned train result is read.

## Stronger success criterion

This experiment will not call a collision "explained" merely because subdivision makes a reverse observation too sparse to detect.

An original mixed cell is **TWO_SIDED_RESOLVED** only when:

- at least one parent-state subcell is `MATCH_ONLY`;
- at least one different parent-state subcell is `REVERSE_ONLY`;
- no testable parent-state subcell remains `MIXED`.

If only one direction remains testable after the split, the cell is labeled **ONE_SIDED_DECONFOUNDED**. That can support parent state as useful structure, but it is not evidence that parent state determines the original direction split.

## Frozen parent-state source

Parent state comes only from:

- Local State Field v1 run `33767475851`
- artifact `mark-local-state-field-v1-frozen`
- artifact ID `9899178820`
- ZIP SHA-256 `be0694bcca9c43a23455e2e97a7eed315b5fcc4eccc63c8e6882e76390d72d27`
- `observation-local-states.jsonl` SHA-256 `af381222aa0268a569c05b86b5952c56726318ac2ca43769afd8e097360ae695`

The parent relation comes from the already frozen masked-slot occurrence table and is the smallest strictly larger wholly-containing observation.

## Forbidden information

No provenance, object identity, institution, language, culture, chronology, occupant token, substitution-family ID, target topology, target local-state ID, grandparent state, or transition-history label may enter v1.

## Lane custody

Train discovers. Holdout validates without refit. Control confirms holdout survivors without refit.

Failure is retained as failure. Mixed subcells are retained rather than reassigned.
