# Mark v6 — Relational Program Discovery

Status: experimental architecture. Passing CI validates machinery only. It does not establish a historical, linguistic, archaeological, semantic, or cultural hypothesis.

## Constitution

> Two things do not belong together because they look alike. They belong together only when the same relationship or transformation explains what they are doing.

Mark v6 replaces the visual-family center of v1–v5 with a relational graph and program-discovery kernel.

Pixels remain primary physical evidence. They are used to recover topology. They are not the space in which program identity is learned.

## What v6 keeps from v5

- exact-byte custody;
- stable continuity tokens and opaque blind IDs;
- exact and perceptual duplicate exclusion before evidence can count;
- machine-proposed multiscale regions;
- sealed train and non-training lanes;
- provenance reopening only after blind artifacts are frozen;
- immutable JSON artifacts and SHA-256 custody chains.

## What v6 explicitly rejects from v5

v6 does not use whole-object visual-family acceptance as evidence of a shared program. It does not define an operation as a delta between nearby visual feature vectors. It does not presume that a museum, medium, photograph collection, script, knot corpus, or any other human category is a meaningful negative class.

The old v5 synthetic fixture also contained a mirrored/restyled form of a training motif in its nominal holdout. That fixture may still be used to exercise code paths, but never as evidence that blind historical transfer has occurred.

## Blind pipeline

```text
physical source bytes
  -> custody + deduplication
  -> machine-proposed multiscale observations
  -> binary foreground topology
  -> skeleton + enclosed regions
  -> anonymous relational graph
  -> recurrent local graph motifs
  -> recurrent whole relational states
  -> physically nested graph edits
  -> masked relational grammar
  -> non-training transfer
  -> degree/relation-count preserving graph rewires
  -> freeze
  -> provenance rejoin
  -> human hypothesis layer
```

No culture, language, chronology, sign name, reading, institution, catalog identity, scholarly interpretation, or presumed semantic class participates in blind program discovery.

## Relational graph v1

Each eligible physical observation becomes `mark_relational_graph_v1`.

The initial anonymous node vocabulary is deliberately small:

- `COMPONENT` — one connected skeleton component;
- `ENDPOINT` — a clustered skeleton termination;
- `JUNCTION` — a clustered skeleton branch/intersection point;
- `CYCLE` — a connected skeleton component with no endpoint or junction node;
- `HOLE` — a background region physically enclosed by foreground.

The initial relation vocabulary is likewise physical:

- `PATH` — a skeleton path between critical nodes;
- `HAS_ENDPOINT`;
- `HAS_JUNCTION`;
- `HAS_CYCLE`;
- `ENCLOSES`.

Absolute orientation, stroke thickness, curvature, font, material, color, aspect ratio, centroid, and museum metadata do not participate in relational identity.

A Weisfeiler–Lehman-style iterative canonical fingerprint gives each graph a deterministic anonymous topology fingerprint. This is a practical canonicalizer, not a proof of graph isomorphism.

## Relational primitives

A relational primitive (`RP####`) is a radius-1 anonymous graph neighborhood recurring across the predeclared minimum number of independent source objects.

The primitive is defined by node/relation structure, not by image similarity.

## Relational states

A relational state (`RS####`) is an exact recurring canonical topology fingerprint across source objects.

This is intentionally stricter than visual clustering. Surface variation can be large while the graph remains identical; conversely, visually similar material that changes connectivity receives a different state.

## Nested transformations

A transformation (`RT####`) can only be proposed between two observations that are physically nested regions of the same source object.

The smaller observation is not paired with an arbitrary nearest neighbor. Its nearest enclosing multiscale observation is located from the already-sealed proposal geometry, and the graph edit between those two physical scopes is recorded.

The first v6 transformation signature uses changes in anonymous node-kind and relation inventories. This is a composition/edit operator, not yet a temporal state transition. Static images alone do not justify temporal language.

