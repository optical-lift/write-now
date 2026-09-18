# Mark V47 pairwise discovery implementation freeze

**Experiment:** `mark:regime-transition-grammar:v47`  
**Status:** FROZEN BEFORE DISCOVERY TRANSITION LABEL JOIN  
**Date:** 2026-09-18

## Frozen inputs

- geometric graph freeze: `607258b2dde59cfae41abdc050fb72c77c0ded83`
- discovery geometry SHA-256: `480c174ff503ad877f5d08cdf0dae78007750334873045bd0d8e91a9e8513f55`
- fixed V46 assignment mapping SHA-256: `633918a3bad435adfdef9859a33743b9fa88bfcf59a79a4ed8a59b71141d9d90`
- discovery rows: 5,305
- discovery sources: 171
- linked discovery edges: 5,134

## Frozen implementation

- pairwise harvester commit: `635cc08c473b0a675bb2c02284a6edf49d81971e`
- pairwise harvester Git blob: `82943ee825455794649aeb4c1d56092b7ffe719c`
- pairwise harvester file SHA-256: `adb6fd2e17b99fc5500863b8fd199ddac6f8953b12429e86064bcff1c81f91fb`

The local execution file was verified to hash to the exact Git blob and passed Python bytecode compilation before execution.

## Frozen transition statistic

Transition key:

`childScale | childRG -> parentScale | parentRG`

Observed conditional probability:

`P(parentRG | childScale, childRG, parentScale)`

Scale-pair marginal baseline:

`P(parentRG | childScale, parentScale)`

Lift:

`conditional probability / scale-pair marginal baseline`

## Frozen matched null

Iterations: **100**

Seed for iteration i:

`first 64 bits of SHA256("mark:regime-transition-grammar:v47|pairwise-null|" + i)`

interpreted as an unsigned big-endian integer.

For each iteration, RG labels are permuted only within each:

`sourceGroupId × proposalScale`

stratum.

The null therefore preserves:

- source identity;
- source-level media mixture;
- proposal scale;
- geometry and parent links;
- per-source/per-scale regime frequencies.

For each observed transition key, the matched null statistic is the distribution of lift under those 100 permutations.

The null cutoff is the empirical NumPy 0.99 quantile of that lift distribution using NumPy's default linear quantile method.

Observed lift must be **strictly greater** than that Q99 value.

## Frozen harvest gates

A transition is discovery-eligible only if all are true:

- occurrences >= 20;
- distinct discovery sources >= 10;
- conditional probability >= 0.50;
- lift >= 1.25;
- observed lift > matched null Q99 lift.

At most 15 candidates are harvested.

Ranking:

1. distinct-source support descending;
2. observed lift minus null-Q99 lift descending;
3. occurrence count descending;
4. transition key lexicographically.

Every observed transition key and every failed gate remains in the output.

## Boundary

No discovery transition label was joined to the frozen geometry before this freeze.

Validation and confirmation transition outcomes remain sealed.
