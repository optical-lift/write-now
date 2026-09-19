# Absence-State Model v1

Status: **instrument construction — freeze before source-law matrix application**
Date: **2026-09-18**
Parent freeze: `5ac0fc9f0abac5d49ac849e0c181e1a8ed55a3c2`

## Purpose

The whole-system reconstruction cannot treat:

```text
law not observed in source
```

as equivalent to:

```text
law absent from source
```

A source may fail to display a law because:

- the required relational opportunity never occurs;
- the source exposes only a different region of a larger system;
- the law is compatible but unused in the sampled evidence;
- the evidence channel cannot preserve the event;
- the source has not been sampled deeply enough;
- the relevant condition occurs but another local constraint prohibits the consequence;
- the source's local structure is genuinely incompatible with the law;
- the measurement instrument cannot adjudicate the case.

The model therefore separates **what happened**, **whether it could have happened**, **whether it could be seen**, and **whether the local structure permits it**.

## Core rule

> **Absence is a derived state, not a direct observation.**

No absence class may be assigned from non-observation alone.

## Four primary axes

Every source × law entry must record four independent axes before a final absence state is derived.

### 1. Instantiation evidence

- `OBSERVED_PRESENT` — at least one admissible instance is directly supported.
- `NOT_OBSERVED` — no admissible instance is present in the inspected evidence.
- `UNKNOWN` — the evidence cannot establish presence or non-presence.

### 2. Opportunity status

An opportunity exists only when the currently known **required law condition** could be instantiated in the source.

- `DEMONSTRATED` — the required roles/relations/condition occur in inspected evidence.
- `POSSIBLE` — the source contains the required role/relation types, but an actual full-condition opportunity is not demonstrated.
- `NONE` — adequate source coverage shows that the complete required condition does not occur, without by itself proving structural incompatibility.
- `OUTSIDE_EXPOSED_REGION` — the source is a partial projection whose observable region does not include the condition needed to instantiate the law.
- `UNKNOWN` — opportunity cannot be adjudicated.

Opportunity is about the **condition**, not the consequence.

### 3. Observability / preservation

- `ADEQUATE` — if the law instantiated in the inspected opportunity, the current evidence and instrument should preserve/detect it at the required resolution.
- `UNMEASURED` — evidence may preserve it, but the relevant measurement has not yet been run.
- `NOT_PRESERVED` — the source/evidence channel is known not to preserve the required relation or consequence.
- `INADEQUATE` — the measurement representation lacks the resolution or controls necessary to adjudicate it.
- `UNKNOWN` — preservation/detectability cannot be established.

### 4. Local compatibility

- `COMPATIBLE` — no known local rule prevents the law and the required relation types can coexist.
- `PROHIBITED` — the required opportunity occurs, but an evidenced local constraint blocks the target consequence/operation under that condition.
- `STRUCTURALLY_INCOMPATIBLE` — the local relational architecture cannot instantiate the law's necessary condition without violating established source structure.
- `UNKNOWN` — compatibility is unresolved.

`PROHIBITED` and `STRUCTURALLY_INCOMPATIBLE` are not synonyms.

- **prohibited**: the relevant opportunity can exist, but the consequence is blocked under that condition;
- **structurally incompatible**: the complete law condition itself cannot exist in the local architecture.

## Coverage modifier

Coverage is recorded separately because an apparently adequate measurement can still have inadequate sampling.

- `ADEQUATE`
- `PARTIAL`
- `NOT_SAMPLED`
- `UNKNOWN`

Coverage alone never proves compatibility or incompatibility.

## Derived source-law states

### PRESENT

Requirements:

- instantiation = `OBSERVED_PRESENT`

Presence outranks all absence classifications.

### OPPORTUNITY_PRESENT_PROHIBITED

Requirements:

- instantiation = `NOT_OBSERVED`
- opportunity = `DEMONSTRATED`
- compatibility = `PROHIBITED`
- observability = `ADEQUATE`

Meaning:

> The condition exists, but a local rule blocks the candidate consequence.

This is genuine negative evidence about local execution, not evidence that the higher-order law is missing.

### OPPORTUNITY_PRESENT_NO_INSTANCE

Requirements:

- instantiation = `NOT_OBSERVED`
- opportunity = `DEMONSTRATED`
- compatibility = `COMPATIBLE`
- observability = `ADEQUATE`
- coverage = `ADEQUATE`

Meaning:

> The complete currently known law condition occurred, the evidence could detect the law pattern, no local blocker is known, and the law pattern was not observed.

This is strong negative evidence against the candidate law applying in this source under the current signature.

It is **not** structural incompatibility: the local architecture can instantiate the condition. It is an empirical failure of the candidate law at an observed opportunity.

### COMPATIBLE_UNUSED

Requirements:

- instantiation = `NOT_OBSERVED`
- opportunity = `POSSIBLE` or `NONE`
- compatibility = `COMPATIBLE`
- observability is not `NOT_PRESERVED` or `INADEQUATE`
- coverage = `ADEQUATE`

Meaning:

> The local architecture is compatible with the law, but the complete condition needed to instantiate/test it does not occur in the adequately covered source evidence.

This corresponds to **possible but unused**.

It is not negative evidence against the law because the complete condition was never presented.

### NOT_PRESERVED

Requirements:

- instantiation != `OBSERVED_PRESENT`
- observability = `NOT_PRESERVED`

Meaning:

> The evidence channel cannot carry the relation/consequence required for adjudication.

No claim about source compatibility is permitted.

