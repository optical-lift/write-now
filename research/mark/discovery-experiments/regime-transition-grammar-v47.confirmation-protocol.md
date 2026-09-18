# Mark V47 pairwise confirmation protocol

**Experiment:** `mark:regime-transition-grammar:v47`  
**Status:** FROZEN BEFORE CONFIRMATION TRANSITION LABEL JOIN  
**Date:** 2026-09-18

## Frozen upstream result

- discovery freeze: `a8a00b372e80976365058bb567193fef4bddf9e6`
- validation freeze: `d61b7fef5a5d378f67878433fe4b9e7cacb4c1f4`
- raw pairwise discovery SHA-256: `e0623f374b3d065288ded3c9c4a1ff636835632b8675ba081045bedfabe564ff`

Exactly the same seven discovery-frozen rule keys are eligible for confirmation.

No validation-derived rule, probability, threshold, or replacement candidate is permitted.

## Frozen confirmation inputs

- confirmation geometry SHA-256: `812aba2f2e813f3d53961753e48d1ee510cad937817815c7dee36ba1f9cc2ad5`
- fixed V46 assignment mapping SHA-256: `633918a3bad435adfdef9859a33743b9fa88bfcf59a79a4ed8a59b71141d9d90`
- confirmation observations: **1,607**
- confirmation sources: **53**
- linked confirmation edges: **1,554**

## Frozen per-rule criteria

Reuse validation criteria unchanged.

A rule is `INSUFFICIENT_CONTRAST` if:

- confirmation context occurrences < **10**, or
- target transition occurs in < **3 distinct confirmation sources**.

Otherwise it is testable.

A testable rule is `TRANSFERRED` only if all are true:

- confirmation conditional probability >= **0.50**;
- confirmation lift >= **1.25**;
- the **discovery-frozen** rule probability yields positive binary log-loss gain over the **discovery-frozen** scale-only baseline on confirmation edges.

A testable rule failing any criterion is `REJECTED_ON_CONFIRMATION`.

## Frozen overall confirmation criterion

`CONFIRMATION_SUPPORTED` requires:

- zero rejected rules;
- at least **5 of 7** frozen rules transferred.

This is identical to the validation support gate.

## No-refit rule

Confirmation may not modify:

- regime assignments;
- graph geometry;
- the seven rule keys;
- discovery probabilities;
- discovery baseline probabilities;
- thresholds;
- validation outcomes.

No provenance or Song semantics may be consumed before the confirmation result is frozen.
