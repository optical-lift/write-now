import crypto from "node:crypto";

const N8=[[-1,-1],[0,-1],[1,-1],[-1,0],[1,0],[-1,1],[0,1],[1,1]];
const N4=[[0,-1],[-1,0],[1,0],[0,1]];
const idx=(x,y,w)=>y*w+x;
const xy=(i,w)=>[i%w,Math.floor(i/w)];
const hash=value=>crypto.createHash("sha256").update(String(value)).digest("hex");

function neighborIndexes(i,w,h,offsets=N8){
  const[x,y]=xy(i,w),out=[];
  for(const[dx,dy]of offsets){const nx=x+dx,ny=y+dy;if(nx>=0&&ny>=0&&nx<w&&ny<h)out.push(idx(nx,ny,w));}
  return out;
}

function connectedSets(mask,w,h,value=1,offsets=N8){
  const seen=new Uint8Array(mask.length),sets=[];
  for(let i=0;i<mask.length;i+=1){
    if(seen[i]||mask[i]!==value)continue;
    const q=[i],members=[];seen[i]=1;let touchesBorder=false;
    for(let p=0;p<q.length;p+=1){
      const cur=q[p];members.push(cur);const[x,y]=xy(cur,w);
      if(x===0||y===0||x===w-1||y===h-1)touchesBorder=true;
      for(const ni of neighborIndexes(cur,w,h,offsets))if(!seen[ni]&&mask[ni]===value){seen[ni]=1;q.push(ni);}
    }
    sets.push({members,touchesBorder});
  }
  return sets;
}

function thin(input,w,h){
  const pixels=Uint8Array.from(input);
  const at=(x,y)=>(x<0||y<0||x>=w||y>=h?0:pixels[idx(x,y,w)]);
  let changed=true,iterations=0;
  while(changed&&iterations++<120){
    changed=false;
    for(const phase of[0,1]){
      const remove=[];
      for(let y=1;y<h-1;y+=1)for(let x=1;x<w-1;x+=1){
        if(!at(x,y))continue;
        const p2=at(x,y-1),p3=at(x+1,y-1),p4=at(x+1,y),p5=at(x+1,y+1),p6=at(x,y+1),p7=at(x-1,y+1),p8=at(x-1,y),p9=at(x-1,y-1);
        const ns=[p2,p3,p4,p5,p6,p7,p8,p9],n=ns.reduce((a,b)=>a+b,0);
        if(n<2||n>6)continue;
        let transitions=0;for(let k=0;k<8;k+=1)if(!ns[k]&&ns[(k+1)%8])transitions+=1;
        if(transitions!==1)continue;
        const ok=phase===0?p2*p4*p6===0&&p4*p6*p8===0:p2*p4*p8===0&&p2*p6*p8===0;
        if(ok)remove.push(idx(x,y,w));
      }
      if(remove.length)changed=true;
      for(const i of remove)pixels[i]=0;
    }
  }
  return pixels;
}

function summarizeSet(members,w){
  let minX=Infinity,minY=Infinity,maxX=-Infinity,maxY=-Infinity,sx=0,sy=0;
  for(const i of members){const[x,y]=xy(i,w);minX=Math.min(minX,x);minY=Math.min(minY,y);maxX=Math.max(maxX,x);maxY=Math.max(maxY,y);sx+=x;sy+=y;}
  return{pixelCount:members.length,bbox:{x:minX,y:minY,width:maxX-minX+1,height:maxY-minY+1},centroid:{x:sx/Math.max(1,members.length),y:sy/Math.max(1,members.length)}};
}

function makeCriticalNodes(skeleton,w,h){
  const endpointMask=new Uint8Array(skeleton.length),junctionMask=new Uint8Array(skeleton.length);
  for(let i=0;i<skeleton.length;i+=1){
    if(!skeleton[i])continue;
    const degree=neighborIndexes(i,w,h).reduce((n,ni)=>n+(skeleton[ni]?1:0),0);
    if(degree<=1)endpointMask[i]=1;
    if(degree>=3)junctionMask[i]=1;
  }
  const nodes=[];
  for(const[kind,mask]of[["ENDPOINT",endpointMask],["JUNCTION",junctionMask]])for(const group of connectedSets(mask,w,h,1,N8))nodes.push({kind,pixels:group.members,...summarizeSet(group.members,w)});
  nodes.sort((a,b)=>a.centroid.y-b.centroid.y||a.centroid.x-b.centroid.x||a.kind.localeCompare(b.kind));
  nodes.forEach((node,i)=>{node.id=`N${String(i+1).padStart(4,"0")}`;});
  return nodes;
}

function skeletonComponents(skeleton,w,h){
  return connectedSets(skeleton,w,h,1,N8).map((group,i)=>({id:`C${String(i+1).padStart(4,"0")}`,...summarizeSet(group.members,w),pixels:group.members}));
}

