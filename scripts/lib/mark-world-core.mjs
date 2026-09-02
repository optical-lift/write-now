export const FEATURE_NAMES = [
  "components","holes","endpoints","junctions","logAspect","orientationCos2","orientationSin2",
  "verticalSymmetry","horizontalSymmetry","inkDensity","componentSizeEntropy","repeatX","repeatY",
  "boundaryComplexity","centroidX","centroidY",
];

const mean = (values) => values.reduce((a,b)=>a+b,0)/Math.max(1,values.length);
const median = (values) => { const s=[...values].sort((a,b)=>a-b),m=Math.floor(s.length/2); return s.length%2?s[m]:(s[m-1]+s[m])/2; };
const quantile = (values,q) => { const s=[...values].sort((a,b)=>a-b); if(!s.length)return 0; const p=(s.length-1)*q,lo=Math.floor(p),hi=Math.ceil(p); return lo===hi?s[lo]:s[lo]+(s[hi]-s[lo])*(p-lo); };
const euclidean = (a,b) => Math.sqrt(a.reduce((sum,value,index)=>sum+(value-b[index])**2,0));

export function worldVector(record) {
  const radians=(record.orientation*Math.PI)/180;
  return [
    record.components,record.holes,record.endpoints,record.junctions,Math.log(Math.max(.05,record.aspect)),
    Math.cos(2*radians),Math.sin(2*radians),record.verticalSymmetry,record.horizontalSymmetry,record.inkDensity,
    record.componentSizeEntropy,record.repeatX,record.repeatY,record.boundaryComplexity,record.centroidX,record.centroidY,
  ];
}

export function fitScaling(records) {
  const matrix=records.map(worldVector);
  const centers=[],scales=[];
  for(let column=0;column<FEATURE_NAMES.length;column+=1){
    const values=matrix.map(row=>row[column]),center=median(values),mad=median(values.map(v=>Math.abs(v-center))),m=mean(values),variance=mean(values.map(v=>(v-m)**2));
    centers.push(center);scales.push(mad>1e-9?mad*1.4826:Math.sqrt(variance)||1);
  }
  return {featureNames:FEATURE_NAMES,centers,scales,clip:8};
}

export function applyScaling(records, scaling) {
  return records.map(record=>worldVector(record).map((value,index)=>Math.max(-scaling.clip,Math.min(scaling.clip,(value-scaling.centers[index])/scaling.scales[index]))));
}

function signedAngleDelta(a,b){let d=b-a;while(d>90)d-=180;while(d<-90)d+=180;return d;}
function complexity(r){return 2*r.components+3*r.holes+r.endpoints+1.5*r.junctions+.5*r.boundaryComplexity;}
function orderedPair(a,b){const ca=complexity(a),cb=complexity(b);if(ca<cb-1e-9)return[a,b];if(cb<ca-1e-9)return[b,a];return a.id.localeCompare(b.id)<=0?[a,b]:[b,a];}

export function operationDelta(from,to){
  return {
    components:to.components-from.components,
    holes:to.holes-from.holes,
    endpoints:to.endpoints-from.endpoints,
    junctions:to.junctions-from.junctions,
    verticalSymmetry:to.verticalSymmetry-from.verticalSymmetry,
    horizontalSymmetry:to.horizontalSymmetry-from.horizontalSymmetry,
    logAspect:Math.log(Math.max(.05,to.aspect))-Math.log(Math.max(.05,from.aspect)),
    orientation:signedAngleDelta(from.orientation,to.orientation),
    inkDensity:to.inkDensity-from.inkDensity,
    componentSizeEntropy:to.componentSizeEntropy-from.componentSizeEntropy,
    repeatX:to.repeatX-from.repeatX,
    repeatY:to.repeatY-from.repeatY,
    boundaryComplexity:to.boundaryComplexity-from.boundaryComplexity,
  };
}

