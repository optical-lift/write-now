# V42 pre-outcome feasibility amendment — F2 donor selection

Experiment ID: `mark:hebrew-centerless-latent-field:v42`
Date: 2026-09-07
Status: committed before any V42 predictive outcome, F2 score, F3 null score, or Masoretic witness query was opened.

## Reason

The original F2 definition chose, for every one of 71,248 holdout recipients, the eligible donor minimizing `md5('v42-matched-control|' || recipient_span_id || '|' || donor_span_id)`. Exact implementation requires ranking approximately 71,248² recipient/donor pairs and is unnecessarily quadratic for a control whose scientific requirement is only deterministic, outcome-independent mismatching of real B fields.

No V42 performance had been calculated or inspected when this feasibility problem was identified.

## Frozen replacement

Construct one deterministic global donor ordering of holdout spans by:

`md5('v42-donor-order|' || span_id), span_id`

For a recipient at rank `r`, inspect donor ranks cyclically beginning at `r+1`, then `r+2`, etc. Select the first donor satisfying both:

1. donor span differs from recipient span;
2. donor and recipient share no canonical token IDs.

Every donor contributes its original preregistered five-member B multiset. The recipient retains its original four-member A multiset. Score donor B under the recipient's frozen F1 distribution with no refitting.

This mapping is fixed before outcomes and depends only on span/token IDs, never intrinsic states, predictions, or outcomes.

All other F2 interpretation and all other V42 definitions remain unchanged.
