# Mark V45 Phase-A result — Song composition-rule harvest

Experiment ID: `mark:song-composition-harvest:v45`

## Integrity

- Sealed research base: `76f7eedbc5a6d154d3bfea3c5bea044317b703ae`
- V45 implementation SHA: `c6d51f22357ddbc457c886965a79d30a913b0b1b`
- Pre-execution freeze SHA: `f561a17386c2a292db2c0dae245ef78ee4ca1ac6`
- V45 bound pre-outcome branch head: `b5b37209e5644d0a3366d0dc060603db72089f6b`
- Candidate closure blob: `f5b4908cb28939ac2b044628a903c3ff8d7e6d99`
- Raw runner candidate packet SHA-256: `4701952d164c21dd39105d74f1fe4441e423c80259d3f6887f9f6697ad690ed6`
- Raw runner summary SHA-256: `1af05d7fadad125ae8c9996682fd9ed42e9161dc2e44236db206c9590d1b3cf7`
- Primary train freeze SHA-256: `1d4a15ccb08fc27137695504a865c1cbd8d36954e07d0552a151582fcee9b0f3`
- Primary evaluator result SHA-256: `06e9d515dc898dd330d962c304c1ad0e61631a058a6191ffa10ed87a06ca05e3`
- Topology train freeze SHA-256: `7b4280663a593a3860fec5b9fe5c02740117d8b701831a7d51a3bd04581a20ac`
- Topology evaluator result SHA-256: `86e3d0d5ddb21a4008eb9b04123882aa19170952eb63742d7c6718b1440f6625`
- Source/corpus lanes: train 84 observations / 43 sources; holdout 230 / 154; control 119 / 63.
- Pair-eligible physical observations: 433.
- Candidate count attempted: 5.
- Candidate count harvested: 3.
- Candidate count open: 0.
- Candidate count insufficient contrast: 2.
- Song semantics opened during Phase A: **no**.

## Candidate summary

| Rule | Feature family | Status | Physical witnesses | Main held-out result | Topology invariance |
|---|---|---|---:|---|---|
| CR-001 | sequential operator composition | **HARVESTED_RULE** | 6 positive + 6 near-counterexamples in raw packet | composition beats input-only by 4.2658 bits/path, A-only by 2.1307, B-only by 0.1788; 151 covered held-out sources; composition beats input-only in 100% of covered source groups | full topology gate passed |
| CR-002 | repetition / count | **HARVESTED_RULE** | 6 positive + 6 near-counterexamples | 8/8 train-frozen idempotence candidates transferred on holdout and 8/8 on control | 9 topology candidates transferred |
| CR-003 | sequential cancellation | **HARVESTED_RULE** | 6 positive + 6 near-counterexamples | 20/20 train-frozen cancellation candidates transferred on holdout and 20/20 on control | 20/20 transferred |
| CR-004 | order sensitivity | **INSUFFICIENT_CONTRAST** | 0 | no A,B / B,A pair met the preregistered train contrast gate | unresolved, not negative |
| CR-005 | input-conditional composition | **INSUFFICIENT_CONTRAST** | 0 | no pair met the preregistered multi-input dominant-output gate | unresolved, not negative |

## CR-001 — factorized sequential composition

The frozen one-step anonymous operator kernels successfully compose into a useful two-step consequence model without fitting the A,B pair directly.

On held-out material:

- 3,088,406 raw four-center paths were encountered;
- 1,344,512 paths were covered by the train-frozen vocabulary;
- coverage spans 151 distinct held-out source groups;
- factorized composition improves log loss by **4.2658 bits/path** over input state alone;
- by **2.1307 bits/path** over the first operator alone;
- by **0.1788 bits/path** over the second operator alone;
- the directly fitted pair model retains only a small **0.0547 bits/path** advantage over factorized composition;
- every covered held-out source group scores composition better than input-only.

The separate control lane repeats the direction of effect: composition improves over input-only by **4.2002 bits/path**, over first-operator-only by **2.1777**, and over second-operator-only by **0.2545**.

Removing normalized path length does not remove the result. Both the length-aware and topology-only full composition gates pass.

**Status: HARVESTED_RULE.**

## CR-002 — operator repetition / idempotence

Eight train-supported A→A candidates were frozen before holdout. All eight transfer under the preregistered holdout criterion, and all eight transfer on the control lane. The topology-only discovery finds nine transferable repetition candidates.

The rule is deliberately narrow: a supported anonymous operator can repeat while preserving its one-step consequence kernel within the frozen tolerance. It does not assert that visual repetition in general is idempotent.

**Status: HARVESTED_RULE.**

## CR-003 — ordered-pair cancellation

Twenty ordered A→B candidates were frozen on train evidence because their composite consequence returned toward the incoming anonymous boundary state more strongly than the one-sided controls. All twenty transfer on holdout; all twenty transfer on control; all twenty transfer under the topology-only representation.

This is operational cancellation only. Phase A assigns no inverse sign meaning, lexical value, historical relationship, or translation.

**Status: HARVESTED_RULE.**

## CR-004 and CR-005

Neither family failed a held-out test. They never reached one.

- CR-004 had zero train-supported operator pairs for which both A→B and B→A independently met support and the frozen order-contrast threshold.
- CR-005 had zero train-supported operator pairs with enough supported incoming states and distinct dominant outputs to satisfy the frozen conditional-composition prerequisite.

Both remain **INSUFFICIENT_CONTRAST**. V45 does not convert absence of a testable candidate into evidence of commutativity or context-independence.

## Strongest candidate for compiler handoff

**Rule ID: CR-001.**

CR-001 is the first Song compiler candidate because it is the broad composition law from which the narrower CR-002 and CR-003 behaviors are special cases or constraints. It has the largest evidence surface: source-separated held-out transfer, matched one-sided and input-only controls, direct-pair comparison, control-lane replication, physical witnesses and near-counterexamples, and a successful topology-only invariance test.

The first compiler test should therefore be purely structural:

**Given two already-identified anonymous physical operators A and B in sequence, compose their independently learned consequence relations and predict the outgoing structural state without introducing a special A+B semantic rule.**

The direct-pair model's small residual advantage should be preserved as an unresolved residual rather than erased. It may represent higher-order interaction not captured by first-order factorization.

## Residuals

V45 does not establish:

- recursive nesting;
- filled-region / enclosure composition;
- direct split/join mutation;
- order sensitivity;
- input-conditional composition;
- lexical identity;
- phonetic identity;
- theological or historical meaning;
- equivalence of named glyphs across cultures.

The small residual advantage of directly fitting A,B pairs over factorized composition remains measurable and should be tracked by the compiler rather than forced into CR-001.

## Phase-A verdict

Phase A supports a **semantic-free compositional operator layer** in the frozen physical Mark representation.

Three operational rules survive the preregistered evidence requirements:

1. sequential anonymous operators can be factorized and composed;
2. a supported subset behaves idempotently under repetition;
3. a supported subset of ordered pairs behaves as operational cancellation.

Two further candidate families remain unresolved because the frozen corpus did not furnish the required contrasts.

This verdict is structural only. No Song meaning has been used to obtain it.