function nearestComponentId(pixel,componentByPixel,w,h){
  if(componentByPixel[pixel])return componentByPixel[pixel];
  const seen=new Set([pixel]),q=[pixel];
  for(let p=0;p<q.length&&p<256;p+=1){
    const cur=q[p];
    for(const ni of neighborIndexes(cur,w,h)){
      if(componentByPixel[ni])return componentByPixel[ni];
      if(!seen.has(ni)){seen.add(ni);q.push(ni);}
    }
  }
  return null;
}

function traceSkeletonPaths(skeleton,w,h,criticalNodes){
  const nodeByPixel=new Map();for(const node of criticalNodes)for(const p of node.pixels)nodeByPixel.set(p,node.id);
  const visited=new Set(),edges=[];
  const pixelEdgeKey=(a,b)=>a<b?`${a}-${b}`:`${b}-${a}`;
  for(const node of criticalNodes)for(const p of node.pixels)for(const ni of neighborIndexes(p,w,h)){
    if(!skeleton[ni]||nodeByPixel.get(ni)===node.id)continue;
    const first=pixelEdgeKey(p,ni);if(visited.has(first))continue;visited.add(first);
    let prev=p,cur=ni,target=null,guard=0;
    while(guard++<skeleton.length+5){
      const owning=nodeByPixel.get(cur);if(owning&&owning!==node.id){target=owning;break;}
      const nexts=neighborIndexes(cur,w,h).filter(x=>skeleton[x]&&x!==prev);if(!nexts.length)break;
      const next=nexts.find(x=>!visited.has(pixelEdgeKey(cur,x)))??nexts[0];visited.add(pixelEdgeKey(cur,next));prev=cur;cur=next;
    }
    if(target)edges.push({source:node.id,target,relation:"PATH"});
  }
  const dedup=[],seen=new Set();
  for(const edge of edges){const pair=[edge.source,edge.target].sort().join(":");const key=`${pair}:${edge.relation}`;if(seen.has(key))continue;seen.add(key);dedup.push(edge);}
  return dedup;
}

function holeNodes(mask,w,h,componentByPixel){
  const holes=connectedSets(mask,w,h,0,N4).filter(group=>!group.touchesBorder),out=[];
  for(let i=0;i<holes.length;i+=1){
    const group=holes[i],touches=new Map();
    for(const p of group.members)for(const ni of neighborIndexes(p,w,h))if(mask[ni]){const cid=nearestComponentId(ni,componentByPixel,w,h);if(cid)touches.set(cid,(touches.get(cid)??0)+1);}
    const container=[...touches.entries()].sort((a,b)=>b[1]-a[1]||a[0].localeCompare(b[0]))[0]?.[0]??null;
    out.push({id:`H${String(i+1).padStart(4,"0")}`,kind:"HOLE",container,...summarizeSet(group.members,w),pixels:group.members});
  }
  return out;
}

const graphNodeLabel=node=>node.kind==="COMPONENT"?"COMPONENT":node.kind;

function incidentDescriptors(graph,nodeId,labels){
  const out=[];
  for(const edge of graph.edges){
    if(edge.source===nodeId)out.push(`OUT:${edge.relation}:${labels.get(edge.target)}`);
    if(edge.target===nodeId)out.push(`IN:${edge.relation}:${labels.get(edge.source)}`);
  }
  return out.sort();
}

export function canonicalRelationalFingerprint(graph,{iterations=3}={}){
  let labels=new Map(graph.nodes.map(node=>[node.id,hash(`NODE:${graphNodeLabel(node)}`).slice(0,24)]));
  for(let round=0;round<iterations;round+=1){
    const next=new Map();
    for(const node of graph.nodes)next.set(node.id,hash(`${labels.get(node.id)}||${incidentDescriptors(graph,node.id,labels).join("|")}`).slice(0,24));
    labels=next;
  }
  const nodeMultiset=[...labels.values()].sort();
  const edgeMultiset=graph.edges.map(edge=>`${labels.get(edge.source)}:${edge.relation}:${labels.get(edge.target)}`).sort();
  return hash(`N:${nodeMultiset.join(",")}||E:${edgeMultiset.join(",")}`);
}

export function localRelationalMotifs(graph,{radius=1}={}){
  let labels=new Map(graph.nodes.map(node=>[node.id,graphNodeLabel(node)]));
  for(let round=0;round<radius;round+=1){
    const next=new Map();
    for(const node of graph.nodes)next.set(node.id,`${graphNodeLabel(node)}{${incidentDescriptors(graph,node.id,labels).join("|")}}`);
    labels=next;
  }
  return graph.nodes.map(node=>({nodeId:node.id,kind:graphNodeLabel(node),signature:hash(labels.get(node.id)).slice(0,24)}));
}

