import crypto from "node:crypto";
import fs from "node:fs/promises";
import path from "node:path";

const realPath=process.env.MARK_REAL_NULL_EVALUATION ?? "artifacts/mark-null-worlds-v1/mark-blind-null-world-evaluation-v1.json";
const scramblePath=process.env.MARK_SCRAMBLE_NULL_EVALUATION ?? "artifacts/mark-spatial-scramble-null-worlds-v1/mark-blind-null-world-evaluation-v1.json";
const outDir=process.env.MARK_SPATIAL_CONTROL_OUT ?? "artifacts/mark-spatial-control-comparison-v1";
const real=JSON.parse(await fs.readFile(realPath,"utf8")),scramble=JSON.parse(await fs.readFile(scramblePath,"utf8"));
for(const[name,value]of[["real",real],["scramble",scramble]]){if(value.schema!=="mark_blind_null_world_evaluation_v1")throw new Error(`${name} has unsupported schema ${value.schema}`);const{blindSha256,...rest}=value;const computed=crypto.createHash("sha256").update(JSON.stringify(rest)).digest("hex");if(!blindSha256||blindSha256!==computed)throw new Error(`${name} SHA-256 verification failed`);}
const ratio=(a,b)=>+(a/Math.max(1e-9,b)).toFixed(6);
const statistics={
  crossSourceTightness:{real:real.statistics.crossSourceTightness.observed,spatialScramble:scramble.statistics.crossSourceTightness.observed,effectRatio:ratio(real.statistics.crossSourceTightness.observed,scramble.statistics.crossSourceTightness.observed)},
  recurrenceScore:{real:real.statistics.recurrenceScore.observed,spatialScramble:scramble.statistics.recurrenceScore.observed,effectRatio:ratio(real.statistics.recurrenceScore.observed,scramble.statistics.recurrenceScore.observed)},
};
const core={schema:"mark_blind_spatial_control_comparison_v1",generatedAt:new Date().toISOString(),sealedRealEvaluationSha256:real.blindSha256,sealedSpatialScrambleEvaluationSha256:scramble.blindSha256,controlContract:{sameStructuralMeasurementAndWorldBuilder:true,spatialArrangementDestroyedBeforeProposal:true,contextLabelsAvailable:false},statistics};
const blindSha256=crypto.createHash("sha256").update(JSON.stringify(core)).digest("hex"),artifact={...core,blindSha256};
await fs.mkdir(outDir,{recursive:true});await fs.writeFile(path.join(outDir,"mark-blind-spatial-control-comparison-v1.json"),`${JSON.stringify(artifact,null,2)}\n`);
await fs.writeFile(path.join(outDir,"summary.txt"),[`schema=${artifact.schema}`,`tightness_real=${statistics.crossSourceTightness.real}`,`tightness_scramble=${statistics.crossSourceTightness.spatialScramble}`,`tightness_real_over_scramble=${statistics.crossSourceTightness.effectRatio}`,`recurrence_real=${statistics.recurrenceScore.real}`,`recurrence_scramble=${statistics.recurrenceScore.spatialScramble}`,`recurrence_real_over_scramble=${statistics.recurrenceScore.effectRatio}`,`blind_sha256=${blindSha256}`].join("\n")+"\n");
if((process.env.MARK_REQUIRE_SPATIAL_CONTROL_GATE??"0")==="1"){
  const floor=Number(process.env.MARK_SPATIAL_CONTROL_RATIO_MIN??1.05);
  if(statistics.crossSourceTightness.effectRatio<floor)throw new Error(`real cross-source tightness did not beat spatial scramble: ${statistics.crossSourceTightness.effectRatio} < ${floor}`);
  if(statistics.recurrenceScore.effectRatio<floor)throw new Error(`real recurrence did not beat spatial scramble: ${statistics.recurrenceScore.effectRatio} < ${floor}`);
}
console.log(`Spatial control real/scramble: tightness=${statistics.crossSourceTightness.effectRatio}, recurrence=${statistics.recurrenceScore.effectRatio}`);
