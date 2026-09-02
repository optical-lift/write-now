import crypto from "node:crypto";
import fs from "node:fs/promises";
import path from "node:path";
import { buildWorldModel } from "./lib/mark-world-core.mjs";

const measurementsPath=process.env.MARK_OBSERVABLE_MEASUREMENTS ?? "artifacts/mark-observable-discovery-v1/mark-observable-measurements-blind-v1.json";
const predictionPath=process.env.MARK_WORLD_PREDICTION ?? "artifacts/mark-world-prediction-v1/mark-blind-world-holdout-prediction-v1.json";
const outDir=process.env.MARK_WORLD_OUT ?? "artifacts/mark-world-v1";
const measurements=JSON.parse(await fs.readFile(measurementsPath,"utf8")),prediction=JSON.parse(await fs.readFile(predictionPath,"utf8"));
for(const[name,value]of[["measurements",measurements],["prediction",prediction]]){const{blindSha256,...rest}=value;const computed=crypto.createHash("sha256").update(JSON.stringify(rest)).digest("hex");if(!blindSha256||blindSha256!==computed)throw new Error(`${name} SHA-256 verification failed`);}
if(measurements.schema!=="mark_observable_measurements_blind_v1")throw new Error(`unsupported measurements ${measurements.schema}`);
if(prediction.schema!=="mark_blind_world_holdout_prediction_v1")throw new Error(`unsupported prediction ${prediction.schema}`);
const worldCore={...buildWorldModel(measurements.records),schema:"mark_blind_world_model_full_v1",generatedAt:new Date().toISOString(),sourceMeasurementsSha256:measurements.blindSha256,validationPredictionSha256:prediction.blindSha256,assemblyContract:{holdoutPredictionsSealedBeforeFullWorldAssembly:true,contextLabelsAvailable:false},limitations:["The full world is assembled only after holdout predictions are sealed.","This is a structural world graph, not an assertion that all recurrent structures share one historical origin."]};
const blindSha256=crypto.createHash("sha256").update(JSON.stringify(worldCore)).digest("hex"),world={...worldCore,blindSha256};
await fs.mkdir(outDir,{recursive:true});await fs.writeFile(path.join(outDir,"mark-blind-world-model-full-v1.json"),`${JSON.stringify(world,null,2)}\n`);
await fs.writeFile(path.join(outDir,"summary.txt"),[`schema=${world.schema}`,`observations=${world.corpus.observations}`,`source_objects=${world.corpus.sourceObjects}`,`families=${world.families.length}`,`primitives=${world.primitives.length}`,`operations=${world.operations.length}`,`reuse_per_vocabulary_entry=${world.compressionDiagnostics.reusePerVocabularyEntry}`,`validation_prediction_sha256=${prediction.blindSha256}`,`blind_sha256=${blindSha256}`].join("\n")+"\n");
console.log(`Assembled full blind world: ${world.corpus.observations} observables, ${world.families.length} families, ${world.operations.length} recurrent operations`);console.log(`Full world SHA-256: ${blindSha256}`);
