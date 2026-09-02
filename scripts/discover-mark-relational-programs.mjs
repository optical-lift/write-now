import crypto from "node:crypto";
import fs from "node:fs/promises";
import path from "node:path";
import { histogramDelta, transformationSignature } from "./lib/mark-relational-core.mjs";

const inputPath=process.env.MARK_RELATIONAL_TRAIN??"artifacts/mark-relational-graphs-v1/mark-relational-train-blind-v1.json";
const outDir=process.env.MARK_RELATIONAL_WORLD_OUT??"artifacts/mark-relational-world-v1";
const minSources=Math.max(2,Number(process.env.MARK_RELATIONAL_MIN_SOURCES??3));
const input=JSON.parse(await fs.readFile(inputPath,"utf8"));
if(input.schema!=="mark_relational_graph_partition_blind_v1"||input.partition!=="train")throw new Error(`expected blind train relational partition; got ${input.schema}/${input.partition}`);
const{blindSha256:suppliedSha,...core}=input,computedSha=crypto.createHash("sha256").update(JSON.stringify(core)).digest("hex");
if(!suppliedSha||suppliedSha!==computedSha)throw new Error("relational train SHA-256 verification failed");
const records=input.records;
if(records.length<4)throw new Error(`relational program discovery needs at least 4 observations; got ${records.length}`);

const sourceCount=values=>new Set(values.map(v=>v.sourceGroupId)).size;
const recurring=(map,make)=>[...map.entries()].map(([signature,items])=>make(signature,items)).filter(item=>item.distinctSourceObjects>=minSources);

const motifMap=new Map();
for(const record of records)for(const motif of record.graph.motifs){if(!motifMap.has(motif.signature))motifMap.set(motif.signature,[]);motifMap.get(motif.signature).push({sourceGroupId:record.sourceGroupId,observationId:record.id,nodeId:motif.nodeId,kind:motif.kind});}
const primitives=recurring(motifMap,(signature,items)=>({signature,count:items.length,distinctSourceObjects:sourceCount(items),examples:items.slice(0,20)})).sort((a,b)=>b.distinctSourceObjects-a.distinctSourceObjects||b.count-a.count||a.signature.localeCompare(b.signature));
primitives.forEach((item,i)=>{item.primitiveId=`RP${String(i+1).padStart(4,"0")}`;});

const stateMap=new Map();
for(const record of records){const key=record.graph.fingerprint;if(!stateMap.has(key))stateMap.set(key,[]);stateMap.get(key).push({sourceGroupId:record.sourceGroupId,observationId:record.id,proposalKind:record.proposalKind,proposalScale:record.proposalScale});}
const relationalStates=recurring(stateMap,(fingerprint,items)=>({fingerprint,count:items.length,distinctSourceObjects:sourceCount(items),examples:items.slice(0,20)})).sort((a,b)=>b.distinctSourceObjects-a.distinctSourceObjects||b.count-a.count||a.fingerprint.localeCompare(b.fingerprint));
relationalStates.forEach((item,i)=>{item.stateId=`RS${String(i+1).padStart(4,"0")}`;});

const area=r=>Math.max(1,r.width*r.height);
const contains=(outer,inner)=>inner.x>=outer.x-1&&inner.y>=outer.y-1&&inner.x+inner.width<=outer.x+outer.width+1&&inner.y+inner.height<=outer.y+outer.height+1;
const bySource=new Map();for(const record of records){if(!bySource.has(record.sourceGroupId))bySource.set(record.sourceGroupId,[]);bySource.get(record.sourceGroupId).push(record);}
const transformationMap=new Map();
for(const[sourceGroupId,group]of bySource){
  for(const child of group){
    const parents=group.filter(candidate=>candidate.id!==child.id&&area(candidate.region)>area(child.region)*1.1&&contains(candidate.region,child.region)).sort((a,b)=>area(a.region)-area(b.region)||a.id.localeCompare(b.id));
    const parent=parents[0];if(!parent)continue;
    const signature=transformationSignature(child.graph,parent.graph),delta=histogramDelta(child.graph,parent.graph);
    if(!transformationMap.has(signature))transformationMap.set(signature,[]);
    transformationMap.get(signature).push({sourceGroupId,fromObservationId:child.id,toObservationId:parent.id,fromScale:child.proposalScale,toScale:parent.proposalScale,delta});
  }
}
const transformations=recurring(transformationMap,(signature,items)=>({signature,count:items.length,distinctSourceObjects:sourceCount(items),delta:items[0]?.delta??null,examples:items.slice(0,20)})).sort((a,b)=>b.distinctSourceObjects-a.distinctSourceObjects||b.count-a.count||a.signature.localeCompare(b.signature));
transformations.forEach((item,i)=>{item.transformationId=`RT${String(i+1).padStart(4,"0")}`;});

