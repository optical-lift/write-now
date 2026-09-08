# V42 Phase-A Hebrew-only results — centerless latent field

Experiment ID: `mark:hebrew-centerless-latent-field:v42`
Date: 2026-09-07
Verdict: **NEGATIVE under the preregistered primary criterion**

Masoretic witness remained sealed throughout this analysis.

Governing commits before outcome scoring:

- preregistration: `5e5b52305224174790e2ecc5c7830e5a55e398a6`
- pre-outcome lexical-subset amendment: `7fd917b88162bdffdfba6f4ace68322b33899588`
- pre-outcome F2 donor amendment: `bac2bcc90f9da8341d8fe965074493464fc19ab8`
- implementation freeze: `0ddba2c27481ed7e255a012f629edc1148f81d0e`

## Integrity

- training spans: 233,929
- holdout spans: 71,248
- primary B score rows: 356,240
- F2 matched-window score rows: 356,240
- F3 membership-null score rows: 7,124,800
- F3 nulls: 20
- rows/null: exactly 356,240 for every null
- F2 donor pairs sharing any canonical token IDs: 0

## Primary F0 vs F1 endpoints

### Full holdout

Missing-token occurrences: 356,240

| Model | CE nats/token | bits/token | perplexity | mean log p |
|---|---:|---:|---:|---:|
| F0 empirical frequency | 2.84331288974504 | 4.10203340573083 | 17.1725622098833 | -2.84331288974504 |
| F1 exact anonymous A-field | 3.01461889130890 | 4.34917572466154 | 20.3813219612950 | -3.01461889130890 |

F1 is worse than F0 by 0.17130600156386 nats/token.

Primary condition 1 (`F1 CE < F0`) **FAILS**.

### Unseen-B-token anti-lookup subset

Missing-token occurrences whose exact consonantal skeleton is absent from all V42 training tokens: 30,654

| Model | CE nats/token | bits/token | perplexity | mean log p |
|---|---:|---:|---:|---:|
| F0 empirical frequency | 3.64448640289363 | 5.25788246004190 | 38.2631159784863 | -3.64448640289363 |
| F1 exact anonymous A-field | 3.74344662659325 | 5.40065188401860 | 42.2433365508978 | -3.74344662659325 |

F1 is worse than F0 by 0.09896022369962 nats/token.

Primary condition 2 (`F1 CE < F0` on unseen B) **FAILS**.

## F2 matched-window control

- true same-window F1 mean log probability: -3.01461889130871
- deterministic matched-window F2 mean log probability: -3.03869104576008
- F2 CE: 3.03869104575971 nats/token

The real same-window pairing is modestly better than the mismatched-window pairing by 0.02407215445137 nats/token.

Primary condition 3 (true same-window F1 mean log p > F2) **PASSES**.

## F3 deterministic membership nulls

Real preregistered split F1 CE: 3.01461889130872 nats/token.

| Null | CE nats/token |
|---:|---:|
| 1 | 3.01317061488792 |
| 2 | 3.01427417828712 |
| 3 | 3.02071430447994 |
| 4 | 3.02033836713840 |
| 5 | 3.01052831287805 |
| 6 | 3.01412696416089 |
| 7 | 3.01583202163134 |
| 8 | 3.01177738895564 |
| 9 | 3.01430522791725 |
| 10 | 3.01882496714226 |
| 11 | 3.01772319847292 |
| 12 | 3.01617957253979 |
| 13 | 3.02024430808483 |
| 14 | 3.01684693192443 |
| 15 | 3.01743248619537 |
| 16 | 3.01958678342622 |
| 17 | 3.01440834284208 |
| 18 | 3.02322717786754 |
| 19 | 3.01522056798833 |
| 20 | 3.01445461735525 |

Null CE range: 3.01052831287805–3.02322717786760.
Mean null CE: 3.01646081670878.

Real split beats 12 of 20 nulls and fails to beat 8 of 20.

Primary condition 4 (beat at least 19 of 20 nulls) **FAILS**.

## Frozen supporting diagnostics

### Seen-A vs unseen-A/backoff

| A status | B rows | F0 CE | F1 CE |
|---|---:|---:|---:|
| training-seen exact A signature | 322,400 | 2.82720100090241 | 3.01648775647647 |
| unseen exact A signature / F0 backoff | 33,840 | 2.99681386382700 | 2.99681386382700 |

The degradation therefore occurs in the exact-signature conditional model itself, not in the preregistered unseen-signature backoff.

### Span intrinsic-state diversity

Because each span has nine members, `repeat excess states = 9 - diversity`.

| Diversity | Repeat excess | B rows | F0 CE | F1 CE |
|---:|---:|---:|---:|---:|
| 2 | 7 | 230 | 2.01159940216635 | 1.94824502179655 |
| 3 | 6 | 3,405 | 2.06498414237528 | 2.02632884357779 |
| 4 | 5 | 20,905 | 2.27427354331273 | 2.30706196247512 |
| 5 | 4 | 65,180 | 2.51315379427331 | 2.62100117769500 |
| 6 | 3 | 109,775 | 2.75931919024755 | 2.94178062774685 |
| 7 | 2 | 100,165 | 3.01669730381184 | 3.23662768536954 |
| 8 | 1 | 46,770 | 3.29124253006001 | 3.50126806346328 |
| 9 | 0 | 9,810 | 3.57325479769634 | 3.73384432625589 |

F1 helps only in the two lowest-diversity strata (diversity 2–3), which together comprise a very small fraction of the holdout. From diversity 4 upward it is worse than F0, with the penalty increasing through more diverse fields.

## Preregistered verdict

V42 required all four primary conditions. Results:

1. F1 beats F0 full holdout — **FAIL**
2. F1 beats F0 unseen-B-token subset — **FAIL**
3. true same-window F1 beats F2 matched-window control — **PASS**
4. real A/B split beats at least 19/20 F3 nulls — **FAIL** (12/20)

Therefore V42 is **NEGATIVE**.

## Interpretation

The exact centerless-field hypothesis tested by V42 is not supported. A four-member exact anonymous intrinsic-state multiset does not provide a generalizable conditional state that improves prediction of the other five members. It substantially overperforms neither the frequency baseline nor arbitrary membership partitions.

There is nevertheless a small same-window association: the recipient A field scores its own B members better than B from a deterministic nonoverlapping donor window. That signal is insufficient for the preregistered field claim and cannot rescue V42.

The diversity diagnostic is informative for future work but is not a rescue analysis: very low-diversity spans show a small F1 advantage, whereas the much more common moderate/high-diversity spans drive the overall failure. Any model aimed specifically at recurrence, concentration, or low-dimensional field structure must be a new experiment (V43 or later), preregistered before outcomes.

No Masoretic data was queried in reaching this verdict.
