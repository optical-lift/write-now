# V37 Preregistration — Fine Physical Glyph State → Hidden Hebrew Operator Path

**Status:** preregistered before V37 outcome inspection  
**Date:** 2026-09-06  
**Research line:** Mark / canon cross-modal structure  
**Predecessor:** V36 glyph path → hidden Hebrew operator path

## Purpose

V36 produced two facts that must now be separated rather than blended:

1. the real three-glyph order ranked the true hidden Hebrew operator path substantially better than reversed or shuffled order; and
2. exact anonymous mark identity substantially outperformed the frozen coarse topology/geometry/symmetry representation.

The open question is whether exact identity is genuinely categorical information, or whether it is functioning as a compressed lookup key for finer physical and relational structure that V36 discarded.

V37 therefore asks:

> **Can a substantially richer computer-readable description of glyph form recover the predictive advantage currently carried by exact anonymous glyph identity?**

The Hebrew target is not changed. Only the resolution of the visible physical representation is changed.

---

## I. Frozen V36 comparison that motivates V37

V36 held out Deuteronomy, Judges, Psalms, and Job and evaluated 145 supported occurrences against 400 supported candidate three-operator paths.

| Endpoint | Exact identity | Coarse combined physical form |
|---|---:|---:|
| top-1 | 2.07% | 0.0% |
| top-5 | 8.97% | 4.14% |
| top-10 | 20.69% | 6.21% |
| top-50 | 61.38% | 46.21% |
| median rank | 41 | 62 |

Order sensitivity in the coarse physical lane was:

| Condition | Median rank | top-10 |
|---|---:|---:|
| real | 62 | 6.21% |
| reversed | 142 | 2.76% |
| deterministic shuffle | 117 | 1.38% |

V37 is not permitted to reinterpret this gap away. It must measure how much of it survives after substantially richer physical representation.

---

## II. Competing explanations

### Explanation A — categorical identity

Each mark identity contains predictive information that is not recoverable from measured physical form. Under this explanation:

```text
coarse form ≈ fine form << exact identity
```

### Explanation B — high-resolution physical proxy

Exact identity preserves fine physical or relational information that V36 lost by compression. Under this explanation:

```text
coarse form < fine form <= exact identity
```

The preregistered working hypothesis is Explanation B, but equality with exact identity is **not** required.

---

## III. No untouched canonical books remain

A fresh whole-book holdout is no longer available. The union of V30–V35-P holdout books covers all 39 canonical books. V36 then reused four of those books.

Therefore V37 uses the preregistered fallback class allowed by the handoff: a deterministic contiguous-passage holdout.

### Frozen passage partition

Each canonical book is divided into non-overlapping five-chapter blocks:

```text
block_index = floor((chapter - 1) / 5)
```

There are 201 such blocks in the current Masoretic mark corpus.

All blocks are ranked globally by:

```text
md5('v37-holdout|' || canonical_book_code || ':' || block_index)
```

with canonical book code and block index as deterministic tie-breakers. The lowest 20% (41 blocks) are V37 holdout; all others are training.

This rule and the exact resulting block list are frozen in `glyph-fine-physical-v37.protocol.json` before hidden Hebrew outcomes are scored.

A three-token path is admissible only if all three tokens belong to the same side of the split. Paths crossing a heldout/training block boundary are excluded.

---

## IV. Visible physical representation is frozen before Hebrew outcomes

The primary glyph carrier is the normalized rendering of each qualifying Masoretic codepoint in **Noto Sans Hebrew Regular**, used as a controlled proxy rather than a physical manuscript witness.

The font binary itself is not added to the repository. The protocol records its SHA-256, version, and units-per-em. A reproducible extractor records only derived physical measurements and render hashes.

No conventional mark names, inherited grammatical functions, translations, Hebrew lemmas, morphology labels, or semantic categories are used to construct the physical representation.

### Fine physical families

The extractor measures continuous or count-valued information including:

- topology: Euler number, holes, components, endpoints, junctions, skeleton length;
- geometry: normalized bounds, size, aspect, density, perimeter, compactness, solidity, eccentricity, orientation, centroids, projection profiles, radial profiles, moment descriptors, boundary complexity;
- continuous symmetry: vertical, horizontal, and 180° rotational scores;
- graph structure: skeleton degree distribution, diameter, branch count and branch-length distribution, terminal-region distribution;
- internal relations: component size distribution, spacing, relative angle, centroid spread, relative scale.

