# V38 — Hebrew-Only Latent Structural Field

**Experiment ID:** `mark:hebrew-latent-structural-field:v38`  
**Date:** 2026-09-07  
**Status:** preregistered before Hebrew holdout outcomes and before V38 Masoretic witness opening

## Governing correction

V30–V37 treated the Masoretic mark layer too easily as though it were the target mark system. V38 formally separates those roles.

The Masoretic marks are an **observable historical witness layer**. They are not the definition of the system V38 is trying to recover.

The target of discovery is an independently recoverable structural field in the Hebrew consonantal text. Only after that field is specified, fit, validated, and frozen may the Masoretic witness be opened for V38 comparison.

This follows the project’s source/shell discipline: a surviving visible carrier must not be promoted into source merely because it is available. It also follows function-before-label: V38 does not begin from conventional accent names, inherited grammatical labels, translations, or semantic interpretation.

V37 is not erased. Its results remain evidence about the Masoretic witness layer and its relationship to Hebrew operators. V38 changes the source-role assumption under which those results are interpreted.

## Core question

> Can a stable, sequentially informative structural field be recovered from the Hebrew consonantal surface without access to Masoretic marks, and after that field is frozen, does the Masoretic witness align with it better than frequency, lexical lookup controls, and deterministic nulls?

The first half of the question is Hebrew-only. The second half is witness comparison.

## Phase A — sealed-witness Hebrew discovery

### Allowed discovery carrier

Only `draft.ot_canonical_tokens_stage.hebrew_surface` may supply linguistic signal, after reducing each token to consonantal Hebrew letters U+05D0–U+05EA in canonical token order.

Book/chapter/verse/token identifiers may be used only for order, deterministic splitting, and provenance.

### Prohibited during Phase A discovery and model selection

The following are sealed and may not enter a V38 discovery feature, state, threshold, graph edge, support decision, lane choice, or model-selection decision:

- `draft.canon_masoretic_marks`
- Unicode cantillation marks
- niqqud / vowel points
- slash segmentation or other editorial punctuation
- `lemma_raw`
- `morph`
- Strong identifiers
- translations
- conventional accent names
- inherited grammatical categories
- semantic labels
- prior V36/V37 mark identities as labels

The consonantal carrier is produced by deleting every character outside U+05D0–U+05EA. Final consonant forms remain because they are part of the consonantal surface; their contribution is separately inspectable.

### Deterministic holdout

The canonical corpus is divided into five-chapter blocks with `block_index=floor((chapter-1)/5)`.

Blocks are ranked by:

`md5('v38-hebrew-blind-holdout|' || book || ':' || block_index), book, block_index`

The lowest `ceil(20%) = 41` of 201 blocks are holdout.

Frozen holdout blocks, rank order:

1. Dan 1–5
2. Job 11–15
3. Pro 31
4. Psa 146–150
5. Ezr 1–5
6. Jdg 1–5
7. Deu 6–10
8. 1Sa 21–25
9. Amo 1–5
10. Jos 21–24
11. Isa 61–65
12. Eze 41–45
13. 2Ki 6–10
14. Jer 1–5
15. Nah 1–3
16. Job 6–10
17. Ecc 11–12
18. Lev 11–15
19. 2Ch 16–20
20. Pro 16–20
21. Psa 76–80
22. Zec 11–14
23. Eze 46–48
24. Psa 21–25
25. Deu 16–20
26. Psa 56–60
27. Eze 6–10
28. 2Ch 31–35
29. Num 1–5
30. Dan 6–10
31. Mal 1–3
32. Psa 61–65
33. Gen 6–10
34. Dan 11–12
35. Zec 1–5
36. Isa 51–55
37. Psa 81–85
38. Gen 31–35
39. Isa 26–30
40. 2Ch 1–5
41. Jon 1–4

No V38 holdout metric may be used to alter the representation after the protocol freeze.

## Hebrew structural representation

### Exact consonantal skeleton

For each token, strip every non-U+05D0–U+05EA character. The resulting consonantal string is `skeleton`.

Exact skeleton identity is **not** the primary latent representation. It is retained only as an upper-bound / lexical-lookup control.

### Primary identity-blind state

For each consonantal skeleton define:

