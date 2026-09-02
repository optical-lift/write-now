import crypto from "node:crypto";
import fs from "node:fs/promises";
import path from "node:path";
import { relationGrammarPaths } from "./lib/mark-relational-core.mjs";

const worldPath=process.env.MARK_RELATIONAL_WORLD??"artifacts/mark-relational-world-v1/mark-relational-program-world-blind-v1.json";
const holdoutPath=process.env.MARK_RELATIONAL_HOLDOUT??"artifacts/mark-relational-graphs-v1/mark-relational-holdout-blind-v1.json";
const secondPath=process.env.MARK_RELATIONAL_SECOND_TRANSFER??"artifacts/mark-relational-graphs-v1/mark-relational-control-blind-v1.json";
const outDir=process.env.MARK_RELATIONAL_EVAL_OUT??"artifacts/mark-relational-transfer-v1";
const nullIterations=Math.max(4,Number(process.env.MARK_RELATIONAL_REWIRE_ITERATIONS??16));

async function readVerified(file,schema){
  const value=JSON.parse(await fs.readFile(file,"utf8"));if(value.schema!==schema)throw new Error(`unsupported ${file} schema ${value.schema}`);
  const{blindSha256:supplied,...core}=value,computed=crypto.createHash("sha256").update(JSON.stringify(core)).digest("hex");if(!supplied||supplied!==computed)throw new Error(`blind SHA-256 verification failed: ${file}`);return value;
}
const world=await readVerified(worldPath,"mark_relational_program_world_blind_v1");
const holdout=await readVerified(holdoutPath,"mark_relational_graph_partition_blind_v1");
const second=await readVerified(secondPath,"mark_relational_graph_partition_blind_v1");
const ruleByContext=new Map(world.grammarRules.map(rule=>[rule.context,rule]));

function examplesFromGraph(graph){
  const out=[];for(const p of relationGrammarPaths(graph)){
    out.push({context:`CENTER:${p.centerKind}|ARM:${p.leftToken}`,outcome:p.rightToken});
    out.push({context:`CENTER:${p.centerKind}|ARM:${p.rightToken}`,outcome:p.leftToken});
  }return out;
}
function score(records){
  let examples=0,covered=0,correct=0;const bySource=new Map();
  for(const record of records){let sExamples=0,sCovered=0,sCorrect=0;for(const ex of examplesFromGraph(record.graph)){examples+=1;sExamples+=1;const rule=ruleByContext.get(ex.context);if(!rule)continue;covered+=1;sCovered+=1;if(rule.predictedOutcome===ex.outcome){correct+=1;sCorrect+=1;}}
    const prior=bySource.get(record.sourceGroupId)??{examples:0,covered:0,correct:0};prior.examples+=sExamples;prior.covered+=sCovered;prior.correct+=sCorrect;bySource.set(record.sourceGroupId,prior);
  }
  return{examples,covered,correct,coverage:+(covered/Math.max(1,examples)).toFixed(6),accuracy:+(correct/Math.max(1,covered)).toFixed(6),sources:[...bySource.entries()].map(([sourceGroupId,v])=>({sourceGroupId,...v,coverage:+(v.covered/Math.max(1,v.examples)).toFixed(6),accuracy:+(v.correct/Math.max(1,v.covered)).toFixed(6)})).sort((a,b)=>a.sourceGroupId.localeCompare(b.sourceGroupId))};
}

