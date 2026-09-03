import crypto from "node:crypto";
import fs from "node:fs/promises";
import path from "node:path";
import sharp from "sharp";

const rosterPath = process.env.MARK_WHITE_PAINT_PHYSICAL_ROSTER ?? "research/mark/discovery-experiments/white-paint-physical-witness-v3.witnesses.json";
const protocolPath = process.env.MARK_WHITE_PAINT_PHYSICAL_PROTOCOL ?? "research/mark/discovery-experiments/white-paint-physical-witness-v3.protocol.json";
const blindOut = process.env.MARK_WHITE_PAINT_PHYSICAL_BLIND_OUT ?? "artifacts/mark-white-paint-physical-witness-v3/blind";
const contextOut = process.env.MARK_WHITE_PAINT_PHYSICAL_CONTEXT_OUT ?? "artifact-staging/white-paint-physical-witness-v3-context";

const shaBytes = (value) => crypto.createHash("sha256").update(value).digest("hex");
const shaJson = (value) => shaBytes(JSON.stringify(value));
const mean = (xs) => xs.length ? xs.reduce((a,b)=>a+b,0)/xs.length : 0;
const std = (xs) => { if(!xs.length) return 0; const m=mean(xs); return Math.sqrt(mean(xs.map(v=>(v-m)**2))); };
const median = (xs) => { if(!xs.length) return 0; const a=[...xs].sort((x,y)=>x-y); const m=Math.floor(a.length/2); return a.length%2?a[m]:(a[m-1]+a[m])/2; };
const idx=(x,y,w)=>y*w+x;

function connectedComponents(mask,w,h,eight=true,collect=false){
  const seen=new Uint8Array(mask.length); const groups=[]; let count=0;
  for(let y=0;y<h;y++)for(let x=0;x<w;x++){
    const s=idx(x,y,w); if(!mask[s]||seen[s])continue; count++; const q=[[x,y]]; seen[s]=1; const pix=[];
    for(let p=0;p<q.length;p++){
      const [cx,cy]=q[p]; if(collect)pix.push(idx(cx,cy,w));
      for(let dy=-1;dy<=1;dy++)for(let dx=-1;dx<=1;dx++){
        if(!dx&&!dy)continue; if(!eight&&dx&&dy)continue; const nx=cx+dx,ny=cy+dy;
        if(nx<0||ny<0||nx>=w||ny>=h)continue; const z=idx(nx,ny,w); if(mask[z]&&!seen[z]){seen[z]=1;q.push([nx,ny]);}
      }
    }
    if(collect)groups.push(pix);
  }
  return collect?groups:count;
}

function removeSmall(mask,w,h,minPixels){
  const out=mask.slice();
  for(const group of connectedComponents(mask,w,h,true,true)) if(group.length<minPixels) for(const z of group) out[z]=0;
  return out;
}

function holes(mask,w,h){
  const seen=new Uint8Array(mask.length); let n=0;
  for(let y=0;y<h;y++)for(let x=0;x<w;x++){
    const s=idx(x,y,w); if(mask[s]||seen[s])continue; let edge=false; const q=[[x,y]]; seen[s]=1;
    for(let p=0;p<q.length;p++){
      const [cx,cy]=q[p]; if(cx===0||cy===0||cx===w-1||cy===h-1)edge=true;
      for(const [dx,dy] of [[1,0],[-1,0],[0,1],[0,-1]]){const nx=cx+dx,ny=cy+dy;if(nx<0||ny<0||nx>=w||ny>=h)continue;const z=idx(nx,ny,w);if(!mask[z]&&!seen[z]){seen[z]=1;q.push([nx,ny]);}}
    }
    if(!edge)n++;
  }
  return n;
}

