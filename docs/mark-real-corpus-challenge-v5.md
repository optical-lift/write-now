# Mark Real-Corpus Challenge v5

Mark v5 is the first challenge designed for heterogeneous physical evidence rather than a synthetic claim-validation fixture. Its purpose is not to prove a historical theory. Its purpose is to determine whether a blind structural world learned from one set of institutions produces replicable, non-trivial structure in material it has never seen while rejecting unrelated controls.

## Governing rule

The real-corpus challenge is assembled before blind harvesting into three institution-separated lanes:

- **train** — source objects from institutions permitted to teach the blind world;
- **holdout** — an entire institution unavailable during world learning;
- **control** — an unrelated institution that never contributes to learning and exists to measure false acceptance.

No institution may occur in more than one lane. Individual objects are machine-enumerated from broad collection feeds rather than selected because they contain a desired mark, medium, culture, date, or interpretation.

The lane is a technical experimental boundary, not contextual evidence. Culture, chronology, geography, catalog identity, conventional reading, object category, and scholarly interpretation remain unavailable to the learner.

## Pilot feeds

The first live pilot is intentionally small enough for the current exact pairwise world builder while exercising the real intake path:

- Art Institute of Chicago — train;
- Cleveland Museum of Art — train;
- Metropolitan Museum of Art — whole-institution holdout;
- Library of Congress photographic collection — unrelated control.

Each feed currently requests up to 24 machine-spread source objects. This approximately 96-object pilot is a systems and inference challenge, not the final corpus scale. Increasing into the thousands requires replacing the current exact pairwise neighbor construction with an indexed or batched neighbor search; v5 does not pretend that ceiling is already removed.

## Intake custody and duplicate defense

Physical captures retain exact SHA-256 custody in the contextual rejoin lane. Before a source can count as independent evidence, intake rejects:

1. exact duplicate bytes; and
2. near-duplicate whole captures using a 64-bit difference hash with a configurable Hamming threshold.

Exclusions are retained in custody with the matching blind source identity and reason. They are not silently discarded and they cannot inflate structural recurrence.

No source pixels are uploaded as v5 workflow artifacts. Blind artifacts contain derived measurements, hashes, opaque source identities, and sealed challenge outputs; custody artifacts contain provenance needed for later inspection.

## Blind proposal budget

Real photographs can contain thousands of thresholded components. Letting every tiny component become an observation would allow visual clutter to dominate the world by count alone.

For every source Mark therefore receives:

- the whole capture;
- up to a configurable maximum of eligible connected components (default 64), chosen only by dark-pixel area;
- adjacent-component neighborhoods; and
- three-component fields.

The component budget is blind and identical across lanes. It uses no object class or semantic information. After salience selection, retained components are restored to spatial order before neighborhood proposals are generated.

## Challenge sequence

The v5 workflow proceeds in this order:

1. machine-enumerate collection feeds;
2. compose train, whole-institution holdout, and unrelated control lanes;
3. harvest exact physical captures and exclude duplicate witnesses;
4. remove provenance from the learner;
5. let Mark propose multiscale observables;
6. measure train, holdout, and control with the same feature engine;
7. freeze a world from train only;
8. compare train structure with feature-shuffled null worlds;
9. score the unseen institution with abstention enabled;
10. score the unrelated control against the same frozen world;
11. compare accepted whole-object holdouts with an ordinary 64-bit image-similarity baseline;
12. spatially scramble training captures, rerun proposal and measurement, and compare the resulting structural world with the real one;
13. only after those blind artifacts are sealed, reopen provenance and rank candidate families for inspection.

## Adversarial controls

### Feature-shuffled null worlds

The v4 null remains active. Structural features are independently permuted across fixed observation/source identities. This preserves marginal feature distributions and source-group sizes while destroying real joint configurations.

### Unrelated institution

The control institution never teaches the model. Its whole-object acceptance rate measures whether the learned family envelopes simply accept almost anything.

A high control acceptance rate is evidence against the usefulness of the learned world, not a cross-cultural discovery.

### Ordinary visual baseline

A 64-bit difference hash is computed for whole captures. An accepted holdout is flagged when an ordinary whole-image nearest neighbor can plausibly explain the match. A candidate is more interesting only when structural acceptance survives while the whole-image baseline says the objects are visually non-trivial.

This is deliberately a cheap baseline. It does not establish mechanism; it prevents obvious visual resemblance from being promoted as structural surprise.

### Spatial destruction

Training captures are converted to grayscale and deterministically divided into a tile grid. Tiles are permuted before Mark is allowed to propose observables again. The retained grid crop contains the same grayscale pixel inventory but its spatial arrangement is destroyed.

The scrambled corpus is measured and modeled with the same Mark code and receives its own shuffled-null evaluation. The real world should show stronger recurrence/tightness than the spatially destroyed world if layout actually carries the signal.

## Post-freeze provenance report

After every blind comparison is sealed, the report rejoins source custody and ranks learned families by evidence useful for human inspection:

- number of independent training source objects;
- number of training institutions;
- whole-object recurrence in the unseen institution;
- holdout recurrence not trivially explained by whole-image similarity;
- false recurrence in the unrelated control institution; and
- global shuffled-null and spatial-control statistics.

The report may expose catalog terms after freeze so humans can inspect what Mark connected. Those terms never become features in the frozen world.

Candidate scores are triage. They are not p-values and they are not historical conclusions.

## What can count as a v5 success

A physically interesting result requires, at minimum:

- a training world stronger than shuffled null worlds;
- recurrence in an institution unavailable during training;
- active abstention rather than universal acceptance;
- materially lower acceptance in the unrelated control lane;
- at least one accepted holdout relation that is not merely the nearest whole-image lookalike; and
- real spatial structure stronger than the spatially scrambled negative control.

Passing those conditions would establish that a blind structural relation survived hostile controls. It would still not establish common authorship, cultural transmission, linguistic identity, historical mechanism, or meaning. Those are later hypotheses that must earn separate evidence.

## Scaling boundary

The current `buildWorldModel` uses exact pairwise distances among training observations. v5 bounds noisy per-source proposals and bounds holdout operation prediction, making the first live pilot tractable. It does **not** yet make exact world construction suitable for arbitrarily large firehose corpora.

The next scale transition is an indexed-neighbor world builder that reproduces exact-pilot results within measured error, followed by institution-level replication on a much larger corpus. Until that replacement is validated, increasing feed sizes should be treated as a performance experiment rather than silently changing the inference regime.