function rng(seed){let x=Number.parseInt(crypto.createHash("sha256").update(seed).digest("hex").slice(0,8),16)>>>0;return()=>{x^=x<<13;x^=x>>>17;x^=x<<5;return(x>>>0)/4294967296;};}
function rewireGraph(graph,seed){
  const random=rng(seed),edges=graph.edges.map(edge=>({...edge}));
  const key=e=>`${e.source}|${e.relation}|${e.target}`;
  for(let attempt=0;attempt<Math.max(16,edges.length*8);attempt+=1){
    if(edges.length<2)break;const i=Math.floor(random()*edges.length),j=Math.floor(random()*edges.length);if(i===j)continue;const a=edges[i],b=edges[j];if(a.relation!==b.relation||a.source===b.source||a.target===b.target)continue;
    const na={...a,target:b.target},nb={...b,target:a.target};if(na.source===na.target||nb.source===nb.target)continue;
    const occupied=new Set(edges.map((e,k)=>k===i||k===j?null:key(e)).filter(Boolean));if(occupied.has(key(na))||occupied.has(key(nb))||key(na)===key(nb))continue;edges[i]=na;edges[j]=nb;
  }
  return{...graph,edges,grammarPaths:relationGrammarPaths({...graph,edges})};
}
function nullScores(records,lane){
  const rows=[];for(let iteration=0;iteration<nullIterations;iteration+=1){const rewired=records.map(record=>({...record,graph:rewireGraph(record.graph,`mark-v6|${lane}|${iteration}|${record.id}`)}));rows.push(score(rewired));}
  const mean=name=>+(rows.reduce((s,row)=>s+row[name],0)/Math.max(1,rows.length)).toFixed(6);
  return{iterations:nullIterations,meanCoverage:mean("coverage"),meanAccuracy:mean("accuracy"),runs:rows.map((row,i)=>({iteration:i,coverage:row.coverage,accuracy:row.accuracy,covered:row.covered,correct:row.correct}))};
}
function evaluateLane(partition,label){const observed=score(partition.records),rewiredNull=nullScores(partition.records,label);return{label,partition:partition.partition,sourceObjects:new Set(partition.records.map(r=>r.sourceGroupId)).size,observations:partition.records.length,observed,rewiredNull,accuracyLift:+(observed.accuracy-rewiredNull.meanAccuracy).toFixed(6)};}
const transferA=evaluateLane(holdout,"transfer_a"),transferB=evaluateLane(second,"transfer_b");
const core={
  schema:"mark_relational_transfer_evaluation_blind_v1",generatedAt:new Date().toISOString(),sourceWorldSha256:world.blindSha256,sourcePartitions:[holdout.blindSha256,second.blindSha256],
  transferA,transferB,
  evaluationContract:{maskedTarget:"one arm of a two-edge relational path",negativeControl:"degree- and relation-count-preserving target swaps within same relation type",categoryAssumption:false,interpretation:"both sealed non-training lanes are transfer tests; neither is presumed meaningless or unrelated"},
};
const blindSha256=crypto.createHash("sha256").update(JSON.stringify(core)).digest("hex"),artifact={...core,blindSha256};
await fs.mkdir(outDir,{recursive:true});await fs.writeFile(path.join(outDir,"mark-relational-transfer-evaluation-blind-v1.json"),`${JSON.stringify(artifact,null,2)}\n`);
await fs.writeFile(path.join(outDir,"summary.txt"),[
  `schema=${artifact.schema}`,`grammar_rules=${world.grammarRules.length}`,`transfer_a_coverage=${transferA.observed.coverage}`,`transfer_a_accuracy=${transferA.observed.accuracy}`,`transfer_a_rewired_accuracy=${transferA.rewiredNull.meanAccuracy}`,`transfer_a_lift=${transferA.accuracyLift}`,`transfer_b_coverage=${transferB.observed.coverage}`,`transfer_b_accuracy=${transferB.observed.accuracy}`,`transfer_b_rewired_accuracy=${transferB.rewiredNull.meanAccuracy}`,`transfer_b_lift=${transferB.accuracyLift}`,`blind_sha256=${blindSha256}`,
].join("\n")+"\n");
console.log(`Transfer A masked-relation accuracy ${transferA.observed.accuracy} vs rewired ${transferA.rewiredNull.meanAccuracy}; lift ${transferA.accuracyLift}`);
console.log(`Transfer B masked-relation accuracy ${transferB.observed.accuracy} vs rewired ${transferB.rewiredNull.meanAccuracy}; lift ${transferB.accuracyLift}`);
