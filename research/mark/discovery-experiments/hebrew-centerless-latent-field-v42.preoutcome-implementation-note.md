# V42 pre-outcome implementation freeze

Experiment ID: `mark:hebrew-centerless-latent-field:v42`
Date: 2026-09-07
Status: implementation frozen before any V42 holdout performance endpoint, F2 matched-window score, F3 membership-null score, or Masoretic witness query was opened.

This note incorporates the preregistration commit `5e5b52305224174790e2ecc5c7830e5a55e398a6`, the lexical-subset feasibility amendment commit `7fd917b88162bdffdfba6f4ace68322b33899588`, and the F2 donor feasibility amendment commit `bac2bcc90f9da8341d8fe965074493464fc19ab8`.

## Frozen source and spans

V42 reuses `instrument.v41_hebrew_tokens` and the frozen V41 block holdout assignment without modification.

Nine consecutive tokens wholly contained in one book/block/split produce:

- training spans: 233,929
- holdout spans: 71,248
- training member occurrences: 2,105,361 = 233,929 × 9
- holdout member occurrences: 641,232 = 71,248 × 9
- deterministic A members: 4/span
- deterministic B members: 5/span
- holdout B occurrences: 356,240

The deterministic reveal rank is exactly:

`md5('v42-reveal|' || book || ':' || chapter || ':' || verse || ':' || position), token_id`

Ranks 1–4 are A; 5–9 are B. Canonical positions and token IDs do not enter model predictors.

## Frozen state alphabet

Each member maps its inherited V41 intrinsic state to the frozen V41 target inventory: the 64 training-selected intrinsic states plus `OTHER` = 65 states.

Inherited V41 target inventory MD5: `f5e92b6e38bdabb3d43fbecb5d4395c6`.

No V42 target reselection occurs.

## Frozen F0

F0 counts state occurrences across all nine members of every V42 training span and uses the empirical state frequency without added smoothing.

- states: 65
- F0 counts MD5: `288af3b6b406d9bbd7c4b41b774bd9a9`

## Frozen F1

For each training span, A is converted to an exact permutation-invariant sparse count signature by grouping its four state categories and serializing sorted `state=count` pairs.

For each exact A signature, B-state occurrences are accumulated across training spans.

- unique training A signatures: 23,468
- nonzero `(A signature, B state)` cells: 199,323
- F1 signature totals MD5: `4ea8373b2035d5522c5791fccbca3b03`
- F1 nonzero count-cell MD5: `b472500da4d753974214400cd1686e07`

For a seen A signature:

`P_F1(y | A) = (count(A,y) + 0.5) / (total_B(A) + 65×0.5)`

For an unseen A signature, F1 backs off exactly once to F0. No partial-signature backoff exists.

Pre-outcome signature-coverage feasibility count:

- holdout A signatures seen in training: 64,480 spans
- holdout A signatures unseen/backoff: 6,768 spans

These are coverage counts only, not performance outcomes.

## Frozen lexical anti-lookup population

The originally preregistered all-nine-unseen span population was empty (0 spans), discovered before outcome scoring. Per the committed pre-outcome amendment, the anti-lookup endpoint is therefore missing-token based:

- holdout B occurrences: 356,240
- B occurrences with consonantal skeleton absent from all V42 training tokens: 30,654
- holdout spans containing at least one unseen B occurrence: 23,658

Skeleton identity is used only for subset membership and is never supplied to F0/F1.

## Frozen F2 matched-window map

Per the committed pre-outcome amendment, holdout spans are globally ranked by:

`md5('v42-donor-order|' || span_id), span_id`

For each recipient, cyclic donor offsets are inspected from +1 upward and the first donor sharing no canonical token IDs is selected.

- recipient/donor pairs: 71,248
- self donors: 0
- maximum cyclic offset required: 2
- donor map MD5: `f5d89a530ea02a8a8f7afc0a18cc5200`

F2 uses recipient A and donor's original five B members, scored by the unchanged frozen F1 distribution with no refitting.

## Frozen F3 membership null implementation

For null `k = 01..20`, each holdout span's nine member bundles are ranked by:

`md5('v42-membership-null-XX|' || token_id), token_id`

The lowest four become null A and the remaining five null B. Null A is serialized with the identical F1 exact-signature procedure. The unchanged frozen training F1 model is used; unseen null-A signatures back off to F0. No refitting occurs.

## Frozen score storage and procedures

The following score tables existed and were empty at implementation freeze:

- `instrument.v42_primary_scores`: 0 rows
- `instrument.v42_f2_scores`: 0 rows
- `instrument.v42_f3_scores`: 0 rows

Frozen procedures:

- `instrument.v42_score_primary()`
- `instrument.v42_score_f2()`
- `instrument.v42_score_f3(k integer)`

Primary scoring writes one row per original holdout B occurrence with F0 log probability, F1 log probability, seen-A status, and unseen-B subset status.

## Custody rule

After this implementation freeze, no change may be made to span width, train/holdout split, state alphabet, A/B assignment, alpha, F0 definition, exact-signature representation, backoff, F2 donor map, F3 null partition, endpoint definitions, or primary success criterion. Any substantive change is V43 or an explicitly labeled post-verdict robustness analysis.

Masoretic witness remains sealed until V42 Phase-A endpoints, F2 control, all 20 F3 nulls, and the Phase-A verdict are committed with a witness-opening SHA.
