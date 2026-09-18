# Mark V47 pairwise validation protocol

**Experiment:** `mark:regime-transition-grammar:v47`  
**Status:** FROZEN BEFORE VALIDATION TRANSITION LABEL JOIN  
**Date:** 2026-09-18

## Frozen discovery result

Discovery freeze:

`a8a00b372e80976365058bb567193fef4bddf9e6`

Raw pairwise discovery SHA-256:

`e0623f374b3d065288ded3c9c4a1ff636835632b8675ba081045bedfabe564ff`

Exactly seven rule keys are eligible for validation. No replacement is permitted.

## Frozen validation inputs

- validation geometry SHA-256: `2108eec52d9f20539305a98a56d59dd0abc9d0904d3ca8f02fb541e221cefe40`
- fixed V46 assignment mapping SHA-256: `633918a3bad435adfdef9859a33743b9fa88bfcf59a79a4ed8a59b71141d9d90`
- validation observations: 2,332
- validation sources: 59
- linked validation edges: 2,273

Confirmation remains sealed.

## Frozen validation statistics

For each discovery-frozen transition:

`childScale | childRG -> parentScale | parentRG`

validation reports:

- context occurrences:
  all validation edges matching childScale, childRG, parentScale;
- target occurrences:
  context edges whose parent RG equals the frozen target;
- target distinct sources;
- validation conditional probability;
- validation scale-pair parent marginal;
- validation lift over that marginal.

No validation statistic alters the discovery model.

## Discovery-frozen predictive check

For each rule, retain from discovery:

- `p_rule` = discovery conditional probability;
- `p_base` = discovery scale-pair parent marginal.

Treat the frozen target as a Bernoulli event on validation context edges.

Compute:

- frozen-rule binary log loss using `p_rule`;
- frozen-baseline binary log loss using `p_base`;
- gain = baseline log loss - rule log loss.

Positive gain means the discovery-frozen transition probability predicts unseen validation edges better than the discovery-frozen scale-only marginal.

No probability is refit on validation.

## Per-rule adjudication

A rule is **INSUFFICIENT_CONTRAST** if either:

- validation context occurrences < **10**, or
- target transition occurs in < **3 distinct validation sources**.

Otherwise it is testable.

A testable rule is **TRANSFERRED** only if all are true:

- validation conditional probability >= **0.50**;
- validation lift >= **1.25**;
- frozen predictive gain over the discovery scale-only baseline > **0 bits/edge**.

A testable rule failing any of those is **REJECTED_ON_VALIDATION**.

## Overall validation status

V47 pairwise validation is **VALIDATION_SUPPORTED** only if:

- no frozen rule is `REJECTED_ON_VALIDATION`;
- at least **5 of 7** frozen rules are `TRANSFERRED`.

Otherwise status is `VALIDATION_RESIDUAL`.

This overall gate is fixed before validation labels are joined to validation geometry.

## Boundary

No validation transition outcome has been inspected before this protocol.

Higher-order discovery has zero candidates, so no higher-order validation is performed.

Confirmation remains sealed until validation is frozen.
