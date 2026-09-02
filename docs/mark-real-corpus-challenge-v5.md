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
8. measure train structure against feature-shuffled null worlds;
9. score the unseen institution with abstention enabled;
10. score the unrelated control against the same frozen world;
11. compare accepted whole-object holdouts with an ordinary 64-bit image-similarity baseline;
12. preserve the exact sealed training observation identities, dimensions, source groups, and grayscale histograms while independently permuting pixels inside every observation, then remeasure and rebuild a spatial-null world;
13. compare the real world with that exact-observation spatial-null world;
14. only after all blind artifacts are sealed, reopen provenance and rank candidate families for inspection;
15. issue one final PASS/FAIL verdict against the predeclared hostile challenge thresholds.

A failed criterion does not stop the earlier measurements from being written. The verdict is intentionally last so a negative experiment still leaves a complete diagnostic record rather than hiding later controls.

## Adversarial controls

### Feature-shuffled null worlds

The v4 null remains active. Structural features are independently permuted across fixed observation/source identities. This preserves marginal feature distributions and source-group sizes while destroying real joint configurations.

### Unrelated institution

The control institution never teaches the model. Its whole-object acceptance rate measures whether the learned family envelopes simply accept almost anything.

A high control acceptance rate is evidence against the usefulness of the learned world, not a cross-cultural discovery.

### Ordinary visual baseline

A 64-bit difference hash is computed for whole captures. An accepted holdout is flagged when an ordinary whole-image nearest neighbor can plausibly explain the match. A candidate is more interesting only when structural acceptance survives while the whole-image baseline says the objects are visually non-trivial.

This is deliberately a cheap baseline. It does not establish mechanism; it prevents obvious visual resemblance from being promoted as structural surprise.

### Exact-observation spatial null

The spatial control operates on the already sealed training observations rather than creating a new set of image fragments. For every train observation it preserves:

- the observation ID;
- the source-group identity;
- the region width and height;
- the number of observations in the experiment; and
- the exact grayscale intensity histogram inside that observation.

It then applies an independent deterministic Fisher-Yates permutation to the pixels within that observation before running the same structural measurement code again. Pixel inventory is therefore unchanged while spatial topology is destroyed.

The spatial-null measurements are learned into a world with the same Mark world builder and receive their own shuffled-null evaluation. Because observation identities and counts are fixed, the real/null comparison is not rewarded merely for generating extra pieces.

#### Rejected first implementation

The first v5 CI attempt used deterministic 4×4 tile permutation at the whole-image level and then allowed Mark to propose new observations. That control was rejected.

It generated artificial tile seams and increased the number of proposed structures. In the fixture, the spatially tiled world became *more* recurrent than the real world: real/scramble cross-source tightness was `0.787345` and real/scramble recurrence was `0.136364`. Those values do not show that spatial order was irrelevant; they show that the negative control manufactured its own repeated geometry.

The tile control therefore cannot be used as evidentiary support and is not part of the v5 verdict. Its failure is retained here as method custody because deleting an unfavorable control result would make the experimental record worse, not cleaner.

## Post-freeze provenance report

After every blind comparison is sealed, the report rejoins source custody and ranks learned families by evidence useful for human inspection:

- number of independent training source objects;
- number of training institutions;
- whole-object recurrence in the unseen institution;
- holdout recurrence not trivially explained by whole-image similarity;
- false recurrence in the unrelated control institution; and
- global shuffled-null and exact-observation spatial-null statistics.

The report may expose catalog terms after freeze so humans can inspect what Mark connected. Those terms never become features in the frozen world.

Candidate scores are triage. They are not p-values and they are not historical conclusions.

## Final hostile verdict

The workflow writes a final verdict only after the provenance report exists. By default every condition below is required:

- cross-source tightness must beat feature-shuffled nulls at empirical `p <= 0.05`;
- recurrence score must beat feature-shuffled nulls at empirical `p <= 0.05`;
- at least one whole object from the unseen institution must be accepted;
- at least one whole object from the unseen institution must be rejected, proving abstention remains active;
- unrelated-control whole-object acceptance must be `<= 0.25`;
- unseen-institution whole-object acceptance must exceed control acceptance by at least `0.10`;
- at least one accepted holdout whole object must remain visually non-trivial under the cheap dHash baseline;
- real cross-source tightness must be at least `1.05×` the exact-observation spatial-null value;
- real recurrence must be at least `1.05×` the exact-observation spatial-null value; and
- at least one family must span two or more training institutions, recur as a visually non-trivial whole-object match in the unseen institution, and accept zero whole objects from the unrelated control institution.

These are challenge gates, not historical significance thresholds. A PASS establishes that a structural relation survived this particular hostile benchmark. A FAIL is a valid experimental outcome and must not be described as evidence for the historical hypothesis.

## What can count as a v5 success

Passing the final verdict would establish that at least one blind structural relation survived independent training institutions, an unseen institution, abstention, an unrelated control institution, a cheap visual baseline, feature-shuffled nulls, and an exact-observation spatial-topology null.

It would still not establish common authorship, cultural transmission, linguistic identity, historical mechanism, or meaning. Those are later hypotheses that must earn separate evidence.

## Scaling boundary

The current `buildWorldModel` uses exact pairwise distances among training observations. v5 bounds noisy per-source proposals and bounds holdout operation prediction, making the first live pilot tractable. It does **not** yet make exact world construction suitable for arbitrarily large firehose corpora.

The next scale transition is an indexed-neighbor world builder that reproduces exact-pilot results within measured error, followed by institution-level replication on a much larger corpus. Until that replacement is validated, increasing feed sizes should be treated as a performance experiment rather than silently changing the inference regime.
