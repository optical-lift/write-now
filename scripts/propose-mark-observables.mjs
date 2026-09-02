import crypto from "node:crypto";
import fs from "node:fs/promises";
import path from "node:path";
import sharp from "sharp";

const harvestPath = process.env.MARK_HARVEST_BLIND ?? "artifacts/mark-harvest-v1/mark-harvested-sources-blind-v1.json";
const outDir = process.env.MARK_PROPOSAL_OUT ?? "artifacts/mark-conveyor-input-v1";
const harvest = JSON.parse(await fs.readFile(harvestPath, "utf8"));
if (harvest.schema !== "mark_harvested_sources_blind_v1") throw new Error(`unsupported harvest schema ${harvest.schema}`);
const { blindSha256: suppliedHarvestSha, ...harvestCore } = harvest;
const computedHarvestSha = crypto.createHash("sha256").update(JSON.stringify(harvestCore)).digest("hex");
if (!suppliedHarvestSha || suppliedHarvestSha !== computedHarvestSha) throw new Error("harvest blind SHA-256 verification failed");

function otsu(gray) {
  const hist = new Array(256).fill(0); for (const v of gray) hist[v] += 1;
  let sum = 0; for (let i=0;i<256;i+=1) sum += i*hist[i];
  let wB=0,sumB=0,best=127,max=-1;
  for (let t=0;t<256;t+=1) { wB+=hist[t]; if(!wB)continue; const wF=gray.length-wB; if(!wF)break; sumB+=t*hist[t]; const mB=sumB/wB,mF=(sum-sumB)/wF,between=wB*wF*(mB-mF)**2; if(between>max){max=between;best=t;} }
  return best;
}
function components(mask,w,h) {
  const seen=new Uint8Array(mask.length), result=[];
  const neighbors=(x,y)=>[[x-1,y-1],[x,y-1],[x+1,y-1],[x-1,y],[x+1,y],[x-1,y+1],[x,y+1],[x+1,y+1]];
  for(let y=0;y<h;y+=1)for(let x=0;x<w;x+=1){const i=y*w+x;if(!mask[i]||seen[i])continue;const q=[[x,y]];seen[i]=1;let minX=x,maxX=x,minY=y,maxY=y,pixels=0;
    for(let p=0;p<q.length;p+=1){const[cx,cy]=q[p];pixels+=1;minX=Math.min(minX,cx);maxX=Math.max(maxX,cx);minY=Math.min(minY,cy);maxY=Math.max(maxY,cy);for(const[nx,ny]of neighbors(cx,cy)){if(nx<0||ny<0||nx>=w||ny>=h)continue;const ni=ny*w+nx;if(mask[ni]&&!seen[ni]){seen[ni]=1;q.push([nx,ny]);}}}
    result.push({x:minX,y:minY,width:maxX-minX+1,height:maxY-minY+1,pixels});
  }
  return result;
}
function padRegion(region,w,h,pad=4){const x=Math.max(0,region.x-pad),y=Math.max(0,region.y-pad),right=Math.min(w,region.x+region.width+pad),bottom=Math.min(h,region.y+region.height+pad);return{x,y,width:right-x,height:bottom-y};}
function union(a,b){const x=Math.min(a.x,b.x),y=Math.min(a.y,b.y),right=Math.max(a.x+a.width,b.x+b.width),bottom=Math.max(a.y+a.height,b.y+b.height);return{x,y,width:right-x,height:bottom-y};}
const keyOf=(r)=>`${r.x},${r.y},${r.width},${r.height}`;
const observationId=(sourceGroupId,kind,region)=>`O${crypto.createHash("sha256").update(`${sourceGroupId}|${kind}|${keyOf(region)}`).digest("hex").slice(0,16).toUpperCase()}`;

const scoredSources = harvest.sources.map(source=>({sourceGroupId:source.sourceGroupId,score:crypto.createHash("sha256").update(`mark-conveyor-holdout-v1|${source.captureToken}`).digest("hex")})).sort((a,b)=>a.score.localeCompare(b.score));
const holdoutCount = harvest.sources.length >= 5 ? Math.max(1, Math.round(harvest.sources.length*0.2)) : 0;
const holdoutSources = new Set(scoredSources.slice(0,holdoutCount).map(x=>x.sourceGroupId));
const laneFor=(sourceGroupId)=>holdoutSources.has(sourceGroupId)?"holdout":"train";