1. `length` — number of consonantal codepoints.
2. `equality_pattern` — letters are relabeled by order of first occurrence without retaining letter identity. Example: a six-letter word with all distinct consonants becomes `1.2.3.4.5.6`; a three-letter pattern with positions 2 and 3 identical becomes `1.2.2`.
3. `terminal_final_form` — boolean indicating whether the final consonant is one of ך ם ן ף ץ.

The frozen primary state key is:

`length | equality_pattern | terminal_final_form`

Corpus reconnaissance performed before outcome opening found 39,956 exact consonantal skeleton types and 739 such identity-blind shape classes across 306,785 tokens. These counts are descriptive carrier facts, not holdout performance outcomes.

### Ablation state

`minus_final_form` removes `terminal_final_form` from the state key. This tests whether final-form orthography materially contributes.

### Exact-skeleton control

`exact_skeleton` uses the full consonantal string as a categorical state. It may show how much performance can be obtained by lexical/consonantal identity lookup, but it may not be interpreted as recovery of the latent mark system.

## Hebrew-only predictive graph

The primary state graph is trained only on non-holdout blocks.

### Node support

Primary shape states with at least 100 training token occurrences are graph nodes. Unsupported states map to `OTHER` for predictive evaluation.

### Transition profile

For every supported node, construct two training-only categorical distributions:

- outgoing immediate-next-state distribution
- incoming immediate-previous-state distribution

The destination alphabet is the 64 most frequent supported primary states in training plus `OTHER`. The top 64 are selected by training frequency descending with state-key ascending tie break.

Apply symmetric Dirichlet smoothing `alpha = 0.5` to each profile dimension.

### Distance

For two supported states A and B:

`distance(A,B) = 0.5 * JS(out_A, out_B) + 0.5 * JS(in_A, in_B)`

where JS is Jensen–Shannon divergence using natural logarithms.

### Graph

For each node, retain its five nearest other nodes by ascending distance, with state-key ascending deterministic tie break. This directed 5-nearest-neighbor graph is the frozen V38 Hebrew latent structural graph.

No Masoretic information may influence node support, profile dimensions, smoothing, distance, or neighbors.

## Phase A Hebrew-only validation endpoints

### Endpoint A1 — heldout next-state cross-entropy

Use the training transition model `P(next_state | current_state)` over supported primary states plus `OTHER`, with `alpha=0.5` smoothing.

Compare heldout cross-entropy against a training unigram next-state baseline using the same alphabet and smoothing.

Report:

- nats/token
- bits/token
- relative perplexity
- delta versus unigram

Primary success criterion: lower heldout cross-entropy than unigram.

### Endpoint A2 — order sensitivity

For each heldout triple of consecutive canonical tokens wholly inside one holdout block, score:

- real order `[0,1,2]`
- reversed `[2,1,0]`
- deterministic rotation `[1,2,0]`

with the training first-order transition score:

`log P(s2|s1) + log P(s3|s2)`

Report mean score and fraction of triples where real > control. Real order outperforming both controls is evidence that the recovered state sequence contains directional organization.

### Endpoint A3 — state coverage and recurrence

Report:

- number of supported graph nodes
- training token coverage
- holdout token coverage
- number of observed training edges
- number and rate of holdout transitions previously seen in training

This is required to distinguish real generalization from sparse lookup.

### Endpoint A4 — final-form ablation

Repeat A1 and A2 with the `minus_final_form` state key. The difference is descriptive; no representation may be changed after seeing it.

### Endpoint A5 — exact-skeleton upper bound

Repeat A1 using exact consonantal skeleton identity with training support >=20 and `OTHER`. This is an upper-bound / lexical-control lane only.

## Phase-A freeze boundary

Before any V38 query reads `draft.canon_masoretic_marks`, the following must be written to repository custody:

- the complete protocol
- the exact training-derived state inventory
- the 64 profile dimensions
- the directed 5-NN graph or a reproducible hash plus extraction script
- Phase A Hebrew-only validation results
- the commit SHA that constitutes the witness-opening boundary

After this boundary, no V38 state definition, support threshold, smoothing parameter, graph rule, holdout, endpoint, or witness scoring rule may be changed. Changes become a separately named robustness experiment or V39.

## Phase B — Masoretic layer opened only as external witness

### Witness definition

After the Phase-A freeze, read `draft.canon_masoretic_marks` for `witness_key='mt_noel_current'`.

