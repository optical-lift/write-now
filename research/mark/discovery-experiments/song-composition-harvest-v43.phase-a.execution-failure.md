# V43 Phase-A execution failure — no verdict

**Experiment:** `mark:song-composition-harvest:v43`  
**Status:** computational execution failure before Phase-A verdict  
**Date:** 2026-09-18

## What completed

The V43 preregistration, candidate construction, exact V5 input packet, lane inventory, reused V9 engine bytes, topology-only surface-invariance protocol, null/control policy, runner, and pre-execution freeze were all committed before V43 outcomes were opened.

The frozen training induction began successfully. The length-aware training pass completed over the exact V43 train lane and reported:

- train observations: 84
- raw one-step transitions: 242,278
- raw four-center composition paths: 476,496
- frozen interface states including OTHER: 108
- eligible operators: 1,122
- train-frozen idempotence candidates: 8
- train-frozen cancellation candidates: 31
- train-frozen order-sensitivity candidates: 0
- train-frozen conditional-composition candidates: 0

These are train-only induction facts, not a Phase-A verdict.

## Failure boundary

The process was terminated by the operating system with `SIGKILL 9` after the train model had frozen and while the evaluator was opening the held-out lane. No complete held-out evaluation packet was produced, so no V43 candidate status may be assigned from this attempt.

Inspection of the frozen V9 implementation identified the execution hazard: `build_probability_functions()` keeps an unbounded in-memory cache for factorized composition probabilities keyed by `(operatorA, operatorB, inputState, outputState)`. The held-out evaluator can visit a combinatorial number of these keys. This converts an otherwise streaming evaluator into an ever-growing memory workload.

The composition equation itself is not implicated:

`K_AB(s2 | s0) = sum_s1 K_A(s1 | s0) * K_B(s2 | s1)`.

## Scientific custody

V43 is **not negative, positive, open, or harvested**. It has **no Phase-A verdict**.

No V43 threshold, candidate definition, lane, corpus input, operator definition, state definition, matched control, or success criterion is changed or reinterpreted here.

Song semantics remained unopened throughout this failed execution. No Song compiler file, translation, named glyph meaning, or semantic relation family was used.

## Next experiment

A successor experiment must preregister the implementation-only repair before reopening holdout:

- preserve the exact V43 scientific design and frozen inputs;
- replace the unbounded composition-probability cache with an exact bounded-memory strategy;
- prove numerical equivalence to the V43 equation/implementation on a finite exhaustive fixture before scoring;
- keep train induction frozen before holdout;
- execute length-aware and topology-control evaluation without allowing memory state to grow across the full consequence space;
- preserve every V43 candidate family and failure condition unchanged.

This note closes the V43 execution attempt without manufacturing a result from an incomplete holdout run.
