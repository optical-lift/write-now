import crypto from "node:crypto";
import fs from "node:fs/promises";
import path from "node:path";
import { predictAgainstWorld } from "./lib/mark-world-core.mjs";

const modelPath=process.env.MARK_WORLD_TRAIN ?? "artifacts/mark-world-train-v1/mark-blind-world-model-train-v1.json";
const holdoutPath=process.env.MARK_OBSERVABLE_HOLDOUT ?? "artifacts/mark-observable-discovery-v1/mark-observable-holdout-blind-v1.json";
const outDir=process.env.MARK_WORLD_PREDICTION_OUT ?? "artifacts/mark-world-prediction-v1";
const model=JSON.parse(await fs.readFile(modelPath,"utf8")),holdout=JSON.parse(await fs.readFile(holdoutPath,"utf8"));
if(model.schema!=="mark_blind_world_model_v1")throw new Error(`unsupported world model ${model.schema}`);
if(holdout.schema!=="mark_observable_feature_partition_blind_v1"||holdout.partition!=="holdout")throw new Error(`prediction requires sealed holdout partition; got ${holdout.schema}/${holdout.partition}`);
for(const [name,value] of [["model",model],["holdout",holdout]]){const{blindSha256,...rest}=value;const computed=crypto.createHash("sha256").update(JSON.stringify(rest)).digest("hex");if(!blindSha256||blindSha256!==computed)throw new Error(`${name} SHA-256 verification failed`);}
if(holdout.records.some(record=>record.lane!=="holdout"))throw new Error("holdout partition contains non-holdout record");
const predictions=predictAgainstWorld(model,holdout.records);
const accepted=predictions.familyPredictions.filter(row=>row.status==="accepted").length;
const abstained=predictions.familyPredictions.filter(row=>row.status==="abstain").length;
const core={
  schema:"mark_blind_world_holdout_prediction_v2",generatedAt:new Date().toISOString(),sealedTrainingWorldSha256:model.blindSha256,sealedHoldoutSha256:holdout.blindSha256,
  predictionContract:{trainingWorldWasSealedFirst:true,holdoutUnavailableToLearner:true,unit:"observable_configuration",categoryLabelsAvailable:false,forcedAssignment:false,abstentionEnabled:true,acceptanceEnvelopeSource:"training_family_member_distances_only"},
  corpus:{holdoutObservations:holdout.records.length,holdoutSourceObjects:new Set(holdout.records.map(r=>r.sourceGroupId)).size,acceptedObservations:accepted,abstainedObservations:abstained},...predictions,
};
const blindSha256=crypto.createHash("sha256").update(JSON.stringify(core)).digest("hex"),artifact={...core,blindSha256};
await fs.mkdir(outDir,{recursive:true});await fs.writeFile(path.join(outDir,"mark-blind-world-holdout-prediction-v2.json"),`${JSON.stringify(artifact,null,2)}\n`);
await fs.writeFile(path.join(outDir,"summary.txt"),[`schema=${artifact.schema}`,`holdout_observations=${artifact.corpus.holdoutObservations}`,`accepted_observations=${accepted}`,`abstained_observations=${abstained}`,`acceptance_rate=${(accepted/Math.max(1,artifact.corpus.holdoutObservations)).toFixed(6)}`,`operation_prediction_sets=${artifact.operationPredictions.length}`,`training_world_sha256=${artifact.sealedTrainingWorldSha256}`,`blind_sha256=${blindSha256}`].join("\n")+"\n");
console.log(`Evaluated ${artifact.familyPredictions.length} unseen observables: ${accepted} accepted, ${abstained} abstained`);console.log(`Prediction SHA-256: ${blindSha256}`);
