# Whole-Topology Condition Test v1 — Freeze

Status: **FROZEN**
Date: **2026-09-19**
Branch: `whole-topology-condition-v1`
Parent independent-discovery branch head: `c0b180bd941750f3f0685be11cd406ebc75bf3d1`

## Preregistered question

Does whole-source pair density explain the contradictory lace source by making local junction matching weaken or reverse?

Untouched test universe:

- 705 source objects
- nine hypothesis-generating sources excluded
- provenance sealed during scoring

Primary predictor:

`observedPairWeight / centers`

Primary outcome:

junction-conditioned matching lift relative to 64 source-local null worlds.

## Primary blind verdict

**NO_DENSITY_SUPPORT**

The predicted relation failed in the opposite direction.

### Junction-conditioned endpoint

- eligible sources: 703
- low-density decile: 71
- low-density median lift: 0.0316411
- remaining-source median lift: 0.0175740
- low minus rest: +0.0140671
- preregistered one-sided tail p: 1.0
- Spearman rho: -0.214860
- preregistered positive-rho p: 1.0

Therefore the candidate:

> lower pair density weakens/reverses the matching law

is rejected.

## Secondary diagnostic

The sign-only negative-lift rate was higher at low density:

- 22.54% low density
- 4.59% elsewhere
- permutation p ≈ 0.00005

This secondary signal does **not** rescue the failed primary hypothesis.

A later strict re-read using the original Independent Source Law Discovery all-64-null gate showed that most weak negative lifts were unresolved rather than genuine contradictions.

## Strict source-local law census

### Junction condition

Of 703 eligible untouched sources:

- 610 strict matches
- 8 strict reversals
- 85 unresolved

### Endpoint condition

Of 701 eligible sources:

- 634 strict matches
- 3 strict reversals
- 64 unresolved

### Joint

- 607 sources strictly match in both directions
- 1 source strictly reverses both
- 1 junction reversal has strict endpoint matching
- 6 junction reversals have unresolved endpoint state
- 2 endpoint reversals have unresolved junction state

The matching law is therefore broadly source-local across the untouched corpus while genuine contradictions remain rare.

## Post-freeze provenance diagnosis

The eight strict junction reversals span five Bavarian digitized pages and three Cleveland Museum objects.

No single institution or object category explains them.

Pair density also does not concentrate the strict reversals: only 2 of the 8 occur in the lowest-density decile.

## New structural omission

The compiler's null generator already preserves:

`(center kind, degree)`

while shuffling arm tokens.

But the learned grammar condition omits degree:

`CENTER:<kind>|ARM:<state>`

This means the current law aggregates distinct junction-degree states that the null model itself treats as non-interchangeable.

That is the next simplest candidate omitted condition.

## Frozen result custody

Successful workflow run:

`35442637903`

Blind-result artifact:

`whole-topology-condition-v1-blind-result`

Artifact ID:

`10585285454`

Internal result SHA-256:

`e6dec3618a6904499de5c0f764dc3ae6643c5062441160ed3f243b27c7911356`

Artifact result-file SHA-256:

`6e646b8e9b4784239e27611e34e3bcb7e81fb6bf7b71125fb0d8fecc47132660`

## Frozen Git blobs

- protocol: `8f441c81757613bf2e3f2fa2fe19b9d3cc236ca8`
- preregistration: `67a4a9a7589fc5d95172227763418e1df5780b7b`
- blind result summary: `9513929b1d453a66f7fe0f7798a7091e6b44f82a`
- blind result reference: `f12e4800bf7239f6403819e3ecfddc4f4e5d6c78`
- blind assessment: `2e5519ea6cb2cb659c3b3f3da9453de08df6b379`
- strict-law census: `5c035ad973902a98f79bf2655304f332cafdac63`
- post-freeze diagnosis: `f67e069b1ed32d37b5ff39af96b553a20569cb01`
- workflow: `fec73faaf72571708a815cf07df078ff240ab1c7`
- preparer: `361fa909a363f710e82eabe7c58427e16f02f092`
- metric extractor: `81661e03fe98f6e0fa5b6044c38e3268d809a10f`
- analyzer: `9329496442992f30719ce4842d78381e381ab072`

## Pre-freeze head

`a177086876e484e46bd87e79bbf8d5cabf15664d`

## Next checkpoint

**Degree-Conditioned Junction Law Test v1**

The next experiment must keep physical extraction, sources, null worlds and scoring custody fixed while adding only junction degree to the local grammar condition.
