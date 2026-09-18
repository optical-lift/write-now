# Mark V47 validation freeze

**Experiment:** `mark:regime-transition-grammar:v47`  
**Status:** VALIDATION SUPPORTED / 7 OF 7 RULES TRANSFERRED / CONFIRMATION MAY OPEN  
**Date:** 2026-09-18

## Frozen upstream custody

- discovery freeze: `a8a00b372e80976365058bb567193fef4bddf9e6`
- validation protocol: `316f21e043dc43049dd04b32d0d87224348a361f`
- validation implementation freeze: `0e35f05db8c3c922b97be062f07264dca2689dc3`
- validation geometry SHA-256: `2108eec52d9f20539305a98a56d59dd0abc9d0904d3ca8f02fb541e221cefe40`
- evaluator Git blob: `1d01dcf1586ba257edd6cd526ad5d001e5ca579d`
- raw validation result SHA-256: `e1f2ebfe4d89713159f2a55b1baa7e5d70fb0dafc54e90c4670b3ad0025163ef`

## Validation verdict

**VALIDATION_SUPPORTED**

All seven discovery-frozen rules transferred on 59 unseen sources:

| Rule | Context | Target | Sources | Validation P | Lift | Frozen predictive gain |
|---|---:|---:|---:|---:|---:|---:|
| local RG-001 -> neighborhood RG-001 | 82 | 69 | 13 | 0.8415 | 7.4777 | +2.0531 bits/edge |
| local RG-002 -> neighborhood RG-002 | 240 | 196 | 29 | 0.8167 | 2.5323 | +0.4772 |
| local RG-004 -> neighborhood RG-004 | 440 | 401 | 23 | 0.9114 | 1.7115 | +0.7590 |
| neighborhood RG-001 -> field RG-001 | 82 | 76 | 9 | 0.9268 | 7.5231 | +2.5486 |
| neighborhood RG-002 -> field RG-002 | 245 | 220 | 20 | 0.8980 | 2.8548 | +0.7477 |
| neighborhood RG-003 -> field RG-003 | 19 | 10 | 4 | 0.5263 | 33.4649 | +1.5231 |
| neighborhood RG-004 -> field RG-004 | 416 | 403 | 25 | 0.9688 | 1.7726 | +0.9768 |

Counts:

- transferred: **7**
- rejected: **0**
- insufficient contrast: **0**

Every rule satisfies the frozen validation gates, including positive prediction gain from the **discovery-frozen** rule probability over the **discovery-frozen** scale-only baseline. Nothing was refit on validation.

## Interpretation boundary

Validation establishes that the seven anonymous cross-scale persistence rules recur in unseen sources.

It does not assign meaning to RG states, and no provenance or Song labels were consumed.

## Confirmation boundary

Confirmation may now open for the same seven exact rules.

The validation thresholds, discovery-frozen probabilities, and overall support gate may not be altered before confirmation.