export function relationGrammarPaths(graph){
  const incident=new Map(graph.nodes.map(n=>[n.id,[]]));
  for(const edge of graph.edges){incident.get(edge.source)?.push({neighbor:edge.target,token:`OUT:${edge.relation}`});incident.get(edge.target)?.push({neighbor:edge.source,token:`IN:${edge.relation}`});}
  const nodeKind=new Map(graph.nodes.map(n=>[n.id,graphNodeLabel(n)])),paths=[];
  for(const center of graph.nodes){
    const arms=incident.get(center.id)??[];
    for(let i=0;i<arms.length;i+=1)for(let j=i+1;j<arms.length;j+=1){
      const a=arms[i],b=arms[j],left=`${nodeKind.get(a.neighbor)}|${a.token}`,right=`${b.token}|${nodeKind.get(b.neighbor)}`,pair=[left,right].sort();
      paths.push({centerId:center.id,centerKind:nodeKind.get(center.id),signature:`${pair[0]}|CENTER:${nodeKind.get(center.id)}|${pair[1]}`,leftToken:pair[0],rightToken:pair[1]});
    }
  }
  return paths.sort((a,b)=>a.signature.localeCompare(b.signature));
}

export function buildRelationalGraph(mask,width,height,{observationId=null,sourceGroupId=null}={}){
  const skeleton=thin(mask,width,height),components=skeletonComponents(skeleton,width,height),componentByPixel={};
  for(const component of components)for(const p of component.pixels)componentByPixel[p]=component.id;
  const critical=makeCriticalNodes(skeleton,width,height),criticalComponent=new Map();
  for(const node of critical){
    const votes=new Map();for(const p of node.pixels){const cid=nearestComponentId(p,componentByPixel,width,height);if(cid)votes.set(cid,(votes.get(cid)??0)+1);}
    criticalComponent.set(node.id,[...votes.entries()].sort((a,b)=>b[1]-a[1]||a[0].localeCompare(b[0]))[0]?.[0]??null);
  }
  const holes=holeNodes(mask,width,height,componentByPixel),nodes=[];
  for(const component of components)nodes.push({id:component.id,kind:"COMPONENT"});
  for(const node of critical)nodes.push({id:node.id,kind:node.kind});
  const cycleComponents=new Set(components.filter(component=>!critical.some(node=>criticalComponent.get(node.id)===component.id)).map(component=>component.id));
  let cycleIndex=0;for(const cid of[...cycleComponents].sort())nodes.push({id:`Y${String(++cycleIndex).padStart(4,"0")}`,kind:"CYCLE",componentId:cid});
  for(const hole of holes)nodes.push({id:hole.id,kind:"HOLE"});
  const edges=[];
  for(const node of critical){const cid=criticalComponent.get(node.id);if(cid)edges.push({source:cid,target:node.id,relation:node.kind==="ENDPOINT"?"HAS_ENDPOINT":"HAS_JUNCTION"});}
  for(const edge of traceSkeletonPaths(skeleton,width,height,critical))edges.push(edge);
  for(const cycle of nodes.filter(n=>n.kind==="CYCLE"))edges.push({source:cycle.componentId,target:cycle.id,relation:"HAS_CYCLE"});
  for(const hole of holes)if(hole.container)edges.push({source:hole.container,target:hole.id,relation:"ENCLOSES"});
  edges.sort((a,b)=>a.source.localeCompare(b.source)||a.relation.localeCompare(b.relation)||a.target.localeCompare(b.target));nodes.sort((a,b)=>a.id.localeCompare(b.id));
  const graph={schema:"mark_relational_graph_v1",observationId,sourceGroupId,nodes,edges};
  graph.fingerprint=canonicalRelationalFingerprint(graph);graph.motifs=localRelationalMotifs(graph,{radius:1});graph.grammarPaths=relationGrammarPaths(graph);
  graph.counts={nodes:nodes.length,edges:edges.length,components:components.length,endpoints:critical.filter(n=>n.kind==="ENDPOINT").length,junctions:critical.filter(n=>n.kind==="JUNCTION").length,holes:holes.length,cycles:nodes.filter(n=>n.kind==="CYCLE").length};
  return graph;
}

export function relationHistogram(graph){
  const nodes={},edges={};for(const node of graph.nodes)nodes[graphNodeLabel(node)]=(nodes[graphNodeLabel(node)]??0)+1;for(const edge of graph.edges)edges[edge.relation]=(edges[edge.relation]??0)+1;return{nodes,edges};
}

export function histogramDelta(from,to){
  const a=relationHistogram(from),b=relationHistogram(to),nodeKinds=[...new Set([...Object.keys(a.nodes),...Object.keys(b.nodes)])].sort(),edgeKinds=[...new Set([...Object.keys(a.edges),...Object.keys(b.edges)])].sort();
  return{nodes:Object.fromEntries(nodeKinds.map(k=>[k,(b.nodes[k]??0)-(a.nodes[k]??0)]).filter(([,v])=>v!==0)),edges:Object.fromEntries(edgeKinds.map(k=>[k,(b.edges[k]??0)-(a.edges[k]??0)]).filter(([,v])=>v!==0))};
}

export function transformationSignature(from,to){return hash(JSON.stringify(histogramDelta(from,to))).slice(0,32);}
