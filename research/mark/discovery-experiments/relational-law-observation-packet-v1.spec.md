# Relational Law Observation Packet v1

Status: **instrument under construction**
Branch: `mark-relational-law-observation-packet-v1`
Parent roadmap: `WHOLE_SYSTEM_RECONSTRUCTION_ROADMAP.md`

## Purpose

This packet is the first instrument required by the whole-system reconstruction roadmap.

Its job is deliberately narrow:

> **Preserve what a Mark experiment actually observed in a substrate-neutral relational form, without assigning a universal law, importing another source's vocabulary, or forcing the observation into a closed ontology.**

It is not a law catalogue.
It is not a cross-source matcher.
It is not a universal grammar.
It is not a semantic interpretation layer.

It is a neutral custody container for evidence that may later participate in those steps.

## Governing distinction

Every packet keeps two layers separate.

### Layer 1 — observed transformation or constraint

What physically, statistically, sequentially, or structurally happened in the experiment?

Examples:

- real sequence order outperformed reversed and shuffled controls;
- an exact identity retained information lost by a coarse physical representation;
- two independently learned one-step kernels composed to predict a two-step consequence;
- a proposed relational representation failed held-out generalization;
- a population-level structural partition transferred under a fixed model but could not be equivalently rebuilt in a smaller source population.

This layer must stay as close as possible to the frozen result.

### Layer 2 — relational structure

What relationships, dependencies, invariants, state changes, role constraints, sequence properties, or boundary conditions are required to describe that result without relying on its original domain labels?

This layer may abstract, but it may not claim a universal law.

A packet therefore may say:

> outcome depends on sequence order while member identities are held fixed

but not:

> this is the universal law of ordered composition.

The latter belongs to a later cross-source equivalence experiment.

## Why negative findings belong in the packet system

The future global reconstruction will be invalid if it preserves only successful rules.

A failed representation can be a stronger constraint than a successful predictor.

Examples already present in Mark include:

- exact one-to-one cross-system identity transfer failing;
- local relational contexts fragmenting the state space without improving held-out Hebrew prediction;
- a centerless exact field representation failing against a frequency baseline;
- a five-regime coordinate system failing an equivalence gate when rebuilt on a smaller source population.

Those failures restrict what a future larger grammar is allowed to claim.

For that reason `evidence.status` supports negative, rejected, diagnostic, unresolved, and insufficient-contrast observations as first-class records.

## Expandability rule

The packet has required structural fields, but the relational vocabulary is not closed.

There is no fixed list of:

- participant types;
- roles;
- relation kinds;
- state kinds;
- transformation kinds;
- invariants;
- composition behaviors.

If a future observation demands a new evidence-bearing dimension that the core packet cannot honestly represent, it belongs first in `extension_fields`.

Only after repeated need should the core schema be revised.

This is deliberate. The instrument must adapt to the evidence rather than making the evidence adapt to it.

## Source independence

The packet preserves the roadmap's opposite-of-export rule.

During local discovery:

- Source A does not receive Source B's operation vocabulary.
- Hebrew does not receive glyph labels.
- Mark does not receive Noel-derived law names.
- Noel does not define the Mark ontology.
- Natural-world analogies do not enter local discovery.

The `isolation` block therefore requires:

- `cross_source_matching_performed = false`;
- an empty external semantic label list;
- `universal_law_label = null`;
- no candidate equivalences.

Those fields are intentionally boring. They make contamination visible.

## Packet sections

### `discovery_lane`

Identifies the observational quarantine container and the experiment that produced the finding.

A source/container boundary is a custody boundary, not an assertion that the container is a true independent grammar.

### `evidence`

Preserves the frozen finding, provenance, result status, and quantitative anchors.

The packet should not strengthen the wording of the source result.

### `observation`

Describes the evidence surface:

- substrate;
- units actually observed;
- context;
- before state when one exists;
- event, manipulation, or contrast;
- after state when one exists;
- measured outcome;
- representation used;
- what was explicitly excluded.

Not every observation is a literal before/after transformation. Field structure, failed representations, population sensitivity, and boundary constraints are allowed.

### `relational`

Describes what must be true relationally for the observation to hold:

- participants and roles;
- relations before;
- relations changed;
- relations after;
- preserved invariants;
- changed properties;
- dependencies;
- role constraints;
- boundary conditions;
- order/repetition/composition/reversibility behavior;
- unknowns.

Unknown is a valid and important value.

### `epistemic`

Sets the ceiling.

Every packet must state:

- what is supported;
- what may not be inferred;
- what remains unresolved.

A packet is allowed to be only a negative constraint.

### `isolation`

Records whether comparison contamination has occurred.

For v1 pilot packets, no cross-source matching is permitted.

## What this instrument must be able to carry

The pilot deliberately includes observations of different kinds so the schema is not quietly optimized for one favored theory.

It must successfully represent:

1. cross-system identity failure;
2. nonrandom organization without successful consequence prediction;
3. incoming-state dependence;
4. context-conditioned transition effects;
5. observation-boundary censoring;
6. sequence-order information;
7. representation information loss;
8. morphology/identity decomposition;
9. identity-blind recurrence;
10. local-context overfitting;
11. center-blind distributed information;
12. failed centerless-field models;
13. sequential composition;
14. repetition/idempotence;
15. cancellation;
16. residual higher-order interaction;
17. population-level structural regimes;
18. scale persistence;
19. absence of higher-order discrete history;
20. coordinate instability under source-population change.

If any of these requires semantic reinterpretation merely to fit the packet, the schema fails its purpose.

## Pilot success criterion

The v1 packet is usable for the next stage only if:

- at least 20 materially different prior Mark findings can be represented without assigning universal-law labels;
- successful and failed findings fit the same custody structure;
- packets preserve enough provenance to return to the frozen result;
- the representation does not require a fixed operator vocabulary;
- no packet requires cross-source matching to be meaningful;
- at least one packet exposes a legitimate missing dimension or expansion pressure, proving that the schema can admit rather than conceal incompleteness.

The goal is not to prove the schema complete.

The goal is to show that it is **neutral enough to carry the evidence forward without flattening it**.

## Next stage if v1 survives

After the pilot is frozen and audited, the next project is the **Prior-Mark Evidence and Constraint Harvest**.

That harvest will produce source-local packets at scale.

Only after source-local catalogues are independently frozen do we design law-level equivalence criteria.

No global grammar is built during this instrument stage.