const bucket=(value,step)=>Math.round(value/step)*step;
export function operationSignature(delta){
  const integer=(name,value)=>`${name}${Math.round(value)>=0?"+":""}${Math.round(value)}`;
  return [
    integer("C",delta.components),integer("H",delta.holes),integer("E",delta.endpoints),integer("J",delta.junctions),
    `V${bucket(delta.verticalSymmetry,.15).toFixed(2)}`,`X${bucket(delta.horizontalSymmetry,.15).toFixed(2)}`,
    `A${bucket(delta.logAspect,.2).toFixed(2)}`,`O${bucket(delta.orientation,15).toFixed(0)}`,
    `D${bucket(delta.inkDensity,.1).toFixed(2)}`,`Q${bucket(delta.componentSizeEntropy,.15).toFixed(2)}`,
    `RX${bucket(delta.repeatX,.15).toFixed(2)}`,`RY${bucket(delta.repeatY,.15).toFixed(2)}`,`B${bucket(delta.boundaryComplexity,.2).toFixed(2)}`,
  ].join(":");
}

export function deltaDistance(a,b){
  const terms=[
    a.components-b.components,a.holes-b.holes,(a.endpoints-b.endpoints)/2,(a.junctions-b.junctions)/2,
    (a.verticalSymmetry-b.verticalSymmetry)/.2,(a.horizontalSymmetry-b.horizontalSymmetry)/.2,
    (a.logAspect-b.logAspect)/.25,signedAngleDelta(b.orientation,a.orientation)/20,(a.inkDensity-b.inkDensity)/.12,
    (a.componentSizeEntropy-b.componentSizeEntropy)/.2,(a.repeatX-b.repeatX)/.2,(a.repeatY-b.repeatY)/.2,(a.boundaryComplexity-b.boundaryComplexity)/.25,
  ];
  return Math.sqrt(terms.reduce((sum,value)=>sum+value*value,0));
}

function primitiveSignature(r){
  const endpointBand=r.endpoints<=1?"E0-1":r.endpoints<=3?"E2-3":r.endpoints<=6?"E4-6":"E7+";
  const junctionBand=r.junctions===0?"J0":r.junctions<=2?"J1-2":"J3+";
  const sym=Math.max(r.verticalSymmetry,r.horizontalSymmetry)>=.82?"SYMH":Math.max(r.verticalSymmetry,r.horizontalSymmetry)>=.58?"SYMM":"SYML";
  const aspect=r.aspect<.65?"TALL":r.aspect>1.55?"WIDE":"BAL";
  const repeat=Math.max(r.repeatX,r.repeatY)>=.72?"REPH":Math.max(r.repeatX,r.repeatY)>=.45?"REPM":"REPL";
  return `C${r.components}:H${r.holes}:${endpointBand}:${junctionBand}:${sym}:${aspect}:${repeat}`;
}

function labelPropagation(records,edges){
  const labels=new Map(records.map(r=>[r.id,r.id]));
  const adjacency=new Map(records.map(r=>[r.id,[]]));
  for(const edge of edges){adjacency.get(edge.a)?.push({id:edge.b,weight:edge.weight});adjacency.get(edge.b)?.push({id:edge.a,weight:edge.weight});}
  for(let iteration=0;iteration<50;iteration+=1){let changed=false;for(const record of [...records].sort((a,b)=>a.id.localeCompare(b.id))){
    const scores=new Map();for(const neighbor of adjacency.get(record.id)??[]){const label=labels.get(neighbor.id);scores.set(label,(scores.get(label)??0)+neighbor.weight);}
    if(!scores.size)continue;const best=[...scores.entries()].sort((a,b)=>b[1]-a[1]||a[0].localeCompare(b[0]))[0][0];
    if(labels.get(record.id)!==best){labels.set(record.id,best);changed=true;}
  }if(!changed)break;}
  const groups=new Map();for(const record of records){const label=labels.get(record.id);if(!groups.has(label))groups.set(label,[]);groups.get(label).push(record.id);}
  return [...groups.values()].map(ids=>ids.sort()).sort((a,b)=>b.length-a.length||a[0].localeCompare(b[0]));
}

function meanDelta(edges){const keys=Object.keys(edges[0].delta);return Object.fromEntries(keys.map(key=>[key,+mean(edges.map(edge=>edge.delta[key])).toFixed(6)]));}
function averageVector(vectors){return vectors[0].map((_,index)=>+mean(vectors.map(v=>v[index])).toFixed(6));}
function acceptanceEnvelope(vectors,prototype){
  const distances=vectors.map(vector=>euclidean(vector,prototype));
  const med=median(distances),mad=median(distances.map(d=>Math.abs(d-med))),q90=quantile(distances,.9),max=Math.max(...distances,0);
  const robust=med+3*Math.max(mad*1.4826,.15);
  const radius=Math.max(.75,q90*1.35,robust,Math.min(max*1.15,12));
  return {acceptanceRadius:+radius.toFixed(6),memberDistanceMedian:+med.toFixed(6),memberDistanceQ90:+q90.toFixed(6),memberDistanceMax:+max.toFixed(6)};
}

