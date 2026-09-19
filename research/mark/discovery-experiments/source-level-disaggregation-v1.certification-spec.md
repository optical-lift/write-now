# Source-Level Disaggregation and Independence Certification v1

Status: **custody classification frozen after replay, before overlap-graph use**
Date: **2026-09-18**

## Purpose

Classify what kind of source independence the recovered V36, V38, and V40 local evidence actually provides.

This specification does not change any scientific outcome or replay threshold. It governs only how later reconstruction is allowed to count the already-frozen source-local results.

## Principle

> Non-overlapping evaluation is not the same thing as independent discovery.

A source occurrence can be real and locally supported while still inheriting a model, representation, or law candidate learned from other sources.

The future whole-system reconstruction must preserve those distinctions.

## Certification axes

Each source-local entry records:

1. **evaluation overlap**
   - whether the scored observations overlap another entry's raw evaluation observations;

2. **training isolation**
   - whether the exact source unit was excluded from model fitting;
   - whether other material from the same higher-level source was still present in training;

3. **model independence**
   - whether the source had its own independently fit local model;

4. **law-discovery independence**
   - whether the law candidate emerged inside that source without importing another source's law label or model;

5. **permitted reconstruction use**
   - what the entry may count as later.

## Certification classes

### INDEPENDENT_LOCAL_DISCOVERY

Requirements:

- source container frozen before discovery;
- no evidence from another source teaches the source which law to find;
- local model/constraint recovered from that source alone or from a preregistered within-source split;
- law signature frozen before cross-source matching;
- raw evidence does not overlap another catalogue counted as independent.

This is the required class for an **independent recurrence count**.

No historical V36/V38/V40 entry qualifies.

### WHOLE_SOURCE_HELDOUT_TRANSFER

Requirements:

- complete higher-level source (for example a whole book) excluded from training/model fitting;
- source receives the already-frozen model/law test afterward;
- meaningful local support under frozen endpoint.

Permitted use:

- strong out-of-source transfer evidence;
- may test whether a law generalizes to an untouched source;
- may **not** count as independent discovery of the law.

V36 Deuteronomy and Judges qualify.

### NONOVERLAPPING_UNIT_SHARED_TRAINING

Requirements:

- exact evaluation unit is held out and raw evaluation observations do not overlap other units in the same experiment;
- the model is trained globally outside that unit;
- material from the same higher-level source may occur in training.

Permitted use:

- source-local transfer/replication;
- law co-occurrence within raw regions;
- heterogeneity analysis;
- may **not** count as independent discovery.

V38 and V40 five-chapter blocks qualify.

### UNRESOLVED_SOURCE_UNIT

Use when the source-local replay does not meet its pre-frozen support criterion or is too sparse.

It is not a negative law edge unless the separate Absence-State Model licenses one.

## Recurrence counting rule

A future graph must keep at least three counts separate:

- `independent_discovery_count`
- `whole_source_transfer_count`
- `shared_training_local_support_count`

They must never be summed into one generic "number of sources."

## Same-source co-occurrence rule

If two separately frozen law tests support different laws in the **same exact raw source unit**, that may be recorded as law co-occurrence.

It does not create independent recurrence.

It is evidence that the source region can jointly expose both relational laws.

## Historical result classes

### V36 / EQC-001

Unit: whole heldout book.

- Deuteronomy: `WHOLE_SOURCE_HELDOUT_TRANSFER`
- Judges: `WHOLE_SOURCE_HELDOUT_TRANSFER`
- Psalms: unresolved for n=7
- Job: unresolved for n=1

### V38 / EQC-002

Unit: frozen five-chapter block.

- supporting block: `NONOVERLAPPING_UNIT_SHARED_TRAINING`
- failing block: `UNRESOLVED_SOURCE_UNIT`

The same book may contribute other blocks to training.

### V40 / EQC-001

Unit: frozen five-chapter block.

- supporting block: `NONOVERLAPPING_UNIT_SHARED_TRAINING`
- failing block: `UNRESOLVED_SOURCE_UNIT`

The same book may contribute other blocks to training.

## Readiness consequence

The historical corpus now supplies strong transfer and local recurrence evidence, but it still supplies:

`independent_discovery_count = 0`

for both strict equivalence clusters.

Therefore the primary cross-source whole-system graph remains gated.

The next scientific experiment must produce genuinely independent local discovery catalogues rather than extracting more pseudo-independent counts from the same historical corpus.
