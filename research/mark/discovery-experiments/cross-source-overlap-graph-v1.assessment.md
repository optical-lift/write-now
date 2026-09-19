# Cross-Source Overlap Graph v1 — Assessment

Status: **COMPLETE — GRAPH VALID, GLOBAL RECONSTRUCTION NOT YET READY**
Date: **2026-09-18**
Protocol freeze: `6e6808bfadb0f79036506fe9bab7cf82f6b373fe`
Parent source-disaggregation freeze: `1ad476d765c6091cceabac6a609d17a34fcc3a22`

## Purpose

Build the first primary Mark source×law overlap graph after replacing overlapping experiment surfaces with certified non-overlapping raw book nodes.

The graph is deliberately descriptive.

It does not infer a global grammar.

## Graph inventory

### Source nodes

**23** certified non-overlapping book nodes.

### Law nodes

Only the two strict same-law signatures already frozen before graph assembly:

- `EQC-001` — component inventory cannot substitute for relational placement/order;
- `EQC-002` — current state identity conditions the consequence/operation contract.

### Positive edges

**20**

- EQC-001 degree: **2**
- EQC-002 degree: **18**

### Open cells

**26**

Every open cell is:

`MEASUREMENT_UNRESOLVED`

There are no negative edges in v1.

This is correct: the historical experiments did not provide clean absence tests for the remaining cells.

## Connected structure

The positive graph has one main connected component containing:

- 18 book nodes;
- EQC-001;
- EQC-002.

Five books are isolated because neither law currently has a positive source-local measurement there:

- Ecclesiastes
- Job
- Nahum
- Proverbs
- Psalms

Isolation in this graph means **no current positive edge**.

It does not mean those books lack either law.

## Descriptive co-presence

Deuteronomy and Judges contain source-local positive evidence for both laws.

Therefore:

```text
EQC-001 positive set = {Deuteronomy, Judges}
```

and both are inside the current EQC-002 positive set.

This yields:

`DESCRIPTIVE_SET_INCLUSION`

only.

It does **not** establish:

- EQC-001 implies EQC-002;
- EQC-002 is upstream of EQC-001;
- the laws compose;
- one is a specialization of the other.

The reason is especially strong here:

EQC-001 was only source-locally measured with meaningful V36 support in two books. Psalms and Job were too sparse, and the other books are unmeasured for EQC-001.

The apparent nestedness is therefore heavily measurement-limited.

## Dependence structure

The 20 positive edges fall into two shared fitted-model families:

- `V36_SHARED_TRAINING_MODEL`: 2 edges
- `V38_SHARED_TRAINING_MODEL`: 18 edges

The book observations themselves are non-overlapping.

The model fits are shared.

Thus:

> graph degree measures **source-local transfer coverage**, not independent rediscovery count.

This distinction must survive every later model comparison.

## What v1 successfully establishes

The graph now has honest source custody.

It establishes that:

1. EQC-002 has positive transfer across 18 non-overlapping books under one frozen V38 model.
2. EQC-001 has positive book-level evidence in Deuteronomy and Judges under one frozen V36 model.
3. Deuteronomy and Judges currently expose both laws.
4. five books remain open rather than negative.
5. experiment overlap no longer creates duplicate source nodes.

This is a major improvement over the provisional experiment-level catalogue.

## What the graph does not yet contain

It has only **two law nodes**.

That is not enough dimensionality to distinguish the final reconstruction alternatives:

- fully independent local grammars;
- several grammar families;
- one larger grammar with partial projections.

With two law nodes, almost any proposed larger architecture would be underconstrained.

The graph would mostly reproduce:

> one broadly observed law + one sparsely measured law.

That is not a whole-system reconstruction.

## Why Step 9 is not ready

The original roadmap expected the overlap graph to contain enough independently recovered local law diversity for larger structure to emerge from overlaps.

v1 does not yet meet that expectation.

The problem is no longer source independence.

The problem is **law localization breadth**.

The Mark harvest contains many other eligible observed-system constraints, but most historical experiments were summarized at multi-source level and have not yet been localized to raw book/object/source nodes.

Examples include:

- history dependence;
- composition;
- cancellation;
- operator identity beyond state;
- context-conditioned consequence;
- topology edit constraints;
- exclusion constraints.

Those remain scientifically real findings.

They simply are not yet source-local graph nodes.

## New readiness gate

Before competing whole-system reconstructions, the primary graph needs a larger source-local law vocabulary.

The next checkpoint should therefore be:

**Source-Local Law Expansion v1**

Goal:

> take the remaining eligible Mark law candidates and determine, one by one, whether frozen historical artifacts permit source-local projection without changing the scientific rule.

For each law:

1. recover exact raw source IDs/partitions;
2. freeze source-local scoring before opening local outcomes where outcomes were not previously published;
3. preserve shared-training dependence;
4. add positive/local negative/open cells using the frozen Absence-State Model;
5. refuse localization where frozen evidence is insufficient.

## Readiness target

Do not move to competing reconstruction models merely because an arbitrary law count is reached.

Move when the expanded graph contains enough law diversity that at least two rival structural organizations make genuinely different predictions about held-out source-law structure.

That is the meaningful gate.

## Verdict

`GRAPH_VALID__LAW_DIMENSION_INSUFFICIENT_FOR_RECONSTRUCTION`

The correct response is to expand the source-local law dimension, not to force a larger grammar from two nodes.
