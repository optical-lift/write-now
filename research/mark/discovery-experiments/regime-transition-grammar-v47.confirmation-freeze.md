# Mark V47 confirmation freeze

**Experiment:** `mark:regime-transition-grammar:v47`  
**Status:** CONFIRMATION RESIDUAL / 6 OF 7 RULES TRANSFERRED / BLIND SCORING CLOSED  
**Date:** 2026-09-18

## Frozen custody

- discovery freeze: `a8a00b372e80976365058bb567193fef4bddf9e6`
- validation freeze: `d61b7fef5a5d378f67878433fe4b9e7cacb4c1f4`
- confirmation protocol: `ea264646f0c86d1d0ba67bfc5450a61e5cfd17dd`
- confirmation implementation freeze: `6a70590b99758cec84b07503f39b78b4517e9042`
- confirmation geometry SHA-256: `812aba2f2e813f3d53961753e48d1ee510cad937817815c7dee36ba1f9cc2ad5`
- evaluator Git blob: `6490bf7f177572f3919f239aa5ea535433913bef`
- evaluator SHA-256: `f4a096c19394fbaa5add325dd2e9ed8fc530a75f43977ff92d07576a3be20e2a`
- raw confirmation result SHA-256: `fa0a3634be01deeaffa009f322bfa1127b7984edfc8075da7995ed8a92825313`

No refit was performed.

No provenance or Song semantic information entered confirmation scoring.

## Confirmation verdict

**CONFIRMATION_RESIDUAL**

Six of seven frozen pairwise persistence rules transfer on the final 53 unseen sources.

### Confirmed rules

| Rule | Context | Target | Sources | Confirmation P | Lift | Frozen predictive gain |
|---|---:|---:|---:|---:|---:|---:|
| local RG-001 -> neighborhood RG-001 | 79 | 65 | 15 | 0.8228 | 5.6023 | +1.9682 bits/edge |
| local RG-002 -> neighborhood RG-002 | 255 | 215 | 35 | 0.8431 | 1.7865 | +0.5527 |
| local RG-004 -> neighborhood RG-004 | 185 | 153 | 18 | 0.8270 | 2.5968 | +0.4758 |
| neighborhood RG-001 -> field RG-001 | 77 | 69 | 12 | 0.8961 | 5.9396 | +2.3516 |
| neighborhood RG-002 -> field RG-002 | 246 | 221 | 25 | 0.8984 | 1.7864 | +0.7494 |
| neighborhood RG-004 -> field RG-004 | 168 | 148 | 14 | 0.8810 | 2.9010 | +0.5573 |

### Rejected frozen rule

`neighborhood|RG-003->field|RG-003`

Confirmation:

- context occurrences: **23**
- target occurrences: **11**
- target sources: **5**
- conditional probability: **0.4782609**
- scale-pair parent marginal: **0.0367505**
- lift: **13.0137**
- discovery-frozen predictive gain over discovery-frozen scale-only baseline: **+1.2550 bits/edge**

It fails exactly one preregistered gate:

`conditional probability >= 0.50`

because 11/23 = 47.83%.

It passes the lift and frozen-predictive-gain gates.

This rule is therefore **REJECTED_ON_CONFIRMATION**, not softened to insufficient contrast or rescued post hoc.

## Overall status

The frozen overall confirmation gate required:

- zero rejected rules; and
- at least five transferred rules.

The second condition passes (6 transferred), but the first fails.

Therefore the experiment's formal confirmation status is `CONFIRMATION_RESIDUAL`, not `CONFIRMATION_SUPPORTED`.

## Full V47 blind result

At the current five-regime / four-scale representation:

1. **Six cross-scale persistence rules are robust through discovery, validation, and confirmation.**
2. The robust states are RG-001, RG-002, and RG-004 across both local -> neighborhood and neighborhood -> field.
3. RG-003 neighborhood -> field persistence was discovery-harvested and validation-transferred but fails the fixed confirmation probability gate.
4. No cross-regime transition survived the discovery harvest.
5. No length-3 or length-4 program adds matched-null-surviving information beyond the first-order model.
6. Field -> object persistence is partly underidentified under the frozen source×scale-preserving null because many source/object strata are singletons.

## Structural interpretation

The current evidence supports a **first-order persistence grammar for a stable subset of structural regimes**, not a universal five-state transition grammar.

RG-003 should be preserved as a boundary/residual state rather than forced into the stable-state result.

This conclusion is still semantic-free.

## Blind boundary closed

The V47 discovery/validation/confirmation scoring lifecycle is closed.

Any next experiment must preserve:

- the six confirmed rules;
- the RG-003 rejection;
- the absence of harvested higher-order programs;
- the field->object null-identifiability limitation.

These outcomes may motivate the next bridge but may not be retroactively changed.