## Masked relational grammar

For every observed two-edge graph path, Mark creates two prediction tasks:

```text
known arm + center node -> masked other arm
```

Rules (`RG####`) are learned only when the same context recurs across independent training source objects.

The non-training lanes are then scored prospectively. The important question is not whether a held-out picture resembles a training picture. It is whether an unseen relational context contains the relationship predicted by the frozen grammar.

## No presumed negative category

The legacy challenge labels `holdout` and `control` remain in the custody pipeline because they are sealed source partitions, but v6 does not interpret `control` as meaningless or unrelated.

The evaluator renames them conceptually:

- transfer A;
- transfer B.

Both may contain real recurring programs. Neither is a false-positive class by definition.

## Relational null

The first v6 null attacks the actual relational claim.

Within each non-training graph, Mark repeatedly swaps edge targets between edges of the same relation type when the swap is valid. This preserves:

- node inventory;
- edge inventory;
- relation counts;
- source out-degree for the swapped edges;
- target in-degree for the swapped edges;
- the same physical observation count.

It changes who is related to whom.

Masked-relation prediction on the real graph is compared with prediction on these rewired graphs. A future evidentiary challenge may predeclare thresholds only before a real run; the v6 CI fixture does not tune or enforce a historical-effect threshold.

## Post-freeze context

`report-mark-relational-programs.mjs` reopens the custody map only after both the blind world and blind transfer evaluation have been sealed.

Human-readable provenance may then be attached to `RP####`, `RS####`, `RT####`, and `RG####`, but it cannot change their frozen anonymous identities.

Semantic names remain hypotheses attached to programs. They do not replace program IDs.

## What CI is allowed to prove

The v6 CI contract may prove only that:

- graph extraction ran across train and both non-training lanes;
- surface metadata and node IDs do not change relational identity in the abstract contract test;
- rewiring connectivity does change relational identity;
- program discovery does not invoke v5 visual-feature distance or whole-image similarity;
- recurrent relational primitives and a maskable grammar are exercised by the synthetic fixture;
- both non-training lanes are evaluated without assigning either one the status of a meaningless negative class;
- the graph-rewire null actually runs.

CI must end with an explicit statement that no historical or semantic hypothesis is asserted.

## Known boundaries of v6.0

1. **2D junction ambiguity.** A raster crossing and a true branch can produce the same junction. Mark must leave that relation anonymous unless additional physical evidence distinguishes them.
2. **Segmentation dependence.** Otsu foreground extraction is still a mechanical assumption. Multi-polarity and learned/document-specific segmentation should become competing evidence channels rather than hidden preprocessing choices.
3. **Static evidence is not time.** Nested composition is a physical graph edit, not proof that one state historically or temporally became another.
4. **Proposal units remain provisional.** Connected components and neighborhoods are intake proposals, not asserted semantic glyph boundaries.
5. **WL fingerprinting is practical, not complete.** Later versions should add explicit subgraph isomorphism/canonical labeling where scale permits.
6. **Custody independence is not historical independence.** Different source objects, repositories, or institutions do not by themselves establish independent invention or transmission.
7. **The first relation vocabulary is intentionally impoverished.** Later kernels should add observable crossing continuity, attachment side, ordering, boundary crossing, repeated-field interruption, pairing, adjacency, and carrier relations without importing semantic names.
8. **No semantics are discovered yet.** v6 discovers anonymous relational recurrence and predictive grammar. Meaning remains a separate hypothesis layer.

## Next scale

Once the relational kernel is stable, the real experiment should maximize heterogeneity rather than hand-select likely marks: manuscripts, seals, textiles, knots, maps, diagrams, game boards, architectural drawings, astronomical figures, accounting marks, pottery, heraldry, modern notation, interfaces, mundane marks, and other legally obtainable physical records.

The intake may know how to fetch those objects. The blind learner may not know which box any object came from until after freeze.
