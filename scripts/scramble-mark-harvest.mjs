import crypto from "node:crypto";
import fs from "node:fs/promises";
import path from "node:path";
import sharp from "sharp";

const inputPath=process.env.MARK_HARVEST_BLIND ?? "artifacts/mark-harvest-v1/mark-harvested-sources-blind-v1.json";
const outDir=process.env.MARK_SCRAMBLE_HARVEST_OUT ?? "artifacts/mark-spatial-scramble-harvest-v1";
const grid=Math.max(2,Math.min(8,Number(process.env.MARK_SCRAMBLE_GRID??4)));
const input=JSON.parse(await fs.readFile(inputPath,"utf8"));
if(input.schema!=="mark_harvested_sources_blind_v1")throw new Error(`unsupported harvest ${input.schema}`);
const{blindSha256,...rest}=input;const computed=crypto.createHash("sha256").update(JSON.stringify(rest)).digest("hex");if(!blindSha256||blindSha256!==computed)throw new Error("harvest SHA-256 verification failed");
function seeded(seedText){let state=Number.parseInt(crypto.createHash("sha256").update(seedText).digest("hex").slice(0,8),16)>>>0;return()=>{state=(state+0x6D2B79F5)>>>0;let t=state;t=Math.imul(t^(t>>>15),t|1);t^=t+Math.imul(t^(t>>>7),t|61);return((t^(t>>>14))>>>0)/4294967296;};}
function permutation(n,seed){const out=Array.from({length:n},(_,i)=>i),rng=seeded(seed);for(let i=n-1;i>0;i-=1){const j=Math.floor(rng()*(i+1));[out[i],out[j]]=[out[j],out[i]];}return out;}
async function scramble(bytes,seed){
  const{data,info}=await sharp(bytes).greyscale().raw().toBuffer({resolveWithObject:true});
  const width=Math.floor(info.width/grid)*grid,height=Math.floor(info.height/grid)*grid;
  if(width<grid*4||height<grid*4)throw new Error(`capture too small for ${grid}x${grid} scramble: ${info.width}x${info.height}`);
  const tileW=width/grid,tileH=height/grid,out=Buffer.alloc(width*height),order=permutation(grid*grid,seed);
  for(let dest=0;dest<order.length;dest+=1){const src=order[dest],dx=(dest%grid)*tileW,dy=Math.floor(dest/grid)*tileH,sx=(src%grid)*tileW,sy=Math.floor(src/grid)*tileH;for(let y=0;y<tileH;y+=1){const from=(sy+y)*info.width+sx,to=(dy+y)*width+dx;data.copy(out,to,from,from+tileW);}}
  return sharp(out,{raw:{width,height,channels:1}}).png().toBuffer();
}
await fs.mkdir(path.join(outDir,"captures"),{recursive:true});
const sources=[];
for(const source of input.sources.filter(row=>row.lane==="train")){
  const absolute=path.resolve(path.dirname(inputPath),source.capturePath),bytes=await fs.readFile(absolute),scrambled=await scramble(bytes,`${input.blindSha256}|${source.continuityToken}|spatial-scramble-v1`);
  const capturePath=path.posix.join("captures",`${source.sourceGroupId}.png`);await fs.writeFile(path.join(outDir,capturePath),scrambled);
  const captureToken=crypto.createHash("sha256").update("mark-spatial-scramble-v1|").update(scrambled).digest("hex");
  sources.push({...source,lane:"train",capturePath,captureMime:"image/png",captureToken});
}
if(sources.length<4)throw new Error(`spatial scramble needs at least four train sources; got ${sources.length}`);
const core={schema:"mark_harvested_sources_blind_v1",corpusKind:"spatial_scramble_negative_control",generatedAt:new Date().toISOString(),sources:sources.sort((a,b)=>a.sourceGroupId.localeCompare(b.sourceGroupId)),deduplicationContract:input.deduplicationContract,blindnessContract:{...input.blindnessContract,negativeControl:true,spatialScramble:`deterministic_${grid}x${grid}_tile_permutation`,contextLabelsAvailable:false}};
const outSha=crypto.createHash("sha256").update(JSON.stringify(core)).digest("hex"),artifact={...core,blindSha256:outSha};
await fs.writeFile(path.join(outDir,"mark-harvested-sources-blind-v1.json"),`${JSON.stringify(artifact,null,2)}\n`);
await fs.writeFile(path.join(outDir,"summary.txt"),[`schema=${artifact.schema}`,`source_objects=${sources.length}`,`grid=${grid}`,`blind_sha256=${outSha}`].join("\n")+"\n");
console.log(`Built ${grid}x${grid} spatial-scramble negative control for ${sources.length} train sources`);
