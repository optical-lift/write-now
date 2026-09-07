# V39 Phase A Result — Hebrew Relational Structural Field

**Experiment:** `mark:hebrew-relational-field:v39`  
**Protocol freeze:** `8e73a8a51bd183785e61279b10ad486a7c64cb17`  
**Masoretic witness status during all results below:** sealed / unread by V39

## Primary Hebrew-only result

V39 tested whether identity-blind relations between neighboring Hebrew consonantal forms improve held-out prediction of the next V38 intrinsic state beyond the current intrinsic state alone.

They do not under the frozen representation.

### H0 / H1 baseline

On 62,096 held-out canonical transitions:

- H0 unigram: **2.8586568171 nats/token**; perplexity **17.4381**
- H1 current intrinsic state: **2.8562256136 nats/token**; perplexity **17.3957**
- H1 delta versus H0: **-0.0024312035 nats**

The V38-like intrinsic state again carries only a small held-out sequential advantage.

### H2 — coarse predecessor relation

On 62,055 held-out transitions with an eligible predecessor relation:

- H1: **2.8560715052 nats**
- H2: **2.8877820994 nats**
- H2 delta versus H1: **+0.0317105941 nats** (worse)
- H2 supported-context coverage: **83.6736%**
- H2 perplexity: **17.9534**

H2 fails the V39 primary success criterion despite high context coverage.

### H3 — exact identity-blind cross-word equality topology

On the same 62,055 transitions:

- H1: **2.8560715052 nats**
- H2: **2.8877820994 nats**
- H3: **2.8990210676 nats**
- H3 delta versus H1: **+0.0429495624 nats** (worse)
- H3 supported-context coverage: **65.4114%**
- H3 perplexity: **18.1564**

H3 also fails the primary criterion.

### H4 — relation-delta context

The corpus-wide H4 scorer exceeded the database statement timeout. The identical frozen scorer was therefore executed in four disjoint groups of holdout books and the negative log-loss sums were aggregated. No model, sample, support threshold, representation, or smoothing value changed.

Across 62,014 eligible held-out windows:

- H1 aggregated: **2.8559305745 nats**
- H2 aggregated: **2.8876017244 nats**
- H4 aggregated: **2.9183185368 nats**
- H4 delta versus H1: **+0.0623879623 nats** (worse)
- H4 supported-context coverage: **24.5138%**

H4 fails both parts of the primary success criterion: it is worse than H1 and supported-context coverage is below 50%.

## Primary verdict

**V39 Phase A is negative.** None of H2–H4 improves held-out Hebrew prediction over H1 under the frozen representation.

This is evidence against the specific V39 hypothesis that these immediate identity-blind neighboring-form relations recover a richer predictive Hebrew structural field.

It is **not** evidence against an underlying authentic mark system. It rejects this representation/recovery route, not the broader hypothesis.

## Reproducibility custody

Derived Hebrew-only experiment tables were materialized in internal schema `instrument` without Masoretic data:

- `v39_hebrew_tokens`
- `v39_hebrew_relations`
- `v39_top64_states`
- `v39_h1_counts`
- `v39_h2_counts`
- `v39_h3_counts`
- `v39_h4_counts`
- context-total tables

Frozen hashes:

- top-64 state inventory: `28bf8a1c20c69502011101544cf53e71`
- H1 training cells: `93c4719e1b9bdeac369b4c5c79fc0d1c`
- H2 training cells: `d9716559fa50b1c854718b171de0134f`
- H3 training cells: `48d9923235099d9e1b7bfba1abe7382b`
- H4 training cells: `ee1d6acb1b7f3ddf06fa9aaa1c573665`

Training cell counts:

- H1: 5,687
- H2: 44,001
- H3: 82,636
- H4: 143,440

## Computational note

The preregistered 20 predecessor-offset adjacency nulls and four-token H4 order-control endpoint were not used to make the primary verdict. Because every richer relational lane already failed the primary held-out criterion, these secondary endpoints cannot rescue the preregistered Phase-A primary claim. They remain unexecuted at this freeze point rather than being silently replaced with cheaper post-hoc controls.

## Interpretation before witness opening

The result says something useful: simple local cross-word equality/overlap relations appear to fragment the Hebrew state space faster than they add generalizable predictive information. A subsequent experiment should therefore avoid merely adding more local categorical context. A stronger recovery route should look for lower-dimensional **global recurrence/position/trajectory structure** learned from Hebrew itself.
