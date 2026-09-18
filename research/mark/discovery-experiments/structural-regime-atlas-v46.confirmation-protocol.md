# Mark V46 confirmation protocol — frozen first anonymous regime atlas

**Experiment:** `mark:structural-regime-atlas:v46`  
**Status:** FROZEN BEFORE CONFIRMATION REGIME ASSIGNMENT  
**Date:** 2026-09-18

## Frozen inputs

- discovery selection freeze: `40da5f34ca2c04c74aa9934a1e7f9671e2ac8aa5`
- validation freeze: `2be5fec0e68fd9d034b4513e467952bf895d9786`
- selected discovery model SHA-256: `5a0a430f8e127f46f31b207fd0be554d8cf622d11550dcb4b0987a5bd1705a5a`
- discovery feature artifact SHA-256: `0d45b335f8b468bed999d2455b4385b32bb742d7f1c7cf542a54b147ac976caf`
- confirmation feature artifact SHA-256: `2064f7d8bb605199709bc72aca92176360fdfcba7aac3181c7b1e7fb6b57ab27`
- confirmation observations: 4,872
- confirmation sources: 146
- confirmation observation-list SHA-256: `f25739969cd0e4f3620949801b54a8fbd54863eca21ac206b38c6f24f4555ca3`
- confirmation source-list SHA-256: `217b6832f575aece03d6b38687cfa7e53f9ca9e94460283f87b279714e9bfc4a`

The confirmation feature artifact was compiled with the exact frozen V46 feature compiler. No confirmation regime assignment was inspected before this protocol was written.

## No-refit rule

Confirmation may not:

- change the R3 feature list;
- refit StandardScaler;
- refit PCA;
- move a centroid;
- change K=5;
- alter any discovery-derived support radius;
- incorporate validation assignments into the model;
- relabel a regime based on validation or confirmation;
- use provenance, OCR, semantic classes, or Song labels.

Each confirmation row is transformed with the frozen discovery scaler/PCA and assigned to the nearest frozen discovery KMeans center.

## Support radii

Reuse the same support definition frozen before validation:

For each RG-001 through RG-005, compute the squared Euclidean distance in frozen PCA space between every **discovery** row assigned to that regime and its frozen centroid.

The regime support radius is the discovery-only empirical 99th percentile of those squared distances.

A confirmation row is `IN_DISTRIBUTION` when its squared distance to its assigned frozen centroid is less than or equal to that regime's frozen discovery 99th-percentile support radius.

Neither validation nor confirmation may alter these radii.

## Confirmation criteria

Reuse the validation gates unchanged.

The first five-regime atlas is **CONFIRMATION_SUPPORTED** only if all are true:

1. overall in-distribution fraction >= **0.90**;
2. every regime's in-distribution fraction >= **0.80**;
3. every one of RG-001..RG-005 appears in at least **20 distinct confirmation sources**;
4. Jensen-Shannon divergence between discovery and confirmation regime occupancy <= **0.10 bits**;
5. every regime receives at least one confirmation observation.

No criterion was added, removed, relaxed, or tightened after validation.

## Additional descriptive diagnostics

Without affecting the frozen pass/fail gate, report:

- confirmation observations and fraction per regime;
- distinct confirmation sources per regime;
- median and 95th-percentile squared centroid distance by regime;
- discovery 99th-percentile support radius by regime;
- nearest/second-nearest centroid margin distribution;
- discovery-vs-confirmation occupancy Jensen-Shannon divergence.

A validation-vs-confirmation occupancy comparison may be reported later as descriptive context only; it is not a confirmation gate.

## Boundary

Provenance/context rejoin remains sealed until the confirmation result and structural atlas are frozen.
