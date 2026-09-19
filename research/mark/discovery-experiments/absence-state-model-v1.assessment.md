# Absence-State Model v1 — Assessment

Status: **COMPLETE — READY TO FREEZE**
Date: **2026-09-18**
Parent freeze: `5ac0fc9f0abac5d49ac849e0c181e1a8ed55a3c2`

## Question

When a candidate law is not observed in a source, what does that non-observation actually mean?

The model was required before building any overlap graph because a partial-projection system cannot safely encode every non-match as a negative edge.

## Main result

Absence is not one state.

The model separates:

1. **whether the law pattern itself is observed;**
2. **whether the complete law condition had an opportunity to occur;**
3. **whether the evidence could preserve/detect it;**
4. **whether the local source structure permits it;**
5. **whether source coverage is adequate.**

Only after those axes are frozen is an absence state derived.

## Ten derived states

### PRESENT

An admissible law instance/pattern is directly supported.

### OPPORTUNITY_PRESENT_PROHIBITED

The complete candidate-law condition exists, but a different evidenced local constraint blocks the candidate law's observable realization.

This is preemption, not proof that the candidate law itself is absent.

### OPPORTUNITY_PRESENT_NO_INSTANCE

The complete condition occurs, observability and coverage are adequate, no blocker or incompatibility is known, and the law pattern still does not appear.

This is the strongest empirical negative state short of structural contradiction.

It was added during instrument construction because the first draft incorrectly called such a case “compatible but unused.”

That correction is important:

> if the complete condition really occurs, a universal candidate law does not get to hide behind “unused.”

### COMPATIBLE_UNUSED

The local architecture is compatible, but the complete condition needed to instantiate/test the law does not occur in adequately covered evidence.

This is **possible but unused**.

It is not evidence against the law.

### NOT_PRESERVED

The evidence channel cannot preserve the required relation/consequence.

### OUTSIDE_EXPOSED_REGION

The source is a partial projection and does not expose the region in which the law condition would arise.

### NOT_YET_OBSERVED

Coverage/opportunity is incomplete enough that non-observation remains weak.

### STRUCTURALLY_INCOMPATIBLE

A frozen local structural rule contradicts a frozen necessary condition of the candidate law.

This is the strongest local architectural negative state.

### MEASUREMENT_UNRESOLVED

The relevant relation may exist, but the current instrument has not measured it or lacks adequate resolution.

### UNKNOWN_ABSENCE

The evidence cannot responsibly support any stronger classification.

## Why the model is multi-axis

A flat absence label would make several different claims indistinguishable.

For example:

```text
law not seen
```

could mean:

```text
the source never had the required condition
```

or:

```text
the condition occurred and the law failed
```

or:

```text
the source medium cannot preserve the evidence
```

or:

```text
another local law blocked the realization
```

or:

```text
the local architecture makes the condition impossible
```

Those have radically different implications for whole-system reconstruction.

## Strong negative evidence now has two distinct forms

### Tested empirical failure

`OPPORTUNITY_PRESENT_NO_INSTANCE`

The source can instantiate the condition, did instantiate it, and the law pattern was absent under adequate observation.

This is evidence against the candidate law applying at that opportunity.

### Structural incompatibility

`STRUCTURALLY_INCOMPATIBLE`

The source architecture cannot instantiate the law's necessary condition without violating an independently established local rule.

This is stronger ontologically at the local-source level, but still does not prove the law is absent from a larger system of which the source is only a partial projection.

## Prohibition is not incompatibility

`OPPORTUNITY_PRESENT_PROHIBITED` means:

- the relevant condition can exist;
- another local law blocks the candidate realization.

`STRUCTURALLY_INCOMPATIBLE` means:

- the candidate law's required condition itself cannot exist in the local architecture.

This distinction is essential if laws interact.

## Positive and negative evidence are intentionally asymmetric

One admissible instance can establish `PRESENT`.

Non-observation cannot establish incompatibility by itself.

That asymmetry is deliberate.

It prevents the reconstruction from inventing negative laws merely because the corpus is sparse.

## Historical confirmation from this project

The need for the model is not hypothetical.

Canon Constraint Adjudication v1 produced five blind `no_match` results.

A later, explicitly targeted canon search recovered partial canon-side structure for **all five**.

Therefore, within this project:

> **no current match has already been empirically demonstrated not to mean “law absent.”**

The v1 no-match statuses were valid at their checkpoint.

They simply described the state of the recovered inventory at that time.

The Absence-State Model preserves exactly that distinction.

## Calibration

The model was pressure-tested on **13 synthetic cases**.

All 10 derived states were exercised.

Additional precedence cases verified that:

- direct presence outranks absence logic;
- non-preservation prevents a tempting incompatibility inference;
- inadequate measurement prevents a prohibition claim;
- partial coverage prevents `COMPATIBLE_UNUSED`;
- a complete observed opportunity with no instance becomes `OPPORTUNITY_PRESENT_NO_INSTANCE`, not “unused.”

All 13 cases pass the frozen reference derivation.

## Reconstruction semantics

For the future source × law matrix:

### Positive edge

Only:

- `PRESENT`

### Strong negative edges

- `OPPORTUNITY_PRESENT_NO_INSTANCE`
- `STRUCTURALLY_INCOMPATIBLE`

These are different kinds of negative evidence and must remain distinct.

### Local blocking relation

- `OPPORTUNITY_PRESENT_PROHIBITED`

This should eventually become an interaction edge between laws, not merely a missing-law marker.

### Non-negative / open states

- `COMPATIBLE_UNUSED`
- `NOT_PRESERVED`
- `OUTSIDE_EXPOSED_REGION`
- `NOT_YET_OBSERVED`
- `MEASUREMENT_UNRESOLVED`
- `UNKNOWN_ABSENCE`

The overlap graph must not treat these as absence of the law.

## Law-version custody

Every absence entry is indexed to a frozen law signature version.

If the law's necessary condition changes, prior absence states become stale.

This is necessary because a source may be incompatible with one overly broad law definition and compatible with a later, more accurate one.

## Source-version custody

New source evidence may legitimately move an entry between states.

Examples:

- `NOT_YET_OBSERVED -> PRESENT`
- `OUTSIDE_EXPOSED_REGION -> PRESENT`
- `MEASUREMENT_UNRESOLVED -> OPPORTUNITY_PRESENT_NO_INSTANCE`
- `COMPATIBLE_UNUSED -> PRESENT`

The prior state remains historical provenance.

## Scientific implication

The model makes the “sources are partial projections” hypothesis testable rather than unfalsifiable.

Without this model, every missing law could always be excused as “not visible here.”

With this model, that escape is blocked.

If a complete opportunity occurs under adequate observation and the law fails, the source receives a real negative edge.

If the local architecture contradicts the law's necessary condition, it receives an even stronger structural negative.

So partial-projection reasoning can no longer erase falsification.

## Next checkpoint

The roadmap can now move to **Frozen Local Law Catalogues**.

Before the global overlap graph exists, each source/container must independently expose:

- which law signatures are present;
- which have demonstrated opportunities;
- which are compatible but unused;
- which are outside the source's exposed region;
- which are unresolved;
- which are blocked by local laws;
- which produce tested negative evidence;
- which are structurally incompatible.

Those catalogues must be frozen independently before cross-source assembly.
