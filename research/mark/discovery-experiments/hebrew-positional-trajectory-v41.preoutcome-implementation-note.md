# V41 pre-outcome implementation freeze

**Experiment:** `mark:hebrew-positional-trajectory:v41`  
**Date:** 2026-09-07  
**Preregistration commit:** `66079e41e9ff7c036957302630aadcf3c4906069`  
**Status:** no V41 Hebrew holdout metric has been computed; V41 has not queried the Masoretic witness.

## Frozen carrier counts

- eligible training center-blind windows: 233,929
- eligible heldout center-blind windows: 71,248
- target alphabet: 64 most frequent training intrinsic targets + `OTHER`

## Frozen P1 ordered feature coding

P1 uses the 38 categorical observations preregistered in V41:

- 24 position-specific neighbor microfeatures (L/R/F at offsets -4,-3,-2,-1,+1,+2,+3,+4)
- 12 position-specific within-side trajectory features (DL/DR over the three left and three right transitions)
- 2 cross-gap features (Xshared, Xboundary)

Dirichlet alpha is 0.5 per categorical emission. Empirical target prior is frozen from training windows.

## Frozen P2 position-erased coding

P2 uses the exact same raw observations but pools positional identity within each family:

- 8 L observations use one pooled L emission table
- 8 R observations use one pooled R emission table
- 8 F observations use one pooled F emission table
- 6 DL observations use one pooled DL emission table
- 6 DR observations use one pooled DR emission table
- Xshared and Xboundary remain unique

No observation is removed relative to P1; only positional identity is erased.

P3 and P4 use the preregistered left/right subsets of the already frozen P1 emissions.

## Deterministic training-table hashes

- target inventory MD5: `f5e92b6e38bdabb3d43fbecb5d4395c6`
- target counts MD5: `2b2a7e9ff51cf7d2128a0c6450e597b9`
- P1 ordered feature counts MD5: `5e06e59812840b0fff32793fec11a63a`
- P2 position-erased counts MD5: `ab82f24694b1477f1b265f470c2728ca`

## Custody

After the commit containing this note, no V41 feature coding, smoothing, target inventory, holdout, model definition, or endpoint may change based on Hebrew holdout performance. Any such change is V42 or a separately labeled robustness test. The Masoretic witness remains sealed until Phase-A results and nulls are committed.