function thin(source,w,h){
  const mask=source.slice();
  const ns=(x,y)=>[mask[idx(x,y-1,w)],mask[idx(x+1,y-1,w)],mask[idx(x+1,y,w)],mask[idx(x+1,y+1,w)],mask[idx(x,y+1,w)],mask[idx(x-1,y+1,w)],mask[idx(x-1,y,w)],mask[idx(x-1,y-1,w)]];
  const tr=(a)=>a.reduce((n,v,i)=>n+(v===0&&a[(i+1)%8]===1?1:0),0);
  for(let it=0;it<64;it++){
    let changed=false;
    for(let pass=0;pass<2;pass++){
      const rm=[];
      for(let y=1;y<h-1;y++)for(let x=1;x<w-1;x++){
        const z=idx(x,y,w);if(!mask[z])continue;const p=ns(x,y),b=p.reduce((a,v)=>a+v,0),a=tr(p);if(b<2||b>6||a!==1)continue;
        const [p2,,p4,,p6,,p8]=p;const ok=pass===0?p2*p4*p6===0&&p4*p6*p8===0:p2*p4*p8===0&&p2*p6*p8===0;if(ok)rm.push(z);
      }
      if(rm.length){changed=true;for(const z of rm)mask[z]=0;}
    }
    if(!changed)break;
  }
  return mask;
}

function clusterJunctions(sk,w,h){
  const deg=new Uint8Array(sk.length),jm=new Uint8Array(sk.length),endpoints=[];let d2=0,turns=0,skeletonPixels=0;
  for(let y=1;y<h-1;y++)for(let x=1;x<w-1;x++){
    const z=idx(x,y,w);if(!sk[z])continue;skeletonPixels++;const ns=[];
    for(let dy=-1;dy<=1;dy++)for(let dx=-1;dx<=1;dx++)if(dx||dy){if(sk[idx(x+dx,y+dy,w)])ns.push([dx,dy]);}
    deg[z]=ns.length;if(ns.length===1)endpoints.push([x,y]);if(ns.length>=3)jm[z]=1;
    if(ns.length===2){d2++;const[a,b]=ns;const dot=(a[0]*b[0]+a[1]*b[1])/(Math.hypot(a[0],a[1])*Math.hypot(b[0],b[1]));if(dot>-0.75)turns++;}
  }
  const seen=new Uint8Array(jm.length),clusters=[];
  for(let y=1;y<h-1;y++)for(let x=1;x<w-1;x++){
    const s=idx(x,y,w);if(!jm[s]||seen[s])continue;const q=[[x,y]];seen[s]=1;let sx=0,sy=0,n=0,max=0;
    for(let p=0;p<q.length;p++){
      const[cx,cy]=q[p],z=idx(cx,cy,w);sx+=cx;sy+=cy;n++;max=Math.max(max,deg[z]);
      for(let dy=-1;dy<=1;dy++)for(let dx=-1;dx<=1;dx++)if(dx||dy){const nx=cx+dx,ny=cy+dy;if(nx<1||ny<1||nx>=w-1||ny>=h-1)continue;const zz=idx(nx,ny,w);if(jm[zz]&&!seen[zz]){seen[zz]=1;q.push([nx,ny]);}}
    }
    clusters.push({x:sx/n,y:sy/n,maxDegree:max});
  }
  return{endpoints,clusters,turnRate:d2?turns/d2:0,skeletonPixels};
}

function sobel(gray,w,h){
  const mag=new Float32Array(gray.length),ang=new Float32Array(gray.length),vals=[];
  const gxK=[-1,0,1,-2,0,2,-1,0,1],gyK=[-1,-2,-1,0,0,0,1,2,1];
  for(let y=1;y<h-1;y++)for(let x=1;x<w-1;x++){
    let gx=0,gy=0,k=0;for(let dy=-1;dy<=1;dy++)for(let dx=-1;dx<=1;dx++,k++){const v=gray[idx(x+dx,y+dy,w)];gx+=v*gxK[k];gy+=v*gyK[k];}
    const m=Math.hypot(gx,gy);mag[idx(x,y,w)]=m;ang[idx(x,y,w)]=Math.atan2(gy,gx);vals.push(m);
  }
  return{mag,ang,vals};
}

