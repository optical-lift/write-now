# Mark Structural Regime Atlas v46 — preregistration

**Experiment ID:** `mark:structural-regime-atlas:v46`  
**Parent evidence:** Mark V45 Phase-A freeze `3ab58910b60b90c7bb682788e742503feeb5f329`  
**Parent post-freeze rejoin:** `b953916415655e76b74ba91144c74d4ace2b087f`  
**Status:** preregistered before structural-regime scoring

## 1. Governing purpose

V46 is not a test whose purpose is to finish the original Song/glyph hypothesis.

Its purpose is to learn **where the next bridge segment should be built**.

V45 established that anonymous physical operators compose, that a supported subset is idempotent under repetition, and that a supported subset cancels operationally. Post-freeze inspection then showed that CR-001 appears in semantically heterogeneous material including printed lettering, binding wear, stains, decoration, illustration/border linework, and surface texture.

V46 therefore asks a broader question:

> What kinds of larger structural organization emerge from the physical operator system, where do those organizations recur, how do they change across scales and regimes, and which observed difference is strong enough to justify the next experiment?

No existing hypothesis receives privileged status.

## 2. What V46 is not

V46 is not:

- a symbol-vs-nonsymbol classifier;
- a glyph decipherment experiment;
- a Song semantics experiment;
- an attempt to prove CR-001 is language;
- an attempt to make V45 look more specific than it is;
- a search for named historical meanings;
- a permission to alter V45.

A result that CR-001 is universal physical graph machinery is useful.
A result that the meaningful distinction appears only at longer sequences is useful.
A result that cross-scale transitions matter more than individual operators is useful.
A result that the present observables are insufficient is useful.

## 3. Frozen source world

Use only the already-custodied Source Rule Atlas physical world:

- GitHub Actions run `33755743472`;
- sealed-evidence artifact id `9893738364`;
- sealed-evidence digest `sha256:5aee2d958875d711a148e08c37c613457eeb734efc8e2c773fa63782faad1a20`;
- full compiler-blind input SHA-256 `4b64315a037b6ff6dfca3d99bade96e4c9c453f589e4beb0aa3dd5e0c2b92786`;
- 714 source objects;
- 23,161 machine-proposed observations.

No new source acquisition is permitted in V46.

## 4. V45/V5 exclusion

All 435 observations selected by the frozen V5 edge-pair manifest are excluded from V46 scoring.

- V5 edge-pair manifest SHA-256: `75e28e9e45bcc2245015b1d6a23000f9589b5b9f4a0104dad4e792d1cd445a36`;
- excluded observation count: 435;
- canonical sorted excluded-observation-id list SHA-256: `1735dbadeb93241237af7af3efbe22a7b4a942a80cf94db301e43caaef827076`.

The untouched V46 pool contains **22,726 observations across all 714 source objects**.

Canonical sorted untouched-observation-id list SHA-256:

`8d8a37a7fa80d42e1bff753b30539497a3bdbda1ce694e410b22328c23ce7b13`.

## 5. Source-separated lanes

Source assignment is deterministic and frozen before outcome inspection.

For each opaque `sourceGroupId`:

`bucket = first_32_bits(SHA256("mark-v46-structural-regime-atlas|" + sourceGroupId)) mod 100`

- 0–59: discovery
- 60–79: validation
- 80–99: confirmation

Frozen inventory:

- **discovery:** 431 sources / 13,482 observations
- **validation:** 137 sources / 4,372 observations
- **confirmation:** 146 sources / 4,872 observations

No source object appears in more than one lane.

Discovery may be used adaptively. Validation may be opened only after a regime representation is frozen. Confirmation may be opened only after all selection/tuning is closed.

## 6. Blindness through confirmation

Before confirmation closes, the regime mapper may use:

- opaque source and observation IDs;
- physical observation geometry;
- graph topology;
- proposal scale/kind if already present in the blind packet;
- V45 anonymous operator identities and frozen consequence functions;
- source-local grouping needed for cross-scale analysis.

It may not use:

- institution;
- title;
- language;
- culture;
- chronology;
- geography;
- OCR/transcription;
- named glyph identity;
- semantic class such as writing/ornament/wear;
- Song ontology labels.

Those may be reopened only after the structural atlas is frozen.

## 7. Target observable families

Implementation must audit which of these can be computed from existing frozen pixels/graphs without new acquisition. Unavailable families remain explicit residuals.

### A. graph morphology
- observation area/aspect;
- center count;
- edge count;
- connected-component count if recoverable;
- center-kind frequencies;
- degree/arity distribution;
- self-loop/parallel-edge incidence;
- path-count density.

