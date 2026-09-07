# V40 pre-outcome implementation freeze

**Experiment:** `mark:hebrew-context-field:v40`  
**Date:** 2026-09-07  
**Predecessor preregistration commit:** `9d1b7ab463708129a818ed884b1fc57a7e5f7fb7`  
**Status at this note:** no V40 Hebrew holdout score has been computed; `draft.canon_masoretic_marks` remains sealed for V40.

## One pre-outcome disambiguation

The preregistration specified standard deviation for the four-token left/right length windows but did not specify sample vs population SD. Before any V40 holdout outcome was opened, implementation was frozen to **population SD (`stddev_pop`)**, because each four-token side is the complete local context window rather than a sample from a larger side-window.

No other feature, holdout, target, smoothing, model, ablation, null, endpoint, or success-criterion change was made.

## Carrier / window counts

- consonantal tokens: 306,785
- V40 training tokens: 238,495
- V40 holdout tokens: 68,290
- eligible center-blind training windows: 237,215
- eligible center-blind holdout windows: 67,962
- intrinsic target types in full carrier: 739
- target alphabet: 64 most frequent training-window intrinsic states + `OTHER`
- training `OTHER` targets: 6,022

## Frozen training-only quintile cutpoints

Ties use the preregistered rule: lowest bin whose upper cutpoint is >= the value.

| # | Feature | q20 | q40 | q60 | q80 |
|---|---|---:|---:|---:|---:|
| 1 | left_mean_len | 3.25 | 3.75 | 4 | 4.5 |
| 2 | right_mean_len | 3.25 | 3.75 | 4 | 4.5 |
| 3 | left_sd_len | 0.707106781186548 | 0.82915619758885 | 1.11803398874989 | 1.29903810567666 |
| 4 | right_sd_len | 0.707106781186548 | 0.82915619758885 | 1.11803398874989 | 1.29903810567666 |
| 5 | left_final_rate | 0 | 0.25 | 0.25 | 0.5 |
| 6 | right_final_rate | 0 | 0.25 | 0.25 | 0.5 |
| 7 | left_mean_equality_complexity | 0.916666666666667 | 0.95 | 1 | 1 |
| 8 | right_mean_equality_complexity | 0.916666666666667 | 0.95 | 1 | 1 |
| 9 | left_mean_abs_len_delta | 0.666666666666667 | 1 | 1.66666666666667 | 2 |
| 10 | right_mean_abs_len_delta | 0.666666666666667 | 1 | 1.66666666666667 | 2 |

Duplicate cutpoints intentionally create empty discretization bins under the frozen tie rule rather than being repaired after inspection.

## Frozen feature alphabets

- F1: 5 bins
- F2: 5 bins
- F3: 5 bins
- F4: 5 bins
- F5: 4 observed bins (`1,2,4,5`)
- F6: 4 observed bins (`1,2,4,5`)
- F7: 3 observed bins (`1,2,3`)
- F8: 3 observed bins (`1,2,3`)
- F9: 5 bins
- F10: 5 bins
- F11: 4 categories (`1..4`)
- F12: 4 categories (`1..4`)
- F13: 5 categories (`0..4`, with 4 meaning 4+)
- F14: 2 categories (`0,1`)

## Frozen database count hashes

These hashes are over deterministic sorted string serializations of the training-derived tables.

- cutpoints MD5: `2bc7abda37633947c73a6a16b9589978`
- target inventory MD5: `2d731d49b74a650ec7cc593f49862775`
- target counts MD5: `705d2720eeb74fd19159038de8faf57f`
- Naive Bayes feature counts MD5: `141ff1140bb7308341b8eb3040dc3908`

## Frozen probability rule

For target `y` and feature `j`:

`P(value | y,j) = (count(y,j,value)+0.5) / (count(y)+0.5*K_j)`

where `K_j` is the frozen observed training alphabet size of feature j.

Target prior is the empirical training-window target frequency over the 65 target categories. C0 uses that prior directly. C1 uses all 14 features; C2 uses `1,3,5,7,9,11`; C3 uses `2,4,6,8,10,12`.

Posterior normalization is by log-sum-exp over all 65 targets.

## Custody rule from this point

After the commit containing this note, no V40 implementation choice above may change based on heldout Hebrew performance. Any modification becomes a separately labeled robustness test or V41. The Masoretic witness remains sealed until Phase A results are committed and a distinct witness-opening boundary is recorded.