function percentile(xs,p){if(!xs.length)return 0;const a=[...xs].sort((x,y)=>x-y);return a[Math.min(a.length-1,Math.max(0,Math.floor((a.length-1)*p)))];}

function objectBBox(gray,w,h){
  const corner=[];const s=Math.max(4,Math.floor(Math.min(w,h)*0.04));
  for(const [x0,y0] of [[0,0],[w-s,0],[0,h-s],[w-s,h-s]])for(let y=y0;y<y0+s;y++)for(let x=x0;x<x0+s;x++)corner.push(gray[idx(x,y,w)]);
  const bg=median(corner),allStd=std(Array.from(gray)),thr=Math.max(12,allStd*0.30);let minX=w,minY=h,maxX=-1,maxY=-1,n=0;
  for(let y=0;y<h;y++)for(let x=0;x<w;x++)if(Math.abs(gray[idx(x,y,w)]-bg)>=thr){minX=Math.min(minX,x);minY=Math.min(minY,y);maxX=Math.max(maxX,x);maxY=Math.max(maxY,y);n++;}
  if(maxX<0||n<0.08*w*h)return{x:0,y:0,w,h};
  const bw=maxX-minX+1,bh=maxY-minY+1;if(bw*bh<0.20*w*h)return{x:0,y:0,w,h};
  return{x:minX,y:minY,w:bw,h:bh};
}

function cropRaw(gray,w,box){const out=new Uint8Array(box.w*box.h);for(let y=0;y<box.h;y++)for(let x=0;x<box.w;x++)out[idx(x,y,box.w)]=gray[idx(box.x+x,box.y+y,w)];return out;}

function tileFeature(gray,w,h,x0,y0,size,protocol){
  const t=new Uint8Array(size*size);const vals=[];for(let y=0;y<size;y++)for(let x=0;x<size;x++){const v=gray[idx(x0+x,y0+y,w)];t[idx(x,y,size)]=v;vals.push(v);}
  const med=median(vals),sd=std(vals),darkThr=med-Math.max(10,0.65*sd);let mask=new Uint8Array(size*size);let ink=0;
  for(let i=0;i<t.length;i++)if(t[i]<=darkThr){mask[i]=1;ink++;}
  let density=ink/mask.length,maskKind="dark";
  const edge=sobel(t,size,size);
  if(density<0.015){const q=Math.max(24,percentile(edge.vals,0.85));mask=new Uint8Array(size*size);ink=0;for(let i=0;i<mask.length;i++)if(edge.mag[i]>=q){mask[i]=1;ink++;}density=ink/mask.length;maskKind="sobel";}
  mask=removeSmall(mask,size,size,protocol.localMask.smallComponentRemovalPixels);ink=mask.reduce((a,v)=>a+v,0);density=ink/mask.length;
  const[minD,maxD]=protocol.localMask.eligibleForegroundDensity;if(density<minD||density>maxD)return null;
  const sk=thin(mask,size,size),top=clusterJunctions(sk,size,size);if(top.skeletonPixels<protocol.localMask.minimumSkeletonPixels||top.skeletonPixels>protocol.localMask.maximumSkeletonFraction*mask.length)return null;
  const componentCount=connectedComponents(mask,size,size,true,false),holeCount=holes(mask,size,size),diag=Math.hypot(size,size),dists=[];
  for(const j of top.clusters)for(const e of top.endpoints)dists.push(Math.hypot(j.x-e[0],j.y-e[1])/diag);
  const minJ=dists.length?Math.min(...dists):null,meanJ=dists.length?mean(dists):null,d3=top.clusters.filter(j=>j.maxDegree===3).length,d4=top.clusters.filter(j=>j.maxDegree>=4).length,maxDegree=top.clusters.reduce((m,j)=>Math.max(m,j.maxDegree),0);
  let operation="other";if(componentCount>1)operation="multi";else if(holeCount>0&&top.endpoints.length>0)operation="loop_continue";else if(holeCount>0&&top.endpoints.length===0)operation="close";else if(maxDegree>=4)operation="cross";else if(top.clusters.length>0&&top.endpoints.length>=3)operation="branch";else if(top.clusters.length===0&&top.endpoints.length===2&&top.turnRate>=protocol.whitePaintClassifier.turnRateThreshold)operation="turn";else if(top.clusters.length===0&&top.endpoints.length===2)operation="persist";
  const relation=minJ==null?null:(minJ<=protocol.whitePaintClassifier.relationNearTerminalThreshold?"near_terminal":"interior");
  return{operation,relation,closure:holeCount>0?"closed":"open",repetitionDegree:Math.min(5,d3),components:componentCount,holes:holeCount,endpoints:top.endpoints.length,junctionClusters:top.clusters.length,degree3JunctionClusters:d3,degree4PlusJunctionClusters:d4,maxJunctionDegree:maxDegree,turnRate:top.turnRate,minJunctionEndpointRatio:minJ,meanJunctionEndpointRatio:meanJ,foregroundDensity:density,localContrast:sd,maskKind};
}

