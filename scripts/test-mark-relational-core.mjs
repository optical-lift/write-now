import assert from "node:assert/strict";
import { canonicalRelationalFingerprint, relationGrammarPaths } from "./lib/mark-relational-core.mjs";

const sameProgramA={
  nodes:[{id:"a",kind:"ENDPOINT",x:10,y:10},{id:"b",kind:"JUNCTION",x:20,y:20},{id:"c",kind:"JUNCTION",x:30,y:20},{id:"d",kind:"ENDPOINT",x:40,y:10}],
  edges:[
    {source:"a",target:"b",relation:"PATH"},
    {source:"b",target:"c",relation:"PATH"},
    {source:"c",target:"d",relation:"PATH"},
  ],
};
const sameProgramDifferentIdsAndSurface={
  nodes:[{id:"w",kind:"ENDPOINT",surfaceStyle:"square"},{id:"x",kind:"JUNCTION",surfaceStyle:"curved"},{id:"y",kind:"JUNCTION",surfaceStyle:"thick"},{id:"z",kind:"ENDPOINT",surfaceStyle:"thin"}],
  edges:[
    {source:"w",target:"x",relation:"PATH"},
    {source:"x",target:"y",relation:"PATH"},
    {source:"y",target:"z",relation:"PATH"},
  ],
};
const sameProgramAllPathDirectionsReversed={
  nodes:sameProgramA.nodes.map(node=>({...node})),
  edges:sameProgramA.edges.map(edge=>({source:edge.target,target:edge.source,relation:edge.relation})),
};
const rewiredSameInventory={
  nodes:sameProgramA.nodes.map(({x:_x,y:_y,...node})=>node),
  edges:[
    {source:"b",target:"a",relation:"PATH"},
    {source:"b",target:"c",relation:"PATH"},
    {source:"b",target:"d",relation:"PATH"},
  ],
};

assert.equal(
  canonicalRelationalFingerprint(sameProgramA),
  canonicalRelationalFingerprint(sameProgramDifferentIdsAndSurface),
  "node identity and surface metadata must not change relational identity",
);
assert.equal(
  canonicalRelationalFingerprint(sameProgramA),
  canonicalRelationalFingerprint(sameProgramAllPathDirectionsReversed),
  "PATH traversal direction is a raster-walk accident and must not change relational identity",
);
assert.deepEqual(
  relationGrammarPaths(sameProgramA).map(row=>row.signature),
  relationGrammarPaths(sameProgramAllPathDirectionsReversed).map(row=>row.signature),
  "masked relational grammar must be invariant to PATH traversal direction",
);
assert.notEqual(
  canonicalRelationalFingerprint(sameProgramA),
  canonicalRelationalFingerprint(rewiredSameInventory),
  "changing who is related to whom must change relational identity even when node and PATH inventories are preserved",
);
assert.ok(relationGrammarPaths(sameProgramA).length>=2,"multi-edge relational structure must expose maskable grammar contexts");
console.log("Mark v6 relational core contract passed");
