import crypto from "node:crypto";
import fs from "node:fs/promises";
import path from "node:path";
import { buildWorldModel } from "./lib/mark-world-core.mjs";

const trainPath=process.env.MARK_OBSERVABLE_TRAIN ?? "artifacts/mark-observable-discovery-v1/mark-observable-train-blind-v1.json";
const outDir=process.env.MARK_WORLD_TRAIN_OUT ?? "artifacts/mark-world-train-v1";
const train=JSON.parse(await fs.readFile(trainPath,"utf8"));
if(train.schema!=="mark_observable_feature_partition_blind_v1"||train.partition!=="train")throw new Error(`world learning requires sealed train partition; got ${train.schema}/${train.partition}`);
const{blindSha256:suppliedSha,...core}=train;
const computed=crypto.createHash("sha256").update(JSON.stringify(core)).digest("hex");
if(!suppliedSha||suppliedSha!==computed)throw new Error("train partition SHA-256 verification failed");
if(train.records.some(record=>record.lane!=="train"))throw new Error("train partition contains non-train record");
const modelCore={...buildWorldModel(train.records),generatedAt:new Date().toISOString(),sourceTrainSha256:train.blindSha256,limitations:[
  "This model receives no object-category, culture, language, chronology, geography, conventional reading, or scholarly interpretation labels.",
  "Families and operations are structural hypotheses over observable configurations, not historical mechanism claims.",
  "The holdout partition is not available to this process.",
]};
const blindSha256=crypto.createHash("sha256").update(JSON.stringify(modelCore)).digest("hex");
const model={...modelCore,blindSha256};
await fs.mkdir(outDir,{recursive:true});
await fs.writeFile(path.join(outDir,"mark-blind-world-model-train-v1.json"),`${JSON.stringify(model,null,2)}\n`);
await fs.writeFile(path.join(outDir,"summary.txt"),[
  `schema=${model.schema}`,`train_observations=${model.corpus.observations}`,`source_objects=${model.corpus.sourceObjects}`,`families=${model.families.length}`,`primitives=${model.primitives.length}`,`operations=${model.operations.length}`,`blind_sha256=${blindSha256}`,
].join("\n")+"\n");
console.log(`Learned blind world: ${model.families.length} families, ${model.primitives.length} primitives, ${model.operations.length} operations`);
console.log(`Training world SHA-256: ${blindSha256}`);