function appearanceFeatures(gray,w,h){
  const vals=Array.from(gray),g=sobel(gray,w,h),hist=new Array(8).fill(0);let total=0;
  for(let i=0;i<g.mag.length;i++){const m=g.mag[i];if(!m)continue;let a=g.ang[i];if(a<0)a+=Math.PI*2;const b=Math.min(7,Math.floor((a/(Math.PI*2))*8));hist[b]+=m;total+=m;}
  if(total)for(let i=0;i<hist.length;i++)hist[i]/=total;
  return{grayscaleMean:mean(vals),grayscaleStd:std(vals),gradientMean:mean(g.vals),gradientStd:std(g.vals),gradientOrientationHistogram:hist};
}

const roster=JSON.parse(await fs.readFile(rosterPath,"utf8"));const protocol=JSON.parse(await fs.readFile(protocolPath,"utf8"));
await fs.mkdir(blindOut,{recursive:true});await fs.mkdir(contextOut,{recursive:true});
const salt=crypto.randomBytes(32).toString("hex"),blindRecords=[],contextMappings=[],failures=[];
for(const systemRow of roster.systems){
  for(const objectId of systemRow.objectIds){
    try{
      const api=roster.provider.objectApiTemplate.replace("{objectId}",String(objectId));const metaRes=await fetch(api,{headers:{"user-agent":"MarkPhysicalWitness/3"}});if(!metaRes.ok)throw new Error(`metadata HTTP ${metaRes.status}`);const meta=await metaRes.json();
      if(meta.isPublicDomain!==true)throw new Error("not public domain");const imageUrl=meta.primaryImage||meta.primaryImageSmall;if(!imageUrl)throw new Error("no primary image");const imgRes=await fetch(imageUrl,{headers:{"user-agent":"MarkPhysicalWitness/3"}});if(!imgRes.ok)throw new Error(`image HTTP ${imgRes.status}`);const imageBytes=Buffer.from(await imgRes.arrayBuffer());const imageSha256=shaBytes(imageBytes);
      const normalized=await sharp(imageBytes).rotate().greyscale().resize({width:protocol.physicalNormalization.maxDimension,height:protocol.physicalNormalization.maxDimension,fit:"inside",withoutEnlargement:true}).raw().toBuffer({resolveWithObject:true});
      const full=Uint8Array.from(normalized.data),fw=normalized.info.width,fh=normalized.info.height;let box=objectBBox(full,fw,fh);const ix=Math.floor(box.w*protocol.physicalNormalization.interiorInsetFraction),iy=Math.floor(box.h*protocol.physicalNormalization.interiorInsetFraction);box={x:box.x+ix,y:box.y+iy,w:box.w-2*ix,h:box.h-2*iy};if(box.w<protocol.physicalNormalization.tileSize||box.h<protocol.physicalNormalization.tileSize)throw new Error("interior too small after inset");
      const interior=cropRaw(full,fw,box),regions=[],contrasts=[];const size=protocol.physicalNormalization.tileSize,stride=protocol.physicalNormalization.tileStride;
      for(let y=0;y+size<=box.h;y+=stride)for(let x=0;x+size<=box.w;x+=stride){const f=tileFeature(interior,box.w,box.h,x,y,size,protocol);if(f){regions.push(f);contrasts.push(f.localContrast);}}
      if(regions.length<protocol.objectAggregation.minimumEligibleRegionsPerObject)throw new Error(`only ${regions.length} eligible local regions`);
      const appearance=appearanceFeatures(interior,box.w,box.h);appearance.localContrastMean=mean(contrasts);appearance.localContrastStd=std(contrasts);
      const sourceId=`W${crypto.createHash("sha256").update(`${salt}|${objectId}`).digest("hex").slice(0,16).toUpperCase()}`;
      blindRecords.push({sourceId,imageSha256,normalizedDimensions:[box.w,box.h],eligibleRegions:regions.length,appearance,regions});
      contextMappings.push({sourceId,system:systemRow.system,providerObjectId:objectId,title:meta.title??null,culture:meta.culture??null,objectDate:meta.objectDate??null,medium:meta.medium??null,department:meta.department??null,objectURL:meta.objectURL??null,imageURL:imageUrl,imageSha256});
    }catch(error){failures.push({system:systemRow.system,objectId,error:String(error?.message??error)});}
  }
}
for(const systemRow of roster.systems){const n=contextMappings.filter(x=>x.system===systemRow.system).length;if(n<roster.minimumAcceptedPerSystem)throw new Error(`system ${systemRow.system} accepted only ${n}, minimum ${roster.minimumAcceptedPerSystem}`);}
blindRecords.sort((a,b)=>a.sourceId.localeCompare(b.sourceId));contextMappings.sort((a,b)=>a.sourceId.localeCompare(b.sourceId));
const blindCore={schema:"mark_white_paint_physical_witness_blind_v3",experimentId:protocol.experimentId,corpusKind:"physical_museum_witness",parentProxyBlindTransferSha256:protocol.parent.proxyBlindTransferSha256,records:blindRecords};const blindCorpusSha256=shaJson(blindCore);const blindPacket={...blindCore,blindCorpusSha256};
const contextCore={schema:"mark_white_paint_physical_witness_context_map_v3",experimentId:protocol.experimentId,blindCorpusSha256,mappings:contextMappings,acquisitionFailures:failures};const contextSha256=shaJson(contextCore);
await fs.writeFile(path.join(blindOut,"physical-witness-blind.json"),JSON.stringify(blindPacket,null,2)+"\n");await fs.writeFile(path.join(contextOut,"physical-witness-context-map.json"),JSON.stringify({...contextCore,contextSha256},null,2)+"\n");
const bySystem=Object.fromEntries(roster.systems.map(s=>[s.system,contextMappings.filter(x=>x.system===s.system).length]));const totalRegions=blindRecords.reduce((a,r)=>a+r.eligibleRegions,0);
await fs.writeFile(path.join(blindOut,"capture-summary.txt"),[`accepted_objects=${blindRecords.length}`,`eligible_regions=${totalRegions}`,`acquisition_failures=${failures.length}`,...Object.entries(bySystem).map(([k,v])=>`system_${k}=${v}`),`blind_corpus_sha256=${blindCorpusSha256}`].join("\n")+"\n");
console.log(JSON.stringify({acceptedObjects:blindRecords.length,eligibleRegions:totalRegions,failures,bySystem,blindCorpusSha256},null,2));