Every nonconstant dimension is centered by its median, scaled by MAD×1.4826 (falling back to standard deviation when necessary), and clipped to [-5, 5]. PCA is then fit **only across the 30 visible glyph forms**, retaining the minimum number of components explaining at least 95% of visible physical variance. Retained PC dimensions are re-scaled to unit standard deviation across glyphs.

The extractor run completed before any V37 hidden-Hebrew scoring and froze these actual values:

- Lane 2: 48 raw fine individual features → 8 retained PCs (95.81% variance);
- Lane 3: 80 raw fine + relational/graph features → 10 retained PCs (95.96% variance).

The derived feature file SHA-256 is frozen in the protocol.

---

## V. Nested predictive lanes

The hidden target remains the V36 target:

```text
O = lemma_raw × realized morphology
```

for a three-token operator path:

```text
O1 → O2 → O3
```

The visible input remains one qualifying glyph per token:

```text
G1 → G2 → G3
```

### Lane 0 — training path frequency

No glyph information. Candidate paths are ranked by training occurrence count.

### Lane 1 — V36 coarse combined physical form

The exact frozen V36 combined topology/geometry/symmetry cluster assignment. Conditional categorical emission with α=5 smoothing toward the training-wide cluster distribution. No candidate-path frequency prior is added to the structural score.

### Lane 2 — fine individual physical state

The 8-PC continuous physical representation derived from topology + geometry + symmetry.

For each supported Hebrew operator and PC dimension, training glyph occurrences estimate a conditional Gaussian. Mean and second moment are shrunk with α=5 toward the training-wide physical distribution. Conditional variance has a frozen floor of 0.0625 in globally standardized PC units.

The candidate-path state score is the sum over positions of the mean per-PC log density of the observed glyph under the candidate operator.

### Lane 3 — fine relational glyph state

The same continuous Gaussian scoring rule, using the 10-PC representation that additionally contains graph and internal component-relation structure.

### Lane 4 — ordered physical transformation structure

Lane 4 adds adjacent-glyph state change.

For each adjacent pair:

```text
Δ(G1,G2) = PC(G2) - PC(G1)
Δ(G2,G3) = PC(G3) - PC(G2)
```

using the frozen Lane-3 PC coordinates.

For each supported Hebrew operator pair, the corresponding training deltas estimate a conditional Gaussian with the same α=5 moment shrinkage and variance floor.

The Lane-4 score gives equal weight to static state and ordered transformation channels:

```text
0.5 × mean static-state log density
+
0.5 × mean adjacent-delta log density
```

This prevents the new channel from winning merely by contributing more dimensions or more summed terms.

### Lane 5 — exact anonymous glyph identity

The V36 categorical exact-codepoint emission model, with α=5 smoothing toward the training-wide glyph distribution and no candidate-path frequency prior.

---

## VI. Frozen support and candidate inventory

To preserve direct comparison with V36:

- supported operator type: at least 20 training occurrences;
- primary candidate path: exact three-operator path observed at least 5 times in training;
- robustness inventory: exact path observed at least 3 times in training;
- all operators in a candidate path must meet operator support.

The holdout does not determine support.

Within each heldout five-chapter block, supported evaluation occurrences are deterministically ordered by:

```text
md5('v37-sample|' || canonical_book_code || ':' || chapter || ':' || verse || ':' || token_position)
```

using the first token of the three-token path. At most 100 supported occurrences per heldout block are retained. The true path must already be present in the training-defined candidate inventory.

---

## VII. Primary endpoint and gap recovery

The primary dependent variable is the rank of the actual three-operator path.

For every lane report:

- top-1;
- top-5;
- top-10;
- top-50;
- median rank;
- mean reciprocal rank.

The key V37 quantity is how much of the V36 identity advantage is recovered by richer physical representation.

For higher-is-better metrics:

```text
gap_recovered = (fine - coarse) / (identity - coarse)
```

For median rank, where lower is better:

```text
gap_recovered = (coarse - fine) / (coarse - identity)
```

If the denominator is zero, gap recovery is undefined for that metric rather than forced to a value.

---

## VIII. Order controls remain central

For every physical lane, compare:

```text
real:      G1 → G2 → G3
reversed:  G3 → G2 → G1
shuffle:   G2 → G3 → G1
```

The cyclic shuffle is deterministic and fixed before scoring.

The strongest proxy-hypothesis result would be improvement concentrated in Lane 4, with real delta order outperforming reversed and shuffled deltas.

---

## IX. Required shape-scramble controls

Rich models can memorize. Therefore V37 freezes 20 deterministic frequency-stratified physical scrambles.

