# Mark V47 discovery closure

**Experiment:** `mark:regime-transition-grammar:v47`  
**Status:** DISCOVERY CLOSED / 7 PAIRWISE RULES FROZEN / 0 HIGHER-ORDER PROGRAMS / VALIDATION MAY OPEN  
**Date:** 2026-09-18

## Pairwise result

Pairwise discovery is frozen at:

- pairwise discovery freeze: `eb9996d49a51ad03284daa5b49d1a4fb744690ad`
- raw pairwise result SHA-256: `e0623f374b3d065288ded3c9c4a1ff636835632b8675ba081045bedfabe564ff`

Seven exact rule keys are frozen for validation:

1. `local|RG-001->neighborhood|RG-001`
2. `neighborhood|RG-001->field|RG-001`
3. `local|RG-002->neighborhood|RG-002`
4. `neighborhood|RG-002->field|RG-002`
5. `neighborhood|RG-003->field|RG-003`
6. `local|RG-004->neighborhood|RG-004`
7. `neighborhood|RG-004->field|RG-004`

No rule may be added, removed, or replaced after validation opens.

## Higher-order result

- higher-order implementation freeze: `9d8688f0ce376a59d068708b7a5db9404ef87a15`
- exact runner Git blob: `a210640547855fee0762997a6f8f39cbcb950b6a`
- raw higher-order result SHA-256: `38366c254af010eee3dad557f02f76d42527481c9e416983db22136077e94b12`

### Length 3
- testable chains: **3,708**
- observed history contexts: **56**
- harvested programs: **0**

### Length 4
- testable chains: **1,838**
- observed history contexts: **57**
- harvested programs: **0**

Several longer contexts improve held-in prediction over the first-order model numerically, but none with the required support also exceeds its matched source×scale-preserving null Q99.

Examples:

- local RG-001 > neighborhood RG-002 -> field RG-002: +0.7247 bits over first-order, but null Q99 = 1.1418;
- neighborhood RG-004 > field RG-002 -> object RG-002: +0.5949 bits, null Q99 = 0.8575;
- local RG-002 > neighborhood RG-004 -> field RG-004: +0.3501 bits, null Q99 = 0.4474.

This result supports a **first-order Markov-like transition description at the current five-regime / four-scale representation**.

It does not prove that the underlying physical system is intrinsically first-order. Higher-order structure may exist in observables that V46 did not encode.

## Discovery verdict

At the current V46 regime resolution:

- stable cross-scale persistence rules exist;
- those rules are strongest from local -> neighborhood and neighborhood -> field;
- no cross-regime jump rule survived discovery;
- longer RG histories do not add matched-null-surviving predictive information beyond the immediate prior regime.

## Validation boundary

Validation may now open for the seven frozen pairwise rules only.

No higher-order program is eligible for validation.

Confirmation remains sealed.