The V38 witness inventory is every codepoint in Unicode Hebrew cantillation range U+0591–U+05AF that is actually present in the witness. A token is primary-witness eligible only when exactly one such cantillation codepoint is attached to that token. Zero or multiple cantillation-codepoint tokens are excluded from the primary witness endpoint.

No conventional accent names are used in scoring.

### Witness models

All emission parameters are training-block only.

- **W0 frequency:** training-wide mark frequency only.
- **W1 identity-blind Hebrew state:** categorical `P(mark | primary_shape_state)` with `alpha=5` shrinkage toward training-wide mark frequency.
- **W2 graph-smoothed Hebrew state:** `0.5 * W1 probability + 0.5 * mean probability of the node’s five frozen Hebrew-graph neighbors`; unsupported states fall back to W0.
- **W3 exact consonantal skeleton:** categorical `P(mark | exact_skeleton)` with the same smoothing. W3 is an upper-bound lexical control, not the latent-system result.

### Primary witness endpoints

On witness-eligible holdout tokens report:

- categorical log loss / cross-entropy
- top-1
- top-3
- top-5
- mean reciprocal rank
- entropy reduction versus W0

Primary comparison: W1 and W2 versus W0. W3 tells whether apparent alignment is mainly lexical lookup.

### Critical anti-lookup subsets

1. **Unseen-skeleton subset:** heldout witness-eligible tokens whose exact consonantal skeleton has zero training occurrences. W3 necessarily falls back; W1/W2 can still succeed if structural generalization is real.
2. **Variable-mark skeleton subset:** exact consonantal skeletons that occur with at least two different witness codepoints in training and/or holdout. This tests whether exact word identity alone explains the witness.

### Witness nulls

Run 20 deterministic frequency-stratified witness-label permutations. After witness frequencies are known, divide witness identities into five frequency strata as evenly as possible, order labels inside each stratum by `md5('v38-witness-scramble-XX|' || codepoint)`, and cyclically rotate labels by one position. Salts are `v38-witness-scramble-00` through `v38-witness-scramble-19`.

The Hebrew graph and states remain untouched. Real witness alignment should outperform the permuted-label distribution.

## Phase C — relation classification, not relabeling

If Phase B shows alignment, do not rename Hebrew latent states with Masoretic accent names.

Instead classify the relationship between the independently recovered Hebrew field and the Masoretic witness:

- one witness identity concentrated in one Hebrew region
- one witness identity spanning multiple Hebrew regions
- multiple witness identities dividing one Hebrew region
- partial correspondence
- transformation / re-encoding
- no detectable correspondence under this representation

This phase is descriptive and may motivate V39. It does not retroactively alter V38.

## Interpretation matrix

### Result 1 — Hebrew field validates; W1/W2 beat frequency and nulls, including unseen skeletons

Preferred statement:

> A structural field recovered without Masoretic information generalizes in Hebrew sequence and independently predicts part of the later Masoretic witness. This is consistent with the witness preserving or responding to structure already present in the Hebrew carrier.

It is not yet proof that the recovered field is the original historical mark system.

### Result 2 — Hebrew field validates; only W3 exact skeleton predicts marks

Preferred statement:

> The Masoretic correspondence is better explained by exact consonantal/lexical identity than by the present identity-blind structural field. The current recovery does not isolate a deeper mark-like system.

### Result 3 — Hebrew field validates; witness does not align

Preferred statement:

> A Hebrew-only sequential structural field exists under this representation, but the Masoretic witness does not substantially track it. The witness may encode a different dimension, preserve only a weak projection, or the recovered field may not be the relevant underlying system.

### Result 4 — Hebrew field itself does not generalize

Preferred statement:

> This V38 representation failed to recover a stable predictive structural field. No conclusion about an underlying authentic mark system follows from that failure.

## Epistemic ceiling

Even a strong V38 result does **not** by itself establish:

- that the recovered graph is the authentic/original historical mark system
- the historical date or provenance of such a system
- that the system causally generated the Hebrew text
- that the Masoretic tradition is a direct copy of it
- semantic meanings for recovered states
- theological claims from statistical structure alone

V38 is designed to establish source/carrier separation first: recover from Hebrew without the Masoretic witness, freeze, then test the witness against the recovered structure.