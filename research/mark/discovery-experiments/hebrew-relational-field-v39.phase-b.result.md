# V39 Phase B Result — External Masoretic Witness Diagnostic

**Experiment:** `mark:hebrew-relational-field:v39`  
**Witness-opening boundary:** `7ac24f95f62d556de210359b32350affdc0bb07d`  
**Phase-A verdict before witness opening:** negative

## Governing interpretation

V39 Phase B is diagnostic only. Because H2–H4 failed to improve held-out Hebrew prediction in Phase A, a witness-only improvement cannot be interpreted as recovery of an independently stable Hebrew latent field.

## Full heldout witness set

Witness-eligible heldout tokens: **46,330**.

Cross-entropy (nats/token):

- W0 witness frequency: **2.5015081232**
- W1 intrinsic Hebrew state: **2.4784025942**
- W2L coarse left relation: **2.5043248613**
- W2R coarse right relation: **2.4888492868**
- W3 bidirectional coarse relation: **2.4715716332**
- W4 exact identity-blind pair topology: **2.4547043377**
- W5 relation-delta: **2.4715716332**
- W6 exact consonantal skeleton: **2.3439179862**

Context coverage at frozen support >=50:

- W2L: **80.3855%**
- W2R: **80.0763%**
- W3: **23.0560%**
- W4 left: **61.1467%**
- W4 right: **60.3011%**

W5 is numerically identical to W3 because the preregistered `Rcoarse` state already contains the left/right length-delta bins. The additional W5 delta terms therefore add no information. This preregistration redundancy was preserved rather than silently changed.

## Full-set observation

W3 and especially W4 improve witness prediction relative to W1 on the full heldout set. W2L and W2R do not.

However, Phase A already showed that these relational contexts do not improve independent Hebrew prediction. Therefore this full-set witness improvement is not evidence that V39 recovered the deeper target system.

## Critical unseen-skeleton subset

Heldout witness tokens whose exact consonantal skeleton has **zero V39 training occurrences**: **4,928**.

Cross-entropy:

- W0 frequency: **2.4810821754**
- W1 intrinsic state: **2.5022593736**
- W3 bidirectional relation: **2.5256040618**
- W4 exact identity-blind pair topology: **2.5201302808**

All Hebrew structural lanes are worse than raw witness frequency on this anti-lookup subset.

## V39 verdict

V39 matches preregistered interpretation case C:

> Witness relational lanes can improve full-set Masoretic prediction even though the corresponding Hebrew-only relational lanes fail to improve the independently held-out Hebrew objective.

The unseen-skeleton failure strengthens the caution. The full-set witness gain is best treated as **context-conditioned witness/lexical structure**, not as evidence that V39 recovered an authentic underlying mark system.

Exact consonantal skeleton W6 remains much stronger on the full set (2.3439 nats), again showing that word identity carries substantial information about the surviving Masoretic witness.

## What V39 falsifies

V39 provides evidence against this specific recovery route:

- immediate neighboring-word overlap
- cross-word equality topology
- local categorical relation deltas

These features fragment the Hebrew state space and overfit rather than yielding a stronger generalizable Hebrew structural field.

## What V39 does not falsify

It does not falsify:

- an underlying authentic mark system encoded by or recoverable from Hebrew
- a lower-dimensional global structural organization
- longer-range recurrence or trajectory structure
- a system represented in relative position, recurrence, cadence, boundary, or global sequence behavior rather than local word-pair topology

## Next methodological implication

V40 should not add more local categorical context. It should recover a low-dimensional global field from Hebrew-only sequence behavior, preferably by learning recurrent context/trajectory classes with the current token identity excluded from the primary representation, freezing those classes, validating them on Hebrew holdout, and only then reopening the Masoretic witness.