const ruleMap=new Map();
function addRule(context,outcome,record,pathIndex){
  if(!ruleMap.has(context))ruleMap.set(context,new Map());const outcomes=ruleMap.get(context);if(!outcomes.has(outcome))outcomes.set(outcome,new Map());
  outcomes.get(outcome).set(record.sourceGroupId,{sourceGroupId:record.sourceGroupId,observationId:record.id,pathIndex});
}
for(const record of records)for(let i=0;i<record.graph.grammarPaths.length;i+=1){
  const p=record.graph.grammarPaths[i];
  addRule(`CENTER:${p.centerKind}|ARM:${p.leftToken}`,p.rightToken,record,i);
  addRule(`CENTER:${p.centerKind}|ARM:${p.rightToken}`,p.leftToken,record,i);
}
const grammarRules=[];
for(const[context,outcomes]of ruleMap){
  const ranked=[...outcomes.entries()].map(([outcome,sources])=>({outcome,distinctSourceObjects:sources.size,examples:[...sources.values()].slice(0,12)})).sort((a,b)=>b.distinctSourceObjects-a.distinctSourceObjects||a.outcome.localeCompare(b.outcome));
  const support=new Set(ranked.flatMap(row=>row.examples.map(e=>e.sourceGroupId))).size;
  if(support<minSources)continue;
  const total=ranked.reduce((s,row)=>s+row.distinctSourceObjects,0),best=ranked[0];
  grammarRules.push({context,predictedOutcome:best.outcome,confidence:+(best.distinctSourceObjects/Math.max(1,total)).toFixed(6),distinctSourceObjects:support,outcomes:ranked.slice(0,12)});
}
grammarRules.sort((a,b)=>b.distinctSourceObjects-a.distinctSourceObjects||b.confidence-a.confidence||a.context.localeCompare(b.context));
grammarRules.forEach((item,i)=>{item.ruleId=`RG${String(i+1).padStart(4,"0")}`;});

const programCore={
  schema:"mark_relational_program_world_blind_v1",generatedAt:new Date().toISOString(),sourceTrainSha256:input.blindSha256,
  corpus:{observations:records.length,sourceObjects:new Set(records.map(r=>r.sourceGroupId)).size,minDistinctSources:minSources},
  primitives,relationalStates,transformations,grammarRules,
  discoveryContract:{
    unit:"relation_and_graph_composition",semanticLabelsAvailable:false,visualFeatureDistanceUsed:false,wholeImageSimilarityUsed:false,
    primitiveRule:"recurrent anonymous radius-1 relational motifs across independent source objects",
    stateRule:"exact canonical topology fingerprints recurring across independent source objects",
    transformationRule:"recurrent graph-relation histogram edits only between physically nested multiscale observations from the same source object",
    grammarRule:"mask one arm of an observed two-edge relational path and learn the other arm from cross-source recurrence",
    prohibitedInference:"no semantic name, culture, language, chronology, institution or presumed negative-control category participates in program discovery",
  },
};
const blindSha256=crypto.createHash("sha256").update(JSON.stringify(programCore)).digest("hex"),artifact={...programCore,blindSha256};
await fs.mkdir(outDir,{recursive:true});
await fs.writeFile(path.join(outDir,"mark-relational-program-world-blind-v1.json"),`${JSON.stringify(artifact,null,2)}\n`);
await fs.writeFile(path.join(outDir,"summary.txt"),[
  `schema=${artifact.schema}`,`train_observations=${artifact.corpus.observations}`,`source_objects=${artifact.corpus.sourceObjects}`,`relational_primitives=${primitives.length}`,`relational_states=${relationalStates.length}`,`nested_transformations=${transformations.length}`,`masked_grammar_rules=${grammarRules.length}`,`blind_sha256=${blindSha256}`,
].join("\n")+"\n");
console.log(`Discovered ${primitives.length} relational primitives, ${relationalStates.length} recurring states, ${transformations.length} nested transformations, and ${grammarRules.length} masked grammar rules`);
console.log(`Relational world SHA-256: ${blindSha256}`);
