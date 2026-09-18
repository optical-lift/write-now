# Mark V47 validation implementation freeze

**Experiment:** `mark:regime-transition-grammar:v47`  
**Status:** FROZEN BEFORE VALIDATION RULE OUTCOMES  
**Date:** 2026-09-18

## Upstream custody

- discovery freeze: `a8a00b372e80976365058bb567193fef4bddf9e6`
- validation protocol commit: `316f21e043dc43049dd04b32d0d87224348a361f`
- raw pairwise discovery SHA-256: `e0623f374b3d065288ded3c9c4a1ff636835632b8675ba081045bedfabe564ff`
- validation geometry SHA-256: `2108eec52d9f20539305a98a56d59dd0abc9d0904d3ca8f02fb541e221cefe40`
- fixed regime mapping SHA-256: `633918a3bad435adfdef9859a33743b9fa88bfcf59a79a4ed8a59b71141d9d90`

## Frozen evaluator

- evaluator commit: `af986e2e029ab352d0350baffd28fd8b81a8eb4f`
- evaluator Git blob: `1d01dcf1586ba257edd6cd526ad5d001e5ca579d`
- evaluator file SHA-256: `51ffa94f13f81b72059a1bb7aa0075cf3ad795688ce590ffd7a89e5da5ffe3c2`

The local execution file was rematerialized from the exact GitHub blob, verified with `git hash-object`, and bytecode-compiled before execution.

## Frozen transfer rules

The validator evaluates only the seven discovery-harvested rule keys.

No rule may be added or substituted.

Per-rule status:

- `INSUFFICIENT_CONTRAST` when context occurrences <10 or target support spans <3 validation sources;
- otherwise `TRANSFERRED` only if validation conditional probability >=0.50, validation lift >=1.25, and discovery-frozen rule probability yields positive binary log-loss gain over the discovery-frozen scale-pair baseline;
- otherwise `REJECTED_ON_VALIDATION`.

Overall `VALIDATION_SUPPORTED` requires:

- zero rejected rules;
- at least five transferred rules.

## Boundary

No validation transition result has been inspected before this freeze.

Confirmation remains sealed.
