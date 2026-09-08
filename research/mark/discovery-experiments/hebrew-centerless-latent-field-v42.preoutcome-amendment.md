# V42 pre-outcome feasibility amendment — lexical anti-lookup subset

Experiment ID: `mark:hebrew-centerless-latent-field:v42`
Date: 2026-09-07
Status: committed before any V42 performance endpoint, matched-window score, membership-null score, or Masoretic witness query was opened.

## Reason for amendment

The original V42 preregistration defined the lexical anti-lookup population as holdout spans for which all nine consonantal skeletons were absent from V42 training.

The implementation feasibility audit found that this population is empty:

- holdout spans: 71,248
- holdout spans with all nine skeletons absent from training: 0

No V42 predictive outcome had been calculated or inspected at this point.

The strongest directly evaluable anti-lookup unit is therefore the missing token itself. Across the frozen deterministic B partition there are:

- 356,240 held-out B token occurrences
- 30,654 B occurrences whose consonantal skeleton is absent from V42 training
- 23,658 holdout spans containing at least one such unseen B occurrence

These are feasibility/count facts only, not performance results.

## Frozen amendment

Replace references to the `lexically-unseen-span subset` in the original preregistration with the following endpoint population:

**unseen-B-token subset** — held-out B token occurrences whose exact consonantal skeleton is absent from every V42 training token.

The predictor remains the full anonymous four-member A multiset. B token skeleton identity is used only to determine subset membership and is never supplied to F0 or F1.

For this population, cross-entropy, bits/token, perplexity, and mean log probability are calculated over only the qualifying unseen B occurrences.

Primary success condition 2 is amended, before outcomes, from:

`F1 cross-entropy < F0 on the lexically-unseen-span subset`

to:

`F1 cross-entropy < F0 on the unseen-B-token subset.`

All other V42 definitions, including the full-holdout criterion, deterministic A/B partition, 65-state alphabet, alpha=0.5, exact-signature backoff rule, F2 matched-window control, F3 membership nulls, and interpretation ceiling remain unchanged.

No further subset redefinition is permitted after V42 performance is opened; any later alternative is V43 or an explicitly labeled post-verdict robustness analysis.
