# Absence-State Model v1 — Freeze

Status: **FROZEN**
Date: **2026-09-18**
Branch: `absence-state-model-v1`
Parent freeze: `5ac0fc9f0abac5d49ac849e0c181e1a8ed55a3c2`

## Final model

Absence is derived from five axes:

- instantiation evidence;
- opportunity status;
- observability/preservation;
- local compatibility;
- coverage.

The model defines ten derived source×law states:

- `PRESENT`
- `OPPORTUNITY_PRESENT_PROHIBITED`
- `OPPORTUNITY_PRESENT_NO_INSTANCE`
- `COMPATIBLE_UNUSED`
- `NOT_PRESERVED`
- `OUTSIDE_EXPOSED_REGION`
- `NOT_YET_OBSERVED`
- `STRUCTURALLY_INCOMPATIBLE`
- `MEASUREMENT_UNRESOLVED`
- `UNKNOWN_ABSENCE`

## Critical correction made before freeze

The first draft incorrectly allowed a complete observed opportunity with no law instance to fall under “compatible but unused.”

That was corrected before freeze.

Under the frozen model:

> If the complete law condition occurs, coverage and observability are adequate, no blocker exists, and the law pattern still does not appear, the state is `OPPORTUNITY_PRESENT_NO_INSTANCE`.

That is a **strong negative edge** against the candidate law applying at the tested opportunity.

By contrast:

> `COMPATIBLE_UNUSED` means the local architecture is compatible but the complete law condition never occurs.

It is not negative evidence against the law.

## Reconstruction semantics

Positive edge:

- `PRESENT`

Strong negative edges:

- `OPPORTUNITY_PRESENT_NO_INSTANCE`
- `STRUCTURALLY_INCOMPATIBLE`

Blocking/interacting-law state:

- `OPPORTUNITY_PRESENT_PROHIBITED`

Open/non-negative states:

- `COMPATIBLE_UNUSED`
- `NOT_PRESERVED`
- `OUTSIDE_EXPOSED_REGION`
- `NOT_YET_OBSERVED`
- `MEASUREMENT_UNRESOLVED`
- `UNKNOWN_ABSENCE`

## Calibration

Thirteen synthetic cases were run.

All **13/13** passed.

All ten derived states were exercised.

The calibration includes precedence tests showing that:

- direct presence outranks absence logic;
- non-preservation blocks a tempting incompatibility inference;
- inadequate measurement blocks a prohibition claim;
- partial coverage prevents `COMPATIBLE_UNUSED`;
- a complete tested opportunity with no instance becomes `OPPORTUNITY_PRESENT_NO_INSTANCE`.

## Historical support from the project

Canon Constraint Adjudication v1 produced five blind `no_match` results.

Targeted Canon Constraint Search v2 later recovered partial canon-side structure for all five.

Therefore the project has already demonstrated empirically:

> **no current match is not equivalent to law absent.**

## Frozen artifact blobs

- spec: `885661f1adfe6abd4e7903378e88714cfa55eb09`
- schema: `0087e785da4d336d4007221a7f7fa8492840397e`
- calibration: `11691eb3e2ebd8f4cb2cf7c53d9416d78dd03466`
- calibration results: `b24a45a6ef7fb700c6ade50f11f8d770965cfaf5`
- manifest: `f9563dafd65614319ee4b1124dc755e87c0ed467`
- assessment: `fe4fecefc8cdf513e205699dbec3c2dac0de6486`
- derivation script: `d8cb75ccc9c2adbf08d95f9b24ab924d60f9d9c9`
- validator: `05b607b59501d4b35969dce038bc062da30be3fc`
- roadmap: `709f4f541c91ef90ab9fb877c6a4e6307da43b67`

## Pre-freeze head

`f116c9b85f2f12f7cc3059c0e3813575311ac752`

## Next checkpoint

**Frozen Local Law Catalogues**

Each source/container must now independently record law presence and absence-state entries under this model before any cross-source overlap graph is built.
