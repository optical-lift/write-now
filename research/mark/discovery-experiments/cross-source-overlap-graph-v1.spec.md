# Cross-Source Overlap Graph v1

Status: **descriptive graph protocol — freeze before graph assembly**
Date: **2026-09-18**
Parent freeze: `1ad476d765c6091cceabac6a609d17a34fcc3a22`

## Purpose

Assemble the first provenance-preserving source×law overlap graph from the certified raw book catalogues.

This graph is not a global grammar.

It may reveal overlap structure, missing measurements, and candidate regions for later reconstruction.

It may not invent law identities, source identities, composition, implication, or universality.

## Admitted source nodes

Only certified `BOOK-*` nodes from:

`source-level-disaggregation-v1.raw-book-registry.json`

Experiment surfaces V36/V38/V40 are evidence contributors, not source nodes.

Canon is excluded from the primary graph.

## Admitted law nodes

Only already-frozen strict equivalence signatures:

- `EQC-001`
- `EQC-002`

No `DISTINCT_LAW_SHARED_PATTERN` pair may be collapsed into a shared law node.

No unmatched local constraint may be silently assigned to one of these law nodes.

## Positive edges

Create a source→law edge only when the source catalogue cell is:

`PRESENT`

Every edge must carry:

- source ID;
- law signature ID/version;
- local evidence entry;
- experiment provenance;
- model-dependence group;
- evidence ceiling.

## Non-edges

`MEASUREMENT_UNRESOLVED` is not a negative edge.

It is preserved in a separate open-cell table.

Future negative states from the Absence-State Model must remain typed; they may not be represented as simple missing edges.

## Dependence custody

Raw book observations are non-overlapping, but many edges share a fitted model.

Therefore every edge carries one of:

- `V36_SHARED_TRAINING_MODEL`
- `V38_SHARED_TRAINING_MODEL`

Graph degree is descriptive coverage, not an independent-replication count.

## Allowed graph diagnostics

v1 may report only:

- source degree;
- law degree;
- connected components;
- exact source-law co-presence;
- unresolved/open-cell counts;
- model-dependence groups;
- descriptive set inclusion/intersection.

## Forbidden v1 inferences

Do not infer:

- law A causes law B;
- law A implies law B;
- law A is prerequisite for law B;
- laws compose because they co-occur;
- one law is more universal because it has higher degree;
- 18 edges equal 18 independent replications;
- books are ontological grammar boundaries;
- absence from an unmeasured cell.

## Nestedness caution

If all observed instances of one law lie inside the observed source set of another law, record only:

`DESCRIPTIVE_SET_INCLUSION`

Do not infer implication unless the narrower law has adequate measurement outside the broader law's positive set and the relevant negative opportunities have been observed.

## Readiness question

After graph assembly, ask:

> Does the graph contain enough independently localized law diversity and typed negative/open evidence to justify competing whole-system reconstruction models?

The graph is allowed to answer **no** and create another prerequisite.
