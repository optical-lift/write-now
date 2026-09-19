# Degree-Conditioned Junction Law Test v1 — Preregistration

Status: **FROZEN BEFORE DEGREE OUTCOMES**  
Date: **2026-09-19**

Whole-Topology Condition Test v1 rejected pair density as the missing condition.

The next candidate is simpler and comes directly from the existing instrument.

The null generator already refuses to interchange centers of different degree:

```
(center kind, degree)
```

But the rule representation discards degree:

```
CENTER:JUNCTION|ARM:X
```

So the current law can be an aggregate of structurally different junction states.

## Hypothesis

> **Junction degree is an omitted law condition.**

The degree-conditioned grammar is:

```
CENTER:JUNCTION|DEGREE:d|ARM:X -> Y
```

Nothing else changes.

## Source custody

The nine original independent-discovery sources stay excluded.

The remaining 705 sources keep their old blind lanes:

- train: 237 — discovery only
- holdout: 236 — validation only
- control: 232 — confirmation only

The degree outcomes of holdout/control may not be opened until the train degree catalogue is frozen.

## Local gate

For one source, one degree and one context-arm state:

- require observed context count >= 30;
- **STRICT_MATCH** when observed matching accuracy exceeds all 64 source-local null accuracies;
- **STRICT_REVERSE** when observed matching accuracy is below all 64;
- otherwise **UNRESOLVED**.

This is the same all-64-null standard used in Independent Source Law Discovery.

## Train discovery

A degree/context pair is cross-source eligible when at least 10 train sources are locally eligible.

Classify it:

- **MATCH_ONLY**: at least 5 strict matches and zero strict reversals;
- **REVERSE_ONLY**: at least 5 strict reversals and zero strict matches;
- **MIXED**: at least one strict match and at least one strict reversal;
- otherwise **UNRESOLVED**.

Only MATCH_ONLY and REVERSE_ONLY enter the frozen train catalogue.

## Validation and confirmation

For every train-admitted degree law, require at least 10 eligible sources in the test lane.

Pass when:

- at least 5 decided sources reproduce the frozen direction; and
- at least 90% of decided sources reproduce it.

Every opposite strict state remains visible.

## Degree-sufficiency verdict

**SUPPORTED** only if every train-admitted degree law passes both holdout and control and no tested degree with at least 10 eligible sources becomes MIXED in holdout or control.

**PARTIAL** if some degree laws survive but another tested degree remains mixed/fails.

**REJECTED** if the train degree structure does not survive, or the dominant degree remains genuinely mixed across independent sources.

If degree fails, the next level is component placement/closure—not provenance category.
