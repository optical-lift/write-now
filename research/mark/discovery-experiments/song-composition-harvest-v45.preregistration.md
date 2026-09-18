# Mark V45 preregistration — transit-cache execution amendment

**Experiment ID:** `mark:song-composition-harvest:v45`  
**Parent failure:** V44 commit `fc536f7e541e23676a90ec89af7dde7f3267bab9`  
**Status:** implementation amendment only; no V45 holdout outcome inspected

## Scientific inheritance

V45 inherits the complete V43/V44 Phase-A scientific design unchanged: exact V5 packet, train/holdout/control lanes, anonymous state and operator definitions, composition equation, smoothing, CR-001 through CR-005, matched controls, topology invariance, thresholds, and all semantic prohibitions.

## Implementation amendments inherited from V44

V45 retains the exact 8,192-entry mapped-key LRU for `pcomp(A,B,i,o)`. The composition equation and summation order remain unchanged.

## Sole new V45 amendment

The inherited V9 core memoizes every `operator_occurrence(incoming, center, outgoing)` inside the current graph object. V45 removes only that memoization.

For every call, V45 recomputes the same:

- operator descriptor;
- operator ID;
- reverse operator ID;
- input interface state;
- output interface state.

No field, hash preimage, state mapping, path rule, ordering rule, or threshold changes. The graph's operator cache remains present but unused.

## Mandatory pre-holdout equivalence

Before V45 may evaluate holdout:

1. V43/V44/V45 probability functions must agree exactly on the finite implementation fixture.
2. V44 and V45 operator occurrences must agree exactly on the finite graph fixture.
3. V45's composition cache must remain bounded at 8,192 entries.
4. The inherited V9 invariant tests must pass.
5. After the exact V5 train split is made, both V44 and V45 inducers must be run on the same train lane for both the primary and topology-control protocols.
6. The complete serialized `operator-algebra-freeze.json` files must match byte-for-byte for V44 and V45 before holdout opens.

If any gate fails, V45 stops with no verdict.

## Phase-A closure

If execution completes, commit the V45 Phase-A candidates, result, and freeze before opening Song semantics. Failed candidates remain evidence.
