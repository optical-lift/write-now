import crypto from "node:crypto";
import fs from "node:fs/promises";
import path from "node:path";

const blindPath=process.env.MARK_WHITE_PAINT_PHYSICAL_BLIND??"artifacts/mark-white-paint-physical-witness-v3/blind/physical-witness-blind.json";
const protocolPath=process.env.MARK_WHITE_PAINT_PHYSICAL_PROTOCOL??"research/mark/discovery-experiments/white-paint-physical-witness-v3.protocol.json";
const outDir=process.env.MARK_WHITE_PAINT_PHYSICAL_FROZEN_OUT??"artifacts/mark-white-paint-physical-witness-v3/frozen";
const sha=v=>crypto.createHash("sha256").update(JSON.stringify(v)).digest("hex");
const mean=a=>a.length?a.reduce((s,v)=>s+v,0)/a.length:0;
const std=a=>{if(!a.length)return 0;const m=mean(a);return Math.sqrt(mean(a.map(v=>(v-m)**2)));};
const OPS=["persist","turn","branch","cross","close","loop_continue","multi","other"];
const protocol=JSON.parse(await fs.readFile(protocolPath,"utf8"));const blind=JSON.parse(await fs.readFile(blindPath,"utf8"));
const coreCheck={...blind};delete coreCheck.blindCorpusSha256;if(sha(coreCheck)!==blind.blindCorpusSha256)throw new Error("blind corpus SHA mismatch");
const sources=blind.records.map(r=>{
  const n=Math.max(1,r.regions.length),opFreq=Object.fromEntries(OPS.map(op=>[op,r.regions.filter(x=>x.operation===op).length/n]));
  const relationEligible=r.regions.filter(x=>x.relation!=null),near=relationEligible.filter(x=>x.relation==="near_terminal").length,interior=relationEligible.filter(x=>x.relation==="interior").length;
  const degrees=r.regions.map(x=>x.repetitionDegree),positiveDegrees=degrees.filter(x=>x>0);
  const white={
    ...Object.fromEntries(OPS.map(op=>[`op_${op}`,opFreq[op]])),
    closureRate:r.regions.filter(x=>x.closure==="closed").length/n,
    nearTerminalRate:relationEligible.length?near/relationEligible.length:0,
    interiorRate:relationEligible.length?interior/relationEligible.length:0,
    relationEligibleRate:relationEligible.length/n,
    repetitionMean:mean(degrees),
    repetitionStd:std(degrees),
    positiveRepetitionFraction:positiveDegrees.length/n,
    meanTurnRate:mean(r.regions.map(x=>x.turnRate)),
    meanEndpoints:mean(r.regions.map(x=>x.endpoints)),
    meanJunctionClusters:mean(r.regions.map(x=>x.junctionClusters))
  };
  const appearance={...r.appearance};
  return{sourceId:r.sourceId,imageSha256:r.imageSha256,eligibleRegions:r.eligibleRegions,white,appearance,diagnostics:{operationCounts:Object.fromEntries(OPS.map(op=>[op,r.regions.filter(x=>x.operation===op).length])),openRegions:r.regions.filter(x=>x.closure==="open").length,closedRegions:r.regions.filter(x=>x.closure==="closed").length,distinctPositiveDegrees:[...new Set(positiveDegrees)].sort((a,b)=>a-b),positiveDegreeRegions:positiveDegrees.length,nearTerminalRegions:near,interiorRegions:interior}};
});
const blindCore={schema:"mark_white_paint_physical_witness_frozen_v3",experimentId:protocol.experimentId,parentProxyBlindTransferSha256:protocol.parent.proxyBlindTransferSha256,blindCorpusSha256:blind.blindCorpusSha256,sourceCount:sources.length,regionCount:blind.records.reduce((s,r)=>s+r.regions.length,0),sources:sources.sort((a,b)=>a.sourceId.localeCompare(b.sourceId)),claimBoundary:protocol.claimBoundary};
const blindFeatureSha256=sha(blindCore);const packet={...blindCore,blindFeatureSha256};await fs.mkdir(outDir,{recursive:true});await fs.writeFile(path.join(outDir,"physical-witness-frozen.json"),JSON.stringify(packet,null,2)+"\n");
const globalOps=Object.fromEntries(OPS.map(op=>[op,blind.records.reduce((s,r)=>s+r.regions.filter(x=>x.operation===op).length,0)]));const open=blind.records.reduce((s,r)=>s+r.regions.filter(x=>x.closure==="open").length,0),closed=blind.records.reduce((s,r)=>s+r.regions.filter(x=>x.closure==="closed").length,0);
await fs.writeFile(path.join(outDir,"blind-summary.txt"),[`source_count=${sources.length}`,`region_count=${packet.regionCount}`,`open_regions=${open}`,`closed_regions=${closed}`,...OPS.map(op=>`operation_${op}=${globalOps[op]}`),`blind_feature_sha256=${blindFeatureSha256}`].join("\n")+"\n");console.log(JSON.stringify({sourceCount:sources.length,regionCount:packet.regionCount,globalOps,open,closed,blindFeatureSha256},null,2));
