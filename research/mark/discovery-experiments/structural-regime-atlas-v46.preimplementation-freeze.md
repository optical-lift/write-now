# Mark Structural Regime Atlas v46 — pre-implementation freeze

**Experiment:** `mark:structural-regime-atlas:v46`  
**Status:** FROZEN FOR IMPLEMENTATION; NO REGIME OUTCOMES OPENED  
**Date:** 2026-09-18  
**Parent V45 post-freeze commit:** `b953916415655e76b74ba91144c74d4ace2b087f`

## Frozen governance blobs

- preregistration: `3f798cec741b06abd56208a3211f6d4a7c3aedf9`
- protocol: `a38e4bc7ec053cf53c34a62e383c567983b528fc`
- START_HERE: `e36f3a7bfda6a2f46fdf1a49532752a2aa7a0b63`
- partition freeze: `09b0bedfc7362f4b78bcaa88f6175fec756e9b8e`
- result template: `44a9862fc99ee304f910a9fa3c2c1153944b0f30`

## Frozen source world

- Source Rule Atlas run: `33755743472`
- sealed evidence artifact id: `9893738364`
- sealed evidence artifact SHA-256: `5aee2d958875d711a148e08c37c613457eeb734efc8e2c773fa63782faad1a20`
- full compiler-blind input SHA-256: `4b64315a037b6ff6dfca3d99bade96e4c9c453f589e4beb0aa3dd5e0c2b92786`
- total source objects: 714
- total observations: 23,161

## Frozen exclusion and untouched pool

All 435 V5-selected observations are excluded.

- V5 edge-pair manifest SHA-256: `75e28e9e45bcc2245015b1d6a23000f9589b5b9f4a0104dad4e792d1cd445a36`
- canonical excluded-observation-id list SHA-256: `1735dbadeb93241237af7af3efbe22a7b4a942a80cf94db301e43caaef827076`
- untouched observations: 22,726
- canonical untouched-observation-id list SHA-256: `8d8a37a7fa80d42e1bff753b30539497a3bdbda1ce694e410b22328c23ce7b13`

## Frozen source-separated lanes

Deterministic partition:

`first_32_bits(SHA256("mark-v46-structural-regime-atlas|" + sourceGroupId)) mod 100`

- discovery 0–59: 431 sources / 13,482 observations
- validation 60–79: 137 sources / 4,372 observations
- confirmation 80–99: 146 sources / 4,872 observations

Partition identities are bound in `structural-regime-atlas-v46.partition-freeze.json`.

## Research direction frozen

V46 does not privilege writing/non-writing, Song compatibility, or any current historical hypothesis.

It asks which structural distinctions recur in the untouched physical world and at what scale.

The allowed next step is only:

1. audit measurable observables;
2. implement a disk-bounded source-blind feature compiler;
3. freeze implementation bytes, feature definitions, normalization, and discovery feature artifact;
4. then begin adaptive discovery on the discovery lane.

Validation, confirmation, and provenance interpretation remain unopened.

No regime score, cluster interpretation, source context, OCR, semantic class, or Song label has been used to select the V46 representation before this freeze.
