import crypto from "node:crypto";
import fs from "node:fs/promises";
import path from "node:path";

const worldPath=process.env.MARK_RELATIONAL_WORLD??"artifacts/mark-relational-world-v1/mark-relational-program-world-blind-v1.json";
const evalPath=process.env.MARK_RELATIONAL_EVAL??"artifacts/mark-relational-transfer-v1/mark-relational-transfer-evaluation-blind-v2.json";
const rejoinPath=process.env.MARK_OBSERVABLE_REJOIN??"artifacts/mark-conveyor-rejoin-v1/mark-observable-custody-rejoin-v1.json";
const outDir=process.env.MARK_RELATIONAL_REPORT_OUT??"artifacts/mark-relational-report-v1";
async function readVerified(file,schema){const value=JSON.parse(await fs.readFile(file,"utf8"));if(value.schema!==schema)throw new Error(`unsupported ${file} schema ${value.schema}`);const{blindSha256:supplied,...core}=value,computed=crypto.createHash("sha256").update(JSON.stringify(core)).digest("hex");if(!supplied||supplied!==computed)throw new Error(`blind SHA-256 verification failed: ${file}`);return value;}
const world=await readVerified(worldPath,"mark_relational_program_world_blind_v1"),evaluation=await readVerified(evalPath,"mark_relational_transfer_evaluation_blind_v2"),rejoin=JSON.parse(await fs.readFile(rejoinPath,"utf8"));
if(rejoin.schema!=="mark_observable_custody_rejoin_v1")throw new Error(`unsupported rejoin ${rejoin.schema}`);
const sourceByGroup=new Map(rejoin.sources.map(source=>[source.sourceGroupId,source]));
const observationByBlind=new Map(rejoin.observations.map(observation=>[observation.blindId,observation]));
function sourceContext(sourceGroupId){const s=sourceByGroup.get(sourceGroupId);if(!s)return{sourceGroupId,missing:true};return{sourceGroupId,sourceId:s.sourceId??null,stableSourceId:s.stableSourceId??null,institution:s.institution??null,objectId:s.objectId??null,sourceUrl:s.sourceUrl??null,rightsBasis:s.rightsBasis??null,context:s.context??null};}
function exampleContext(example){const o=observationByBlind.get(example.observationId);return{observationId:example.observationId,stableObservationId:o?.stableObservationId??null,proposal:o?.context??null,region:o?.region??null,source:sourceContext(example.sourceGroupId)};}
function attachExamples(items,idKey){return items.map(item=>({[idKey]:item[idKey],signature:item.signature??item.fingerprint??item.context,count:item.count??null,distinctSourceObjects:item.distinctSourceObjects??null,delta:item.delta??null,confidence:item.confidence??null,predictedOutcome:item.predictedOutcome??null,examples:(item.examples??item.outcomes?.flatMap(row=>row.examples??[])??[]).slice(0,20).map(exampleContext)}));}
const report={
  schema:"mark_relational_program_context_report_v2",generatedAt:new Date().toISOString(),sealedWorldSha256:world.blindSha256,sealedEvaluationSha256:evaluation.blindSha256,
  warning:"Context was reopened only after the relational world and transfer evaluation were sealed. Context does not retroactively alter anonymous program identity.",
  transferResults:{transferA:evaluation.transferA,transferB:evaluation.transferB},
  nullAudit:{transferA:evaluation.transferA.rewiredNull.diagnostics,transferB:evaluation.transferB.rewiredNull.diagnostics},
  primitives:attachExamples(world.primitives,"primitiveId"),relationalStates:attachExamples(world.relationalStates,"stateId"),transformations:attachExamples(world.transformations,"transformationId"),grammarRules:attachExamples(world.grammarRules,"ruleId"),
};
await fs.mkdir(outDir,{recursive:true});await fs.writeFile(path.join(outDir,"mark-relational-program-context-report-v2.json"),`${JSON.stringify(report,null,2)}\n`);
await fs.writeFile(path.join(outDir,"summary.txt"),[`schema=${report.schema}`,`relational_primitives=${report.primitives.length}`,`relational_states=${report.relationalStates.length}`,`transformations=${report.transformations.length}`,`grammar_rules=${report.grammarRules.length}`,`transfer_a_lift=${evaluation.transferA.accuracyLift}`,`transfer_a_null_swaps=${report.nullAudit.transferA.totalAcceptedSwaps}`,`transfer_a_null_changed_observation_rate=${report.nullAudit.transferA.changedDistinctObservationRate}`,`transfer_b_lift=${evaluation.transferB.accuracyLift}`,`transfer_b_null_swaps=${report.nullAudit.transferB.totalAcceptedSwaps}`,`transfer_b_null_changed_observation_rate=${report.nullAudit.transferB.changedDistinctObservationRate}`].join("\n")+"\n");
console.log(`Reopened provenance for ${world.primitives.length} primitives, ${world.relationalStates.length} states, ${world.transformations.length} transformations, and ${world.grammarRules.length} grammar rules after freeze`);
