# Mark V47 geometric transition-graph freeze

**Experiment:** `mark:regime-transition-grammar:v47`  
**Status:** GEOMETRY FROZEN / REGIME LABEL JOIN NOT YET OPENED  
**Date:** 2026-09-18

## Governing custody

- V47 preimplementation freeze: `010dcd5f2789399e5f74bed1c65140b497475756`
- pre-graph custody amendment: `41dce0c4bc3a5d63c4173b846ef1e83fb96fe370`
- corrected graph-builder commit: `1e66419577cbb8131aebfe515d418374d6ff217d`
- corrected graph-builder Git blob: `2a0bbcca01e75db9065428ab9151ed83885fb0f8`
- corrected graph-builder SHA-256: `f5274b2626c8cdc5a8dffac02182e7b65d7de37da5a1f54bdfcb982b85d75e42`

The locally executed builder was verified to hash to the exact committed Git blob before successful execution.

## Input custody

- blind input SHA-256: `4b64315a037b6ff6dfca3d99bade96e4c9c453f589e4beb0aa3dd5e0c2b92786`
- frozen V46 exclusion ID-list SHA-256: `1735dbadeb93241237af7af3efbe22a7b4a942a80cf94db301e43caaef827076`
- V47 source-pool SHA-256: `b9cc1accbca97380178d8408e7c4d38f9b18ad22c64a785c5f5a8e835c82c729`
- fixed V46 regime-assignment mapping SHA-256, bound but not consumed by parent selection: `633918a3bad435adfdef9859a33743b9fa88bfcf59a79a4ed8a59b71141d9d90`

The graph contains exactly the preregistered 9,244 untouched observations from 283 V47 sources.

## Frozen parent rule

Parent selection consumed only:

- opaque source/observation IDs;
- proposal scale;
- proposal kind;
- rectangular geometry.

It did **not** consume RG-001..RG-005.

For each child, the builder chose at most one same-source parent using the preregistered rule:

1. strictly greater proposal scale;
2. at least 95% child-area containment;
3. lowest eligible higher scale;
4. greatest containment;
5. smallest parent area;
6. lexicographically smallest parent observation ID.

## Geometry artifact custody

- all-lane geometry SHA-256: `e504325c7f176c9ffc325b324f75d5bc49ddd4d8a797de15552ba0728eb88476`
- exact local geometry-summary SHA-256: `406296ffbac35ed5462af5f26b38319fe6a1706c6e076227db953a96843c67cf`

Lane artifacts:

- discovery: `480c174ff503ad877f5d08cdf0dae78007750334873045bd0d8e91a9e8513f55`
- validation: `2108eec52d9f20539305a98a56d59dd0abc9d0904d3ca8f02fb541e221cefe40`
- confirmation: `812aba2f2e813f3d53961753e48d1ee510cad937817815c7dee36ba1f9cc2ad5`

## Coverage only — no regime outcomes

### Discovery
- observations: **5,305**
- sources / roots: **171**
- linked observations: **5,134**
- linked fraction: **96.78%**
- node-to-root chain length 1: 171
- length 2: 1,426
- length 3: 1,870
- length 4: 1,838

Scale-pair links:
- local -> neighborhood: 1,990
- neighborhood -> field: 1,716
- field -> object: 1,265
- neighborhood -> object: 139
- local -> object: 22
- local -> field: 2

### Validation
- observations: **2,332**
- sources / roots: **59**
- linked: **2,273**
- linked fraction: **97.47%**
- chain length 4 nodes: **802**

### Confirmation
- observations: **1,607**
- sources / roots: **53**
- linked: **1,554**
- linked fraction: **96.70%**
- chain length 4 nodes: **550**

The geometry is therefore sufficient to support pairwise transitions and substantial three-/four-level chain tests without changing the preregistered parent rule.

## Independent integrity audit

A separate post-build pass verified:

- exact frozen observation sets in every lane;
- exact frozen source sets in every lane;
- unique observation IDs;
- every linked parent belongs to the same source;
- every linked parent is strictly higher scale;
- every linked edge satisfies >=95% child containment;
- exactly one root per source;
- no regime field exists in the geometry rows.

## Custody repair record

The first builder invocation stopped before producing graph output because it included 190 previously excluded observations from the same source pool.

A narrow exclusion fix was documented before any graph result existed.

The first repository update intended to implement that fix did not alter the file bytes; this was also detected before rerun. The actual corrected implementation is the blob bound above.

Neither failed attempt produced a graph artifact or transition outcome.

## Boundary now open

The geometric graph is frozen.

The next permitted action is to join the already-frozen V46 assignment mapping to **discovery geometry only** and evaluate the preregistered pairwise transition rules and matched nulls.

Validation and confirmation transition labels remain unopened until discovery candidates are frozen.
