# V48 execution checkpoint contract

V48 is explicitly designed to survive chat/tool timeouts without restarting scientific work.

## General rule

One governed computational boundary per turn/session.

A later checkpoint may consume only exact hashes from earlier frozen checkpoints.

No stage may silently recompute an earlier artifact under different code.

## CP1 — coordinate models

Inputs:
- frozen V46 structural feature rows;
- 171 coordinate-fit sources only;
- canonical V46 assignment mapping for alignment only.

Outputs:
- equivalent R3 model;
- R3 canonical alignment;
- R4 source-relative model;
- equivalence diagnostics;
- SHA-256 identities.

Stop and freeze.

## CP2 — development edge features

Compile only the 59 boundary-development sources into edge-level continuous predictors and persist/change targets using CP1.

Output sufficient feature rows only.

Stop and freeze.

## CP3 — development model selection

Run B0/B1/B2/C1/C2/C3 with source-grouped CV.
Preserve every C and every fold.

Output sufficient statistics + selected frozen model.

Stop and freeze.

## CP4 — validation edge features

Compile only the 53 boundary-validation sources.
No scoring.

Stop and freeze.

## CP5 — validation observed score

Score selected model and B2 on frozen validation features.
No nulls.

Stop and freeze.

## CP6.0–CP6.9 — validation null batches

Ten independent immutable batches:
- CP6.0 iterations 0–9
- CP6.1 iterations 10–19
- ...
- CP6.9 iterations 90–99

Each batch emits only:
- null gain bits/edge;
- source-positive fraction;
- any other preregistered metric required for adjudication.

A timeout after a completed batch never invalidates or reruns earlier batches.

## CP7 — validation adjudication

Combine CP5 + all ten CP6 batches.
Apply frozen validation gate.
No model repair.

Stop and freeze.

## CP8 — final-confirmation edge features

Only if CP7 supports validation.
Compile the 431 fresh final-confirmation sources.
No scoring.

Stop and freeze.

## CP9 — final-confirmation observed score

Score frozen selected model and B2.
Stop and freeze.

## CP10.0–CP10.9 — final-confirmation null batches

Same 10×10 architecture and fixed iteration identities.

## CP11 — final confirmation adjudication

Combine CP9 + CP10.0–10.9.
Apply the validation gate unchanged.
Freeze final structural result.

## CP12 — context rejoin

Only after CP11.

No semantic/context information may influence any earlier checkpoint.
