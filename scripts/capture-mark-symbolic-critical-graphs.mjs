import crypto from 'node:crypto';
import fs from 'node:fs/promises';
import path from 'node:path';
import { chromium } from 'playwright';

const url = process.env.GLYPH_ATLAS_URL ?? 'http://127.0.0.1:3000/glyph-atlas';
const outDir = process.env.MARK_SYMBOLIC_GRAPH_OUT ?? 'artifacts/mark-symbolic-specificity-v1/glyphs';
const sha = (v) => crypto.createHash('sha256').update(JSON.stringify(v)).digest('hex');
await fs.mkdir(outDir,{recursive:true});

const browser = await chromium.launch({headless:true});
const page = await browser.newPage({viewport:{width:1440,height:1200}});
await page.goto(url,{waitUntil:'networkidle',timeout:120000});
await page.waitForFunction(() => {
  const cards=[...document.querySelectorAll('.glyphCard')];
  return cards.length===300 && cards.every(c=>!c.textContent?.includes('ANALYZING'));
},{timeout:120000});
await page.evaluate(()=>document.fonts?.ready);

const raw = await page.$$eval('.glyphCard',(cards)=>{
  const idx=(x,y,w)=>y*w+x;
  const neighbors8=(x,y,w,h)=>{const a=[];for(let dy=-1;dy<=1;dy++)for(let dx=-1;dx<=1;dx++){if(!dx&&!dy)continue;const nx=x+dx,ny=y+dy;if(nx>=0&&ny>=0&&nx<w&&ny<h)a.push([nx,ny]);}return a;};
  const thin=(source,w,h)=>{
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
  };
  const maskHash=(mask,w,h)=>{let hsh=2166136261>>>0;const mix=(v)=>{hsh^=v&255;hsh=Math.imul(hsh,16777619)>>>0;};mix(w);mix(h);for(const v of mask)mix(v);return hsh.toString(16).padStart(8,'0');};
  const buildGraph=(sk,w,h)=>{
    const degree=new Uint8Array(sk.length);
    for(let y=0;y<h;y++)for(let x=0;x<w;x++){const z=idx(x,y,w);if(!sk[z])continue;let d=0;for(const [nx,ny] of neighbors8(x,y,w,h))if(sk[idx(nx,ny,w)])d++;degree[z]=d;}
    const owner=new Int32Array(sk.length);owner.fill(-1);const nodes=[];
    const seenJ=new Uint8Array(sk.length);
    for(let y=0;y<h;y++)for(let x=0;x<w;x++){
      const s=idx(x,y,w);if(!sk[s]||degree[s]<3||seenJ[s])continue;
      const q=[[x,y]];seenJ[s]=1;const pix=[];let sx=0,sy=0;
      for(let p=0;p<q.length;p++){
        const [cx,cy]=q[p],cz=idx(cx,cy,w);pix.push(cz);sx+=cx;sy+=cy;
        for(const [nx,ny] of neighbors8(cx,cy,w,h)){const nz=idx(nx,ny,w);if(sk[nz]&&degree[nz]>=3&&!seenJ[nz]){seenJ[nz]=1;q.push([nx,ny]);}}
      }
      const id=nodes.length;nodes.push({id,kind:'JUNCTION',x:sx/pix.length,y:sy/pix.length,pixels:pix});for(const z of pix)owner[z]=id;
    }
    for(let y=0;y<h;y++)for(let x=0;x<w;x++){
      const z=idx(x,y,w);if(!sk[z]||degree[z]>1||owner[z]>=0)continue;const id=nodes.length;nodes.push({id,kind:'ENDPOINT',x,y,pixels:[z]});owner[z]=id;
    }
    const pixelEdgeKey=(a,b)=>a<b?`${a}:${b}`:`${b}:${a}`;const used=new Set();const edges=[];let unresolved=0,arms=0;
    for(const n of nodes){
      for(const pz of n.pixels){const px=pz%w,py=Math.floor(pz/w);
        for(const [nx,ny] of neighbors8(px,py,w,h)){
          const nz=idx(nx,ny,w);if(!sk[nz])continue;if(owner[nz]===n.id)continue;const firstKey=pixelEdgeKey(pz,nz);if(used.has(firstKey))continue;arms++;
          let prev=pz,cur=nz,steps=1;used.add(firstKey);let target=owner[cur];let guard=0;
          while(target<0&&guard++<sk.length){
            const cx=cur%w,cy=Math.floor(cur/w);const cand=[];
            for(const [xx,yy] of neighbors8(cx,cy,w,h)){const zz=idx(xx,yy,w);if(!sk[zz]||zz===prev)continue;const k=pixelEdgeKey(cur,zz);if(!used.has(k))cand.push(zz);}
            if(cand.length!==1)break;const nxt=cand[0];used.add(pixelEdgeKey(cur,nxt));prev=cur;cur=nxt;steps++;target=owner[cur];
          }
          if(target<0){unresolved++;continue;}
          const a=n.id,b=target;if(a===b&&steps<=2)continue;const na=nodes[a],nb=nodes[b];edges.push({a,b,pathSteps:steps,chordPixels:Math.hypot(na.x-nb.x,na.y-nb.y),selfLoop:a===b});
        }
      }
    }
    const clean=[];const seenEdge=new Set();
    for(const e of edges){const key=`${Math.min(e.a,e.b)}|${Math.max(e.a,e.b)}|${e.pathSteps}|${Math.round(e.chordPixels*1000)}`;if(seenEdge.has(key))continue;seenEdge.add(key);clean.push(e);}
    const graphDegree=new Array(nodes.length).fill(0);for(const e of clean){if(e.a===e.b)graphDegree[e.a]+=2;else{graphDegree[e.a]++;graphDegree[e.b]++;}}
    const outNodes=nodes.map(n=>({id:n.id,kind:n.kind,x:n.x,y:n.y,degree:graphDegree[n.id]}));
    return {nodes:outNodes,edges:clean,unresolvedArms:unresolved,totalArms:arms,traceResolution:arms?1-unresolved/arms:1};
  };
  return cards.map(card=>{
    const atlasId=card.querySelector('.glyphIdentity strong')?.textContent?.trim()??'';const mark=card.querySelector('.glyphMark');const char=mark?.textContent??'';const font=mark?getComputedStyle(mark).fontFamily:'serif';
    const canvas=document.createElement('canvas');canvas.width=112;canvas.height=112;const ctx=canvas.getContext('2d',{willReadFrequently:true});if(!ctx)return {atlasId,supported:false};ctx.clearRect(0,0,112,112);ctx.fillStyle='#111';ctx.textAlign='center';ctx.textBaseline='middle';ctx.font=`76px ${font}`;ctx.fillText(char,56,58);
    const px=ctx.getImageData(0,0,112,112).data;let minX=112,minY=112,maxX=-1,maxY=-1;
    for(let y=0;y<112;y++)for(let x=0;x<112;x++)if(px[(y*112+x)*4+3]>=48){minX=Math.min(minX,x);minY=Math.min(minY,y);maxX=Math.max(maxX,x);maxY=Math.max(maxY,y);}
    if(maxX<0)return {atlasId,supported:false};const w=maxX-minX+3,h=maxY-minY+3,mask=new Uint8Array(w*h);
    for(let y=minY-1;y<=maxY+1;y++)for(let x=minX-1;x<=maxX+1;x++){if(x<0||y<0||x>=112||y>=112)continue;if(px[(y*112+x)*4+3]>=96)mask[idx(x-(minX-1),y-(minY-1),w)]=1;}
    const sk=thin(mask,w,h),graph=buildGraph(sk,w,h);return {atlasId,supported:true,rasterHash:maskHash(mask,w,h),width:w,height:h,...graph};
  });
});
await browser.close();
if(raw.length!==300)throw new Error(`expected 300 glyphs, got ${raw.length}`);
const supported=raw.filter(r=>r.supported&&r.nodes.length>=2&&r.edges.length>=1&&r.traceResolution>=0.90);
const groups=new Map();for(const r of supported){if(!groups.has(r.rasterHash))groups.set(r.rasterHash,[]);groups.get(r.rasterHash).push(r.atlasId);}const suspicious=new Set([...groups.values()].filter(ids=>ids.length>=4).flat());
const eligible=supported.filter(r=>!suspicious.has(r.atlasId));if(eligible.length<180)throw new Error(`too few eligible glyph graphs: ${eligible.length}`);
const salt=crypto.randomBytes(32).toString('hex');const records=eligible.map(r=>({id:`B${crypto.createHash('sha256').update(`${salt}|${r.atlasId}`).digest('hex').slice(0,16).toUpperCase()}`,width:r.width,height:r.height,nodes:r.nodes,edges:r.edges,traceResolution:r.traceResolution})).sort((a,b)=>a.id.localeCompare(b.id));
const core={schema:'mark_symbolic_critical_graph_corpus_v1',corpusKind:'standardized_symbolic_proxy',captured:raw.length,supported:supported.length,eligible:eligible.length,excludedRasterCollisions:suspicious.size,records};const corpusSha256=sha(core);
await fs.writeFile(path.join(outDir,'symbolic-critical-graphs.json'),JSON.stringify({...core,corpusSha256})+'\n');
await fs.writeFile(path.join(outDir,'summary.txt'),`captured=${raw.length}\nsupported=${supported.length}\neligible=${eligible.length}\ncollision_excluded=${suspicious.size}\ncorpus_sha256=${corpusSha256}\n`);
console.log(JSON.stringify({eligible:eligible.length,corpusSha256},null,2));
