const N8=[[-1,-1],[0,-1],[1,-1],[-1,0],[1,0],[-1,1],[0,1],[1,1]];
const N4=[[0,-1],[-1,0],[1,0],[0,1]];

function forEachNeighborIndex(index,w,h,offsets,visit){
  const x=index%w,y=Math.floor(index/w);
  for(const[dx,dy]of offsets){const nx=x+dx,ny=y+dy;if(nx>=0&&ny>=0&&nx<w&&ny<h)visit(ny*w+nx);}
}

function components(mask,w,h,value,offsets,interiorOnly=false,includeSizes=false){
  const seen=new Uint8Array(mask.length),queue=new Int32Array(mask.length),sizes=[];let count=0;
  for(let start=0;start<mask.length;start+=1){
    if(seen[start]||mask[start]!==value)continue;
    let head=0,tail=0,size=0;queue[tail++]=start;seen[start]=1;
    const sx=start%w,sy=Math.floor(start/w);let touchesBorder=sx===0||sy===0||sx===w-1||sy===h-1;
    while(head<tail){
      const cur=queue[head++];size+=1;
      forEachNeighborIndex(cur,w,h,offsets,ni=>{
        if(seen[ni]||mask[ni]!==value)return;seen[ni]=1;const nx=ni%w,ny=Math.floor(ni/w);if(nx===0||ny===0||nx===w-1||ny===h-1)touchesBorder=true;queue[tail++]=ni;
      });
    }
    if(!interiorOnly||!touchesBorder){count+=1;if(includeSizes)sizes.push(size);}
  }
  return includeSizes?{count,sizes}:count;
}

function otsu(gray){
  const hist=new Array(256).fill(0);for(const value of gray)hist[value]+=1;const total=gray.length;let sum=0;
  for(let i=0;i<256;i+=1)sum+=i*hist[i];let sumB=0,weightB=0,best=127,maxBetween=-1;
  for(let t=0;t<256;t+=1){weightB+=hist[t];if(!weightB)continue;const weightF=total-weightB;if(!weightF)break;sumB+=t*hist[t];const meanB=sumB/weightB,meanF=(sum-sumB)/weightF,between=weightB*weightF*(meanB-meanF)**2;if(between>maxBetween){maxBetween=between;best=t;}}
  return best;
}

function thin(input,w,h){
  const pixels=Uint8Array.from(input),remove=new Uint8Array(input.length);const at=(x,y)=>(x<0||y<0||x>=w||y>=h?0:pixels[y*w+x]);let changed=true,iterations=0;
  while(changed&&iterations++<120){changed=false;for(const phase of[0,1]){remove.fill(0);let removeCount=0;
    for(let y=1;y<h-1;y+=1)for(let x=1;x<w-1;x+=1){if(!at(x,y))continue;const p2=at(x,y-1),p3=at(x+1,y-1),p4=at(x+1,y),p5=at(x+1,y+1),p6=at(x,y+1),p7=at(x-1,y+1),p8=at(x-1,y),p9=at(x-1,y-1),ns=[p2,p3,p4,p5,p6,p7,p8,p9],n=ns.reduce((a,b)=>a+b,0);if(n<2||n>6)continue;let transitions=0;for(let i=0;i<8;i+=1)if(!ns[i]&&ns[(i+1)%8])transitions+=1;if(transitions!==1)continue;const ok=phase===0?p2*p4*p6===0&&p4*p6*p8===0:p2*p4*p8===0&&p2*p6*p8===0;if(ok){remove[y*w+x]=1;removeCount+=1;}}
    if(removeCount)changed=true;for(let i=0;i<remove.length;i+=1)if(remove[i])pixels[i]=0;
  }}return pixels;
}

function graphCounts(skeleton,w,h){
  const endpointMask=new Uint8Array(skeleton.length),junctionMask=new Uint8Array(skeleton.length);
  for(let i=0;i<skeleton.length;i+=1){if(!skeleton[i])continue;let degree=0;forEachNeighborIndex(i,w,h,N8,ni=>{if(skeleton[ni])degree+=1;});if(degree===1)endpointMask[i]=1;if(degree>=3)junctionMask[i]=1;}
  return{endpoints:components(endpointMask,w,h,1,N8),junctions:components(junctionMask,w,h,1,N8)};
}

function symmetry(mask,w,h,vertical){let same=0,total=0;for(let y=0;y<h;y+=1)for(let x=0;x<w;x+=1){const mx=vertical?w-1-x:x,my=vertical?y:h-1-y,a=mask[y*w+x],b=mask[my*w+mx];if(a||b){total+=1;if(a===b)same+=1;}}return total?same/total:0;}

function orientationFromMask(mask,w,h,count,sumX,sumY){
  if(count<2)return 0;const mx=sumX/count,my=sumY/count;let xx=0,yy=0,xy=0;
  for(let y=0;y<h;y+=1)for(let x=0;x<w;x+=1)if(mask[y*w+x]){const dx=x-mx,dy=y-my;xx+=dx*dx;yy+=dy*dy;xy+=dx*dy;}
  let degrees=.5*Math.atan2(2*xy,xx-yy)*180/Math.PI;if(degrees<0)degrees+=180;return degrees;
}

