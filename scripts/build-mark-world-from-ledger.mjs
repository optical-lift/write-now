import crypto from "node:crypto";
import fs from "node:fs/promises";
import path from "node:path";
import { buildWorldModel } from "./lib/mark-world-core.mjs";

const ledgerPath=process.env.MARK_LEDGER ?? "artifacts/mark-observable-ledger-v1/mark-observable-measurement-ledger-blind-v1.json";
const outDir=process.env.MARK_LEDGER_WORLD_OUT ?? "artifacts/mark-ledger-world-v1";
const ledger=JSON.parse(await fs.readFile(ledgerPath,"utf8"));
if(ledger.schema!=="mark_observable_measurement_ledger_blind_v1")throw new Error(`unsupported ledger ${ledger.schema}`);
const{blindSha256,...ledgerCore}=ledger;const computed=crypto.createHash("sha256").update(JSON.stringify(ledgerCore)).digest("hex");if(!blindSha256||blindSha256!==computed)throw new Error("ledger SHA-256 verification failed");
const model=buildWorldModel(ledger.records,{neighborK:Number(process.env.MARK_WORLD_NEIGHBOR_K??10),minDistinctSources:Number(process.env.MARK_WORLD_MIN_SOURCES??3)});
const core={...model,schema:"mark_blind_continuous_world_model_v1",generatedAt:new Date().toISOString(),sourceLedgerSha256:ledger.blindSha256,lineage:{parentLedgerSha256:ledger.parentLedgerSha256,inputMeasurementShas:ledger.inputMeasurementShas},assemblyContract:{entireAccumulatedBlindLedgerUsed:true,contextLabelsAvailable:false,duplicateObservationsCollapsedBeforeWorldBuild:true},limitations:["This continuous world ranks structural recurrence; it does not infer a historical mechanism.","Context may be rejoined only through a separately accumulated custody ledger after this world is sealed."]};
const worldSha256=crypto.createHash("sha256").update(JSON.stringify(core)).digest("hex"),world={...core,blindSha256:worldSha256};
await fs.mkdir(outDir,{recursive:true});await fs.writeFile(path.join(outDir,"mark-blind-continuous-world-v1.json"),`${JSON.stringify(world,null,2)}\n`);
await fs.writeFile(path.join(outDir,"summary.txt"),[`schema=${world.schema}`,`observations=${world.corpus.observations}`,`source_objects=${world.corpus.sourceObjects}`,`families=${world.families.length}`,`primitives=${world.primitives.length}`,`operations=${world.operations.length}`,`reuse_per_vocabulary_entry=${world.compressionDiagnostics.reusePerVocabularyEntry}`,`source_ledger_sha256=${ledger.blindSha256}`,`blind_sha256=${worldSha256}`].join("\n")+"\n");
console.log(`Continuous Mark world: ${world.corpus.observations} observations, ${world.families.length} families, ${world.primitives.length} primitives, ${world.operations.length} operations`);
console.log(`Continuous world SHA-256: ${worldSha256}`);
