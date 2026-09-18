# Mark V46 validation freeze — first anonymous regime atlas

**Experiment:** `mark:structural-regime-atlas:v46`  
**Status:** VALIDATION SUPPORTED / CONFIRMATION STILL SEALED  
**Date:** 2026-09-18

## Frozen upstream identities

- discovery feature freeze commit: `996b7d51237ccb91cdc3bad15408fff255e07319`
- discovery selection freeze commit: `40da5f34ca2c04c74aa9934a1e7f9671e2ac8aa5`
- selected model SHA-256: `5a0a430f8e127f46f31b207fd0be554d8cf622d11550dcb4b0987a5bd1705a5a`
- discovery feature artifact SHA-256: `0d45b335f8b468bed999d2455b4385b32bb742d7f1c7cf542a54b147ac976caf`

## Validation feature custody

Validation was compiled with the exact frozen V46 feature compiler:

- compiler Git blob: `05ad94392a59d5207f1a78f79f495f4154d9971c`
- validation observations: **4,372**
- validation sources: **137**
- validation feature JSONL SHA-256: `915a156ae27b9bc1d1539246c2ef554bf5e82d1da56c905c9e3fa934f3d13562`
- exact local feature summary SHA-256: `8d735557b43eac8ef1ad657b8abdf8da080d32893a0d98e66db8a1974d67d065`
- exact local feature contract SHA-256: `8b79903d3cd3af755733ecd8b6d49342835474bf9cd629a718b0910dcb54325e`
- validation observation-list SHA-256: `17311f30d5e7e0140d816e62b10cda21a1f58978eab7e6785ba3b1b73dd07e34`
- validation source-list SHA-256: `326e9e77e10d31790a50624df15f0cd7634e1d1c90440a4a2b0d2d2602c54b40`

Post-run custody verified:

- 4,372 unique expected validation observation IDs;
- 137 expected validation source IDs;
- zero missing/extra observations;
- zero discovery/confirmation rows;
- schema and lane exactness.

Repository custody:

- validation feature summary commit: `0c39e16d7be1253a5f51f27bf958af9d496c80d5`
- validation feature summary blob: `dee2c8b70e63bcfcfcf48d64842fd8a076f54d7f`

## Validation protocol and evaluator

The assignment and pass/fail criteria were frozen before validation regime assignments were inspected.

- validation protocol commit: `edc5e5a21363a68781a69ba31677ae0043b2ed89`
- validation protocol blob: `5d5a9b552dedc0106342006f5d78219229950c93`
- evaluator commit: `91ab8392a0aa60c245844738ecdfcb587e7c856f`
- evaluator Git blob: `b2c6aa4843f7d54ab49ff15f868deb8defc2dba3`
- evaluator file SHA-256: `3087fc4aed39465ade7f6f5fe2191e9494a4ead307a884169ac07fa841572de3`

The evaluator performs:

`frozen discovery StandardScaler -> frozen discovery PCA -> nearest frozen K=5 centroid`

No fitting operation is performed on validation.

Each regime's support radius is its **discovery-only 99th percentile squared centroid distance**.

Frozen criteria:

1. overall in-distribution fraction >= 0.90;
2. each regime in-distribution fraction >= 0.80;
3. each regime occurs in >=20 distinct validation sources;
4. discovery-vs-validation occupancy Jensen-Shannon divergence <=0.10 bits;
5. every regime is present.

## Result

**Status: VALIDATION_SUPPORTED**

Exact local result SHA-256:

`475781855f7adb1db58dc330252c151b1c8323bbb0bc1874481cd748c3cba467`

Exact local assignment packet SHA-256:

`b77417e78caaf53ccbdd4e10a1a6540b97802907a468e6fd1f1c24f10905b056`

Repository validation result:

- result commit: `9883229c6f0ea2b6b60bcac3ec0c269bd13f6609`
- result blob: `690bbe9bce8a287d75c6bd6e3f646c8392e4230d`

### Overall

- overall in-distribution fraction: **0.9910796**
- occupancy Jensen-Shannon divergence: **0.0037602 bits**
- overall median nearest-vs-second-centroid margin: **0.7965**
- refit performed: **no**

### RG-001

- observations: **413** / 9.45%
- distinct validation sources: **39**
- within discovery Q99 support: **99.27%**

### RG-002

- observations: **1,380** / 31.56%
- distinct validation sources: **96**
- within discovery Q99 support: **99.20%**

### RG-003

- observations: **191** / 4.37%
- distinct validation sources: **39**
- within discovery Q99 support: **100%**

### RG-004

- observations: **2,277** / 52.08%
- distinct validation sources: **89**
- within discovery Q99 support: **99.17%**

### RG-005

- observations: **111** / 2.54%
- distinct validation sources: **44**
- within discovery Q99 support: **94.59%**

Every frozen validation gate passed.

## What this result establishes

The five-regime topology/ecology atlas was not merely a partition peculiar to the 431 discovery sources.

Without refitting, changing K, moving centroids, or using context, the frozen atlas assigns 4,372 observations from 137 unseen sources with:

- extremely high support under discovery-derived regime radii;
- all five regimes recurring across many independent sources;
- negligible change in the aggregate regime occupancy distribution.

This is evidence that the anonymous structural regimes recur outside the data that selected them.

It is **not** yet evidence about what those regimes mean.

## Preserved residuals

- RG-005 has the lowest validation support fraction, 94.59%, although it remains well above the frozen 80% regime gate.
- RG-003 has the lowest median centroid margin among the five regimes in the raw evaluator output and may sit closer to a structural boundary.
- source-relative R4 structure remains a preserved competing axis;
- exact V45-law ecology remains unavailable in feature compiler v1;
- higher-order operator programs remain unmeasured;
- cross-scale regime transitions remain unmeasured.

None of these residuals is repaired before confirmation.

## Boundary

Up to this freeze:

- provenance remains sealed;
- no semantic regime labels have been assigned;
- no source titles/institutions/languages have been opened;
- Song has not been used to interpret the regimes;
- confirmation has not been compiled or assigned.

The next permitted action is **confirmation** using the same frozen feature compiler, model, assignment rule, and support radii.

No validation-derived model change is permitted before confirmation.