export function buildWorldModel(records,{neighborK=10,minDistinctSources=3}={}){
  if(records.length<4)throw new Error(`world model requires at least 4 observations; got ${records.length}`);
  const scaling=fitScaling(records),scaled=applyScaling(records,scaling),indexById=new Map(records.map((r,i)=>[r.id,i]));
  const nearest=records.map((record,i)=>records.map((other,j)=>({id:other.id,j,distance:i===j?Infinity:euclidean(scaled[i],scaled[j])})).filter(x=>Number.isFinite(x.distance)).sort((a,b)=>a.distance-b.distance||a.id.localeCompare(b.id)).slice(0,Math.min(neighborK,records.length-1)));
  const ranks=nearest.map(list=>new Map(list.map((item,index)=>[item.id,index+1])));
  const similarity=[];const seen=new Set();
  for(let i=0;i<records.length;i+=1)for(const item of nearest[i]){
    const key=[records[i].id,item.id].sort().join("::");if(seen.has(key))continue;seen.add(key);
    const j=item.j,reverse=ranks[j].get(records[i].id)??neighborK+1,mutual=reverse<=neighborK;
    if(!mutual&&item.distance>2.5)continue;
    const rankWeight=1/(1+Math.min(ranks[i].get(item.id)??neighborK+1,reverse));
    similarity.push({a:records[i].id,b:item.id,distance:+item.distance.toFixed(6),mutual,weight:+((mutual?2:1)+rankWeight).toFixed(6),crossSource:records[i].sourceGroupId!==records[j].sourceGroupId});
  }
  similarity.sort((a,b)=>b.weight-a.weight||a.distance-b.distance||a.a.localeCompare(b.a)||a.b.localeCompare(b.b));
  const communities=labelPropagation(records,similarity.filter(edge=>edge.mutual)).map((ids,index)=>({familyId:`F${String(index+1).padStart(4,"0")}`,ids,size:ids.length,distinctSourceObjects:new Set(ids.map(id=>records[indexById.get(id)].sourceGroupId)).size}));

  const opEdges=[];const opSeen=new Set();
  for(let i=0;i<records.length;i+=1)for(const item of nearest[i]){
    const other=records[item.j];if(records[i].sourceGroupId===other.sourceGroupId)continue;
    const pair=[records[i].id,other.id].sort().join("::");if(opSeen.has(pair))continue;opSeen.add(pair);
    const [from,to]=orderedPair(records[i],other),delta=operationDelta(from,to);
    opEdges.push({from:from.id,to:to.id,sourceGroups:[from.sourceGroupId,to.sourceGroupId].sort(),delta,signature:operationSignature(delta),neighborDistance:+item.distance.toFixed(6)});
  }
  const opMap=new Map();for(const edge of opEdges){if(!opMap.has(edge.signature))opMap.set(edge.signature,[]);opMap.get(edge.signature).push(edge);}
  const operations=[...opMap.entries()].map(([signature,edges])=>({
    operationId:"",signature,edgeCount:edges.length,distinctSourceObjects:new Set(edges.flatMap(edge=>edge.sourceGroups)).size,meanDelta:meanDelta(edges),examples:edges.sort((a,b)=>a.neighborDistance-b.neighborDistance).slice(0,16).map(({from,to,sourceGroups,neighborDistance})=>({from,to,sourceGroups,neighborDistance})),
  })).filter(op=>op.edgeCount>=2&&op.distinctSourceObjects>=minDistinctSources).sort((a,b)=>b.distinctSourceObjects-a.distinctSourceObjects||b.edgeCount-a.edgeCount||a.signature.localeCompare(b.signature)).slice(0,160);
  operations.forEach((op,index)=>{op.operationId=`OP${String(index+1).padStart(4,"0")}`;});

  const primitiveMap=new Map();for(const record of records){const signature=primitiveSignature(record);if(!primitiveMap.has(signature))primitiveMap.set(signature,[]);primitiveMap.get(signature).push(record);}
  const primitives=[...primitiveMap.entries()].map(([signature,members])=>({
    primitiveId:"",signature,count:members.length,distinctSourceObjects:new Set(members.map(m=>m.sourceGroupId)).size,ids:members.map(m=>m.id).sort(),
  })).filter(p=>p.count>=3&&p.distinctSourceObjects>=minDistinctSources).sort((a,b)=>b.distinctSourceObjects-a.distinctSourceObjects||b.count-a.count||a.signature.localeCompare(b.signature)).slice(0,160);
  primitives.forEach((p,index)=>{p.primitiveId=`P${String(index+1).padStart(4,"0")}`;});

  const families=communities.map(family=>{
    const vectors=family.ids.map(id=>scaled[indexById.get(id)]),prototypeScaled=averageVector(vectors);
    return {...family,prototypeScaled,...acceptanceEnvelope(vectors,prototypeScaled)};
  });
  const reusedAssignments=primitives.reduce((sum,p)=>sum+p.count,0)+operations.reduce((sum,o)=>sum+o.edgeCount*2,0);
  return {
    schema:"mark_blind_world_model_v1",
    scaling,
    discoveryContract:{unit:"observable_configuration",categoryLabelsAvailable:false,neighborK,minDistinctSources,communityRule:"deterministic weighted label propagation over mutual structural-neighbor graph",operationRule:"recurrent quantized deltas among cross-source local neighbors",primitiveRule:"recurrent coarse structural states across independent source objects",abstentionRule:"nearest family is accepted only inside that family's training-derived robust distance envelope"},
    corpus:{observations:records.length,sourceObjects:new Set(records.map(r=>r.sourceGroupId)).size},
    families,primitives,operations,
    graph:{similarityEdges:similarity.slice(0,Math.min(5000,similarity.length))},
    compressionDiagnostics:{literalFeatureCells:records.length*FEATURE_NAMES.length,recurrentVocabularyEntries:primitives.length+operations.length,reusedAssignments,reusePerVocabularyEntry:+(reusedAssignments/Math.max(1,primitives.length+operations.length)).toFixed(6)},
  };
}

