# Mark Regime Transition Grammar v47 — preimplementation freeze

**Experiment:** `mark:regime-transition-grammar:v47`  
**Status:** FROZEN BEFORE TRANSITION GRAPH BUILD  
**Date:** 2026-09-18  
**Parent V46 next-bridge commit:** `f4b338e37b8323166feb7669569889b85637f52b`

## Frozen governance blobs

- preregistration: `70fef364d8bc145d2efcc61e7b11182262036a53`
- protocol: `a4daa0ce6d5e15b734cdc18aae5fd2537d9f42b1`
- START_HERE: `1662d15a375b0ccb558fd6a0eec15dd1375fb20e`
- partition freeze: `81084c3fe517008b17269464823b4bda39eb7df6`

## Frozen V46 inputs

- V46 confirmation freeze: `8a17e73d1f4bfde58f252e94aaa7f76a17fffdd0`
- selected regime model SHA-256: `5a0a430f8e127f46f31b207fd0be554d8cf622d11550dcb4b0987a5bd1705a5a`
- V47 fixed regime-assignment mapping SHA-256: `633918a3bad435adfdef9859a33743b9fa88bfcf59a79a4ed8a59b71141d9d90`
- alphabet: RG-001..RG-005

## Frozen source pool

Only V46 validation + confirmation sources may participate:

- sources: **283**
- observations: **9,244**
- source-list SHA-256: `b9cc1accbca97380178d8408e7c4d38f9b18ad22c64a785c5f5a8e835c82c729`

The 431 V46 discovery sources that fitted the regime centroids are excluded from V47 transition-rule learning.

## Frozen V47 source-separated lanes

Partition salt:

`mark-v47-regime-transition-grammar|`

- discovery: 171 sources / 5,305 observations
- validation: 59 sources / 2,332 observations
- confirmation: 53 sources / 1,607 observations

Exact identities are bound in the partition-freeze blob.

## Frozen geometric parent rule

Transition edges are built without reading regime labels.

Scale rank:

`local < neighborhood < field < object`

For child A and candidate parent B:

- same source required;
- parent must have strictly greater scale rank;
- parent must cover >=95% of child rectangular area;
- choose lowest eligible higher scale;
- then greatest containment fraction;
- then smallest parent area;
- then lexicographically smallest parent observation ID.

At most one parent is assigned per observation.

## Frozen null and candidate rules

Null:

- 100 deterministic permutations;
- shuffle frozen RG labels within each source x proposal-scale stratum;
- preserve geometry, parent edges, source identity, scale counts, and per-source-per-scale regime marginals.

Pairwise discovery candidate minimums:

- >=20 occurrences;
- >=10 discovery sources;
- conditional probability >=0.50;
- lift over scale-pair marginal >=1.25;
- observed lift above matched 99th-percentile null lift.

At most 15 candidates are harvested.

Higher-order lengths 3 and 4 open only if pairwise discovery yields at least one harvested rule.

## Boundary

No transition outcome, transition count, regime-pair enrichment, chain motif, validation result, or confirmation result was inspected before this freeze.

The next permitted action is only:

1. implement the geometric graph builder;
2. verify source/observation partitions and fixed assignment custody;
3. build the graph without joining RG labels into parent selection;
4. report graph coverage and chain-length/scale-pair inventory only;
5. freeze graph-builder bytes and graph artifact SHA.

Only after that graph freeze may discovery regime labels be joined to edges.