### OUTSIDE_EXPOSED_REGION

Requirements:

- instantiation != `OBSERVED_PRESENT`
- opportunity = `OUTSIDE_EXPOSED_REGION`

Meaning:

> The source is a partial projection and does not expose the region in which the law's condition would arise.

This state is essential for the partial-projection hypothesis.

### NOT_YET_OBSERVED

Use when:

- no instance is observed;
- no prohibition/incompatibility is established;
- opportunity is `POSSIBLE`, `UNKNOWN`, or demonstrated under only partial coverage;
- and the evidence is not known to be unpreservable.

Meaning:

> Current non-observation is epistemically weak and should remain open.

### STRUCTURALLY_INCOMPATIBLE

Requirements:

- instantiation = `NOT_OBSERVED`
- compatibility = `STRUCTURALLY_INCOMPATIBLE`
- evidence establishing the conflicting local structure is present.

Meaning:

> The source's local architecture cannot instantiate the necessary condition as currently defined.

This is the only derived state that licenses a provisional claim that the law is locally unavailable because of structure.

It does **not** prove that the source is outside a larger system containing the law.

### MEASUREMENT_UNRESOLVED

Requirements:

- observability = `INADEQUATE` or `UNMEASURED`
- no direct presence has already been established.

Meaning:

> The source may contain the law, but the current measurement cannot answer.

### UNKNOWN_ABSENCE

Use only when the other states cannot be responsibly assigned.

## Precedence

Derive the state in this order:

1. `PRESENT`
2. `NOT_PRESERVED`
3. `MEASUREMENT_UNRESOLVED`
4. `OUTSIDE_EXPOSED_REGION`
5. `OPPORTUNITY_PRESENT_PROHIBITED`
6. `STRUCTURALLY_INCOMPATIBLE`
7. `OPPORTUNITY_PRESENT_NO_INSTANCE`
8. `COMPATIBLE_UNUSED`
9. `NOT_YET_OBSERVED`
10. `UNKNOWN_ABSENCE`

The precedence prevents, for example, a measurement failure from being mislabeled as structural incompatibility.

## Evidence requirements

### To claim PROHIBITED

Require all of:

- an evidenced opportunity satisfying the law's known condition;
- an evidenced local constraint applying to that opportunity;
- a defined target consequence/operation;
- adequate observability.

Statistical absence alone is not prohibition.

### To claim STRUCTURALLY_INCOMPATIBLE

Require:

- a frozen necessary condition for the candidate law;
- a frozen local structural rule;
- a demonstrated contradiction between them;
- evidence that the contradiction is not merely a missing measurement or missing source region.

### To claim OPPORTUNITY_PRESENT_NO_INSTANCE

Require:

- the complete frozen law condition occurs;
- adequate coverage;
- adequate observability;
- no known prohibition;
- no structural incompatibility;
- no admissible law instance/pattern is observed.

This state is the strongest empirical non-occurrence evidence short of a demonstrated contradiction.

### To claim COMPATIBLE_UNUSED

Require:

- the local relation/role architecture is compatible;
- the complete law condition is not observed in adequately covered evidence;
- no known prohibition or structural incompatibility;
- the evidence channel is not known to erase the relevant relation.

Do not use this state merely because a law “could sound possible.”

## Negative evidence is asymmetric

A positive instance can establish `PRESENT`.

A missing instance cannot establish `STRUCTURALLY_INCOMPATIBLE` without additional structural evidence.

Therefore positive and negative evidence have intentionally different burdens.

## Partial-source rule

A source is not assumed to expose the full larger system.

If the source lacks the roles/relations needed for a law because its observable region never reaches them, assign:

`OUTSIDE_EXPOSED_REGION`

not:

`STRUCTURALLY_INCOMPATIBLE`

unless the local architecture actively forbids those roles/relations.

## Law revision rule

Absence states are indexed to a **specific frozen law signature version**.

If the law's necessary condition changes later, every affected absence state becomes stale and must be re-adjudicated.

Do not silently carry absence labels across law-definition revisions.

## Source revision rule

Likewise, new evidence may move a source-law entry:

- `NOT_YET_OBSERVED -> PRESENT`
- `OUTSIDE_EXPOSED_REGION -> PRESENT`
- `MEASUREMENT_UNRESOLVED -> COMPATIBLE_UNUSED`
- etc.

The prior state remains provenance history.

## Whole-system reconstruction rule

The future overlap graph may treat only `PRESENT` as a positive law occurrence.

It must preserve all other states explicitly.

Especially:

- `NOT_YET_OBSERVED` is not a negative edge;
- `OUTSIDE_EXPOSED_REGION` is not a negative edge;
- `NOT_PRESERVED` is not a negative edge;
- `MEASUREMENT_UNRESOLVED` is not a negative edge;
- `OPPORTUNITY_PRESENT_NO_INSTANCE` is strong negative evidence against the law applying at the tested opportunity, but not structural incompatibility;
- `COMPATIBLE_UNUSED` is not negative evidence against the law because the complete condition never occurred;
- `OPPORTUNITY_PRESENT_PROHIBITED` is evidence of an active local constraint;
- `STRUCTURALLY_INCOMPATIBLE` is the strongest local negative edge.

## No semantic filling

Absence status must be derived from source evidence and the frozen law signature.

Do not use conventional cultural, linguistic, historical, biblical, or symbolic expectations to decide what “should” be present.

## Freeze-before-application rule

This model must be frozen before any source × law absence matrix is constructed.
