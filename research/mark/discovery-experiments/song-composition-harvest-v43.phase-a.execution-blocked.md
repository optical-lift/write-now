# V43 Phase-A execution block

**Experiment:** `mark:song-composition-harvest:v43`  
**Status:** stopped under the frozen Phase-A stop condition  
**Execution branch:** `mark-song-composition-harvest-v43`  
**Pre-execution head:** `b5ef4e3664d73b02d3b2b2a17d36a48c91b5f2bd`

## Boundary compliance

The V43 runner, primary protocol, topology-control protocol, and all five reused V9 engine files were verified byte-for-byte against the Git blob SHAs frozen in `song-composition-harvest-v43.phase-a.execution-freeze.json` before execution.

No Song repository or Song compiler semantics were opened. No translation, named glyph meaning, semantic dictionary, role-pair label, new source, Atlas, Noel, or production system was used.

## Input custody reverified

The frozen V5 split reproduced exactly:

- eligible observations: **433**
- train: **84 observations**
- holdout: **230 observations**
- control: **119 observations**
- edge-pair manifest SHA-256: `75e28e9e45bcc2245015b1d6a23000f9589b5b9f4a0104dad4e792d1cd445a36`
- critical-edge world SHA-256: `8061fa13da32f869c9a001432a659a2a7647cfefa876175df7d21b5d9d138aea`
- projector rows SHA-256: `e3dadcd6daf2921433c856458a651fcbfea6569852c67954d45d704699d71e2e`
- split SHA-256: `3a9607132c806a097c22aa1422ccd26ded231e0ddc69e4008f9502eac72b1c45`

## Last completed scientific state

Primary train induction completed and froze before evaluation failure.

Frozen operator model:

- operator algebra freeze SHA-256: `b3b6ab19428b115eebdd1bf8c44b0ec9e604dfba7724e2002b0486463e31a853`
- freeze file SHA-256: `1d4a15ccb08fc27137695504a865c1cbd8d36954e07d0552a151582fcee9b0f3`

Length-aware train inventory:

- transitions: **242,278**
- four-center composition paths: **476,496**
- covered composition paths: **97,568**
- states: **108**
- eligible operators: **1,122**
- train path coverage: **0.204761**
- frozen idempotence candidates: **8**
- frozen cancellation candidates: **20**
- frozen order-sensitivity candidates: **0**
- frozen conditional-composition candidates: **0**

Topology train inventory from the same frozen primary engine:

- transitions: **242,278**
- four-center composition paths: **476,496**
- covered composition paths: **100,302**
- states: **62**
- eligible operators: **1,124**
- train path coverage: **0.210499**

The zero train candidates for order sensitivity and conditional composition are preserved as observed pre-holdout consequences of the frozen candidate construction. They are not reselected or rescued.

## Execution failure

The unchanged holdout/control evaluator was then started from the frozen train model. The process was terminated by `SIGKILL (9)` before it emitted an evaluation result file.

Immediately before termination the evaluator had reached approximately **2.78 GB resident memory** inside an execution container with a **4 GiB cgroup memory limit**. The recorded execution log SHA-256 is:

`b07f31cea019c9d18f1ed23b76937c76dbc9638cc6aebaba56b33f9734fb41e3`

No completed V43 holdout/control score packet exists from this attempt. Therefore no Phase-A candidate status is assigned from partial in-memory work, and the required closure artifacts:

- `song-composition-harvest-v43.phase-a.candidates.json`
- `song-composition-harvest-v43.phase-a.result.md`
- `song-composition-harvest-v43.phase-a.freeze.md`

have **not** been created.

## Governing disposition

The pre-execution freeze explicitly requires Phase A to stop rather than redesign if the frozen runner cannot execute against the exact frozen inputs.

Accordingly, this attempt stops here. The evaluator is not optimized, sharded, rewritten, threshold-adjusted, or otherwise changed after holdout opening.

A future continuation must preserve the already-frozen runner, protocols, model construction, controls, candidate definitions, and train freeze and execute them in an environment capable of completing the unchanged evaluator. Any implementation change would require a newly governed experiment rather than silently altering V43.
