import crypto from "node:crypto";
import fs from "node:fs/promises";
import path from "node:path";
import { canonicalRelationalFingerprint, relationGrammarPaths } from "./lib/mark-relational-core.mjs";

const worldPath=process.env.MARK_RELATIONAL_WORLD??"artifacts/mark-relational-world-v1/mark-relational-program-world-blind-v1.json";
const holdoutPath=process.env.MARK_RELATIONAL_HOLDOUT??"artifacts/mark-relational-graphs-v1/mark-relational-holdout-blind-v1.json";
const secondPath=process.env.MARK_RELATIONAL_SECOND_TRANSFER??"artifacts/mark-relational-graphs-v1/mark-relational-control-blind-v1.json";
const outDir=process.env.MARK_RELATIONAL_EVAL_OUT??"artifacts/mark-relational-transfer-v1";
const nullIterations=Math.max(4,Number(process.env.MARK_RELATIONAL_REWIRE_ITERATIONS??16));
const symmetricRelations=new Set(["PATH"]);

async function readVerified(file,schema){
  const value=JSON.parse(await fs.readFile(file,"utf8"));
  if(value.schema!==schema)throw new Error(`unsupported ${file} schema ${value.schema}`);
  const{blindSha256:supplied,...core}=value,computed=crypto.createHash("sha256").update(JSON.stringify(core)).digest("hex");
  if(!supplied||supplied!==computed)throw new Error(`blind SHA-256 verification failed: ${file}`);
  return value;
}
const world=await readVerified(worldPath,"mark_relational_program_world_blind_v1");
const holdout=await readVerified(holdoutPath,"mark_relational_graph_partition_blind_v1");
const second=await readVerified(secondPath,"mark_relational_graph_partition_blind_v1");
const ruleByContext=new Map(world.grammarRules.map(rule=>[rule.context,rule]));

function examplesFromGraph(graph){
  const out=[];
  for(const p of relationGrammarPaths(graph)){
    out.push({context:`CENTER:${p.centerKind}|ARM:${p.leftToken}`,outcome:p.rightToken});
    out.push({context:`CENTER:${p.centerKind}|ARM:${p.rightToken}`,outcome:p.leftToken});
  }
  return out;
}
function score(records){
  let examples=0,covered=0,correct=0;const bySource=new Map();
  for(const record of records){
    let sExamples=0,sCovered=0,sCorrect=0;
    for(const ex of examplesFromGraph(record.graph)){
      examples+=1;sExamples+=1;const rule=ruleByContext.get(ex.context);if(!rule)continue;covered+=1;sCovered+=1;if(rule.predictedOutcome===ex.outcome){correct+=1;sCorrect+=1;}
    }
    const prior=bySource.get(record.sourceGroupId)??{examples:0,covered:0,correct:0};prior.examples+=sExamples;prior.covered+=sCovered;prior.correct+=sCorrect;bySource.set(record.sourceGroupId,prior);
  }
  return{examples,covered,correct,coverage:+(covered/Math.max(1,examples)).toFixed(6),accuracy:+(correct/Math.max(1,covered)).toFixed(6),sources:[...bySource.entries()].map(([sourceGroupId,v])=>({sourceGroupId,...v,coverage:+(v.covered/Math.max(1,v.examples)).toFixed(6),accuracy:+(v.correct/Math.max(1,v.covered)).toFixed(6)})).sort((a,b)=>a.sourceGroupId.localeCompare(b.sourceGroupId))};
}

