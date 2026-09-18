# Mark V46 validation protocol — frozen first anonymous regime atlas

**Experiment:** `mark:structural-regime-atlas:v46`  
**Status:** FROZEN BEFORE VALIDATION REGIME ASSIGNMENT  
**Date:** 2026-09-18

## Frozen inputs

- discovery selection freeze: `40da5f34ca2c04c74aa9934a1e7f9671e2ac8aa5`
- selected discovery model SHA-256: `5a0a430f8e127f46f31b207fd0be554d8cf622d11550dcb4b0987a5bd1705a5a`
- discovery feature artifact SHA-256: `0d45b335f8b468bed999d2455b4385b32bb742d7f1c7cf542a54b147ac976caf`
- validation feature artifact SHA-256: `915a156ae27b9bc1d1539246c2ef554bf5e82d1da56c905c9e3fa934f3d13562`
- validation observations: 4,372
- validation sources: 137
- validation observation-list SHA-256: `17311f30d5e7e0140d816e62b10cda21a1f58978eab7e6785ba3b1b73dd07e34`
- validation source-list SHA-256: `326e9e77e10d31790a50624df15f0cd7634e1d1c90440a4a2b0d2d2602c54b40`

The validation feature artifact was compiled with the exact frozen V46 feature compiler. No regime assignment was inspected before this protocol was written.

## No-refit rule

Validation may not:

- change the R3 feature list;
- refit StandardScaler;
- refit PCA;
- move a centroid;
- change K=5;
- relabel a discovery regime based on validation;
- use provenance, OCR, semantic classes, or Song labels.

Each validation row is transformed with the frozen discovery scaler/PCA and assigned to the nearest frozen KMeans center.

## Discovery-only support radii

For each RG-001 through RG-005, compute the squared Euclidean distance in frozen PCA space between every **discovery** row assigned to that regime and its frozen centroid.

The regime support radius is the discovery-only empirical 99th percentile of those squared distances.

A validation row is `IN_DISTRIBUTION` when its squared distance to its assigned frozen centroid is less than or equal to that regime's frozen discovery 99th-percentile support radius.

Validation outcomes may not alter these radii.

## Frozen validation criteria

The first five-regime atlas is considered **VALIDATION_SUPPORTED** only if all are true:

1. overall in-distribution fraction >= **0.90**;
2. every regime's in-distribution fraction >= **0.80**;
3. every one of RG-001..RG-005 appears in at least **20 distinct validation sources**;
4. Jensen-Shannon divergence between discovery and validation regime occupancy <= **0.10 bits**;
5. every regime receives at least one validation observation.

If any criterion fails, the result is not repaired by refitting. The failure becomes a validation residual to inspect under the V46 governance before confirmation opens.

## Additional descriptive diagnostics

Without affecting the frozen pass/fail gate, report:

- validation observations and fraction per regime;
- distinct validation sources per regime;
- median and 95th-percentile squared centroid distance by regime;
- discovery 99th-percentile support radius by regime;
- nearest/second-nearest centroid margin distribution;
- occupancy Jensen-Shannon divergence.

These diagnostics are structural only.

## Boundary

Confirmation remains sealed regardless of whether validation passes until the validation result and residuals are frozen.
