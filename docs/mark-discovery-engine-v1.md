# Mark Discovery Engine v1

The first use of Mark is machine discovery across large glyph inventories. The visible Glyph Atlas is an inspection surface; it is not the research authority.

## Goal

Find structural patterns that are difficult for a human observer to notice because they recur across different visual forms, media, and historical classifications.

The engine searches blind representations for:

1. **Stable nearest-neighbor pairs** — two glyphs remain unusually close under at least three independent representation spaces.
2. **Stable groups** — groups co-cluster under at least three representations.
3. **Central structures** — glyphs occupying dense regions of the combined structural space.
4. **Bridge structures** — glyphs whose local neighbors belong to multiple machine-discovered clusters.
5. **Rare structures** — glyphs unusually distant from their nearest neighbors.
6. **Recurrent structural motifs** — repeated pre-semantic combinations of component count, enclosure, terminal/junction bands, symmetry, and aspect.

## Blindness contract

The discovery runner may use only anonymous Atlas IDs (`G#####`) and computer-derived physical measurements. The blind artifact must not contain:

- historical system identity
- language
- sign name
- Unicode label
- conventional reading
- meaning
- chronology
- geography
- display provenance
- the rendered character itself
- the font family

Context can be rejoined only after the blind artifact is written and SHA-256 identified.

## Representation spaces

The v1 proxy run uses four independent spaces:

- **topology:** connected components, enclosed regions, skeleton terminals, skeleton junction candidates
- **geometry:** log aspect ratio and principal orientation represented as a 180-degree-periodic vector
- **symmetry:** vertical symmetry, horizontal symmetry, and asymmetry between those axes
- **combined:** topology + geometry + symmetry

Each feature space is robustly centered/scaled before Euclidean comparison.

The engine does not treat a match found in one representation as strong evidence. Cross-representation recurrence is scored explicitly.

## Cluster selection

For each representation, deterministic farthest-first k-means is evaluated across a bounded range of cluster counts. The selected count maximizes mean silhouette score. Initialization and tie handling are deterministic so the same rendered corpus produces the same discovery result.

## Raster collision guard

The 300-sign v0 corpus is composed of standardized font/Unicode display proxies. Missing glyph fonts can render many unrelated characters as the same fallback box. The headless runner therefore calculates an anonymous raster hash for each rendered form and quarantines large identical-raster collision groups before discovery.

This guard is not a substitute for physical evidence. It only prevents obvious rendering failures from becoming candidate patterns.

## Evidence tiers

### Tier 0 — display-proxy hypothesis generator

The 300 standardized signs can produce candidate structures. These are useful for deciding where to spend physical-corpus effort, but they are **not historical evidence**.

### Tier 1 — physical-witness replication

A candidate must recur in governed Mark physical witnesses without relying on normalized fonts or conventional sign drawings.

### Tier 2 — cross-source/cross-medium replication

A candidate must survive across distinct physical source objects and, where applicable, different media or independent corpora.

Only Tier 2 candidates should inform the later search for a universal glyph.

## Universal glyph consequence

The eventual universal glyph is not selected by visual averaging. Once the physical corpus is large enough, Mark will search for a structural form that optimizes generative reach across the discovered space: low description complexity, high centrality, high transformation reach, and robustness across independent corpora.