await fs.mkdir(path.join(outDir,"captures"),{recursive:true});
const blindSources=[]; const observations=[]; const proposalAudit=[];
for(const source of harvest.sources){
  const absolute=path.resolve(path.dirname(harvestPath),source.capturePath);
  const bytes=await fs.readFile(absolute);
  const target=path.posix.join("captures",path.basename(source.capturePath));
  await fs.writeFile(path.join(outDir,target),bytes);
  blindSources.push({...source,lane:laneFor(source.sourceGroupId),capturePath:target});
  const{data,info}=await sharp(bytes).greyscale().raw().toBuffer({resolveWithObject:true});
  const threshold=otsu(data),mask=new Uint8Array(data.length);for(let i=0;i<data.length;i+=1)mask[i]=data[i]<=threshold?1:0;
  const minPixels=Math.max(12,Math.round(info.width*info.height*0.0005));
  const found=components(mask,info.width,info.height).filter(c=>c.pixels>=minPixels&&c.width>=2&&c.height>=2).sort((a,b)=>a.x-b.x||a.y-b.y);
  const candidates=[];
  candidates.push({kind:"whole_capture",scale:"object",region:{x:0,y:0,width:info.width,height:info.height}});
  for(const component of found)candidates.push({kind:"connected_component",scale:"local",region:padRegion(component,info.width,info.height)});
  for(let i=0;i<found.length-1;i+=1)candidates.push({kind:"adjacent_component_neighborhood",scale:"neighborhood",region:padRegion(union(found[i],found[i+1]),info.width,info.height,6)});
  for(let i=0;i<found.length-2;i+=1)candidates.push({kind:"three_component_field",scale:"field",region:padRegion(union(union(found[i],found[i+1]),found[i+2]),info.width,info.height,6)});
  const unique=new Map();for(const candidate of candidates){const key=keyOf(candidate.region);if(!unique.has(key))unique.set(key,candidate);}
  for(const candidate of unique.values()){
    const id=observationId(source.sourceGroupId,candidate.kind,candidate.region);
    observations.push({id,sourceGroupId:source.sourceGroupId,lane:laneFor(source.sourceGroupId),region:candidate.region,segmentation:{polarity:"dark_on_light",threshold:"otsu"},proposalKind:candidate.kind,proposalScale:candidate.scale});
    proposalAudit.push({id,sourceGroupId:source.sourceGroupId,proposalKind:candidate.kind,proposalScale:candidate.scale,region:candidate.region});
  }
}
if(observations.length<10)throw new Error(`proposer produced too few observations: ${observations.length}`);
const blindCore={
  schema:"mark_observable_input_blind_v1",corpusKind:harvest.corpusKind,generatedAt:new Date().toISOString(),lanePolicy:"deterministic_source_level_80_20_holdout_from_blind_capture_token",sourceHarvestSha256:harvest.blindSha256,
  sources:blindSources.sort((a,b)=>a.sourceGroupId.localeCompare(b.sourceGroupId)),observations:observations.sort((a,b)=>a.id.localeCompare(b.id)),
  blindnessContract:{unit:"machine_proposed_observable_configuration",permitted:["opaque_ids","source_independence","capture_adapter","local_capture_path","salted_capture_token","region","segmentation","proposal_scale","proposal_kind","train_or_holdout_lane"],forbidden:["object_category","culture","language","sign_name","reading","meaning","chronology","geography","institution","catalog_identity","scholarly_interpretation"]},
};
const blindInputSha256=crypto.createHash("sha256").update(JSON.stringify(blindCore)).digest("hex");
const blind={...blindCore,blindInputSha256};
await fs.writeFile(path.join(outDir,"mark-observable-input-blind-v1.json"),`${JSON.stringify(blind,null,2)}\n`);
const auditCore={schema:"mark_observable_proposals_blind_v1",generatedAt:blind.generatedAt,sealedBlindInputSha256:blindInputSha256,sourceHarvestSha256:harvest.blindSha256,proposals:proposalAudit.sort((a,b)=>a.id.localeCompare(b.id))};
const auditSha256=crypto.createHash("sha256").update(JSON.stringify(auditCore)).digest("hex");
await fs.writeFile(path.join(outDir,"mark-observable-proposals-blind-v1.json"),`${JSON.stringify({...auditCore,blindSha256:auditSha256},null,2)}\n`);
await fs.writeFile(path.join(outDir,"summary.txt"),[`schema=${blind.schema}`,`source_objects=${blind.sources.length}`,`proposed_observations=${blind.observations.length}`,`train_observations=${blind.observations.filter(o=>o.lane==="train").length}`,`holdout_observations=${blind.observations.filter(o=>o.lane==="holdout").length}`,`blind_sha256=${blindInputSha256}`].join("\n")+"\n");
console.log(`Proposed ${blind.observations.length} multiscale observables from ${blind.sources.length} anonymous source objects`);
console.log(`Proposal blind SHA-256: ${blindInputSha256}`);
