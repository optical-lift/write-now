# Mark Structural Regime Atlas v46 — discovery feature freeze

**Experiment:** `mark:structural-regime-atlas:v46`  
**Status:** DISCOVERY FEATURE ARTIFACT FROZEN / REGIME DISCOVERY NOT YET OPENED  
**Date:** 2026-09-18

## Governing boundary

This freeze closes the V46 feature-compilation boundary.

No clustering, regime assignment, feature-selection by outcome, validation-lane inspection, confirmation-lane inspection, provenance rejoin, OCR/transcription, semantic class, named glyph identity, or Song ontology label was used to create or select this feature artifact.

The next permitted action is adaptive **discovery-lane regime analysis only**, preserving every attempted representation as required by the V46 preregistration.

## Parent governance

- V45 post-freeze parent: `b953916415655e76b74ba91144c74d4ace2b087f`
- V46 preimplementation freeze: `a965b583840ef8cb5c58d5d36ab53d7139661cb0`
- V46 preregistration blob: `3f798cec741b06abd56208a3211f6d4a7c3aedf9`
- V46 protocol blob: `a38e4bc7ec053cf53c34a62e383c567983b528fc`
- V46 partition-freeze blob: `09b0bedfc7362f4b78bcaa88f6175fec756e9b8e`

## Frozen implementation

- feature compiler commit: `64a40323d7b54fbc5ca8a2e7bcb0760690eb40ea`
- dependency-pin commit: `cb209a77fc0a7dc7871721fe4d8c8ebecd2ad7b8`
- compiler Git blob: `05ad94392a59d5207f1a78f79f495f4154d9971c`
- compiler file SHA-256: `045a2416f3f3ee9d5d633d02ed9dce0b50d569a950404e1e38b445c5d06b7eaf`
- requirements Git blob: `24b4ff0d98a2629b724fdad0569c1ba0bb313249`

The locally executed compiler was verified with `git hash-object` to equal the committed compiler blob exactly before the full run.

The built-in V46 feature-compiler self-test passed before full execution.

## Frozen evidence custody

- Source Rule Atlas run: `33755743472`
- sealed evidence artifact ID: `9893738364`
- sealed evidence ZIP SHA-256: `5aee2d958875d711a148e08c37c613457eeb734efc8e2c773fa63782faad1a20`
- blind compiler input SHA-256: `4b64315a037b6ff6dfca3d99bade96e4c9c453f589e4beb0aa3dd5e0c2b92786`
- excluded V5/V45 observation-list SHA-256: `1735dbadeb93241237af7af3efbe22a7b4a942a80cf94db301e43caaef827076`
- discovery source-list SHA-256: `a36f428e48c0fcfb70a81c3f6c6aa743740985046928c3d8bb8c4a648fb302df`
- discovery observation-list SHA-256: `a79d274f4b747359aaa891d8d1a8901a2702bce1856b8bed4fb0cc55d0a8f93e`

## Discovery feature artifact

- lane: `discovery`
- source objects: **431**
- observations / rows: **13,482**
- structural-feature JSONL SHA-256: `0d45b335f8b468bed999d2455b4385b32bb742d7f1c7cf542a54b147ac976caf`
- local summary JSON SHA-256: `824c147c32e77590115c28005a4b978e0d3bc4e09b5a5ad271d9df9b9c067ab8`
- local feature-contract JSON SHA-256: `1b0197a56be75a0cbd38932785f920577cc0e0b3b24dc8accea249829126fe2b`
- runtime stderr SHA-256: `0c76ff0376b472693a0e3672f0e4750996fea15dc9829346a0af104e1fa5b4a3`
- scientificFreezeEligible: **true**
- process exit status: **0**

Repository custody copies:

- discovery summary commit: `55e08de0e4304719a1d0600f451faa9323eaee1f`
- discovery summary blob: `249d633382b0b9fcf425e428d3704b7d71a58832`
- discovery feature-contract commit: `51edac02c37426b89307c0573a9aec15f1d71afe`
- discovery feature-contract blob: `88334ee7867dd89780fcbae9b317993815cbfff8`

The large JSONL artifact is bound by its SHA-256 rather than interpreted or reduced in this freeze.

## Integrity verification

A separate post-run integrity pass verified:

- exactly 13,482 unique row observation IDs;
- exactly 431 source IDs;
- row observation-ID set exactly equals the frozen discovery partition after the 435 exclusions;
- row source-ID set exactly equals the frozen discovery source set;
- zero missing observation IDs;
- zero extra observation IDs;
- every row has `v46Lane = discovery`;
- every row has schema `mark_structural_feature_row_v46_v1`;
- every row carries the frozen feature-availability contract;
- no forbidden provenance/context keys were found in the row records.

No validation or confirmation row was compiled.

## Runtime envelope

- Python: `3.13.5`
- NumPy: `2.3.5`
- OpenCV: `4.13.0`
- scikit-image: `0.26.0`
- wall time: **6:07.83**
- maximum resident set size: **830,560 KB**
- swaps: **0**

## Measurability audit

### MEASURED — graph morphology

The compiler records deterministic source-blind physical features including:

- observation area/aspect;
- dark-pixel fraction after frozen Otsu segmentation;
- skeleton pixel count/density;
- connected-component count;
- 8-neighbor adjacency edge count;
- 8-neighbor cycle rank;
- isolated/endpoint/path/junction pixels;
- endpoint/junction cluster counts;
- degree histogram and mean degree;
- degree-2 segment count and fixed length-bin statistics.

### PARTIAL — operator ecology

V46 compiler v1 records a deliberately V46-native local topology-token ecology:

- 8-neighbor skeleton occupancy mask;
- canonicalized under D4 rotations/reflections;
- type/token reuse;
- entropy/concentration;
- critical-point token ecology;
- top anonymous local topology types.

This is **not** called or treated as the frozen V45 operator vocabulary.

### UNAVAILABLE — exact V45 law ecology

The exact V5 critical-edge projector is absent from the V46 parent branch and the current execution environment lacks the Rust toolchain required to rebuild that old projector directly.

V46 therefore does not substitute a visually or mathematically similar extractor and does not claim CR-001/002/003 scores in this artifact.

This absence is preserved as a residual, not hidden.

### UNAVAILABLE IN COMPILER V1 — higher-order operator programs

No longer-sequence result is present in this feature artifact.

V46 discovery may add a separate higher-order attempt later, provided that attempt is preserved and does not rewrite this frozen feature artifact.

### DEFERRED — cross-scale persistence / transition

This requires source-local joins among already-compiled records. It does not require new pixel acquisition and may be attempted during discovery as a separate preserved representation.

## Frozen feature-generation contract

- source blind: **true**
- semantic labels consumed: **false**
- provenance consumed: **false**
- new source acquisition: **false**
- segmentation: OpenCV Otsu on exact observation crop
- foreground: grayscale value <= Otsu threshold
- skeletonization: `skimage.morphology.skeletonize`
- graph adjacency: 8-neighbor pixel graph
- local topology token: 8-neighbor occupancy bitmap canonicalized over D4 rotations/reflections
- normalization at compiler: **none**
- missing-value handling: **no imputation**
- V45 exactness claimed: **false**
- V45 substitution forbidden: **true**

## What is still sealed

At this freeze:

- no anonymous regimes exist yet;
- no cluster count has been selected;
- no structural representation has been selected by discovery outcome;
- no validation source has been scored;
- no confirmation source has been scored;
- no provenance/source meanings have been reopened;
- no writing/ornament/wear categories have been used;
- no Song semantic mapping has been attempted.

The discovery lane may now be opened under the adaptive V46 discovery rules.