export function predictAgainstWorld(model,holdoutRecords){
  const scaled=applyScaling(holdoutRecords,model.scaling);
  const familyPredictions=holdoutRecords.map((record,index)=>{
    const ranked=model.families.map(family=>({familyId:family.familyId,distance:+euclidean(scaled[index],family.prototypeScaled).toFixed(6),acceptanceRadius:family.acceptanceRadius??0})).sort((a,b)=>a.distance-b.distance||a.familyId.localeCompare(b.familyId));
    const nearest=ranked[0]??null,accepted=Boolean(nearest&&nearest.distance<=nearest.acceptanceRadius);
    return {id:record.id,sourceGroupId:record.sourceGroupId,proposalKind:record.proposalKind??null,proposalScale:record.proposalScale??null,status:accepted?"accepted":"abstain",acceptedFamilyId:accepted?nearest.familyId:null,nearestFamily:nearest,predictedFamilies:ranked.slice(0,5)};
  });
  const operationPredictions=model.operations.slice(0,100).map(operation=>{
    const candidates=[];
    for(let i=0;i<holdoutRecords.length;i+=1)for(let j=i+1;j<holdoutRecords.length;j+=1){
      if(holdoutRecords[i].sourceGroupId===holdoutRecords[j].sourceGroupId)continue;
      const[from,to]=orderedPair(holdoutRecords[i],holdoutRecords[j]),delta=operationDelta(from,to);
      candidates.push({from:from.id,to:to.id,sourceGroups:[from.sourceGroupId,to.sourceGroupId].sort(),distance:+deltaDistance(delta,operation.meanDelta).toFixed(6)});
    }
    candidates.sort((a,b)=>a.distance-b.distance||a.from.localeCompare(b.from)||a.to.localeCompare(b.to));
    return {operationId:operation.operationId,signature:operation.signature,predictedPairs:candidates.slice(0,12)};
  });
  return {familyPredictions,operationPredictions};
}
