import crypto from "node:crypto";
import fs from "node:fs/promises";
import path from "node:path";

const inputPaths=(process.env.MARK_REJOIN_INPUTS ?? "artifacts/mark-conveyor-rejoin-v1/mark-observable-custody-rejoin-v1.json").split(",").map(x=>x.trim()).filter(Boolean);
const existingPath=process.env.MARK_EXISTING_CONTEXT_LEDGER ?? null;
const outDir=process.env.MARK_CONTEXT_LEDGER_OUT ?? "artifacts/mark-context-ledger-v1";
let prior=null;
if(existingPath){prior=JSON.parse(await fs.readFile(existingPath,"utf8"));if(prior.schema!=="mark_context_ledger_v1")throw new Error(`unsupported context ledger ${prior.schema}`);const{sha256,...core}=prior;const computed=crypto.createHash("sha256").update(JSON.stringify(core)).digest("hex");if(!sha256||sha256!==computed)throw new Error("existing context ledger SHA-256 verification failed");}
const sources=new Map((prior?.sources??[]).map(source=>[source.stableSourceId,source]));
const observations=new Map((prior?.observations??[]).map(observation=>[observation.stableObservationId,observation]));
const inputCustody=[];let sourceInsertions=0,sourceReplacements=0,observationInsertions=0,observationReplacements=0;
for(const inputPath of inputPaths){
  const rejoin=JSON.parse(await fs.readFile(inputPath,"utf8"));if(rejoin.schema!=="mark_observable_custody_rejoin_v1")throw new Error(`unsupported rejoin ${rejoin.schema} (${inputPath})`);
  inputCustody.push({corpusId:rejoin.corpusId,status:rejoin.status,sealedBlindInputSha256:rejoin.sealedBlindInputSha256,packetSha256:rejoin.packetSha256});
  for(const source of rejoin.sources){if(!source.stableSourceId)throw new Error(`source missing stableSourceId (${source.sourceId})`);if(sources.has(source.stableSourceId))sourceReplacements+=1;else sourceInsertions+=1;sources.set(source.stableSourceId,source);}
  for(const observation of rejoin.observations){if(!observation.stableObservationId)throw new Error(`observation missing stableObservationId (${observation.blindId})`);if(observations.has(observation.stableObservationId))observationReplacements+=1;else observationInsertions+=1;observations.set(observation.stableObservationId,observation);}
}
const core={
  schema:"mark_context_ledger_v1",generatedAt:new Date().toISOString(),parentContextLedgerSha256:prior?.sha256??null,inputCustody,
  summary:{sources:sources.size,observations:observations.size,sourceInsertions,sourceReplacements,observationInsertions,observationReplacements},
  sources:[...sources.values()].sort((a,b)=>a.stableSourceId.localeCompare(b.stableSourceId)),observations:[...observations.values()].sort((a,b)=>a.stableObservationId.localeCompare(b.stableObservationId)),
};
const sha256=crypto.createHash("sha256").update(JSON.stringify(core)).digest("hex"),ledger={...core,sha256};
await fs.mkdir(outDir,{recursive:true});await fs.writeFile(path.join(outDir,"mark-context-ledger-v1.json"),`${JSON.stringify(ledger,null,2)}\n`);
await fs.writeFile(path.join(outDir,"summary.txt"),[`schema=${ledger.schema}`,`sources=${ledger.summary.sources}`,`observations=${ledger.summary.observations}`,`source_insertions=${sourceInsertions}`,`source_replacements=${sourceReplacements}`,`observation_insertions=${observationInsertions}`,`observation_replacements=${observationReplacements}`,`sha256=${sha256}`].join("\n")+"\n");
console.log(`Context ledger: ${sources.size} source objects and ${observations.size} observations`);
