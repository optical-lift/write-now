import crypto from "node:crypto";
import fs from "node:fs/promises";
import path from "node:path";
import { chromium } from "playwright";

const url = process.env.GLYPH_ATLAS_URL ?? "http://127.0.0.1:3000/glyph-atlas";
const blindOut = process.env.MARK_WHITE_PAINT_GLYPH_BLIND_OUT ?? "artifacts/mark-white-paint-glyph-transfer-v2/blind";
const contextOut = process.env.MARK_WHITE_PAINT_GLYPH_CONTEXT_OUT ?? "artifact-staging/white-paint-glyph-context-v2";

function sha(value) {
  return crypto.createHash("sha256").update(JSON.stringify(value)).digest("hex");
}

await fs.mkdir(blindOut, { recursive: true });
await fs.mkdir(contextOut, { recursive: true });
const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1440, height: 1200 } });
await page.goto(url, { waitUntil: "networkidle", timeout: 120_000 });
await page.waitForFunction(() => {
  const cards = [...document.querySelectorAll(".glyphCard")];
  return cards.length === 300 && cards.every((card) => !card.textContent?.includes("ANALYZING"));
}, { timeout: 120_000 });
await page.evaluate(() => document.fonts?.ready);

const raw = await page.$$eval(".glyphCard", (cards) => {
  const idx = (x, y, w) => y * w + x;
  const cc = (mask, w, h, eight = true) => {
    const seen = new Uint8Array(mask.length); let count = 0;
    for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
      const s = idx(x, y, w); if (!mask[s] || seen[s]) continue;
      count++; const q = [[x, y]]; seen[s] = 1;
      for (let p = 0; p < q.length; p++) {
        const [cx, cy] = q[p];
        for (let dy = -1; dy <= 1; dy++) for (let dx = -1; dx <= 1; dx++) {
          if (!dx && !dy) continue; if (!eight && dx && dy) continue;
          const nx = cx + dx, ny = cy + dy;
          if (nx < 0 || ny < 0 || nx >= w || ny >= h) continue;
          const n = idx(nx, ny, w); if (mask[n] && !seen[n]) { seen[n] = 1; q.push([nx, ny]); }
        }
      }
    }
    return count;
  };
  const holes = (mask, w, h) => {
    const seen = new Uint8Array(mask.length); let n = 0;
    for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
      const s = idx(x, y, w); if (mask[s] || seen[s]) continue;
      let edge = false; const q = [[x, y]]; seen[s] = 1;
      for (let p = 0; p < q.length; p++) {
        const [cx, cy] = q[p]; if (!cx || !cy || cx === w - 1 || cy === h - 1) edge = true;
        for (const [dx, dy] of [[1,0],[-1,0],[0,1],[0,-1]]) {
          const nx = cx + dx, ny = cy + dy;
          if (nx < 0 || ny < 0 || nx >= w || ny >= h) continue;
          const z = idx(nx, ny, w); if (!mask[z] && !seen[z]) { seen[z] = 1; q.push([nx, ny]); }
        }
      }
      if (!edge) n++;
    }
    return n;
  };
  const thin = (source, w, h) => {
    const mask = source.slice();
    const ns = (x, y) => [mask[idx(x,y-1,w)],mask[idx(x+1,y-1,w)],mask[idx(x+1,y,w)],mask[idx(x+1,y+1,w)],mask[idx(x,y+1,w)],mask[idx(x-1,y+1,w)],mask[idx(x-1,y,w)],mask[idx(x-1,y-1,w)]];
    const tr = (a) => a.reduce((n, v, i) => n + (v === 0 && a[(i+1)%8] === 1 ? 1 : 0), 0);
    for (let it = 0; it < 64; it++) {
      let changed = false;
      for (let pass = 0; pass < 2; pass++) {
        const rm = [];
        for (let y = 1; y < h-1; y++) for (let x = 1; x < w-1; x++) {
          const z = idx(x,y,w); if (!mask[z]) continue; const p = ns(x,y); const b = p.reduce((a,v)=>a+v,0); const a = tr(p);
          if (b < 2 || b > 6 || a !== 1) continue;
          const [p2,,p4,,p6,,p8] = p;
          const ok = pass === 0 ? p2*p4*p6 === 0 && p4*p6*p8 === 0 : p2*p4*p8 === 0 && p2*p6*p8 === 0;
          if (ok) rm.push(z);
        }
        if (rm.length) { changed = true; rm.forEach((z)=>mask[z]=0); }
      }
      if (!changed) break;
    }
    return mask;
  };
  const symmetry = (mask, w, h, vertical) => {
    let u=0,m=0;
    for (let y=0;y<h;y++) for(let x=0;x<w;x++) {
      const a=mask[idx(x,y,w)], b=mask[idx(vertical?w-1-x:x,vertical?y:h-1-y,w)];
      if(a||b)u++; if(a!==b)m++;
    }
    return u ? Math.max(0,1-m/u) : 0;
  };
  const orientation = (mask,w,h) => {
    let n=0,mx=0,my=0; for(let y=0;y<h;y++)for(let x=0;x<w;x++)if(mask[idx(x,y,w)]){n++;mx+=x;my+=y;}
    if(!n)return 0; mx/=n;my/=n;let xx=0,yy=0,xy=0;
    for(let y=0;y<h;y++)for(let x=0;x<w;x++)if(mask[idx(x,y,w)]){const dx=x-mx,dy=y-my;xx+=dx*dx;yy+=dy*dy;xy+=dx*dy;}
    let a=0.5*Math.atan2(2*xy,xx-yy); if(a<0)a+=Math.PI; return a;
  };
  const boundaryComplexity = (mask,w,h) => {
    let ink=0,b=0; for(let y=0;y<h;y++)for(let x=0;x<w;x++)if(mask[idx(x,y,w)]){ink++; if([[1,0],[-1,0],[0,1],[0,-1]].some(([dx,dy])=>{const nx=x+dx,ny=y+dy;return nx<0||ny<0||nx>=w||ny>=h||!mask[idx(nx,ny,w)];}))b++;} return ink?b/ink:0;
  };
  const maskHash = (mask,w,h) => {
    let hsh=2166136261>>>0; const mix=(v)=>{hsh^=v&255;hsh=Math.imul(hsh,16777619)>>>0;}; mix(w);mix(h); for(const v of mask)mix(v); return hsh.toString(16).padStart(8,"0");
  };
  const clusterJunctions = (sk,w,h) => {
    const deg = new Uint8Array(sk.length), jm = new Uint8Array(sk.length); const endpoints=[]; let d2=0, turns=0;
    for(let y=1;y<h-1;y++)for(let x=1;x<w-1;x++){
      const z=idx(x,y,w);if(!sk[z])continue;const ns=[];
      for(let dy=-1;dy<=1;dy++)for(let dx=-1;dx<=1;dx++)if(dx||dy){if(sk[idx(x+dx,y+dy,w)])ns.push([dx,dy]);}
      deg[z]=ns.length;if(ns.length===1)endpoints.push([x,y]);if(ns.length>=3)jm[z]=1;
      if(ns.length===2){d2++;const [a,b]=ns;const dot=(a[0]*b[0]+a[1]*b[1])/(Math.hypot(...a)*Math.hypot(...b));if(dot>-0.75)turns++;}
    }
    const seen=new Uint8Array(jm.length), clusters=[];
    for(let y=1;y<h-1;y++)for(let x=1;x<w-1;x++){const s=idx(x,y,w);if(!jm[s]||seen[s])continue;const q=[[x,y]];seen[s]=1;let sx=0,sy=0,n=0,max=0;
      for(let p=0;p<q.length;p++){const[cx,cy]=q[p],z=idx(cx,cy,w);sx+=cx;sy+=cy;n++;max=Math.max(max,deg[z]);for(let dy=-1;dy<=1;dy++)for(let dx=-1;dx<=1;dx++)if(dx||dy){const nx=cx+dx,ny=cy+dy;if(nx<1||ny<1||nx>=w-1||ny>=h-1)continue;const zz=idx(nx,ny,w);if(jm[zz]&&!seen[zz]){seen[zz]=1;q.push([nx,ny]);}}}
      clusters.push({x:sx/n,y:sy/n,maxDegree:max});
    }
    return {endpoints,clusters,turnRate:d2?turns/d2:0};
  };
  return cards.map((card) => {
    const atlasId = card.querySelector(".glyphIdentity strong")?.textContent?.trim() ?? "";
    const mark = card.querySelector(".glyphMark"); const char=mark?.textContent??""; const font=mark?getComputedStyle(mark).fontFamily:"serif";
    const canvas=document.createElement("canvas");canvas.width=112;canvas.height=112;const ctx=canvas.getContext("2d",{willReadFrequently:true});
    if(!ctx)return {atlasId,supported:false};ctx.clearRect(0,0,112,112);ctx.fillStyle="#111";ctx.textAlign="center";ctx.textBaseline="middle";ctx.font=`76px ${font}`;ctx.fillText(char,56,58);
    const px=ctx.getImageData(0,0,112,112).data;let minX=112,minY=112,maxX=-1,maxY=-1;
    for(let y=0;y<112;y++)for(let x=0;x<112;x++)if(px[(y*112+x)*4+3]>=48){minX=Math.min(minX,x);minY=Math.min(minY,y);maxX=Math.max(maxX,x);maxY=Math.max(maxY,y);}
    if(maxX<0)return {atlasId,supported:false};const w=maxX-minX+3,h=maxY-minY+3,mask=new Uint8Array(w*h);let ink=0;
    for(let y=minY-1;y<=maxY+1;y++)for(let x=minX-1;x<=maxX+1;x++){if(x<0||y<0||x>=112||y>=112)continue;if(px[(y*112+x)*4+3]>=96){mask[idx(x-(minX-1),y-(minY-1),w)]=1;ink++;}}
    const sk=thin(mask,w,h), top=clusterJunctions(sk,w,h), componentCount=cc(mask,w,h,true), holeCount=holes(mask,w,h), angle=orientation(mask,w,h);
    const diag=Math.max(1,Math.hypot(w,h)), dists=[]; for(const j of top.clusters)for(const e of top.endpoints)dists.push(Math.hypot(j.x-e[0],j.y-e[1])/diag);
    const minJ=dists.length?Math.min(...dists):null, meanJ=dists.length?dists.reduce((a,v)=>a+v,0)/dists.length:null;
    const d3=top.clusters.filter(j=>j.maxDegree===3).length,d4=top.clusters.filter(j=>j.maxDegree>=4).length,maxDegree=top.clusters.reduce((m,j)=>Math.max(m,j.maxDegree),0);
    let operation="other";
    if(componentCount>1)operation="multi";
    else if(holeCount>0&&top.endpoints.length>0)operation="loop_continue";
    else if(holeCount>0&&top.endpoints.length===0)operation="close";
    else if(maxDegree>=4)operation="cross";
    else if(top.clusters.length>0&&top.endpoints.length>=3)operation="branch";
    else if(top.clusters.length===0&&top.endpoints.length===2&&top.turnRate>=0.08)operation="turn";
    else if(top.clusters.length===0&&top.endpoints.length===2)operation="persist";
    const relation=minJ==null?null:(minJ<=0.22?"near_terminal":"interior");
    return {atlasId,supported:true,rasterHash:maskHash(mask,w,h),features:{components:componentCount,holes:holeCount,endpoints:top.endpoints.length,junctionClusters:top.clusters.length,degree3JunctionClusters:d3,degree4PlusJunctionClusters:d4,maxJunctionDegree:maxDegree,turnRate:top.turnRate,minJunctionEndpointRatio:minJ,meanJunctionEndpointRatio:meanJ,repetitionDegree:Math.min(5,d3),closure:holeCount>0?"closed":"open",operation,relation,logAspect:Math.log(w/Math.max(1,h)),verticalSymmetry:symmetry(mask,w,h,true),horizontalSymmetry:symmetry(mask,w,h,false),cos2Orientation:Math.cos(2*angle),sin2Orientation:Math.sin(2*angle),density:ink/Math.max(1,w*h),boundaryComplexity:boundaryComplexity(mask,w,h)}};
  });
});
await browser.close();