function rng(seed){let x=Number.parseInt(crypto.createHash("sha256").update(seed).digest("hex").slice(0,8),16)>>>0;return()=>{x^=x<<13;x^=x>>>17;x^=x<<5;return(x>>>0)/4294967296;};}
function canonicalEdgeKey(edge){
  if(symmetricRelations.has(edge.relation)){const pair=[edge.source,edge.target].sort();return`${pair[0]}|${edge.relation}|${pair[1]}`;}
  return`${edge.source}|${edge.relation}|${edge.target}`;
}
function validReplacement(edges,i,j,nextA,nextB){
  if(nextA.source===nextA.target||nextB.source===nextB.target)return false;
  const occupied=new Set(edges.map((edge,k)=>k===i||k===j?null:canonicalEdgeKey(edge)).filter(Boolean));
  const aKey=canonicalEdgeKey(nextA),bKey=canonicalEdgeKey(nextB);
  return aKey!==bKey&&!occupied.has(aKey)&&!occupied.has(bKey);
}
function rewireGraph(graph,seed){
  const random=rng(seed),edges=graph.edges.map(edge=>({...edge}));
  const attemptsLimit=Math.max(24,edges.length*12);let attempts=0,acceptedSwaps=0,rewiredEdgeTouches=0;
  for(;attempts<attemptsLimit;attempts+=1){
    if(edges.length<2)break;
    const i=Math.floor(random()*edges.length),j=Math.floor(random()*edges.length);if(i===j)continue;
    const a=edges[i],b=edges[j];if(a.relation!==b.relation)continue;
    let nextA,nextB;
    if(symmetricRelations.has(a.relation)){
      const distinct=new Set([a.source,a.target,b.source,b.target]);if(distinct.size<4)continue;
      if(random()<0.5){nextA={...a,source:a.source,target:b.target};nextB={...b,source:b.source,target:a.target};}
      else{nextA={...a,source:a.source,target:b.source};nextB={...b,source:a.target,target:b.target};}
    }else{
      if(a.source===b.source||a.target===b.target)continue;
      nextA={...a,target:b.target};nextB={...b,target:a.target};
    }
    if(!validReplacement(edges,i,j,nextA,nextB))continue;
    edges[i]=nextA;edges[j]=nextB;acceptedSwaps+=1;rewiredEdgeTouches+=2;
  }
  const rewired={...graph,edges};
  rewired.grammarPaths=relationGrammarPaths(rewired);
  const before=graph.fingerprint??canonicalRelationalFingerprint(graph),after=canonicalRelationalFingerprint(rewired);
  return{graph:rewired,diagnostics:{attempts,acceptedSwaps,rewiredEdgeTouches,fingerprintChanged:before!==after,beforeFingerprint:before,afterFingerprint:after}};
}
function nullScores(records,lane){
  const rows=[];let totalAttempts=0,totalAcceptedSwaps=0,totalRewiredEdgeTouches=0,changedGraphRuns=0,eligibleGraphRuns=0;
  const changedObservationIds=new Set();
  for(let iteration=0;iteration<nullIterations;iteration+=1){
    const rewired=[];let runAttempts=0,runAccepted=0,runTouches=0,runChanged=0;
    for(const record of records){
      const result=rewireGraph(record.graph,`mark-v6|${lane}|${iteration}|${record.id}`);
      rewired.push({...record,graph:result.graph});runAttempts+=result.diagnostics.attempts;runAccepted+=result.diagnostics.acceptedSwaps;runTouches+=result.diagnostics.rewiredEdgeTouches;
      if(record.graph.edges.length>=2)eligibleGraphRuns+=1;
      if(result.diagnostics.fingerprintChanged){runChanged+=1;changedGraphRuns+=1;changedObservationIds.add(record.id);}
    }
    totalAttempts+=runAttempts;totalAcceptedSwaps+=runAccepted;totalRewiredEdgeTouches+=runTouches;
    const scored=score(rewired);rows.push({...scored,rewire:{attempts:runAttempts,acceptedSwaps:runAccepted,rewiredEdgeTouches:runTouches,fingerprintChangedGraphs:runChanged}});
  }
  const mean=name=>+(rows.reduce((s,row)=>s+row[name],0)/Math.max(1,rows.length)).toFixed(6);
  const graphRuns=records.length*nullIterations;
  return{
    iterations:nullIterations,meanCoverage:mean("coverage"),meanAccuracy:mean("accuracy"),
    diagnostics:{graphRuns,eligibleGraphRuns,totalAttempts,totalAcceptedSwaps,totalRewiredEdgeTouches,changedGraphRuns,changedGraphRunRate:+(changedGraphRuns/Math.max(1,graphRuns)).toFixed(6),changedDistinctObservations:changedObservationIds.size,changedDistinctObservationRate:+(changedObservationIds.size/Math.max(1,records.length)).toFixed(6)},
    runs:rows.map((row,i)=>({iteration:i,coverage:row.coverage,accuracy:row.accuracy,covered:row.covered,correct:row.correct,rewire:row.rewire})),
  };
}
function evaluateLane(partition,label){
  const observed=score(partition.records),rewiredNull=nullScores(partition.records,label);
  return{label,partition:partition.partition,sourceObjects:new Set(partition.records.map(r=>r.sourceGroupId)).size,observations:partition.records.length,observed,rewiredNull,accuracyLift:+(observed.accuracy-rewiredNull.meanAccuracy).toFixed(6)};
}
const transferA=evaluateLane(holdout,"transfer_a"),transferB=evaluateLane(second,"transfer_b");
const core={
  schema:"mark_relational_transfer_evaluation_blind_v2",generatedAt:new Date().toISOString(),sourceWorldSha256:world.blindSha256,sourcePartitions:[holdout.blindSha256,second.blindSha256],
  transferA,transferB,
  evaluationContract:{maskedTarget:"one arm of a two-edge relational path",negativeControl:"degree-preserving double-edge swaps for undirected PATH and source-out/target-in preserving target swaps for directed relations; relation counts and node inventory stay fixed",nullDiagnosticsRequired:true,categoryAssumption:false,interpretation:"both sealed non-training lanes are transfer tests; neither is presumed meaningless or unrelated"},
};
const blindSha256=crypto.createHash("sha256").update(JSON.stringify(core)).digest("hex"),artifact={...core,blindSha256};
await fs.mkdir(outDir,{recursive:true});
await fs.writeFile(path.join(outDir,"mark-relational-transfer-evaluation-blind-v2.json"),`${JSON.stringify(artifact,null,2)}\n`);
await fs.writeFile(path.join(outDir,"summary.txt"),[
  `schema=${artifact.schema}`,`grammar_rules=${world.grammarRules.length}`,
  `transfer_a_coverage=${transferA.observed.coverage}`,`transfer_a_accuracy=${transferA.observed.accuracy}`,`transfer_a_rewired_accuracy=${transferA.rewiredNull.meanAccuracy}`,`transfer_a_lift=${transferA.accuracyLift}`,`transfer_a_null_swaps=${transferA.rewiredNull.diagnostics.totalAcceptedSwaps}`,`transfer_a_null_changed_graph_rate=${transferA.rewiredNull.diagnostics.changedGraphRunRate}`,`transfer_a_null_changed_observation_rate=${transferA.rewiredNull.diagnostics.changedDistinctObservationRate}`,
  `transfer_b_coverage=${transferB.observed.coverage}`,`transfer_b_accuracy=${transferB.observed.accuracy}`,`transfer_b_rewired_accuracy=${transferB.rewiredNull.meanAccuracy}`,`transfer_b_lift=${transferB.accuracyLift}`,`transfer_b_null_swaps=${transferB.rewiredNull.diagnostics.totalAcceptedSwaps}`,`transfer_b_null_changed_graph_rate=${transferB.rewiredNull.diagnostics.changedGraphRunRate}`,`transfer_b_null_changed_observation_rate=${transferB.rewiredNull.diagnostics.changedDistinctObservationRate}`,`blind_sha256=${blindSha256}`,
].join("\n")+"\n");
console.log(`Transfer A masked-relation accuracy ${transferA.observed.accuracy} vs rewired ${transferA.rewiredNull.meanAccuracy}; lift ${transferA.accuracyLift}; null swaps ${transferA.rewiredNull.diagnostics.totalAcceptedSwaps}; changed observations ${transferA.rewiredNull.diagnostics.changedDistinctObservationRate}`);
console.log(`Transfer B masked-relation accuracy ${transferB.observed.accuracy} vs rewired ${transferB.rewiredNull.meanAccuracy}; lift ${transferB.accuracyLift}; null swaps ${transferB.rewiredNull.diagnostics.totalAcceptedSwaps}; changed observations ${transferB.rewiredNull.diagnostics.changedDistinctObservationRate}`);
