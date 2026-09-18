# V47 pre-graph custody amendment

**Experiment:** `mark:regime-transition-grammar:v47`  
**Date:** 2026-09-18  
**Status:** NARROW INPUT-CUSTODY REPAIR BEFORE ANY GRAPH OUTCOME

The first invocation of the committed graph builder stopped before emitting any graph artifact.

Observed error:

`V47 observation pool count drift: 9434`

Cause: selecting the 283 V46 validation+confirmation sources from the original 23,161-observation blind packet also reintroduced 190 observations belonging to the 435-observation V5/V45 exclusion set.

The preregistered V47 pool is 9,244 **untouched** observations. Therefore the graph builder must enforce the already-frozen V46 exclusion set before geometric parent selection.

Sole amendment:

- add the frozen V46 exclusion packet as an input;
- require exactly 435 excluded IDs;
- require canonical exclusion-ID SHA-256 `1735dbadeb93241237af7af3efbe22a7b4a942a80cf94db301e43caaef827076`;
- remove those IDs before V47 pool/partition verification.

No parent edge, graph coverage count, scale-pair count, transition count, regime label, validation outcome, or confirmation outcome was emitted or inspected before this amendment.

Failed-run stderr SHA-256:

`aa6a05c2dff5515260953ade2642f5bd706db6515203e5260095452d07ea92cb`


## Implementation correction

The first repository update intended to apply the exclusion repair but did not alter the builder bytes. This was detected before rerunning the graph builder and before any graph artifact existed.

The actual corrected builder commit is:

`1e66419577cbb8131aebfe515d418374d6ff217d`

Corrected builder Git blob:

`2a0bbcca01e75db9065428ab9151ed83885fb0f8`

Corrected builder file SHA-256:

`f5274b2626c8cdc5a8dffac02182e7b65d7de37da5a1f54bdfcb982b85d75e42`

The corrected local execution file was verified to hash to that exact Git blob before the successful graph build.
