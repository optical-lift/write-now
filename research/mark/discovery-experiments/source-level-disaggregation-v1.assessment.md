# Source-Level Disaggregation and Independence Certification v1 — Assessment

Status: **COMPLETE — READY TO FREEZE**
Date: **2026-09-18**
Parent local-catalogue freeze: `b5d0562212c5767f161c22aaae164b66af796f94`

## Purpose

Frozen Local Law Catalogues v1 exposed a serious readiness failure:

> three experiment-local Mark catalogues could not be counted as three independent sources because V36, V38 and V40 reuse overlapping biblical books/blocks.

This checkpoint replaces experiment-name pseudo-sources with actual non-overlapping raw evaluation sources wherever the frozen evidence permits it.

## Overlap audit

The concern was real.

V36 held out four whole books:

- Deuteronomy
- Judges
- Psalms
- Job

V38 held out 41 deterministic five-chapter blocks.

V40 held out 41 deterministic five-chapter blocks.

V38 and V40 share **10 exact holdout blocks**.

V38 contains **11 holdout blocks** inside the four V36 books.

V40 contains **11 holdout blocks** inside the four V36 books.

Therefore:

> experiment boundaries are not source-independence boundaries.

The provisional experiment-level catalogue graph must not be used for recurrence counting.

## Correct raw source unit

For the current Hebrew/glyph evidence family, the v1 source node is:

> **canonical biblical book**

Different book nodes contain non-overlapping heldout token observations.

The source registry therefore certifies:

`CERTIFIED_NONOVERLAPPING_BOOK`

for the raw evaluation evidence.

This does **not** mean the book nodes are independent model fits.

Model dependence is carried separately.

## Shared-model dependence

Book nodes may share:

- `V36_SHARED_TRAINING_MODEL`
- `V38_SHARED_TRAINING_MODEL`

This distinction is fundamental.

The current evidence can support:

> the same frozen law/model transfers to multiple non-overlapping raw source books.

It cannot yet support:

> eighteen independently trained models discovered the same law.

Future overlap/reconstruction work must preserve that difference.

## V36 retrospective localization

V36's frozen published result already reported meaningful book-level outcomes.

### Deuteronomy

n = 94 supported paths.

- real median rank: 64
- reversed: 122.5
- shuffled: 108
- real top-10: 6.38%
- reversed: 3.19%
- shuffled: 2.13%

### Judges

n = 43.

- real median rank: 40
- reversed: 230
- shuffled: 138
- real top-10: 6.98%
- reversed: 0%
- shuffled: 0%

Both therefore receive source-local support for `EQC-001`:

> component inventory cannot substitute for relational placement/order.

Psalms (n=7) and Job (n=1) remain `MEASUREMENT_UNRESOLVED`.

No rerun or threshold change was used for this V36 localization.

## V38 source-local replay

The aggregate V38 A1 result had never been opened block by block.

Before querying block outcomes, a source-local replay protocol was frozen at:

`0b49e2cd54ce7320c5dacbd8ab5ce12dd306d0d1`

The replay preserves exactly:

- the original state representation;
- the original deterministic holdout;
- the original training set;
- support threshold 100;
- top-64 destination alphabet + OTHER;
- first-order transition model;
- alpha 0.5 smoothing;
- training unigram baseline;
- five-chapter boundaries.

The only change is final aggregation:

> one score row per already-frozen holdout block instead of one score over all heldout blocks.

### Frozen local-support rule

A block earns `SOURCE_LOCAL_SUPPORT` only if:

- transitions >= 100; and
- frozen conditional CE - frozen unigram CE < 0.

A failure to satisfy that rule does **not** become negative evidence about the law.

It becomes:

`UNRESOLVED_BY_SHARED_MODEL`

because a globally trained transition model may fail in a book whose local law uses different state-specific probabilities.

## V38 replay result

- holdout blocks: **41**
- source-local support blocks: **24**
- unresolved blocks: **17**
- distinct books containing at least one supporting block: **18**

Supporting books:

- 1 Samuel
- 2 Chronicles
- 2 Kings
- Amos
- Daniel
- Deuteronomy
- Ezekiel
- Ezra
- Genesis
- Isaiah
- Judges
- Jeremiah
- Jonah
- Joshua
- Leviticus
- Malachi
- Numbers
- Zechariah

