# V43 Phase-A pre-execution freeze

**Status:** frozen before V43 operator induction or outcome inspection  
**Experiment:** `mark:song-composition-harvest:v43`  
**Implementation commit:** `49932d0777f4d5bd5d966307a20e52ee2a131d03`  
**Execution-config commit:** `acaca3c17e289e7d8654cd4e3ea8035ae1c98a1a`  
**Execution-config blob:** `2ad7eb3f4f152c651e11b79c3f2eb94f7d92d014`

## Integrity statement

No V43 operator model has been induced, no V43 candidate has been scored, and no holdout/control outcome has been inspected before this freeze.

The only corpus operation performed before this freeze was a custody-only split inventory over the already-frozen V5 projector rows so the exact eligible lane counts, distinct-source counts, and lane byte hashes could be recorded. No Mark feature, operator, candidate law, prediction, or success metric was computed by that inventory.

Song semantics remain unopened. No file from `optical-lift/song-ontology` has been read. No translation, named glyph meaning, Song family name, or semantic dictionary has been used.

## Frozen input

Phase A consumes only the already-frozen V5 packet:

- GitHub Actions run: `33807154154`
- artifact: `mark-critical-edge-correspondence-v5-frozen`
- artifact ID: `9913458910`
- downloaded ZIP SHA-256: `dfa99eb8b858efd599203b05e610ad950dc376cd0a2715ead1b8f79cd4adf75f`
- edge-pair manifest canonical SHA-256: `75e28e9e45bcc2245015b1d6a23000f9589b5b9f4a0104dad4e792d1cd445a36`
- critical-edge world canonical SHA-256: `8061fa13da32f869c9a001432a659a2a7647cfefa876175df7d21b5d9d138aea`
- projector rows SHA-256: `e3dadcd6daf2921433c856458a651fcbfea6569852c67954d45d704699d71e2e`
- pair-eligible observations: **433**

Exact eligible lanes:

| Lane | Observations | Distinct sources | Lane JSONL SHA-256 |
| --- | ---: | ---: | --- |
| train | 84 | 43 | `d57b7f9049674a0ac38c4ada3690ef1cfd8edd45cced6b3775e5f7689d257931` |
| holdout | 230 | 154 | `89fb772b88b9c444e4fa5414f60c7e6a85f1373e71d2864790e75c5de2a6363a` |
| control | 119 | 63 | `af7f21dca4984a5be11a0023ba21f71b4404721a441634950387f67e9d59cbbf` |

Only train may induce state/operator vocabularies, kernels, or candidate laws. Holdout and control are evaluation-only.

## Frozen implementation

V43 reuses the already-tested V9 anonymous operator machinery narrowly, rather than redesigning it.

- V43 runner blob: `3ab1611b86e26593cee58e46798d1e0829387ec7`
- V9 core blob: `b924ec8943e2afd7c53c01868ee8bea675574476`
- V9 custody splitter blob: `b3250f7b8899bb2ec2a74c40c6a78879050de21f`
- V9 inducer blob: `e471eb366e4485b3e16334295394483ee0e62f3b`
- V9 evaluator blob: `02efc627bf2d0d9db6e6ca71c6ff1780c7ba6b6c`
- V9 invariant test blob: `59935136d136b64b95d03e2bf415f9545fe75735`
- primary V9 reference protocol blob: `a91e8280832ecad75679120d28ff8e64bd9081f2`
- topology-only surface-invariance protocol blob: `c99cf9aced9d14b1f6b0dd388ba2fba13afe9613`

The topology-only protocol changes exactly one scientific selector from the V9 reference: `lawDiscovery.variant` is `topology` instead of `lengthAware`. Thresholds, lanes, candidate-law definitions, support requirements, and transfer criteria remain unchanged.

## Frozen measurable field

The V5 projector can physically expose, without reopening pixels or semantics:

- center kind and arity;
- center-to-center adjacency/connectivity;
- parallel path multiplicity and self-loops;
- endpoint/junction port structure;
- relative local geometry available in the projected path evidence;
- graph topology sufficient for ordered local transit and four-center composition;
- formal operator reversal;
- train/holdout/control source separation and exact physical observation provenance.

Recursive nesting/embedding is not faithfully represented by this contracted edge world. A direct split/join mutation harvest would require reopening V5 correspondence-pair machinery and its role-pair context rather than pretending the current anonymous path representation supplies that edit. Neither is forced into Phase A.

## Frozen Phase-A candidate construction

Exactly five serious candidate rule families will be attempted:

1. `CR-001` — factorized sequential operator composition.
2. `CR-002` — operator idempotence under repetition.
3. `CR-003` — ordered-pair cancellation toward input boundary state.
4. `CR-004` — order sensitivity / noncommutativity.
5. `CR-005` — input-conditional composition.

The exact definitions and residual limits are frozen in `song-composition-harvest-v43.phase-a.execution-freeze.json`. No additional candidate may be added after outcomes are visible. A failed candidate remains in the final packet.

## Frozen tests and controls

Each candidate must report T1–T7 as applicable:

- multiple positive physical witnesses;
- near-counterexamples;
- direct ablation;
- surface-invariance control;
- matched control;
- held-out transfer;
- downstream consequence preservation where applicable.

The matched controls are already part of the frozen operator design: input-only, one-sided A/B, direct pair, one-step A, expected identity return, swapped operator order, and collapsed incoming-state consequence.

No stochastic null is used in Phase A. The random-null iteration count is frozen at zero and the unused seed is `mark-v43-phase-a-null-v1-unused`; this prevents a post-outcome choice to introduce or tune a random null.

## Stop conditions

Phase A stops rather than redesigning if the frozen runner cannot execute against these exact inputs, if any parent hash drifts, if holdout changes the induced model, if a candidate needs a new physical projection/source, or if semantics would be required to interpret a result.

The only permitted edit after this freeze and before execution is the mechanical replacement of `preexecution_freeze_sha: "PENDING"` in the execution config with the commit SHA that creates this file. No runner, protocol, threshold, candidate definition, input, or control may change before execution.
