import crypto from "node:crypto";
import fs from "node:fs/promises";
import path from "node:path";
import { predictAgainstWorld } from "./lib/mark-world-core.mjs";

const modelPath=process.env.MARK_WORLD_TRAIN ?? "artifacts/mark-world-train-v1/mark-blind-world-model-train-v1.json";
const controlPath=process.env.MARK_OBSERVABLE_CONTROL ?? "artifacts/mark-observable-discovery-v1/mark-observable-control-blind-v1.json";
const outDir=process.env.MARK_CONTROL_EVALUATION_OUT ?? "artifacts/mark-control-evaluation-v1";
const model=JSON.parse(await fs.readFile(modelPath,"utf8"));
const control=JSON.parse(await fs.readFile(controlPath,"utf8"));
if(model.schema!=="mark_blind_world_model_v1")throw new Error(`unsupported world model ${model.schema}`);
if(control.schema!=="mark_observable_feature_partition_blind_v1"||control.partition!=="control")throw new Error(`control evaluation requires sealed control partition; got ${control.schema}/${control.partition}`);
for(const[name,value]of[["model",model],["control",control]]){const{blindSha256,...rest}=value;const computed=crypto.createHash("sha256").update(JSON.stringify(rest)).digest("hex");if(!blindSha256||blindSha256!==computed)throw new Error(`${name} SHA-256 verification failed`);}
if(!control.records.length)throw new Error("control lane is empty");
const predictions=predictAgainstWorld(model,control.records);
const familyById=new Map(predictions.familyPredictions.map(row=>[row.id,row]));
const whole=control.records.filter(record=>record.proposalKind==="whole_capture").map(record=>familyById.get(record.id)).filter(Boolean);
const acceptedAll=predictions.familyPredictions.filter(row=>row.status==="accepted").length;
const acceptedWhole=whole.filter(row=>row.status==="accepted").length;
const rates={
  allObservableAcceptance:+(acceptedAll/Math.max(1,predictions.familyPredictions.length)).toFixed(6),
  wholeObjectAcceptance:+(acceptedWhole/Math.max(1,whole.length)).toFixed(6),
};
const core={
  schema:"mark_blind_control_evaluation_v1",generatedAt:new Date().toISOString(),sealedTrainingWorldSha256:model.blindSha256,sealedControlSha256:control.blindSha256,
  controlContract:{controlNeverContributedToTraining:true,contextLabelsAvailable:false,unitOfPrimaryRate:"whole_source_object"},
  corpus:{observations:control.records.length,sourceObjects:new Set(control.records.map(r=>r.sourceGroupId)).size,wholeObjects:whole.length},
  accepted:{observations:acceptedAll,wholeObjects:acceptedWhole},rates,
  wholeObjectPredictions:whole,
};
const blindSha256=crypto.createHash("sha256").update(JSON.stringify(core)).digest("hex"),artifact={...core,blindSha256};
await fs.mkdir(outDir,{recursive:true});
await fs.writeFile(path.join(outDir,"mark-blind-control-evaluation-v1.json"),`${JSON.stringify(artifact,null,2)}\n`);
await fs.writeFile(path.join(outDir,"summary.txt"),[`schema=${artifact.schema}`,`control_source_objects=${artifact.corpus.sourceObjects}`,`control_whole_objects=${whole.length}`,`control_whole_acceptance=${rates.wholeObjectAcceptance}`,`control_all_observable_acceptance=${rates.allObservableAcceptance}`,`blind_sha256=${blindSha256}`].join("\n")+"\n");
if((process.env.MARK_REQUIRE_CONTROL_GATE??"0")==="1"){
  const max=Number(process.env.MARK_CONTROL_MAX_WHOLE_ACCEPTANCE??0.35);
  if(rates.wholeObjectAcceptance>max)throw new Error(`unrelated control acceptance is too high: ${rates.wholeObjectAcceptance} > ${max}`);
}
console.log(`Control whole-object acceptance=${rates.wholeObjectAcceptance} (${acceptedWhole}/${whole.length})`);