function normalizedEntropy(sizes){if(sizes.length<=1)return 0;const total=sizes.reduce((a,b)=>a+b,0);let e=0;for(const size of sizes){const p=size/total;e-=p*Math.log(p);}return e/Math.log(sizes.length);}

function projectionRepeat(mask,w,h,axis){
  const vector=axis==="x"?new Array(w).fill(0):new Array(h).fill(0);if(axis==="x")for(let y=0;y<h;y+=1)for(let x=0;x<w;x+=1)vector[x]+=mask[y*w+x];else for(let y=0;y<h;y+=1)for(let x=0;x<w;x+=1)vector[y]+=mask[y*w+x];if(vector.length<6)return 0;const average=vector.reduce((a,b)=>a+b,0)/vector.length,centered=vector.map(v=>v-average),energy=centered.reduce((a,b)=>a+b*b,0);if(energy<1e-9)return 0;let best=0;const maxLag=Math.max(1,Math.floor(vector.length/3));for(let lag=2;lag<=maxLag;lag+=1){let numerator=0,left=0,right=0;for(let i=0;i<vector.length-lag;i+=1){const a=centered[i],b=centered[i+lag];numerator+=a*b;left+=a*a;right+=b*b;}const denom=Math.sqrt(left*right);if(denom>1e-9)best=Math.max(best,numerator/denom);}return Math.max(0,best);
}

function perimeter(mask,w,h){let p=0;for(let y=0;y<h;y+=1)for(let x=0;x<w;x+=1){const i=y*w+x;if(!mask[i])continue;for(const[dx,dy]of N4){const nx=x+dx,ny=y+dy;if(nx<0||ny<0||nx>=w||ny>=h||!mask[ny*w+nx])p+=1;}}return p;}

export function measureObservable(gray,width,height,{polarity="dark_on_light",threshold="otsu"}={}){
  const resolvedThreshold=threshold==="otsu"?otsu(gray):Number(threshold),raw=new Uint8Array(gray.length);
  for(let i=0;i<gray.length;i+=1)raw[i]=polarity==="light_on_dark"?(gray[i]>=resolvedThreshold?1:0):(gray[i]<=resolvedThreshold?1:0);
  let minX=width,minY=height,maxX=-1,maxY=-1,ink=0;
  for(let y=0;y<height;y+=1)for(let x=0;x<width;x+=1)if(raw[y*width+x]){ink+=1;minX=Math.min(minX,x);minY=Math.min(minY,y);maxX=Math.max(maxX,x);maxY=Math.max(maxY,y);}
  if(!ink)return{eligible:false,qualityWarnings:["no_foreground"]};
  const w=maxX-minX+1,h=maxY-minY+1,mask=new Uint8Array(w*h);let sumX=0,sumY=0;
  for(let y=minY;y<=maxY;y+=1)for(let x=minX;x<=maxX;x+=1)if(raw[y*width+x]){const nx=x-minX,ny=y-minY;mask[ny*w+nx]=1;sumX+=nx;sumY+=ny;}
  const componentInfo=components(mask,w,h,1,N8,false,true),holes=components(mask,w,h,0,N4,true),graph=graphCounts(thin(mask,w,h),w,h),warnings=[],foregroundFraction=ink/(width*height);
  if(ink<20)warnings.push("very_low_foreground");if(foregroundFraction>.78)warnings.push("foreground_dominates_region");if(minX===0||minY===0||maxX===width-1||maxY===height-1)warnings.push("foreground_touches_region_border");
  const cx=(sumX/ink)/Math.max(1,w-1),cy=(sumY/ink)/Math.max(1,h-1),inkDensity=ink/(w*h);
  return{eligible:!warnings.includes("foreground_dominates_region"),qualityWarnings:warnings,mask,normalizedWidth:w,normalizedHeight:h,components:componentInfo.count,holes,endpoints:graph.endpoints,junctions:graph.junctions,verticalSymmetry:+symmetry(mask,w,h,true).toFixed(6),horizontalSymmetry:+symmetry(mask,w,h,false).toFixed(6),aspect:+(w/Math.max(1,h)).toFixed(6),orientation:+orientationFromMask(mask,w,h,ink,sumX,sumY).toFixed(6),inkDensity:+inkDensity.toFixed(6),eulerCharacteristic:componentInfo.count-holes,componentSizeEntropy:+normalizedEntropy(componentInfo.sizes).toFixed(6),repeatX:+projectionRepeat(mask,w,h,"x").toFixed(6),repeatY:+projectionRepeat(mask,w,h,"y").toFixed(6),boundaryComplexity:+(perimeter(mask,w,h)/Math.max(1,ink)).toFixed(6),centroidX:+cx.toFixed(6),centroidY:+cy.toFixed(6)};
}
