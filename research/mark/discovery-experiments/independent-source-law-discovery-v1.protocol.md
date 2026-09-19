# Independent Source Law Discovery v1 — Frozen Protocol

Status: **FROZEN BEFORE LOCAL RULE OUTCOMES**
Date: **2026-09-18**
Parent checkpoint: `f366c4c9628020a6d638595a84727ea0bc1acc1c`

## Question

Can isolated physical Mark source objects independently expose relational constraints using only their own observed structure and their own structure-preserving null worlds, without receiving another source's rule vocabulary, state inventory, operator labels, canon labels, or the already-known EQC-001/EQC-002 identities?

## Source selection

The source set is frozen separately in `independent-source-law-discovery-v1.source-selection.json`.

Selection uses only blind custody/support metadata:

1. retain the original sealed 714-source universe;
2. within each original blind lane (`train`, `holdout`, `control`), rank source objects by frozen observation count descending;
3. break ties by anonymous `sourceGroupId` ascending;
4. select the top three per lane.

The original lane is used only to force diversity across the sealed acquisition design. It is **not** used as a training/validation role in this experiment.

Nine source objects are selected before any local rule incidence is opened.

## Discovery isolation

Each selected source is processed **alone**.

For source S:

- input contains only S and its frozen observations/capture;
- every observation is relabeled to local lane `train` mechanically;
- no other source participates in model fitting, rule generation, null generation, ranking, or admission;
- no global source-rule atlas row is used;
- no prior Mark rule list is used;
- provenance remains sealed;
- canon remains sealed;
- EQC/MCR identities remain sealed.

The output catalogue receives source-local IDs only:

`ISLD-Sxx-L001, L002, ...`

## Why there is no internal train/holdout split

The frozen observation proposals within a source overlap heavily in image space. Crop-level splitting would leak pixels across partitions. Fixed spatial grids discard too much support.

The experiment therefore does **not** manufacture pseudo-independent internal partitions.

Each whole source is one discovery world.

Cross-source comparison occurs only after all nine catalogues are frozen.

## Physical measurement contract

Reuse the frozen Mark sparse physical extractor/compiler mechanics:

- same capture;
- same frozen observation rectangles and segmentation custody;
- same threshold resolution;
- same tiling/skeletonization;
- same critical-center extraction;
- same arm tracing;
- unresolved arms excluded from grammar multiplicity;
- same anonymous grammar primitive:
  `CENTER:<kind>|ARM:<context_arm> -> <outcome_arm>`.

These primitive names are measurement coordinates, not universal law names.

## Source-local null world

For every observation independently:

1. preserve center kind;
2. preserve center degree;
3. preserve the complete arm inventory inside each `(center kind, degree)` bucket;
4. shuffle the pooled arms across centers in that same observation/bucket;
5. recompute grammar counts.

Thus the null asks:

> If this source contained the same local physical ingredients but not the observed assignment of arms to centers, how much of the relational rule would remain?

No other source enters the null.

## Null iterations

Run **64 deterministic null iterations** per observation.

The null seed remains the compiler's frozen seed form:

`sourceGroupId | observationId | iteration | centerKind | degree`.

The 64 worlds are a calibration distribution, not a formal family-wise significance claim.

## Candidate universe

For each observed context, consider the union of outcome arms appearing either:

- in the observed source; or
- in any of its 64 source-local null worlds.

This is required so local discovery can recover both:

- **enrichment** — an outcome occurs more often than source-local rearrangement permits;
- **exclusion** — an outcome occurs less often than source-local rearrangement predicts, including zero observed instances when the null supplies real opportunity.

Do not restrict candidates to globally known rules or to the observed top outcome.

## Per-candidate statistics

For every `context -> outcome` pair report:

- observed context count;
- observed outcome count;
- observed accuracy = outcome/context;
- 64 null context counts;
- 64 null outcome counts;
- 64 null accuracies;
- null mean accuracy;
- null minimum/maximum accuracy;
- signed lift = observed accuracy - null mean accuracy;
- null exceedances above/equal observed;
- null under-runs below/equal observed;
- observed outcome mass;
- mean null outcome mass.

## Admission gates

A pair is eligible for the **local law catalogue** only when:

- observed context count >= **30**; and
- comparison mass >= **10**, where comparison mass is:
  - observed outcome count for enrichment;
  - mean null outcome count for exclusion.

### Enrichment admission

Admit as `RELATIONAL_ENRICHMENT` when:

- signed lift > 0; and
- observed accuracy is greater than **every one of the 64 null accuracies**.

### Exclusion admission

Admit as `RELATIONAL_EXCLUSION` when:

- signed lift < 0; and
- observed accuracy is lower than **every one of the 64 null accuracies**.

Pairs that do not pass remain frozen diagnostics, not laws.

No threshold may be changed after any source outcome is opened.

## Ranking inside each source

Rank admitted local constraints by:

1. absolute signed lift descending;
2. observed context count descending;
3. comparison mass descending;
4. context string ascending;
5. outcome string ascending.

The rank is local only and carries no cross-source identity.

## Catalogue representation

Every admitted local constraint preserves two layers:

### Surface measurement

- center kind;
- context arm;
- outcome arm;
- enrichment/exclusion direction;
- observed/null statistics.

### Relational statement

Use only source-local language:

- enrichment: `under local condition C, outcome O is constrained toward occurrence relative to source-local rearrangement`;
- exclusion: `under local condition C, outcome O cannot be treated as freely occurring at the source-local rearrangement rate`.

Do not assign a global law name.

## Catalogue freeze

All nine local catalogues must be hashed and committed before:

- comparing one selected source to another;
- opening source provenance;
- checking prior source-rule atlas incidence;
- opening EQC-001/EQC-002 labels;
- using canon;
- clustering local rules across sources.

## Independence status

A catalogue produced under this protocol may receive:

`INDEPENDENT_LOCAL_DISCOVERY`

because its candidate constraints and null comparison are recovered from that source alone before cross-source matching.

This does not mean the physical extraction algorithm differs by source. The shared extractor is an instrument, not a learned cross-source law model.

## Failure behavior

A source with zero admitted constraints receives an empty frozen catalogue.

That is an experimental result.

Do not lower thresholds, add more sources, or import rules from another source to make a catalogue non-empty.

## Next opening

Only after all nine catalogue hashes are frozen:

1. translate each local catalogue into the frozen relational-law observation language;
2. apply the frozen Law-Equivalence Adjudication language across independently discovered local constraints;
3. only then ask whether any map to existing EQC-001/EQC-002 or define new law families.
