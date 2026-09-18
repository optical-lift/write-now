# V44 Phase-A execution failure — no verdict

**Experiment:** `mark:song-composition-harvest:v44`  
**Status:** computational execution failure before Phase-A verdict  
**Date:** 2026-09-18  
**Parent V43 failure:** `5843d6a1fe1bdf5e12a0fa1ef5c507027932b9d1`

## What V44 proved

V44's sole preregistered implementation amendment was successful on its own terms:

- the V43/V44 probability-equivalence gate passed with exact equality;
- the composition cache was bounded at exactly 8,192 entries after 10,256 misses;
- all inherited V9 invariant tests passed;
- the exact V5 input packet and frozen lane hashes revalidated;
- length-aware train induction completed with the same frozen counts as V43;
- topology train induction completed;
- the train model froze successfully.

Length-aware train facts:

- observations: 84
- transitions: 242,278
- four-center paths: 476,496
- covered paths: 97,568
- frozen states including OTHER: 108
- eligible operators: 1,122
- idempotence candidates before cap: 8
- cancellation candidates before cap: 31, frozen to the preregistered maximum 20
- order-sensitivity candidates: 0
- conditional-composition candidates: 0

The train freeze SHA was:

`b3b6ab19428b115eebdd1bf8c44b0ec9e604dfba7724e2002b0486463e31a853`

These are train-only induction facts, not a Phase-A verdict.

## Failure boundary

The held-out evaluator was again terminated by the operating system with `SIGKILL 9` before a complete held-out result packet was written.

Live memory measurements showed that the bounded composition cache prevented the original V43 consequence-cache runaway, but a second inherited memory hazard remained.

The V9 graph object memoizes every two-port transit occurrence in `graph["operatorCache"]`. On a large frozen holdout observation with:

- 28,431 centers;
- 26,144 non-self center bundles;
- 104,852 distinct ordered transit occurrences;
- 223,270 oriented simple four-center paths;

the V44 evaluator reached about 354 MB RSS for that single observation and retained about 309 MB after the observation was deleted and garbage collection ran. Across the held-out lane, process RSS climbed past 2.6 GB before `SIGKILL 9`.

A diagnostic implementation that **only disables the per-observation transit memoization** on that same frozen observation produced the same operator/state calculations while:

- leaving `operatorCache` at 0 entries;
- peaking around 228 MB RSS;
- falling to about 184 MB after the row;
- preserving the bounded 8,192-entry composition cache.

That diagnostic was performed only after V44 had failed. It is not a V44 outcome and cannot amend V44 retroactively.

## Scientific custody

V44 has **no Phase-A verdict**.

No candidate status is assigned from the incomplete held-out run. No V44 scientific threshold, candidate definition, input, lane, state definition, operator definition, equation, matched control, or success criterion is changed here.

Song semantics remained unopened.

## Successor requirement

A successor experiment may make one additional implementation-only amendment:

- preserve the V44 bounded composition cache;
- stop memoizing per-observation `operator_occurrence` objects;
- recompute the exact same operator descriptor, operator ID, reverse ID, input state, and output state on demand;
- prove equivalence before holdout, preferably by requiring the complete train freeze packet to match V44 exactly;
- preserve all V43/V44 scientific design and candidate rules unchanged.

This note closes V44 without manufacturing a scientific result from an incomplete held-out evaluation.
