# Mark V44 preregistration — bounded-memory execution amendment

**Experiment ID:** `mark:song-composition-harvest:v44`  
**Parent failure:** V43 commit `5843d6a1fe1bdf5e12a0fa1ef5c507027932b9d1`  
**Status:** implementation amendment only; no V44 holdout outcome inspected

## Purpose

V44 exists only because the frozen V43 evaluator was killed after train induction while opening holdout. V44 does not change the scientific experiment.

V44 inherits V43 exactly for:

- the V5 frozen physical packet and all custody hashes;
- train / holdout / control lane membership;
- interface-state definition and support thresholds;
- anonymous operator definition and support thresholds;
- composition equation and smoothing;
- the five frozen candidate families CR-001 through CR-005;
- all matched controls, ablations, transfer gates, and success/failure thresholds;
- the topology-only surface-invariance control;
- the prohibition on Song semantics, translations, named glyph meanings, provenance rejoin, new-source acquisition, and product/runtime changes.

## Sole implementation amendment

V43's `pcomp(A,B,i,o)` memoized every mapped `(A,B,i,o)` key in an unbounded Python dictionary.

V44 computes the identical expression in the identical summation order:

`K_AB(s2 | s0) = sum_s1 K_A(s1 | s0) * K_B(s2 | s1)`

but stores at most **8,192** mapped `(A,B,inputState,outputState)` results in an LRU cache. Cache eviction changes only whether an exact value is recomputed later; it cannot change the value.

The incoming and outgoing states are mapped to the frozen vocabulary before the cache key is formed, exactly as in V43.

## Mandatory equivalence gate

Before the V5 corpus may be evaluated, V44 must:

1. compare the V43 and V44 probability functions over a finite exhaustive fixture and require exact floating-point equality;
2. force more than 8,192 composition keys and verify the V44 cache never exceeds 8,192 entries;
3. run the inherited engine invariant tests;
4. refuse execution if any V44 scientific protocol differs from the V43 frozen protocol except experiment/custody metadata.

## Phase-A candidate set

Exactly the same five candidates remain frozen:

- CR-001 — factorized sequential operator composition;
- CR-002 — operator idempotence under repetition;
- CR-003 — ordered-pair cancellation toward input boundary state;
- CR-004 — order sensitivity / noncommutativity;
- CR-005 — input-conditional composition.

No candidate may be added, dropped, redefined, or retuned after outcomes are visible.

## Closure

If the bounded evaluator completes, V44 must produce the Phase-A candidates, result, and freeze artifacts before any Song semantics are opened.

If it still cannot execute, record another computational failure. Do not tune the scientific experiment to make it run.
