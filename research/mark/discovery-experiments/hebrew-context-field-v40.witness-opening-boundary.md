# V40 witness-opening boundary

**Experiment:** `mark:hebrew-context-field:v40`  
**Date:** 2026-09-07

This commit is the explicit boundary after which V40 Phase B may read the Masoretic witness.

Frozen upstream custody:

- preregistration: `9d1b7ab463708129a818ed884b1fc57a7e5f7fb7`
- pre-outcome implementation freeze: `b7ad6a8843dcf2cd0282b25890b478f00560924b`
- null-index freeze: `26e4926ef08ba5bc3ff8706c3b3194ac20fd6d49`
- Phase-A Hebrew-only result: `369b2078e2587af7db88c3703c0a4277be41b083`

At the Phase-A result boundary, `draft.canon_masoretic_marks` had not been queried for V40.

From this commit onward, Phase B may read Masoretic cantillation codepoints only as an external witness under the already-preregistered M0–M4 rules. No V40 Hebrew representation, feature, bin, target, holdout, success criterion, or Phase-A verdict may change based on Phase-B results.