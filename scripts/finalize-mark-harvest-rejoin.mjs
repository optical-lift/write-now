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
const stableSourceId=(continuityToken)=>`CS${crypto.createHash("sha256").update(continuityToken).digest("hex").slice(0,18).toUpperCase()}`;
const stableObservationId=(continuityToken)=>`CO${crypto.createHash("sha256").update(continuityToken).digest("hex").slice(0,18).toUpperCase()}`;
const regionKey=(region)=>`${Math.round(region.x)},${Math.round(region.y)},${Math.round(region.width)},${Math.round(region.height)}`;
const sourceIds=new Set(input.sources.map(source=>source.sourceGroupId));
for(const source of harvestRejoin.sources)if(!sourceIds.has(source.sourceGroupId))throw new Error(`rejoin contains source absent from blind proposal field: ${source.sourceGroupId}`);
const sourceByBlind=new Map(harvestRejoin.sources.map(source=>[source.sourceGroupId,source]));
const observations=input.observations.map(observation=>{
  const source=sourceByBlind.get(observation.sourceGroupId);if(!source)throw new Error(`proposal references source absent from custody map: ${observation.sourceGroupId}`);
  const proposalKind=observation.proposalKind??"manual",continuity=crypto.createHash("sha256").update(`${source.continuityToken}|${proposalKind}|${regionKey(observation.region)}`).digest("hex");
  return {
    blindId:observation.id,stableObservationId:stableObservationId(continuity),observationContinuityToken:continuity,observationId:`AUTO-${observation.id}`,
    sourceId:source.sourceId,sourceGroupId:observation.sourceGroupId,stableSourceId:stableSourceId(source.continuityToken),region:observation.region,
    context:{proposalKind,proposalScale:observation.proposalScale??"unknown",machineProposed:true},
  };
});
const sources=harvestRejoin.sources.map(source=>({...source,stableSourceId:stableSourceId(source.continuityToken)}));
const rejoin={
  schema:"mark_observable_custody_rejoin_v1",sealedBlindInputSha256:input.blindInputSha256,packetSha256:harvestRejoin.manifestSha256,corpusId:harvestRejoin.harvestId,status:harvestRejoin.status,
  sources:sources.sort((a,b)=>a.stableSourceId.localeCompare(b.stableSourceId)),observations:observations.sort((a,b)=>a.stableObservationId.localeCompare(b.stableObservationId)),
};
await fs.mkdir(outDir,{recursive:true});
await fs.writeFile(path.join(outDir,"mark-observable-custody-rejoin-v1.json"),`${JSON.stringify(rejoin,null,2)}\n`);
console.log(`Bound ${observations.length} machine-proposed observations back to ${rejoin.sources.length} custody records without changing the blind input`);
