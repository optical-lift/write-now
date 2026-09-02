import crypto from "node:crypto";
import fs from "node:fs/promises";
import path from "node:path";

const worldPath=process.env.MARK_WORLD ?? "artifacts/mark-world-v1/mark-blind-world-model-full-v1.json";
const measurementsPath=process.env.MARK_OBSERVABLE_MEASUREMENTS ?? "artifacts/mark-observable-discovery-v1/mark-observable-measurements-blind-v1.json";
const rejoinPath=process.env.MARK_OBSERVABLE_REJOIN ?? "artifacts/mark-observable-rejoin-v1/mark-observable-custody-rejoin-v1.json";
const outDir=process.env.MARK_WORLD_REJOIN_OUT ?? "artifacts/mark-world-rejoin-v1";
const world=JSON.parse(await fs.readFile(worldPath,"utf8")),measurements=JSON.parse(await fs.readFile(measurementsPath,"utf8")),rejoin=JSON.parse(await fs.readFile(rejoinPath,"utf8"));
for(const[name,value]of[["world",world],["measurements",measurements]]){const{blindSha256,...rest}=value;const computed=crypto.createHash("sha256").update(JSON.stringify(rest)).digest("hex");if(!blindSha256||blindSha256!==computed)throw new Error(`${name} SHA-256 verification failed`);}
if(world.sourceMeasurementsSha256!==measurements.blindSha256)throw new Error("world/measurement custody chain mismatch");
if(rejoin.sealedBlindInputSha256!==measurements.blindInputSha256)throw new Error("rejoin/blind input custody chain mismatch");

const sourceByBlind=new Map(rejoin.sources.map(source=>[source.sourceGroupId,source]));
const observationByBlind=new Map(rejoin.observations.map(observation=>[observation.blindId,observation]));
const measurementById=new Map(measurements.records.map(record=>[record.id,record]));
function contextLabel(id){
  const measurement=measurementById.get(id),observation=observationByBlind.get(id),source=measurement?sourceByBlind.get(measurement.sourceGroupId):null;
  const box=source?.context?.boxLabel??source?.objectCategory??source?.context?.objectCategory??"unlabeled";
  return {id,sourceGroupId:measurement?.sourceGroupId??null,boxLabel:box,sourceId:source?.sourceId??null,observationId:observation?.observationId??null,sourceContext:source?.context??null,observationContext:observation?.context??null};
}
const families=world.families.map(family=>{const members=family.ids.map(contextLabel),boxes=[...new Set(members.map(member=>member.boxLabel))].sort();return{familyId:family.familyId,size:family.size,distinctSourceObjects:family.distinctSourceObjects,distinctContextBoxes:boxes.length,contextBoxes:boxes,crossBox:boxes.length>=2,members};});
const primitives=world.primitives.map(primitive=>{const members=primitive.ids.map(contextLabel),boxes=[...new Set(members.map(member=>member.boxLabel))].sort();return{primitiveId:primitive.primitiveId,signature:primitive.signature,count:primitive.count,distinctSourceObjects:primitive.distinctSourceObjects,distinctContextBoxes:boxes.length,contextBoxes:boxes,crossBox:boxes.length>=2};});
const operations=world.operations.map(operation=>{const ids=[...new Set(operation.examples.flatMap(example=>[example.from,example.to]))],members=ids.map(contextLabel),boxes=[...new Set(members.map(member=>member.boxLabel))].sort();return{operationId:operation.operationId,signature:operation.signature,edgeCount:operation.edgeCount,distinctSourceObjects:operation.distinctSourceObjects,distinctContextBoxes:boxes.length,contextBoxes:boxes,crossBox:boxes.length>=2,examples:operation.examples.map(example=>({from:contextLabel(example.from),to:contextLabel(example.to),neighborDistance:example.neighborDistance}))};});
const contextual={schema:"mark_world_context_rejoin_v1",generatedAt:new Date().toISOString(),sealedBlindWorldSha256:world.blindSha256,corpusId:rejoin.corpusId,status:rejoin.status,summary:{families:families.length,crossBoxFamilies:families.filter(x=>x.crossBox).length,primitives:primitives.length,crossBoxPrimitives:primitives.filter(x=>x.crossBox).length,operations:operations.length,crossBoxOperations:operations.filter(x=>x.crossBox).length},families,primitives,operations};
await fs.mkdir(outDir,{recursive:true});await fs.writeFile(path.join(outDir,"mark-world-context-rejoin-v1.json"),`${JSON.stringify(contextual,null,2)}\n`);
await fs.writeFile(path.join(outDir,"summary.txt"),[`schema=${contextual.schema}`,`sealed_blind_world_sha256=${world.blindSha256}`,`families=${contextual.summary.families}`,`cross_box_families=${contextual.summary.crossBoxFamilies}`,`primitives=${contextual.summary.primitives}`,`cross_box_primitives=${contextual.summary.crossBoxPrimitives}`,`operations=${contextual.summary.operations}`,`cross_box_operations=${contextual.summary.crossBoxOperations}`].join("\n")+"\n");
console.log(`Rejoined context after freeze: ${contextual.summary.crossBoxFamilies}/${contextual.summary.families} families cross prior boxes`);
