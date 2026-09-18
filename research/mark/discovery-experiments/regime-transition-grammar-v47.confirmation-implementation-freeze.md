# Mark V47 confirmation implementation freeze

**Experiment:** `mark:regime-transition-grammar:v47`  
**Status:** FROZEN BEFORE CONFIRMATION RULE OUTCOMES  
**Date:** 2026-09-18

## Upstream custody

- discovery freeze: `a8a00b372e80976365058bb567193fef4bddf9e6`
- validation freeze: `d61b7fef5a5d378f67878433fe4b9e7cacb4c1f4`
- confirmation protocol commit: `ea264646f0c86d1d0ba67bfc5450a61e5cfd17dd`
- raw pairwise discovery SHA-256: `e0623f374b3d065288ded3c9c4a1ff636835632b8675ba081045bedfabe564ff`
- confirmation geometry SHA-256: `812aba2f2e813f3d53961753e48d1ee510cad937817815c7dee36ba1f9cc2ad5`
- fixed regime mapping SHA-256: `633918a3bad435adfdef9859a33743b9fa88bfcf59a79a4ed8a59b71141d9d90`

## Frozen evaluator

- evaluator commit: `3c6fe96be858337d0b69badc7391ceccbba05662`
- evaluator Git blob: `6490bf7f177572f3919f239aa5ea535433913bef`
- evaluator file SHA-256: `f4a096c19394fbaa5add325dd2e9ed8fc530a75f43977ff92d07576a3be20e2a`

The local execution file was deterministically derived from the already-frozen validation evaluator by changing only the lane-specific geometry identity, row/source/edge counts, output/status field names, and rejection label. Its Git object hash exactly matches the committed GitHub blob, and it bytecode-compiles before execution.

## Frozen confirmation rules

Exactly the same seven discovery-frozen transition keys are evaluated.

Per-rule criteria are unchanged from validation:

- `INSUFFICIENT_CONTRAST` if context occurrences <10 or target support spans <3 confirmation sources;
- otherwise `TRANSFERRED` only if conditional probability >=0.50, lift >=1.25, and the discovery-frozen rule probability yields positive binary log-loss gain over the discovery-frozen scale-only baseline;
- otherwise `REJECTED_ON_CONFIRMATION`.

Overall `CONFIRMATION_SUPPORTED` requires:

- zero rejected rules;
- at least five transferred rules.

No validation statistic is used to fit or modify any confirmation rule.

## Boundary

No confirmation transition outcome has been inspected before this freeze.

Provenance and Song semantics remain excluded from confirmation scoring.
