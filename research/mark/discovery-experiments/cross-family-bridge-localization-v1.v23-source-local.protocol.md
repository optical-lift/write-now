# Cross-Family Bridge Localization v1 — V23 Source-Local Replay Protocol

Status: **FROZEN BEFORE SOURCE-LOCAL V23 OUTCOMES**
Date: **2026-09-18**
Parent experiment: `mark:structural-transition-consequence:v23`
Parent adjudication: `GLYPH_ONLY_STRUCTURAL_TRANSFORMATION`

## Exact aggregate reconstruction gate

Before source-local scoring, the V23 train model was rebuilt from the exact frozen artifacts:

- V21 Hebrew train artifact ID `9975190318`
- V21 Hebrew sealed evaluation artifact ID `9975190564`
- V10 glyph train artifact ID `9949415443`
- V10 glyph sealed evaluation artifact ID `9949415857`

Using the frozen V23 equations, the reconstruction matches the published non-permutation metrics exactly for:

- holdout/control;
- lemma;
- lemmaCoarseMorph;
- lemmaFullMorph;
- glyph;
- covered event counts;
- evaluable operator counts;
- operator-balanced interaction gain;
- operator-balanced total gain;
- positive interaction operator fraction.

Source-local outcomes remain unopened at this protocol freeze.

## Hebrew source restoration

The V21 packet stores only:

`anonymousUnitId = "V" + sha256(osisID)[:20]`

Book identity is restored only by recomputing this frozen hash over canonical OSIS verse IDs.

Validation requirement:

> every one of the 23,213 V21 train/holdout/control anonymous unit IDs must resolve uniquely to one canonical Hebrew Bible book.

No verse text, gloss, semantics, or conventional interpretation enters source-local scoring.

Source unit:

> canonical book

Because the V21 split is verse-hash based, a book contains both holdout and control verses. The book receives one source-local result only; holdout and control are internal replication lanes.

## Hebrew law target: MCR-089

Neutral target:

> incoming structural state alone cannot determine immediate outgoing state; current operator identity contributes additional information.

To isolate the operator main effect rather than the interaction term, score each covered event with:

`main_gain = log2 Pinv(outcome | state, operator) - log2 Pstate(outcome | state)`

where both distributions are the exact frozen V23 train models.

### Hebrew book support rule

A book is `SOURCE_LOCAL_SUPPORT` for MCR-089 only if:

1. each of lemma, lemmaCoarseMorph and lemmaFullMorph has at least **100 covered events** in the book's holdout lane;
2. each representation has at least **100 covered events** in the book's control lane;
3. mean event-level main_gain > 0 in **all three representations** in holdout;
4. mean event-level main_gain > 0 in **all three representations** in control.

Anything else is:

`UNRESOLVED_BY_SHARED_MODEL`

A failure is not a negative law edge.

This is intentionally stricter than merely reproducing the aggregate positive main effect.

## Glyph source unit

The frozen V10 evaluation packet exposes anonymous inscription identities but no opened cultural provenance.

Source unit:

> anonymous inscription

Do not relabel an inscription as a cultural/historical source.

## Glyph law target: MCR-072

Neutral target:

> immediate outgoing structural consequence contains context-conditioned operator information beyond the invariant operator model.

For each covered event, use the exact frozen V23 distributions:

- interaction gain = `log2 Pctx - log2 Pinv`
- total gain = `log2 Pctx - log2 Pstate`

### Glyph inscription support rule

An inscription is `SOURCE_LOCAL_SUPPORT` only if:

1. at least **20 covered events**;
2. at least **2 distinct frozen operators** among covered events;
3. at least **2 distinct frozen shared states** among covered events;
4. mean event-level interaction gain > 0;
5. mean event-level total gain > 0.

The threshold was frozen after inspecting raw inscription sizes only, not source-local V23 gains.

Anything else is:

`UNRESOLVED_BY_SHARED_MODEL`

No per-inscription permutation p-value is claimed.

## Bridge rule

MCR-072 and MCR-089 are **not** predeclared to be the same law.

Localizing both sides does not create a bridge by itself.

After source-local results freeze, any cross-family law identity would still require the already-frozen Law-Equivalence Adjudication Language.

The source-local replay is allowed to conclude:

> no strict bridge law currently exists.

## No tuning

No support threshold, representation requirement, lane-replication rule, source unit, or gain definition may change after source-local outcomes are opened.
