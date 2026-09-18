# Mark V46 discovery selection freeze — first anonymous regime atlas

**Experiment:** `mark:structural-regime-atlas:v46`  
**Status:** DISCOVERY REPRESENTATION SELECTED / VALIDATION STILL SEALED  
**Date:** 2026-09-18

## Inputs already frozen

- discovery feature freeze: `996b7d51237ccb91cdc3bad15408fff255e07319`
- discovery feature artifact SHA-256: `0d45b335f8b468bed999d2455b4385b32bb742d7f1c7cf542a54b147ac976caf`
- first-set runner commit: `f9cfb375c683ba0a6e9ddc054620d2b6ef2c537f`
- first-set runner blob: `04cfda603db2ab9d3fcfda872c02e43660adf009`
- exact first-set results SHA-256: `ebf418e6e653bc8bb6d527e0ae6e15bd11b9a9c0b0e787aebe54c05500021658`
- exact all-attempt assignments SHA-256: `c95f5e1dc747e07fbb013163ab80bc996b8e09279f491b3fb88c273e44aef5d3`

No validation, confirmation, provenance, OCR, semantic label, named glyph identity, or Song structure was opened before this selection.

## First attempt set

Four representations were run at K=2 through K=10, producing 36 preserved attempts:

1. R1 — full morphology;
2. R2 — scale-normalized morphology/topology;
3. R3 — topology/ecology emphasis;
4. R4 — source-relative normalized structure.

Fifteen attempts cleared the frozen minimum gates.

Across R1/R2/R3, K=5 is the last broad regime count that remains eligible before K>=6 repeatedly creates a smallest regime below the frozen 1.5% minimum.

Cross-representation agreement also peaks at K=5 among the eligible multi-view solutions:

- K=2 mean same-K cross-view ARI: 0.4479
- K=3: 0.3254
- K=4: 0.3827
- **K=5: 0.6869**

For the two representations that remove most absolute-scale influence while retaining topology:

- R2 K=5 ↔ R3 K=5 ARI: **0.8880**

R4 source-relative solutions are stable internally but deliberately orthogonal to the absolute/topological atlas; they are preserved as a competing within-source representation rather than discarded.

## Additional blind discovery audits

### Proposal-mechanism audit

For the selected R3 K=5 assignment, normalized mutual information with both proposal kind and proposal scale is approximately **0.0207**. The selected regimes therefore are not simply a restatement of the proposal machinery.

### Coarse-to-fine hierarchy audit

Within R3, the eligible K=2→3→4→5 sequence is mostly nested. Child-cluster parent purities were:

- K2→K3: **1.000 / 0.873 / 1.000**
- K3→K4: **0.974 / 0.999 / 0.991 / 0.844**
- K4→K5: **0.959 / 0.980 / 1.000 / 0.974 / 0.718**

This supports reading K=5 as the deepest supported discovery partition before K=6 creates an under-mass split, rather than as an isolated arbitrary clustering.


## Selected first atlas

**Selected attempt: `R3_TOPOLOGY_ECOLOGY:K5`.**

Selection is based only on discovery structural criteria:

- silhouette: **0.3551**
- residual compactness: **0.5572**
- mean seed ARI: **0.9941**
- mean source-holdback ARI: **0.9537**
- minimum regime fraction: **0.0256**
- minimum distinct sources in any regime: **133**
- strong agreement with independently parameterized R2 K=5: **ARI 0.8880**

R3 is preferred over R2 for the first atlas because it intentionally removes absolute area/density magnitude from the feature set and centers the representation on anonymous topology/ecology, degree structure, and path-length composition. This choice does not assert that scale is irrelevant; R1/R2 remain preserved discovery alternatives.

## Frozen anonymous regime identities

The selected model was rerun from the frozen discovery feature artifact with the committed attempt definition.

It reproduced the saved R3 K=5 assignment exactly:

- saved-assignment ARI: **1.0**
- exact label array equality before anonymous renaming: **true**
- PCA components retained: **12**

Anonymous regime IDs are assigned by a deterministic non-semantic rule:

> sort the five raw KMeans centers lexicographically in PCA coordinate order; assign RG-001 through RG-005.

Discovery inventory:

- **RG-001:** 1,237 observations / 9.18% / 154 sources
- **RG-002:** 4,832 / 35.84% / 299 sources
- **RG-003:** 865 / 6.42% / 150 sources
- **RG-004:** 6,203 / 46.01% / 251 sources
- **RG-005:** 345 / 2.56% / 133 sources

No semantic names are assigned.

## Frozen selected-model artifacts

- selected model path: `research/mark/discovery-experiments/structural-regime-atlas-v46.discovery-selected-model.json`
- selected model commit: `829ae8193f2ebb5ba660d565c19de7abc71468e6`
- selected model Git blob: `8cd936b3aa7d1f4b34b127bccdc92a002de07352`
- exact selected discovery assignments SHA-256 after deterministic anonymous regime renaming: `a01f00c4bce32c97ecb1679135457063e60de8df50b73f2d5972f4c650461b15`

The selected model is fully determined by:

- the frozen R3 feature list in the committed runner;
- `StandardScaler` fit on discovery only;
- PCA with `n_components=0.95`, `svd_solver=full`;
- KMeans K=5, random state 4601, n_init=20, max_iter=500, Lloyd algorithm;
- the frozen discovery feature bytes.

The selected-model Git blob above is the repository custody identity for the resulting fitted scaler/PCA/centers and now includes the deterministic raw-label → RG-ID map.

## Anonymous structural signatures

These are quantitative discovery signatures only.

### RG-001
Highest positive standardized offsets include high-degree pixels (degree 4–7), cycle density, mean degree, junction density, short one-pixel path segments, and topology entropy.

### RG-002
Higher path-segment density, degree-3 share, and short path bins; lower topology concentration and fewer long segments.

### RG-003
High component density, endpoints, degree-1/degree-0 share and type/token diversity; low mean degree and lower repetition.

### RG-004
High degree-2 share and longer path bins; lower junction/path-segment density and lower topology entropy.

### RG-005
Strong 64+ path-bin concentration, unusually concentrated critical topology types, and low short-path / degree-3 prevalence.

These descriptions do not identify what material the regimes contain.

## What remains unresolved

- R4 source-relative structure may represent a second, within-source axis not captured by the selected atlas.
- Exact V45 CR-001/002/003 ecology is still unavailable in compiler v1.
- Higher-order operator sequences remain unmeasured.
- Cross-scale source-local transitions have not yet been constructed.
- No context/provenance has been opened to interpret any regime.

## Next permitted boundary

The selected five-regime assignment rule is now frozen.

The next permitted action is to compile the **validation feature lane using the already-frozen V46 feature compiler**, then assign those rows to RG-001..RG-005 using the frozen discovery scaler/PCA/centers **without refitting or changing K**.

Confirmation and provenance remain sealed.
