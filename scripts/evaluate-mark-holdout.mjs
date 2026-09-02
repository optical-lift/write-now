import crypto from "node:crypto";
import fs from "node:fs/promises";
import path from "node:path";

const predictionPath=process.env.MARK_WORLD_PREDICTION ?? "artifacts/mark-world-prediction-v1/mark-blind-world-holdout-prediction-v2.json";
const custodyPath=process.env.MARK_HARVEST_REJOIN ?? "artifacts/mark-harvest-rejoin-v1/mark-harvest-custody-rejoin-v1.json";
const outDir=process.env.MARK_HOLDOUT_EVAL_OUT ?? "artifacts/mark-holdout-evaluation-v1";
const prediction=JSON.parse(await fs.readFile(predictionPath,"utf8"));
const custody=JSON.parse(await fs.readFile(custodyPath,"utf8"));
if(prediction.schema!=="mark_blind_world_holdout_prediction_v2")throw new Error(`unsupported prediction schema ${prediction.schema}`);
if(custody.schema!=="mark_harvest_custody_rejoin_v1")throw new Error(`unsupported custody schema ${custody.schema}`);
for(const [name,value,hashName] of [["prediction",prediction,"blindSha256"]]){const supplied=value[hashName];const rest={...value};delete rest[hashName];const computed=crypto.createHash("sha256").update(JSON.stringify(rest)).digest("hex");if(!supplied||supplied!==computed)throw new Error(`${name} SHA-256 verification failed`);}

const truthBySource=new Map(custody.sources.map(source=>[source.sourceGroupId,source.context?.validationTruth?.openSetRelation??null]));
const whole=prediction.familyPredictions.filter(row=>row.proposalKind==="whole_capture");
const scored=[];
for(const row of whole){
  const truth=truthBySource.get(row.sourceGroupId);
  if(!truth)continue;
  if(!["known","novel"].includes(truth))throw new Error(`unsupported validation truth ${truth}`);
  const predicted=row.status==="accepted"?"known":"novel";
  scored.push({id:row.id,sourceGroupId:row.sourceGroupId,truth,predicted,status:row.status,acceptedFamilyId:row.acceptedFamilyId,nearestFamily:row.nearestFamily,correct:truth===predicted});
}
const known=scored.filter(x=>x.truth==="known").length,novel=scored.filter(x=>x.truth==="novel").length;
const tp=scored.filter(x=>x.truth==="known"&&x.predicted==="known").length;
const fp=scored.filter(x=>x.truth==="novel"&&x.predicted==="known").length;
const tn=scored.filter(x=>x.truth==="novel"&&x.predicted==="novel").length;
const fn=scored.filter(x=>x.truth==="known"&&x.predicted==="novel").length;
const accepted=tp+fp,abstained=tn+fn;
const precision=tp/Math.max(1,tp+fp),recall=tp/Math.max(1,known),coverage=accepted/Math.max(1,scored.length),accuracy=(tp+tn)/Math.max(1,scored.length);
const core={schema:"mark_holdout_open_set_evaluation_v1",generatedAt:new Date().toISOString(),sealedPredictionSha256:prediction.blindSha256,evaluationContract:{truthUnavailableToDiscovery:true,truthOpenedOnlyAfterPredictionFreeze:true,unit:"whole_capture",knownMeans:"same generating structural family exists in training",novelMeans:"generating structural family absent from training"},counts:{scored:scored.length,known,novel,tp,fp,tn,fn,accepted,abstained},metrics:{precision:+precision.toFixed(6),recall:+recall.toFixed(6),coverage:+coverage.toFixed(6),abstentionRate:+(abstained/Math.max(1,scored.length)).toFixed(6),accuracy:+accuracy.toFixed(6)},rows:scored};
const sha256=crypto.createHash("sha256").update(JSON.stringify(core)).digest("hex"),artifact={...core,sha256};
await fs.mkdir(outDir,{recursive:true});await fs.writeFile(path.join(outDir,"mark-holdout-open-set-evaluation-v1.json"),`${JSON.stringify(artifact,null,2)}\n`);
await fs.writeFile(path.join(outDir,"summary.txt"),[`schema=${artifact.schema}`,`scored_whole_captures=${scored.length}`,`known=${known}`,`novel=${novel}`,`accepted=${accepted}`,`abstained=${abstained}`,`precision=${artifact.metrics.precision}`,`recall=${artifact.metrics.recall}`,`coverage=${artifact.metrics.coverage}`,`accuracy=${artifact.metrics.accuracy}`,`sha256=${sha256}`].join("\n")+"\n");

const requireGate=(process.env.MARK_REQUIRE_OPEN_SET_GATE??"0")==="1";
if(requireGate){
  if(known<1||novel<1)throw new Error(`open-set fixture must score at least one known and one novel whole capture; got known=${known} novel=${novel}`);
  if(accepted<1||abstained<1)throw new Error(`open-set predictor must both accept and abstain; got accepted=${accepted} abstained=${abstained}`);
  const precisionFloor=Number(process.env.MARK_OPEN_SET_PRECISION_FLOOR??0.8);
  if(precision<precisionFloor)throw new Error(`open-set precision ${precision.toFixed(4)} below floor ${precisionFloor}`);
  if(coverage>=1)throw new Error("open-set coverage is 100%; abstention is not functioning");
  if(accuracy<0.75)throw new Error(`open-set accuracy ${accuracy.toFixed(4)} below 0.75`);
}
console.log(`Scored ${scored.length} frozen whole-capture predictions: ${accepted} accepted, ${abstained} abstained, accuracy=${accuracy.toFixed(3)}`);