### B. anonymous operator ecology
- eligible-operator path coverage;
- distinct operator count;
- operator type/token ratio;
- operator frequency entropy;
- concentration / reuse;
- reverse-pair incidence where measurable.

### C. V45 law ecology
Using the frozen V45 model without refit:
- CR-001 composition gain over input-only;
- gain over A-only;
- gain over B-only;
- direct-pair residual advantage;
- eligible CR-002 repetition/idempotence incidence;
- eligible CR-003 cancellation incidence.

### D. higher-order operator programs
Discovery may measure anonymous operator sequences beyond two steps, including:
- sequence support at lengths 2–4 initially;
- repeated n-gram reuse;
- next-operator conditional entropy;
- sequence surprise / predictability;
- whether independently learned operator kernels remain informative when composed across more than two steps.

If longer sequence lengths are added during discovery, every attempted length and reason must be preserved. The chosen program representation must freeze before validation.

### E. cross-scale persistence and transition
Where observations from the same source overlap or nest across proposal scales:
- operator-vocabulary persistence;
- regime persistence/change;
- motif survival;
- emergence/disappearance of higher-order programs.

This is a structural hierarchy probe, not an assumption that one scale corresponds to character/word/line.

## 8. Regime discovery

V46 does not preregister one "correct" number of clusters.

The discovery lane is allowed to compare deterministic multi-resolution unsupervised representations. At minimum, implementation must preserve:

- the exact feature set for every attempted representation;
- normalization/transformation;
- distance/similarity definition;
- all parameter values;
- seeds where relevant;
- regime count and unassigned/noise rate;
- stability under resampling or source holdback;
- memory/runtime profile.

A representation may be selected for validation only by a frozen selection rule based on structural stability, source recurrence, residual compactness, and out-of-sample assignability—not by how exciting its post-hoc visual interpretation looks.

No provenance interpretation is allowed during selection.

## 9. Validation and confirmation

After discovery selects a regime representation:

1. freeze the feature compiler and regime definition;
2. assign validation sources without refit except as explicitly preregistered;
3. inspect failure/residual structure;
4. freeze any permitted technical repair before confirmation;
5. assign confirmation sources;
6. report all regime stability and higher-order results.

Confirmation is not a single pass/fail hypothesis test. It answers whether the discovered structural distinctions recur in genuinely unseen sources.

## 10. Required outputs

V46 must emit:

1. **regime atlas** — anonymous regime IDs with quantitative signatures;
2. **operator ecology table** — vocabulary/reuse/composition profile per regime;
3. **higher-order program table** — recurring sequences and predictability by regime;
4. **cross-scale transition map** — where measurable;
5. **residual ledger** — systematic structure not explained by the chosen atlas;
6. **confirmation report** — what reproduced on unseen sources;
7. **post-confirmation context rejoin** — only after structural freeze;
8. **next-bridge decision record** — evidence-ranked directions, not one forced conclusion.

## 11. Next-bridge branches

V46 is explicitly designed to branch.

### Branch A — universal substrate
If CR-001 and related operator ecology are substantially invariant across regimes, treat them as lower-level graph substrate and move the experiment **up one structural scale**.

### Branch B — regime-specific operator vocabulary
If regimes differ strongly in which operators are reused, test how restricted operator vocabularies create larger organization.

### Branch C — higher-order separation
If one- and two-step physics are generic but longer operator programs differ, focus the next experiment on **composition of compositions** rather than individual marks.

### Branch D — cross-scale organization
If stable regime transitions occur across nested/overlapping scales, test a hierarchical grammar of regime transitions.

### Branch E — unexplained residual
If the atlas is unstable or differences disappear after complexity control, identify what physical observable the present representation is discarding and build the next extractor around that residual.

More than one branch may be supported. V46 must preserve competing explanations.

## 12. Interpretation after structural freeze

Only after confirmation and atlas freeze may provenance/source pixels be rejoined to ask:

- what kinds of material populate each regime;
- whether writing, ornament, wear, illustration, or other categories concentrate anywhere;
- whether those categories were actually the important axis or merely one interpretation;
- which discovered structural layer is the best target for a new semantic experiment.

Interpretation cannot change regime definitions or confirmation scores.

## 13. Relationship to Song

Song is not the destination V46 must prove.

If a discovered structure later aligns naturally with Song, that becomes a new test.
If it pressures Song to change, that becomes a versioned Song research question.
If it sits below Song as generic physical machinery, it remains useful Mark infrastructure.

The governing direction is:

`evidence -> discovered structure -> next question`

not:

`current ontology -> force evidence into expected categories`.
