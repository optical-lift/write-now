import crypto from "node:crypto";
import fs from "node:fs/promises";
import path from "node:path";
import sharp from "sharp";
import { measureObservable } from "./lib/mark-image-observable.mjs";

const inputPath=process.env.MARK_OBSERVABLE_INPUT ?? "artifacts/mark-conveyor-input-v1/mark-observable-input-blind-v1.json";
const trainPath=process.env.MARK_OBSERVABLE_TRAIN ?? "artifacts/mark-observable-discovery-v1/mark-observable-train-blind-v1.json";
const outDir=process.env.MARK_SPATIAL_NULL_OUT ?? "artifacts/mark-spatial-null-discovery-v1";
const input=JSON.parse(await fs.readFile(inputPath,"utf8"));
const train=JSON.parse(await fs.readFile(trainPath,"utf8"));
if(input.schema!=="mark_observable_input_blind_v1")throw new Error(`unsupported blind input ${input.schema}`);
if(train.schema!=="mark_observable_feature_partition_blind_v1"||train.partition!=="train")throw new Error(`spatial null requires sealed train partition; got ${train.schema}/${train.partition}`);
{
  const{blindInputSha256,...rest}=input;const computed=crypto.createHash("sha256").update(JSON.stringify(rest)).digest("hex");if(!blindInputSha256||blindInputSha256!==computed)throw new Error("blind input SHA-256 verification failed");
}
{
  const{blindSha256,...rest}=train;const computed=crypto.createHash("sha256").update(JSON.stringify(rest)).digest("hex");if(!blindSha256||blindSha256!==computed)throw new Error("train partition SHA-256 verification failed");
}

function seeded(seedText){let state=Number.parseInt(crypto.createHash("sha256").update(seedText).digest("hex").slice(0,8),16)>>>0;return()=>{state^=state<<13;state^=state>>>17;state^=state<<5;return(state>>>0)/4294967296;};}
function permutePixels(gray,seedText){
  const out=Uint8Array.from(gray),rng=seeded(seedText);
  for(let i=out.length-1;i>0;i-=1){const j=Math.floor(rng()*(i+1));const tmp=out[i];out[i]=out[j];out[j]=tmp;}
  return out;
}
const sourceById=new Map(input.sources.map(row=>[row.sourceGroupId,row]));
const observationById=new Map(input.observations.map(row=>[row.id,row]));
const decoded=new Map();
for(const source of input.sources.filter(row=>row.lane==="train")){
  const absolute=path.resolve(path.dirname(inputPath),source.capturePath);
  const{data,info}=await sharp(await fs.readFile(absolute)).greyscale().raw().toBuffer({resolveWithObject:true});
  decoded.set(source.sourceGroupId,{data,width:info.width,height:info.height});
}
const records=[];
for(const original of train.records){
  const observation=observationById.get(original.id),source=sourceById.get(original.sourceGroupId),image=decoded.get(original.sourceGroupId);
  if(!observation||!source||!image)throw new Error(`spatial null cannot resolve sealed train observation ${original.id}`);
  const r=observation.region??{x:0,y:0,width:image.width,height:image.height};
  const x0=Math.max(0,Math.round(r.x)),y0=Math.max(0,Math.round(r.y)),w=Math.min(image.width-x0,Math.round(r.width)),h=Math.min(image.height-y0,Math.round(r.height));
  if(w<=0||h<=0)throw new Error(`invalid spatial-null region on ${observation.id}`);
  const gray=new Uint8Array(w*h);
  for(let y=0;y<h;y+=1)for(let x=0;x<w;x+=1)gray[y*w+x]=image.data[(y0+y)*image.width+x0+x];
  const shuffled=permutePixels(gray,`${input.blindInputSha256}|${observation.id}|within-observation-spatial-null-v1`);
  const result=measureObservable(shuffled,w,h,observation.segmentation);
  if(!result.eligible)throw new Error(`spatial-null permutation made sealed train observation ineligible (${observation.id}: ${(result.qualityWarnings??[]).join(",")})`);
  const maskToken=crypto.createHash("sha256").update(input.blindInputSha256).update("|spatial-null-v1|").update(Buffer.from(result.mask)).digest("hex");
  const{mask,normalizedWidth,normalizedHeight,eligible,...features}=result;
  records.push({
    id:original.id,sourceGroupId:original.sourceGroupId,lane:"train",captureToken:original.captureToken,maskToken,
    proposalKind:original.proposalKind,proposalScale:original.proposalScale,sourceContinuityToken:original.sourceContinuityToken,observationContinuityToken:original.observationContinuityToken,
    normalizedWidth,normalizedHeight,...features,
  });
}
records.sort((a,b)=>a.id.localeCompare(b.id));
if(records.length!==train.records.length)throw new Error(`spatial-null record count drifted: ${records.length} != ${train.records.length}`);
if(records.some((row,index)=>row.id!==[...train.records].sort((a,b)=>a.id.localeCompare(b.id))[index].id))throw new Error("spatial-null observation identity drifted");
const core={
  schema:"mark_observable_feature_partition_blind_v1",partition:"train",generatedAt:new Date().toISOString(),sourceMeasurementsSha256:train.sourceMeasurementsSha256,
  spatialNullContract:{sourceTrainPartitionSha256:train.blindSha256,blindInputSha256:input.blindInputSha256,observationIdsPreservedExactly:true,sourceGroupsPreservedExactly:true,regionDimensionsPreservedExactly:true,grayscaleHistogramPreservedPerObservation:true,method:"deterministic Fisher-Yates permutation of grayscale pixels independently inside every sealed train observation before remeasurement",purpose:"destroy within-observation spatial topology without changing observation count or per-observation intensity inventory",contextLabelsAvailable:false},
  records,
};
const blindSha256=crypto.createHash("sha256").update(JSON.stringify(core)).digest("hex"),artifact={...core,blindSha256};
await fs.mkdir(outDir,{recursive:true});
await fs.writeFile(path.join(outDir,"mark-observable-train-blind-v1.json"),`${JSON.stringify(artifact,null,2)}\n`);
await fs.writeFile(path.join(outDir,"summary.txt"),[`schema=${artifact.schema}`,`train_observations=${records.length}`,`source_objects=${new Set(records.map(row=>row.sourceGroupId)).size}`,`observation_identity_preserved=true`,`per_observation_histogram_preserved=true`,`spatial_topology_destroyed=true`,`blind_sha256=${blindSha256}`].join("\n")+"\n");
console.log(`Built exact-observation spatial null for ${records.length} train observations across ${new Set(records.map(row=>row.sourceGroupId)).size} sources`);
