# Mark V47 higher-order discovery implementation freeze

**Experiment:** `mark:regime-transition-grammar:v47`  
**Status:** FROZEN BEFORE LENGTH-3/4 CHAIN OUTCOMES  
**Date:** 2026-09-18

## Upstream authorization

- pairwise discovery freeze: `eb9996d49a51ad03284daa5b49d1a4fb744690ad`
- pairwise raw result SHA-256: `e0623f374b3d065288ded3c9c4a1ff636835632b8675ba081045bedfabe564ff`
- harvested pairwise rules: 7

Because pairwise discovery harvested at least one rule, V47 Phase B is authorized.

## Frozen inputs

- discovery geometry SHA-256: `480c174ff503ad877f5d08cdf0dae78007750334873045bd0d8e91a9e8513f55`
- fixed V46 mapping SHA-256: `633918a3bad435adfdef9859a33743b9fa88bfcf59a79a4ed8a59b71141d9d90`
- discovery observations: 5,305
- discovery sources: 171

Validation and confirmation remain unopened.

## Frozen implementation

- higher-order harvester commit: `0915a72b8c1ed147b7fc74260141613667317884`
- Git blob: `a210640547855fee0762997a6f8f39cbcb950b6a`
- file SHA-256: `ad793c9f143dbb40c42cdcf926fd5bee05ed571a38ab63b15965b8276ff9f200`

The local execution file was rematerialized from the current GitHub blob, verified with `git hash-object`, and bytecode-compiled successfully before execution.

## Frozen chain definition

For length 3 and length 4 separately:

- begin at any discovery observation;
- follow its frozen parent pointer repeatedly;
- retain the chain only when the requested number of nodes exists;
- node order is child -> parent -> ancestor -> rootward ancestor.

Skipped proposal scales are allowed when they already exist in the frozen geometry.

## Frozen predictive comparison

Symmetric additive smoothing:

- alpha = **0.5**
- regime alphabet size = **5**

Higher-order model:

`P(next RG | complete prior scale+RG history and next scale)`

First-order baseline:

`P(next RG | immediate prior scale+RG and next scale)`

Scale-only baseline:

`P(next RG | immediate prior scale and next scale)`

Metric:

mean negative log2 likelihood over all chains sharing the observed context.

Higher-order gain:

`first-order log loss - higher-order log loss`

Positive values mean the longer history improves held-in discovery prediction beyond the pairwise model.

## Frozen matched null

Iterations: **100**

Seed i:

`first 64 bits of SHA256("mark:regime-transition-grammar:v47|higher-order-null|" + i)`

interpreted as unsigned big-endian.

Labels are shuffled only within each:

`sourceGroupId × proposalScale`

stratum.

For every observed higher-order context, compare the observed gain over first order to the matched null distribution for the same context key.

Null cutoff:

NumPy default linear 0.99 quantile.

Observed gain must be strictly above null Q99.

## Frozen candidate definition

For each observed history context:

1. find the dominant next RG;
2. create a full program key from the prior history plus that dominant next RG;
3. preserve the entire context even when it fails.

Candidate gates:

- dominant full-program occurrences >= **20**;
- dominant full-program distinct sources >= **10**;
- dominant next-regime probability >= **0.50**;
- held-in gain over first-order > **0 bits**;
- gain strictly above matched null Q99.

At most 15 programs are harvested per chain length.

Ranking:

1. distinct-source support descending;
2. gain above matched-null Q99 descending;
3. dominant occurrences descending;
4. program key lexicographically.

## Boundary

No length-3 or length-4 regime program outcome has been inspected before this freeze.

Validation and confirmation remain sealed until Phase-B discovery is frozen.
