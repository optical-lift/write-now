# Mark Falsifiability Layer v4

Mark v4 adds a validation layer that prevents the conveyor from treating forced nearest-neighbor assignment or synthetic fixture design as evidence.

## Governing rule

A Mark run may build a world without proving a hypothesis. A run may be called validated only when it can lose.

Validation therefore requires three independent gates:

1. **Abstention** — a holdout observation is assigned to a learned family only when it falls inside a distance envelope learned from training-family members. Otherwise the result is `abstain`.
2. **Prospective scoring** — the frozen training world makes holdout assignments before holdout truth is available to the evaluator. When a synthetic validation fixture supplies private truth labels, the evaluator reports accepted precision, recall, abstention rate, and coverage instead of counting every returned nearest neighbor as a success.
3. **Null worlds** — the observed cross-source structure is compared with deterministic shuffled-source null worlds. The validation report records empirical p-values for recurrent operations and family source diversity. A structural pattern must outperform the null distribution to be promoted as a validated anomaly.

## Evidence language

The pipeline distinguishes these statements:

- `assigned`: the nearest family was computed.
- `accepted`: the nearest family fell inside the training-derived acceptance envelope.
- `abstained`: the nearest family was too distant to support assignment.
- `correct`: an accepted synthetic-fixture assignment matched private fixture truth.
- `null_exceedance`: the observed structural statistic exceeded the shuffled-world distribution.

For physical evidence there is normally no ground-truth family label. Physical runs therefore report acceptance/abstention and null-world statistics, but never manufacture a correctness score.

## Synthetic fixture rule

A synthetic fixture used for validation must contain both:

- positive families that recur through transformations; and
- distractor structures that should not be accepted into those families.

Context-box labels are never truth labels. Context remains sealed until after world freeze. Private fixture truth exists only for CI evaluation and is not admitted to discovery.

## Validation gate

CI fails when a synthetic validation run cannot demonstrate all of the following:

- at least one accepted holdout assignment;
- at least one abstention;
- accepted precision above the configured floor;
- non-trivial holdout coverage below 100% (proving abstention is active);
- an observed recurrent-structure statistic stronger than most shuffled null worlds.

These thresholds validate the machinery, not a historical claim. Real historical promotion still requires independent physical evidence, provenance, replication, and mechanism testing.
