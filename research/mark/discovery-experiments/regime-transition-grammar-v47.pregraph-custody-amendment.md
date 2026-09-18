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
