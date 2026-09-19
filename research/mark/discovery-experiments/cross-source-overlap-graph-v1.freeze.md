# Cross-Source Overlap Graph v1 — Freeze

Status: **FROZEN**
Date: **2026-09-18**
Branch: `cross-source-overlap-graph-v1`
Parent source-disaggregation freeze: `1ad476d765c6091cceabac6a609d17a34fcc3a22`

## Graph result

- source nodes: **23**
- law nodes: **2**
- positive edges: **20**
- open unresolved cells: **26**

Law degree:

- `EQC-001`: 2
- `EQC-002`: 18

Co-presence:

- BOOK-Deu
- BOOK-Jdg

## Positive component

The main positive component contains:

- 18 book nodes
- EQC-001
- EQC-002

Five book nodes are isolated in the positive graph:

- BOOK-Ecc
- BOOK-Job
- BOOK-Nah
- BOOK-Pro
- BOOK-Psa

Their isolation means no current positive edge, not law absence.

## Dependence custody

- 18 positive edges use `V38_SHARED_TRAINING_MODEL`
- 2 positive edges use `V36_SHARED_TRAINING_MODEL`

Book observations are non-overlapping.

Model fits are shared.

Graph degree is therefore descriptive transfer coverage, not independent rediscovery count.

## Nestedness custody

The observed EQC-001 positive set is contained in the observed EQC-002 positive set.

This is frozen only as:

`DESCRIPTIVE_SET_INCLUSION`

No implication, prerequisite, specialization, composition, or causal relation is inferred.

## Readiness verdict

`GRAPH_VALID__LAW_DIMENSION_INSUFFICIENT_FOR_RECONSTRUCTION`

The source layer is now adequate.

The law layer is not.

Two law nodes do not provide enough dimensionality to distinguish:

- fully independent local grammars;
- multiple grammar families;
- one larger grammar with partial projections.

## Next checkpoint

**Source-Local Law Expansion v1**

Localize additional already-supported Mark constraints into certified raw source nodes where frozen historical evidence permits it.

Do not create new law identities merely to increase graph density.

## Frozen artifact blobs

- spec: `4ddc4305cfd23d4c57d9d7844b8460f05486c747`
- schema: `d72cede020061c3413d94354f7023e6228c36b0f`
- protocol freeze: `b28bdcdf839e2a846cfbf8ecc8fcb30ed52c7cae`
- graph: `bd7e0824275a552b4194987e4c6b463b37d8a258`
- assessment: `34606c273dc19e7c0d0e5cbe4a29ff8282d4be3c`
- manifest: `9dc238dfc03ea03b5cb975f29404a0128663a1be`
- validator: `2f168dae67b721015f30044525d9159e5c97028c`
- roadmap: `a181c97587b129beaeac9353140fe196ed6d28ca`

## Pre-freeze head

`cd4063f22e2c7a252eba864ee5385e28418f2ed2`
