# V44 Phase-A pre-execution freeze

**Experiment:** `mark:song-composition-harvest:v44`  
**Status:** frozen before V44 holdout outcome inspection  
**Parent V43 failure:** `5843d6a1fe1bdf5e12a0fa1ef5c507027932b9d1`  
**Implementation SHA:** `ad25874a2a87c2aea1923b3f419e25987afda1ea`  
**Execution-config commit:** `abad23ab367c0376526f5e9c95284239d0b03396`  
**Execution-config blob before mechanical bind:** `38d86aaaf4b7deea85d446405c1eea3f1dae72b7`

## Scientific design

V44 inherits the V43 Phase-A scientific design without alteration.

Frozen inputs remain:

- V5 run `33807154154`
- artifact `mark-critical-edge-correspondence-v5-frozen`
- artifact ZIP SHA-256 `dfa99eb8b858efd599203b05e610ad950dc376cd0a2715ead1b8f79cd4adf75f`
- edge-pair manifest canonical SHA-256 `75e28e9e45bcc2245015b1d6a23000f9589b5b9f4a0104dad4e792d1cd445a36`
- critical-edge world canonical SHA-256 `8061fa13da32f869c9a001432a659a2a7647cfefa876175df7d21b5d9d138aea`
- projector rows SHA-256 `e3dadcd6daf2921433c856458a651fcbfea6569852c67954d45d704699d71e2e`
- pair-eligible observations: 433
- train: 84 observations / 43 distinct sources
- holdout: 230 observations / 154 distinct sources
- control: 119 observations / 63 distinct sources

The five candidate definitions CR-001 through CR-005, all thresholds, state/operator definitions, smoothing, matched controls, topology-only invariance control, and lane rules are unchanged from the frozen V43 execution config.

## Implementation-only amendment

The V44 core blob is `6dee34d6200134700b752ed1bc76cb38f9ce0729`.

Relative to the V43 core, the only probability-engine change is:

- V43: unbounded dictionary cache for mapped `(A,B,inputState,outputState)` composition probabilities.
- V44: exact LRU cache with maximum 8,192 mapped keys.

The composition equation, summation order, state mapping, smoothing, and return values are unchanged. Cache eviction only causes an exact value to be recomputed.

Frozen V44 runner blob: `42252c2e1cbc959ad22969405fd03ceb383c86c1`.

Inherited unchanged engine blobs:

- splitter: `b3250f7b8899bb2ec2a74c40c6a78879050de21f`
- inducer: `e471eb366e4485b3e16334295394483ee0e62f3b`
- evaluator: `02efc627bf2d0d9db6e6ca71c6ff1780c7ba6b6c`
- invariant tests: `59935136d136b64b95d03e2bf415f9545fe75735`

Protocol blobs remain byte-identical to V43:

- primary: `a91e8280832ecad75679120d28ff8e64bd9081f2`
- topology-only: `c99cf9aced9d14b1f6b0dd388ba2fba13afe9613`

Bounded-equivalence test blob: `7c184c263d3e1fd412cea8cd0ddf23dd449162ec`.

## Mandatory gate

Before the real V5 runner may score holdout, the runner itself must:

1. verify every frozen implementation blob above;
2. execute the V43/V44 exact probability-equivalence test;
3. verify the 8,192-entry cache bound;
4. execute the inherited V9 invariant tests;
5. revalidate the frozen V5 packet and lane inventory.

If any gate fails, V44 stops with no verdict.

## Outcome boundary

No V44 holdout/control outcome has been inspected before this freeze.

No Song ontology file has been opened. No translation, named glyph meaning, Song relation-family name, or semantic dictionary has been used.

After this note is committed, the only permitted pre-run edit is the mechanical replacement of `preexecution_freeze_sha: "PENDING"` with the commit SHA creating this note. No runner, protocol, threshold, candidate, input, or control may change before execution.
