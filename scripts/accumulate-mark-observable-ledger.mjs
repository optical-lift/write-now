import crypto from "node:crypto";
import fs from "node:fs/promises";
import path from "node:path";

const inputPaths=(process.env.MARK_MEASUREMENT_INPUTS ?? "artifacts/mark-observable-discovery-v1/mark-observable-measurements-blind-v1.json").split(",").map(x=>x.trim()).filter(Boolean);
const existingPath=process.env.MARK_EXISTING_LEDGER ?? null;
const outDir=process.env.MARK_LEDGER_OUT ?? "artifacts/mark-observable-ledger-v1";

function verify(value,label){const{blindSha256,...core}=value;const computed=crypto.createHash("sha256").update(JSON.stringify(core)).digest("hex");if(!blindSha256||blindSha256!==computed)throw new Error(`${label} SHA-256 verification failed`);return blindSha256;}
function stableSourceId(record){if(!record.sourceContinuityToken)return record.sourceGroupId;return `CS${crypto.createHash("sha256").update(record.sourceContinuityToken).digest("hex").slice(0,18).toUpperCase()}`;}
function stableObservationId(record){if(!record.observationContinuityToken)return record.id;return `CO${crypto.createHash("sha256").update(record.observationContinuityToken).digest("hex").slice(0,18).toUpperCase()}`;}
function canonicalRecord(record){return{...record,id:stableObservationId(record),sourceGroupId:stableSourceId(record),originalBlindId:record.id,originalSourceGroupId:record.sourceGroupId};}

let prior=null;
if(existingPath){prior=JSON.parse(await fs.readFile(existingPath,"utf8"));if(prior.schema!=="mark_observable_measurement_ledger_blind_v1")throw new Error(`unsupported existing ledger ${prior.schema}`);verify(prior,"existing ledger");}
const recordById=new Map();
if(prior)for(const record of prior.records)recordById.set(record.id,record);
const inputMeasurementShas=[];let replacements=0,insertions=0;
for(const inputPath of inputPaths){
  const artifact=JSON.parse(await fs.readFile(inputPath,"utf8"));
  if(artifact.schema!=="mark_observable_measurements_blind_v1")throw new Error(`unsupported measurement artifact ${artifact.schema} (${inputPath})`);
  inputMeasurementShas.push(verify(artifact,inputPath));
  for(const raw of artifact.records){const record=canonicalRecord(raw);if(recordById.has(record.id))replacements+=1;else insertions+=1;recordById.set(record.id,record);}
}
const records=[...recordById.values()].sort((a,b)=>a.id.localeCompare(b.id));
if(records.length<4)throw new Error(`ledger requires at least four observations; got ${records.length}`);
const sourceObjects=new Set(records.map(r=>r.sourceGroupId));
const corpusKinds=new Set(records.map(r=>r.corpusKind).filter(Boolean));
const core={
  schema:"mark_observable_measurement_ledger_blind_v1",generatedAt:new Date().toISOString(),parentLedgerSha256:prior?.blindSha256??null,inputMeasurementShas:[...new Set(inputMeasurementShas)].sort(),
  continuityContract:{source:"stable source ID derived from private-key HMAC continuity token",observation:"stable observation ID derived from source continuity plus machine proposal region and scale",duplicatePolicy:"latest verified measurement replaces the same stable observation; no duplicate evidence weight"},
  corpus:{observations:records.length,sourceObjects:sourceObjects.size,insertions,replacements},records,
  limitations:["The ledger preserves structural measurements only; contextual source identity remains outside this artifact.","Replacing a repeated observation updates measurement state but never increases recurrence counts."],
};
const blindSha256=crypto.createHash("sha256").update(JSON.stringify(core)).digest("hex"),ledger={...core,blindSha256};
await fs.mkdir(outDir,{recursive:true});await fs.writeFile(path.join(outDir,"mark-observable-measurement-ledger-blind-v1.json"),`${JSON.stringify(ledger,null,2)}\n`);
await fs.writeFile(path.join(outDir,"summary.txt"),[`schema=${ledger.schema}`,`observations=${ledger.corpus.observations}`,`source_objects=${ledger.corpus.sourceObjects}`,`insertions=${insertions}`,`replacements=${replacements}`,`parent_ledger_sha256=${ledger.parentLedgerSha256??"none"}`,`blind_sha256=${blindSha256}`].join("\n")+"\n");
console.log(`Accumulated blind ledger: ${records.length} observations across ${sourceObjects.size} source objects (${insertions} new, ${replacements} replaced)`);
console.log(`Ledger SHA-256: ${blindSha256}`);
