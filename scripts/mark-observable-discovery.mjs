import crypto from "node:crypto";
import fs from "node:fs/promises";
import path from "node:path";
import sharp from "sharp";
import { measureObservable } from "./lib/mark-image-observable.mjs";

const sharpVersion=sharp.versions?.sharp ?? "unknown";
const inputPath=process.env.MARK_OBSERVABLE_INPUT ?? "artifacts/mark-observable-input-v1/mark-observable-input-blind-v1.json";
const outDir=process.env.MARK_OBSERVABLE_OUT ?? "artifacts/mark-observable-discovery-v1";
const input=JSON.parse(await fs.readFile(inputPath,"utf8"));
if(input.schema!=="mark_observable_input_blind_v1")throw new Error(`unsupported blind input schema ${input.schema}`);
const{blindInputSha256:suppliedSha,...inputCore}=input;
const computedSha=crypto.createHash("sha256").update(JSON.stringify(inputCore)).digest("hex");
if(!suppliedSha||suppliedSha!==computedSha)throw new Error("blind observable input SHA-256 verification failed");

const sourceById=new Map(input.sources.map(source=>[source.sourceGroupId,source]));
const decoded=new Map();
for(const source of input.sources){
  if(source.adapter!=="image_2d")throw new Error(`unsupported adapter ${source.adapter}`);
  const absolute=path.resolve(path.dirname(inputPath),source.capturePath);
  const{data,info}=await sharp(await fs.readFile(absolute)).greyscale().raw().toBuffer({resolveWithObject:true});
  decoded.set(source.sourceGroupId,{data,width:info.width,height:info.height});
}

const measured=[];
for(const observation of input.observations){
  const source=sourceById.get(observation.sourceGroupId),image=decoded.get(observation.sourceGroupId);
  if(!source||!image)throw new Error(`unknown source ${observation.sourceGroupId}`);
  const r=observation.region??{x:0,y:0,width:image.width,height:image.height};
  const x0=Math.max(0,Math.round(r.x)),y0=Math.max(0,Math.round(r.y)),w=Math.min(image.width-x0,Math.round(r.width)),h=Math.min(image.height-y0,Math.round(r.height));
  if(w<=0||h<=0)throw new Error(`invalid region on ${observation.id}`);
  const gray=new Uint8Array(w*h);
  for(let y=0;y<h;y+=1)for(let x=0;x<w;x+=1)gray[y*w+x]=image.data[(y0+y)*image.width+x0+x];
  const result=measureObservable(gray,w,h,observation.segmentation);
  if(!result.eligible){measured.push({id:observation.id,sourceGroupId:observation.sourceGroupId,lane:observation.lane,eligible:false,qualityWarnings:result.qualityWarnings});continue;}
  const maskToken=crypto.createHash("sha256").update(input.blindInputSha256).update(Buffer.from(result.mask)).digest("hex");
  const{mask,normalizedWidth,normalizedHeight,eligible,...features}=result;
  measured.push({
    id:observation.id,sourceGroupId:observation.sourceGroupId,lane:observation.lane,captureToken:source.captureToken,maskToken,
    normalizedWidth,normalizedHeight,...features,
  });
}
const eligible=measured.filter(record=>record.eligible!==false);
if(eligible.length<4)throw new Error(`too few eligible observable configurations: ${eligible.length}/${measured.length}`);
const records=eligible.map(({eligible:_eligible,...record})=>record).sort((a,b)=>a.id.localeCompare(b.id));

const blindCore={
  schema:"mark_observable_measurements_blind_v1",
  corpusKind:input.corpusKind,
  generatedAt:new Date().toISOString(),
  blindInputSha256:input.blindInputSha256,
  runtime:{node:process.version,sharp:sharpVersion},
  corpus:{totalObservations:measured.length,eligibleObservations:records.length,sourceObjects:input.sources.length,trainObservations:records.filter(r=>r.lane==="train").length,holdoutObservations:records.filter(r=>r.lane==="holdout").length},
  records,
  exclusions:measured.filter(r=>r.eligible===false).map(({eligible:_eligible,...r})=>r),
  blindnessContract:input.blindnessContract,
};
const blindSha256=crypto.createHash("sha256").update(JSON.stringify(blindCore)).digest("hex");
const artifact={...blindCore,blindSha256};
function partition(name,subset){const core={schema:"mark_observable_feature_partition_blind_v1",partition:name,generatedAt:artifact.generatedAt,sourceMeasurementsSha256:blindSha256,records:subset};const sha=crypto.createHash("sha256").update(JSON.stringify(core)).digest("hex");return{...core,blindSha256:sha};}
const train=partition("train",records.filter(r=>r.lane==="train"));
const holdout=partition("holdout",records.filter(r=>r.lane==="holdout"));
if(records.length>=10&&holdout.records.length<1)throw new Error("observable corpus requires at least one source-level holdout observation");
await fs.mkdir(outDir,{recursive:true});
await fs.writeFile(path.join(outDir,"mark-observable-measurements-blind-v1.json"),`${JSON.stringify(artifact,null,2)}\n`);
await fs.writeFile(path.join(outDir,"mark-observable-train-blind-v1.json"),`${JSON.stringify(train,null,2)}\n`);
await fs.writeFile(path.join(outDir,"mark-observable-holdout-blind-v1.json"),`${JSON.stringify(holdout,null,2)}\n`);
await fs.writeFile(path.join(outDir,"summary.txt"),[
  `schema=${artifact.schema}`,`source_objects=${artifact.corpus.sourceObjects}`,`eligible_observations=${artifact.corpus.eligibleObservations}`,
  `train_observations=${train.records.length}`,`train_sha256=${train.blindSha256}`,`holdout_observations=${holdout.records.length}`,`holdout_sha256=${holdout.blindSha256}`,`blind_sha256=${blindSha256}`,
].join("\n")+"\n");
console.log(`Measured ${records.length}/${measured.length} observable configurations across ${input.sources.length} source objects`);
console.log(`Blind measurement SHA-256: ${blindSha256}`);
