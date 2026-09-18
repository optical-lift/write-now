# V45 Phase-A pre-execution freeze

**Experiment:** `mark:song-composition-harvest:v45`  
**Status:** frozen before V45 holdout outcome inspection  
**Parent V44 failure:** `fc536f7e541e23676a90ec89af7dde7f3267bab9`  
**Implementation SHA:** `c6d51f22357ddbc457c886965a79d30a913b0b1b`  
**Execution-config commit:** `a652b0252891da179ec2a0d3d47dd09c7759bab0`  
**Execution-config blob before mechanical bind:** `cfe095015ad1935d71141fc36ac1a96ff170df99`

## Scientific inheritance

V45 inherits the exact V43/V44 scientific experiment without alteration:

- frozen V5 physical packet and hashes;
- 433 pair-eligible observations;
- train 84 / holdout 230 / control 119;
- anonymous state and two-port operator definitions;
- composition equation and smoothing;
- CR-001 through CR-005;
- all train support thresholds, held-out transfer gates, matched controls, ablations, and topology-only invariance rules;
- zero stochastic null iterations;
- all semantic prohibitions.

## Implementation lineage

V45 retains V44's exact mapped-key `pcomp` LRU with maximum 8,192 entries.

The sole new change is removal of per-observation `operator_occurrence` memoization. The operator is recomputed on demand from the same descriptor and state functions. No operator descriptor field or hash preimage changes.

Frozen blobs:

- runner: `8c38403e6ec5fdd72e352e3763ea1ab79b6e672e`
- V45 core: `3a974db7afae84f7c5f54d23291bacf0a8d741ae`
- splitter: `b3250f7b8899bb2ec2a74c40c6a78879050de21f`
- inducer: `e471eb366e4485b3e16334295394483ee0e62f3b`
- evaluator: `02efc627bf2d0d9db6e6ca71c6ff1780c7ba6b6c`
- inherited invariant tests: `59935136d136b64b95d03e2bf415f9545fe75735`
- implementation equivalence test: `019f6012d83b9ad04d8c9dfe5da1f76259c4ddec`
- exact train-freeze comparison: `6f8a9c571a788ae124271a5e756ae959c5268c52`
- primary protocol: `a91e8280832ecad75679120d28ff8e64bd9081f2`
- topology protocol: `c99cf9aced9d14b1f6b0dd388ba2fba13afe9613`

## Mandatory pre-holdout gates

V45 must stop before holdout unless all of these pass:

1. V43/V44/V45 probability functions are exactly equal on the implementation fixture.
2. V44/V45 operator occurrence records are exactly equal on the graph fixture.
3. V45 `pcomp` cache remains bounded at 8,192.
4. inherited V9 invariant tests pass.
5. exact V5 packet and lane hashes revalidate.
6. V44 and V45 train induction are both run on the exact V5 train lane under the primary protocol and their serialized freeze packets match byte-for-byte.
7. the same byte-for-byte V44/V45 train-freeze identity holds under the topology-control protocol.

No V45 holdout/control outcome has been inspected before this freeze. Song semantics remain unopened.

After this note is committed, the only permitted pre-run edit is mechanical replacement of `preexecution_freeze_sha: "PENDING"` with this note's commit SHA.
