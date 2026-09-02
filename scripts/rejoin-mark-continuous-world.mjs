import crypto from "node:crypto";
import fs from "node:fs/promises";
import path from "node:path";

const worldPath=process.env.MARK_CONTINUOUS_WORLD ?? "artifacts/mark-ledger-world-v1/mark-blind-continuous-world-v1.json";
const contextPath=process.env.MARK_CONTEXT_LEDGER ?? "artifacts/mark-context-ledger-v1/mark-context-ledger-v1.json";
const outDir=process.env.MARK_CONTINUOUS_REJOIN_OUT ?? "artifacts/mark-continuous-rejoin-v1";
const world=JSON.parse(await fs.readFile(worldPath,"utf8")),context=JSON.parse(await fs.readFile(contextPath,"utf8"));
if(world.schema!=="mark_blind_continuous_world_model_v1")throw new Error(`unsupported continuous world ${world.schema}`);
if(context.schema!=="mark_context_ledger_v1")throw new Error(`unsupported context ledger ${context.schema}`);
const{blindSha256,...worldCore}=world;const computedWorld=crypto.createHash("sha256").update(JSON.stringify(worldCore)).digest("hex");if(!blindSha256||blindSha256!==computedWorld)throw new Error("continuous world SHA-256 verification failed");
const{sha256,...contextCore}=context;const computedContext=crypto.createHash("sha256").update(JSON.stringify(contextCore)).digest("hex");if(!sha256||sha256!==computedContext)throw new Error("context ledger SHA-256 verification failed");
const sourceByStable=new Map(context.sources.map(source=>[source.stableSourceId,source]));
const observationByStable=new Map(context.observations.map(observation=>[observation.stableObservationId,observation]));
function labelFor(id){
  const observation=observationByStable.get(id);const source=observation?sourceByStable.get(observation.stableSourceId):null;
  const box=source?.context?.boxLabel??source?.objectCategory??source?.context?.objectCategory??source?.context?.collectionType??"unlabeled";
  return{id,stableSourceId:observation?.stableSourceId??null,sourceId:source?.sourceId??null,boxLabel:box,sourceContext:source?.context??null,observationContext:observation?.context??null,sourceUrl:source?.sourceUrl??null,institution:source?.institution??null,objectId:source?.objectId??null};
}
const familyRows=world.families.map(family=>{const members=family.ids.map(labelFor),boxes=[...new Set(members.map(x=>x.boxLabel))].sort();return{familyId:family.familyId,size:family.size,distinctSourceObjects:family.distinctSourceObjects,distinctContextBoxes:boxes.length,contextBoxes:boxes,crossBox:boxes.length>=2,members};});
const primitiveRows=world.primitives.map(primitive=>{const members=primitive.ids.map(labelFor),boxes=[...new Set(members.map(x=>x.boxLabel))].sort();return{primitiveId:primitive.primitiveId,signature:primitive.signature,count:primitive.count,distinctSourceObjects:primitive.distinctSourceObjects,distinctContextBoxes:boxes.length,contextBoxes:boxes,crossBox:boxes.length>=2,members};});
const operationRows=world.operations.map(operation=>{const ids=[...new Set(operation.examples.flatMap(example=>[example.from,example.to]))],members=ids.map(labelFor),boxes=[...new Set(members.map(x=>x.boxLabel))].sort();return{operationId:operation.operationId,signature:operation.signature,edgeCount:operation.edgeCount,distinctSourceObjects:operation.distinctSourceObjects,distinctContextBoxes:boxes.length,contextBoxes:boxes,crossBox:boxes.length>=2,examples:operation.examples.map(example=>({from:labelFor(example.from),to:labelFor(example.to),neighborDistance:example.neighborDistance}))};});
const core={schema:"mark_continuous_world_context_rejoin_v1",generatedAt:new Date().toISOString(),sealedBlindWorldSha256:world.blindSha256,contextLedgerSha256:context.sha256,summary:{families:familyRows.length,crossBoxFamilies:familyRows.filter(x=>x.crossBox).length,primitives:primitiveRows.length,crossBoxPrimitives:primitiveRows.filter(x=>x.crossBox).length,operations:operationRows.length,crossBoxOperations:operationRows.filter(x=>x.crossBox).length},families:familyRows,primitives:primitiveRows,operations:operationRows};
const contextualSha256=crypto.createHash("sha256").update(JSON.stringify(core)).digest("hex"),artifact={...core,sha256:contextualSha256};
await fs.mkdir(outDir,{recursive:true});await fs.writeFile(path.join(outDir,"mark-continuous-world-context-rejoin-v1.json"),`${JSON.stringify(artifact,null,2)}\n`);
await fs.writeFile(path.join(outDir,"summary.txt"),[`schema=${artifact.schema}`,`sealed_blind_world_sha256=${world.blindSha256}`,`context_ledger_sha256=${context.sha256}`,`families=${artifact.summary.families}`,`cross_box_families=${artifact.summary.crossBoxFamilies}`,`primitives=${artifact.summary.primitives}`,`cross_box_primitives=${artifact.summary.crossBoxPrimitives}`,`operations=${artifact.summary.operations}`,`cross_box_operations=${artifact.summary.crossBoxOperations}`,`sha256=${contextualSha256}`].join("\n")+"\n");
console.log(`Continuous context rejoin: ${artifact.summary.crossBoxFamilies}/${artifact.summary.families} families cross prior boxes`);
