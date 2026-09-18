# Mark V47 pairwise discovery freeze

**Experiment:** `mark:regime-transition-grammar:v47`  
**Status:** 7 PAIRWISE RULES HARVESTED / HIGHER-ORDER DISCOVERY NOW AUTHORIZED / VALIDATION SEALED  
**Date:** 2026-09-18

## Frozen implementation and inputs

- geometry freeze: `607258b2dde59cfae41abdc050fb72c77c0ded83`
- pairwise implementation freeze: `bd11ba9b02bdc8a8bd9a3ad0292062a64887fc8a`
- discovery geometry SHA-256: `480c174ff503ad877f5d08cdf0dae78007750334873045bd0d8e91a9e8513f55`
- fixed regime mapping SHA-256: `633918a3bad435adfdef9859a33743b9fa88bfcf59a79a4ed8a59b71141d9d90`
- pairwise runner Git blob: `82943ee825455794649aeb4c1d56092b7ffe719c`
- exact raw pairwise result SHA-256: `e0623f374b3d065288ded3c9c4a1ff636835632b8675ba081045bedfabe564ff`

The raw result retains all 73 observed transition keys, every failed gate, all matched-null summary statistics, and harvested flags.

## Pairwise verdict

Seven transitions pass every preregistered gate.

All seven are **regime persistence** rules: the child and parent remain in the same RG state as scale increases.

### RG-001
- local -> neighborhood: 150 occurrences / 36 sources / P=0.7389 / lift=6.8393 / null Q99=5.9440
- neighborhood -> field: 163 / 28 / P=0.9157 / lift=8.1000 / null Q99=7.0193

### RG-002
- local -> neighborhood: 611 / 95 / P=0.8393 / lift=2.0002 / null Q99=1.8373
- neighborhood -> field: 643 / 79 / P=0.9134 / lift=2.2137 / null Q99=2.0202

### RG-003
- neighborhood -> field: 44 / 14 / P=0.6377 / lift=17.9387 / null Q99=13.4535

### RG-004
- local -> neighborhood: 719 / 72 / P=0.8833 / lift=2.0802 / null Q99=1.9834
- neighborhood -> field: 726 / 58 / P=0.9553 / lift=2.1827 / null Q99=2.0941

No cross-regime transition met all frozen harvest gates.

## Important null interpretation

Several field -> object identity transitions have high raw persistence but do **not** pass the matched null.

For example:

- field RG-001 -> object RG-001: P=0.6014, lift=6.3936, but matched null Q99 is exactly 6.3936;
- field RG-002 -> object RG-002: P=0.8760, lift=1.9967, but matched null Q99 is exactly 1.9967.

This is not evidence that field-to-object persistence is absent.

The V47 null shuffles labels within each source × scale stratum. At object scale, many source strata contain only one object observation, so the object label cannot change under the null. In that circumstance the null correctly refuses to call raw persistence evidence of an additional transition rule beyond source/scale composition.

This is preserved as an identifiability boundary.

## Discovery interpretation boundary

The pairwise result supports:

> structural regime identity often persists across local -> neighborhood and neighborhood -> field scale expansion beyond what is expected from each source's scale-specific regime mixture.

It does **not** establish semantic identity or meaning.

## Phase B authorization

Because Phase A harvested at least one pairwise rule, the preregistered higher-order discovery may now open.

Lengths 3 and 4 may be tested.

The higher-order test must be frozen before chain outcomes are inspected and must compare longer-history prediction against:

- the first-order transition model;
- scale-only marginals;
- matched source-and-scale-preserving permutation nulls.

Validation and confirmation transition outcomes remain sealed until all higher-order discovery candidates are frozen.