if (raw.length !== 300) throw new Error(`expected 300 glyphs, got ${raw.length}`);
const supported = raw.filter(r=>r.supported);
const groups = new Map();
for (const r of supported) { if(!groups.has(r.rasterHash))groups.set(r.rasterHash,[]); groups.get(r.rasterHash).push(r.atlasId); }
const suspicious = new Set([...groups.values()].filter(ids=>ids.length>=4).flat());
const eligible = supported.filter(r=>!suspicious.has(r.atlasId));
if (eligible.length < 180) throw new Error(`too few eligible glyphs after raster collision guard: ${eligible.length}`);
const salt=crypto.randomBytes(32).toString("hex");
const mappings=eligible.map(r=>({atlasId:r.atlasId,blindId:`B${crypto.createHash("sha256").update(`${salt}|${r.atlasId}`).digest("hex").slice(0,16).toUpperCase()}`}));
const bByG=new Map(mappings.map(x=>[x.atlasId,x.blindId]));
const records=eligible.map(r=>({id:bByG.get(r.atlasId),features:r.features})).sort((a,b)=>a.id.localeCompare(b.id));
const core={schema:"mark_white_paint_glyph_proxy_blind_v2",corpusKind:"standardized_display_proxy",captured:raw.length,supported:supported.length,eligible:eligible.length,excludedRasterCollisions:suspicious.size,records};
const blindSha256=sha(core);await fs.writeFile(path.join(blindOut,"white-paint-glyph-proxy-blind.json"),JSON.stringify({...core,blindSha256},null,2)+"\n");
await fs.writeFile(path.join(blindOut,"capture-summary.txt"),`captured=${raw.length}\nsupported=${supported.length}\neligible=${eligible.length}\ncollision_excluded=${suspicious.size}\nblind_corpus_sha256=${blindSha256}\n`);
const context={schema:"mark_white_paint_glyph_proxy_context_map_v2",blindCorpusSha256:blindSha256,mappings:mappings.sort((a,b)=>a.blindId.localeCompare(b.blindId))};
await fs.writeFile(path.join(contextOut,"white-paint-glyph-context-map.json"),JSON.stringify(context,null,2)+"\n");
console.log(JSON.stringify({blindSha256,eligible:eligible.length,excluded:suspicious.size},null,2));
