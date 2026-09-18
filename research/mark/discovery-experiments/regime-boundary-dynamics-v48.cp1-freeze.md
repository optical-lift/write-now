# Mark Regime Boundary Dynamics v48 — CP1 closure freeze

**Experiment:** `mark:regime-boundary-dynamics:v48`  
**Status:** CLOSED AT CP1 — EQUIVALENCE GATE FAILED  
**Date:** 2026-09-18

## Governing contract

V48 preregistered that the source-separated equivalent R3 coordinate model had to satisfy all three gates before any boundary modeling could begin:

- aligned ARI against canonical V46 assignments >= **0.85**;
- >= **50** coordinate-fit observations in every aligned regime;
- >= **20** coordinate-fit sources in every aligned regime.

Failure of any gate closes V48 without compiling persist/change targets.

No threshold may be weakened after seeing CP1.

## Exact implementation custody

- preimplementation freeze: `bd9b6ad11410b73c868741a3eb3c3fbe897fe380`
- CP1 fitter commit: `f71b0ab200376f84b2d602f4f94fce015549789d`
- CP1 fitter Git blob: `6b45ef87f3ce7fa9a3d71c20ed5db30e6378e7ac`
- locally executed fitter SHA-256: `61197bf7107465e37df1f7fe5d53b605fa5115460578a6f80f4cd03939f16982`

The local executable was verified with `git hash-object` to equal the committed Git blob before execution.

## Frozen CP1 input custody

Only the 171-source coordinate-fit lane was opened.

- sources: **171**
- observations: **5,305**
- source-list SHA-256: `b77f4f48353764d42888a0de4fb6f1027c78d11565b69ecefe88dd74dffbddbc`
- observation-list SHA-256: `c219978ab6ad8e81bf3ce55634ea9c167c00d4d666e214c43bef093dd2b13795`
- canonical assignment subset SHA-256: `433fa6c1aaa5190522175f2545faa3c9cdff3ffab0b564bddda255d5a43e4c00`

Frozen upstream feature artifacts:

- V46 validation features: `915a156ae27b9bc1d1539246c2ef554bf5e82d1da56c905c9e3fa934f3d13562`
- V46 confirmation features: `2064f7d8bb605199709bc72aca92176360fdfcba7aac3181c7b1e7fb6b57ab27`

## Exact CP1 output custody

- R3 equivalent model SHA-256: `2392f5be84b89bee61246cb548fc076c6877dabe2746c0c896f19d7d2555dc20`
- R4 source-relative model SHA-256: `775a074078f8ebdf8dff6e44659c2f9766d4f91aa74990523805377c3b22ad68`
- coordinate-fit assignment packet SHA-256: `5c1f2fd0988cc9bb8d237117a6fdebe84367f98c7e906a2e82b9571787cc5e45`
- CP1 summary SHA-256: `e99b1dd47077e86febaa08680c1bd5b355a4adbf4371f370313cba8c030d8b99`

The large coordinate packet and fitted-model bytes are frozen by SHA-256. They are not used downstream because the equivalence gate failed.

## R3 equivalence result

The source-separated rebuild used the exact preregistered R3 contract:

- 32 R3 features;
- StandardScaler;
- PCA retaining >=95% variance;
- 12 retained PCA components;
- KMeans K=5;
- random state 4601;
- n_init 20;
- max_iter 500;
- Lloyd algorithm;
- one-to-one alignment to canonical RG-001..RG-005 maximizing assignment agreement.

Result:

- explained variance retained: **0.95510**
- aligned agreement fraction: **0.77587**
- aligned ARI: **0.61066**

Aligned regime counts:

- RG-001: 596 observations / 58 sources
- RG-002: 2,036 / 120
- RG-003: 728 / 81
- RG-004: 1,880 / 112
- RG-005: 65 / 39

Population/support gates pass.

The equivalence gate fails only because:

`0.61066 < 0.85`

## R4 source-relative fit

R4 was fitted as preregistered on the same 171 sources before the CP1 status was known:

- raw features: 37
- retained PCA components: 17
- explained variance retained: **0.95159**

R4 is preserved as a CP1 artifact but receives no boundary target because V48 closes at the failed R3 equivalence gate.

## Structural meaning of this failure

This result says the five-regime partition is reproducible as a stable atlas under the original V46 training design, but **a five-cluster model refit only on the 171 V47-discovery sources does not reconstruct the same regime boundaries closely enough to be treated as an equivalent coordinate system**.

That is an important limitation of the proposed V48 design.

It does not reverse V46 or V47.

It does mean V48 cannot honestly use this rebuilt coordinate system as if it were the same RG space.

## Unopened material

Because CP1 failed:

- no persist/change targets were compiled;
- the 59-source boundary-development lane was not opened;
- the 53-source boundary-validation lane was not opened;
- the 431-source final-confirmation lane was not opened;
- no logistic model was fit;
- no null batch was run;
- no provenance was consumed.

## Closure

V48 is closed at CP1.

The next experiment must respond to the failed coordinate-equivalence assumption rather than weakening the 0.85 gate.

Possible future directions may include testing coordinate transport/alignment without reclustering, or treating source-relative continuous structure independently of the canonical five-state partition, but those are **new experiments** and are not authorized by this closure.
