import crypto from "node:crypto";
import fs from "node:fs/promises";
import path from "node:path";

const inputPath=process.env.MARK_OBSERVABLE_INPUT ?? "artifacts/mark-conveyor-input-v1/mark-observable-input-blind-v1.json";
const harvestRejoinPath=process.env.MARK_HARVEST_REJOIN ?? "artifacts/mark-harvest-rejoin-v1/mark-harvest-custody-rejoin-v1.json";
const outDir=process.env.MARK_OBSERVABLE_REJOIN_OUT ?? "artifacts/mark-conveyor-rejoin-v1";
const input=JSON.parse(await fs.readFile(inputPath,"utf8"));
const harvestRejoin=JSON.parse(await fs.readFile(harvestRejoinPath,"utf8"));
if(input.schema!=="mark_observable_input_blind_v1")throw new Error(`unsupported observable input ${input.schema}`);
if(harvestRejoin.schema!=="mark_harvest_custody_rejoin_v1")throw new Error(`unsupported harvest rejoin ${harvestRejoin.schema}`);
const{blindInputSha256,...inputCore}=input;
const computedInputSha=crypto.createHash("sha256").update(JSON.stringify(inputCore)).digest("hex");
if(!blindInputSha256||blindInputSha256!==computedInputSha)throw new Error("observable input SHA-256 verification failed");
if(input.sourceHarvestSha256!==harvestRejoin.sealedHarvestBlindSha256)throw new Error("harvest/proposal custody chain mismatch");
const sourceIds=new Set(input.sources.map(source=>source.sourceGroupId));
for(const source of harvestRejoin.sources)if(!sourceIds.has(source.sourceGroupId))throw new Error(`rejoin contains source absent from blind proposal field: ${source.sourceGroupId}`);
const observations=input.observations.map(observation=>({
  blindId:observation.id,
  observationId:`AUTO-${observation.id}`,
  sourceId:null,
  sourceGroupId:observation.sourceGroupId,
  region:observation.region,
  context:{proposalKind:observation.proposalKind??"unknown",proposalScale:observation.proposalScale??"unknown",machineProposed:true},
}));
const sourceByBlind=new Map(harvestRejoin.sources.map(source=>[source.sourceGroupId,source]));
for(const observation of observations){const source=sourceByBlind.get(observation.sourceGroupId);if(!source)throw new Error(`proposal references source absent from custody map: ${observation.sourceGroupId}`);observation.sourceId=source.sourceId;}
const rejoin={
  schema:"mark_observable_custody_rejoin_v1",
  sealedBlindInputSha256:input.blindInputSha256,
  packetSha256:harvestRejoin.manifestSha256,
  corpusId:harvestRejoin.harvestId,
  status:harvestRejoin.status,
  sources:harvestRejoin.sources,
  observations:observations.sort((a,b)=>a.blindId.localeCompare(b.blindId)),
};
await fs.mkdir(outDir,{recursive:true});
await fs.writeFile(path.join(outDir,"mark-observable-custody-rejoin-v1.json"),`${JSON.stringify(rejoin,null,2)}\n`);
console.log(`Bound ${observations.length} machine-proposed observations back to ${rejoin.sources.length} custody records without changing the blind input`);
