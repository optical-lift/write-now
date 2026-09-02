import crypto from "node:crypto";
import fs from "node:fs/promises";
import path from "node:path";
import sharp from "sharp";
import { measureObservable } from "./lib/mark-image-observable.mjs";
import { buildRelationalGraph } from "./lib/mark-relational-core.mjs";

const inputPath=process.env.MARK_RELATIONAL_INPUT??"artifacts/mark-conveyor-input-v1/mark-observable-input-blind-v1.json";
const outDir=process.env.MARK_RELATIONAL_OUT??"artifacts/mark-relational-graphs-v1";
const input=JSON.parse(await fs.readFile(inputPath,"utf8"));
if(input.schema!=="mark_observable_input_blind_v1")throw new Error(`unsupported blind input schema ${input.schema}`);
const{blindInputSha256:suppliedSha,...inputCore}=input;
const computedSha=crypto.createHash("sha256").update(JSON.stringify(inputCore)).digest("hex");
if(!suppliedSha||suppliedSha!==computedSha)throw new Error("blind observable input SHA-256 verification failed");

const sourceById=new Map(input.sources.map(source=>[source.sourceGroupId,source])),decoded=new Map();
for(const source of input.sources){
  if(source.adapter!=="image_2d")throw new Error(`unsupported adapter ${source.adapter}`);
  const absolute=path.resolve(path.dirname(inputPath),source.capturePath);
  const{data,info}=await sharp(await fs.readFile(absolute)).greyscale().raw().toBuffer({resolveWithObject:true});
  decoded.set(source.sourceGroupId,{data,width:info.width,height:info.height});
}

const records=[],exclusions=[];
for(const observation of input.observations){
  const source=sourceById.get(observation.sourceGroupId),image=decoded.get(observation.sourceGroupId);
  if(!source||!image)throw new Error(`unknown source ${observation.sourceGroupId}`);
  const r=observation.region??{x:0,y:0,width:image.width,height:image.height};
  const x0=Math.max(0,Math.round(r.x)),y0=Math.max(0,Math.round(r.y)),w=Math.min(image.width-x0,Math.round(r.width)),h=Math.min(image.height-y0,Math.round(r.height));
  if(w<=0||h<=0){exclusions.push({id:observation.id,sourceGroupId:observation.sourceGroupId,reason:"invalid_region"});continue;}
  const gray=new Uint8Array(w*h);for(let y=0;y<h;y+=1)for(let x=0;x<w;x+=1)gray[y*w+x]=image.data[(y0+y)*image.width+x0+x];
  const measured=measureObservable(gray,w,h,observation.segmentation);
  if(!measured.eligible){exclusions.push({id:observation.id,sourceGroupId:observation.sourceGroupId,reason:"measurement_ineligible",qualityWarnings:measured.qualityWarnings});continue;}
  const graph=buildRelationalGraph(measured.mask,measured.normalizedWidth,measured.normalizedHeight,{observationId:observation.id,sourceGroupId:observation.sourceGroupId});
  records.push({
    id:observation.id,sourceGroupId:observation.sourceGroupId,lane:observation.lane,proposalKind:observation.proposalKind??"manual",proposalScale:observation.proposalScale??"manual",
    region:{x:x0,y:y0,width:w,height:h},captureToken:source.captureToken,maskToken:crypto.createHash("sha256").update(input.blindInputSha256).update(Buffer.from(measured.mask)).digest("hex"),graph,
  });
}
records.sort((a,b)=>a.id.localeCompare(b.id));
if(records.length<4)throw new Error(`too few eligible relational observations: ${records.length}`);
const core={
  schema:"mark_relational_graph_corpus_blind_v1",generatedAt:new Date().toISOString(),sourceBlindInputSha256:input.blindInputSha256,
  corpus:{observations:records.length,sourceObjects:new Set(records.map(r=>r.sourceGroupId)).size,train:records.filter(r=>r.lane==="train").length,holdout:records.filter(r=>r.lane==="holdout").length,control:records.filter(r=>r.lane==="control").length},
  records,exclusions,
  blindnessContract:{...input.blindnessContract,relationalExtraction:"program discovery receives topology graph only; source provenance and semantic labels remain sealed"},
};
const blindSha256=crypto.createHash("sha256").update(JSON.stringify(core)).digest("hex"),artifact={...core,blindSha256};
function partition(name,subset){
  const partitionCore={schema:"mark_relational_graph_partition_blind_v1",partition:name,generatedAt:artifact.generatedAt,sourceCorpusSha256:blindSha256,records:subset};
  return{...partitionCore,blindSha256:crypto.createHash("sha256").update(JSON.stringify(partitionCore)).digest("hex")};
}
const train=partition("train",records.filter(r=>r.lane==="train")),holdout=partition("holdout",records.filter(r=>r.lane==="holdout")),control=partition("control",records.filter(r=>r.lane==="control"));
await fs.mkdir(outDir,{recursive:true});
await fs.writeFile(path.join(outDir,"mark-relational-graphs-blind-v1.json"),`${JSON.stringify(artifact,null,2)}\n`);
await fs.writeFile(path.join(outDir,"mark-relational-train-blind-v1.json"),`${JSON.stringify(train,null,2)}\n`);
await fs.writeFile(path.join(outDir,"mark-relational-holdout-blind-v1.json"),`${JSON.stringify(holdout,null,2)}\n`);
await fs.writeFile(path.join(outDir,"mark-relational-control-blind-v1.json"),`${JSON.stringify(control,null,2)}\n`);
await fs.writeFile(path.join(outDir,"summary.txt"),[
  `schema=${artifact.schema}`,`source_objects=${artifact.corpus.sourceObjects}`,`observations=${artifact.corpus.observations}`,`train=${artifact.corpus.train}`,`holdout=${artifact.corpus.holdout}`,`control=${artifact.corpus.control}`,`blind_sha256=${blindSha256}`,
].join("\n")+"\n");
console.log(`Built ${records.length} blind relational graphs across ${artifact.corpus.sourceObjects} source objects`);
console.log(`Relational graph SHA-256: ${blindSha256}`);
