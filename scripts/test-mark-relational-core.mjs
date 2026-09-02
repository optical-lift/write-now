import assert from "node:assert/strict";
import { canonicalRelationalFingerprint, relationGrammarPaths } from "./lib/mark-relational-core.mjs";

const sameProgramA={
  nodes:[{id:"a",kind:"ENDPOINT",x:10,y:10},{id:"b",kind:"JUNCTION",x:20,y:20},{id:"c",kind:"ENDPOINT",x:30,y:30}],
  edges:[{source:"a",target:"b",relation:"PATH"},{source:"b",target:"c",relation:"PATH"}],
};
const sameProgramB={
  nodes:[{id:"x",kind:"ENDPOINT",surfaceStyle:"curved"},{id:"z",kind:"ENDPOINT",surfaceStyle:"square"},{id:"y",kind:"JUNCTION",surfaceStyle:"thick"}],
  edges:[{source:"y",target:"z",relation:"PATH"},{source:"x",target:"y",relation:"PATH"}],
};
const rewiredProgram={
  nodes:[{id:"a",kind:"ENDPOINT"},{id:"b",kind:"JUNCTION"},{id:"c",kind:"ENDPOINT"}],
  edges:[{source:"a",target:"c",relation:"PATH"},{source:"b",target:"c",relation:"PATH"}],
};
assert.equal(canonicalRelationalFingerprint(sameProgramA),canonicalRelationalFingerprint(sameProgramB),"node identity and surface metadata must not change relational identity");
assert.notEqual(canonicalRelationalFingerprint(sameProgramA),canonicalRelationalFingerprint(rewiredProgram),"changing who is related to whom must change relational identity even when node/edge counts are preserved");
assert.equal(relationGrammarPaths(sameProgramA).length,1,"two-edge path must expose one maskable grammar context");
console.log("Mark v6 relational core contract passed");
