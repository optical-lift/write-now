# Canon-Model Research Lineage Bridge

**Status:** Selected research preservation rule  
**Date:** 2026-09-05  
**Purpose:** Ensure current Write Now research—especially Mark/glyph experiments, corpus packets, manuscript/historical recovery, and future book recovery—can later enter a controlled canon-model research program without sacrificing scientific provenance or contaminating present experiments.

The governing long-term architecture lives in:

`optical-lift/atlas` → `map/intelligence/CANON-CORPUS-TRAINING-ARCHITECTURE.md`

This bridge does not make Write Now a model-training repository. Write Now remains a research/recovery instrument. It defines what Write Now must preserve so later corpus admission is possible.

---

## 1. Governing rule

> **Research first. Training later.**

No current experiment, recovered source, transcription, glyph relation, or historical claim should be altered merely to make it easier to train a future model.

A future Training Candidate must point back to an independently recoverable research lineage.

---

## 2. Current Mark work is already part of the lineage

The existing structure under `research/mark/` is retained as scientific evidence infrastructure:

- `observable-corpus/`
- `harvest-feeds/`
- `harvest-manifests/`
- `feed-fixtures/`
- `discovery-experiments/`

Blind protocols, corpus snapshots, held-out lanes, anonymous representations, leakage controls, experiment outputs, and unblinding events are research artifacts first.

Do not flatten them into a future training dataset.

---

## 3. Every new experiment should preserve

Where applicable:

- stable experiment ID;
- frozen protocol + hash;
- hypothesis and competing explanation;
- exact permitted inputs;
- forbidden/leakage inputs;
- train/induction/control/holdout partition;
- immutable corpus/feed snapshot IDs/hashes;
- code commit;
- random seed(s);
- environment/runtime metadata sufficient for reproduction;
- exact run outputs;
- protocol deviations;
- adjudication;
- unblinding record;
- later reinterpretations as new records rather than edits to the original result.

A failed experiment remains preserved.

---

## 4. Every source-recovery thread should preserve

For manuscripts, books, archival documents, inscriptions, images, and other historical witnesses:

- stable source/witness identity;
- repository/catalog identifier;
- exact item/folio/page/region;
- surrogate/capture identity and content hash where possible;
- acquisition provenance;
- rights/license/access status;
- transcription state(s);
- normalization/editorial interventions;
- alternate readings;
- translation state(s);
- dating/provenance uncertainty;
- claims that depend on the source;
- adjudication history.

The recovered/reconstructed text is a projection over witnesses, not a substitute for them.

---

## 5. Preserve correction histories

Future model research needs more than polished conclusions.

When a reading, relationship, function, or experiment interpretation changes, preserve:

```text
original evidence
→ original candidate
→ reason for pressure/correction
→ revised candidate
→ adjudication
→ unresolved remainder
```

Rejected interpretations and tempting false matches are potentially high-value negative training/evaluation material later.

---

## 6. Training and evaluation candidacy

Write Now may label an artifact as:

- `training_candidate`
- `evaluation_candidate`
- `research_only`
- `restricted`
- `unresolved`

These labels do **not** themselves admit anything into a training corpus.

Actual admission belongs to the future corpus-governance path defined in Atlas intelligence architecture.

Never use a sealed evaluation candidate as training material for the model it is intended to evaluate.

---

## 7. Glyph-specific rule

Mark evidence should continue to preserve the physical chain:

```text
source object
→ surface
→ capture
→ region
→ mark instance
→ components
→ relations / junction graph
→ anonymous sequence / derived representation
→ experiment
→ adjudication
```

Interpretive meaning must remain downstream of observable structure.

This is especially important if future model comparisons use glyph data as independent transfer or prediction tests.

---

## 8. Book-recovery rule

Write Now book recovery should increasingly preserve a source-critical chain compatible with:

```text
Work
→ Expression
→ Manifestation
→ Item
→ Surrogate
→ exact region
→ transcription
→ normalized reading
→ interpretation
→ adjudication
```

A clean reconstructed chapter or book may be useful to readers and future models, but the scientific asset is the recoverable lineage beneath it.

---

## 9. What not to do

- Do not overwrite failed hypotheses with corrected ones.
- Do not discard contradictory witnesses because one reading won.
- Do not let model-generated transcription silently replace the source image.
- Do not let OCR confidence stand in for scholarly adjudication.
- Do not move held-out evidence into development because a test is inconvenient.
- Do not retroactively change scoring after opening results without recording a new protocol/version.
- Do not call an interpretive claim an observation.
- Do not call future training usefulness scientific confirmation.

---

## 10. Near-term implementation expectation

No model-training code is required now.

The immediate requirement is preservation discipline:

1. keep protocols and feeds immutable/versioned;
2. assign stable IDs to experiments and major source/recovery objects;
3. hash snapshots/artifacts where practical;
4. preserve corrections and adjudications append-only;
5. distinguish research evidence, hypotheses, findings, and future training/evaluation candidacy;
6. keep blind/held-out material sealed from development context;
7. ensure future researchers can reconstruct what was known **before** each result was opened.

If these are maintained, today's glyph and recovery research can later become scientifically useful model-training or evaluation material without rewriting its history.