These receive book-level `PRESENT` support for `EQC-002`:

> current state identity conditions the consequence/operation contract.

## Replay verification

The 41 block rows recombine to the original published V38 A1 endpoint.

Reconstructed:

- transitions: **58,691**
- conditional CE: **2.8360684584**
- unigram CE: **2.8437660829**
- delta: **-0.0076976245**

Published:

- transitions: **58,691**
- conditional CE: **2.836068**
- unigram CE: **2.843770**
- delta: **-0.007701**

Absolute differences are rounding-scale only.

Verdict:

`REPLAY_MATCHES_PUBLISHED_AGGREGATE_WITHIN_ROUNDING`

This strongly supports that the block disaggregation is a faithful decomposition of the frozen V38 endpoint rather than a new analysis model.

## Unified raw-source catalogues

The provisional experiment nodes have now been replaced for reconstruction purposes by **23 book-level catalogues**.

Every catalogue carries exactly two currently shared law targets:

- `EQC-001`
- `EQC-002`

### EQC-001

`PRESENT`:

- BOOK-Deu
- BOOK-Jdg

All other book entries remain `MEASUREMENT_UNRESOLVED`.

### EQC-002

`PRESENT` in **18 books**:

- BOOK-1Sa
- BOOK-2Ch
- BOOK-2Ki
- BOOK-Amo
- BOOK-Dan
- BOOK-Deu
- BOOK-Eze
- BOOK-Ezr
- BOOK-Gen
- BOOK-Isa
- BOOK-Jdg
- BOOK-Jer
- BOOK-Jon
- BOOK-Jos
- BOOK-Lev
- BOOK-Mal
- BOOK-Num
- BOOK-Zec

Five books remain `MEASUREMENT_UNRESOLVED` under the shared-model replay.

### Co-presence

Only:

- BOOK-Deu
- BOOK-Jdg

currently have `PRESENT` entries for both EQC-001 and EQC-002.

This is a source-level fact.

It is not yet evidence that the two laws compose or form one larger law.

## What has now been certified

### Certified

1. Book nodes are non-overlapping raw evaluation sources.
2. Experiment-name pseudo-replication has been removed.
3. V38 block replay faithfully reconstructs the published aggregate.
4. EQC-002 transfers positively into 18 raw book sources under one frozen shared training model.
5. EQC-001 has book-local positive evidence in Deuteronomy and Judges.
6. Deuteronomy and Judges contain current evidence for both laws.

### Not certified

1. The books are not independent **model fits**.
2. V38 positive books did not each independently discover the state vocabulary.
3. V36 Deuteronomy/Judges did not independently learn their glyph/operator model.
4. Unresolved books are not negative law examples.
5. Co-presence does not establish composition.
6. Current book boundaries are observational source nodes, not asserted ontology boundaries.

## Overlap-graph readiness

The source-independence failure from Frozen Local Law Catalogues v1 is now repaired sufficiently to construct the **first descriptive overlap graph**, provided the graph carries dependence metadata.

The permitted claim is:

> a frozen law representation/model has source-local positive support across multiple non-overlapping raw book observations.

The graph may **not** convert the number of book edges into an independent-replication p-value or universality count.

### Readiness verdict

`READY_FOR_DESCRIPTIVE_OVERLAP_GRAPH_WITH_SHARED_MODEL_DEPENDENCE`

## Required graph constraints

The first overlap graph must:

- use `BOOK-*` nodes only for the primary Mark lane;
- never use V36/V38/V40 experiment nodes as independent sources;
- carry model-dependence-group metadata on every edge;
- treat `PRESENT` as a positive edge;
- keep `MEASUREMENT_UNRESOLVED` as open/non-negative;
- exclude canon from the primary Mark graph;
- not infer composition from co-presence;
- not infer universality from edge count.

## Next checkpoint

**Cross-Source Overlap Graph v1**

The graph should initially be descriptive and provenance-preserving.

Its purpose is to reveal which already-frozen laws overlap in which non-overlapping raw sources without allowing the graph itself to invent new equivalences or grammar.