Training-only visible glyph frequency divides the 30 glyph identities into five frequency strata. Within each stratum and each salt:

```text
v37-shape-scramble-00
...
v37-shape-scramble-19
```

physical vectors are reassigned among identities by deterministic MD5 order and one-position cyclic rotation. Glyph frequencies, support, candidate inventory, and Hebrew outcomes remain unchanged.

The real physical representation must be compared with this null distribution.

A secondary family-scramble control independently reassigns one raw physical family at a time within the same frequency strata before normalization/PCA, using frozen salts. This asks whether any apparent gain depends on the correct cross-family composition of each glyph.

---

## X. Ablations

The all-physical Lane-4 model is rerun after removing, one family at a time:

- topology;
- geometry;
- symmetry;
- internal component relations;
- graph refinement.

The derived feature file freezes the PCA representation for each of those ablations before outcomes are opened.

Removing the sequence-delta channel is exactly Lane 3 and is the primary delta ablation.

Ablations are interpreted only after primary lane results are frozen.

---

## XI. Identity-within-shape test

The chosen proxy font contains two exact-render identity collisions, discovered from render hashes before outcome inspection:

```text
U+0596 and U+05AD
U+059C and U+059D
```

Within this font, each pair has an identical recorded normalized rendering despite different Unicode identities.

This creates a particularly clean identity-within-shape control. On heldout paths containing one or more of these codepoints compare:

1. the exact-identity model; and
2. a collapsed-identity model in which each exact-render pair is a single anonymous category.

If exact identity materially outperforms collapsed identity on this subset, then information remains that this physical witness cannot express. If the advantage disappears, that favors the physical-proxy explanation for at least these matched forms.

This test does **not** prove that the two identities are physically identical in manuscripts; it is explicitly a proxy-font test.

---

## XII. Shape-within-identity perturbation

V37 does not claim to run the manuscript-witness version of this test unless multiple canon-aligned physical realizations of the same mark identity are available under governed provenance.

A second digital font may be used only as a separately labeled rendering-robustness analysis. It is not a substitute for physical manuscript witnesses.

The physical-witness question remains:

> holding mark identity fixed, do real physical variations predict different Hebrew structural outcomes?

That requires a larger canon-aligned physical-witness corpus.

---

## XIII. Secondary Hebrew projections

Using the same candidate inventory and frozen lane score, additionally report:

- individual operator recovery;
- morphology-path recovery;
- lemma-path recovery.

These are secondary to exact joint-path rank. They may explain *where* a gain occurs but may not replace the primary result.

---

## XIV. Interpretation matrix

### Result 1 — rich physical representation matches identity

Preferred reading:

> exact identity was largely acting as a lookup key for fine-grained physical structure in this proxy system.

### Result 2 — physical representation closes much but not all of the gap

Preferred reading:

> measured physical form carries substantial operator information, while either relevant physical variables remain unmeasured or identity adds a categorical component.

This is the preregistered most likely result.

### Result 3 — fine physical form does not improve over coarse form

Preferred reading:

> the V36 proxy hypothesis is weakened; current evidence favors exact mark category over the measured graphic structure.

Do not rescue the hypothesis by adding post hoc features to V37.

### Result 4 — sequence deltas produce the major gain

Preferred reading:

> the most informative physical variable may be transformation between glyph states rather than static glyph shape.

This would be the most important positive structural result.

---

## XV. Epistemic ceiling

Even a strong V37 result would not establish:

- that glyphs generate Hebrew;
- that glyphs are historically upstream of Hebrew;
- that a digital font is equivalent to a manuscript witness;
- that physical similarity establishes semantic identity;
- that exact Hebrew surface text can be reconstructed from marks;
- causation.

It would establish only the degree to which a richer, semantic-blind physical representation can account for the predictive information currently carried by exact anonymous glyph identity on a frozen hidden-operator task.

---

## XVI. Freeze rule

Before opening V37 hidden outcomes, freeze in the repository:

- this preregistration;
- the protocol JSON;
- exact passage holdout blocks;
- qualifying glyph inventory;
- coarse V36 mapping;
- fine feature extractor;
- derived feature artifact and hashes;
- normalization and PCA rule;
- support thresholds;
- candidate inventory rule;
- Gaussian smoothing and variance floor;
- Lane-4 channel weighting;
- deterministic sample rule;
- order controls;
- scramble salts/rule;
- ablations;
- primary endpoint.

Any material change after outcome inspection is a separately labeled robustness analysis or a new experiment. Null and contradictory results remain in the record.
