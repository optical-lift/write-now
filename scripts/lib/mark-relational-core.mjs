import crypto from "node:crypto";

const N8=[[-1,-1],[0,-1],[1,-1],[-1,0],[1,0],[-1,1],[0,1],[1,1]];
const N4=[[0,-1],[-1,0],[1,0],[0,1]];
const N8_INVERSE=[7,6,5,4,3,2,1,0];
const idx=(x,y,w)=>y*w+x;
const xy=(i,w)=>[i%w,Math.floor(i/w)];
const hash=value=>crypto.createHash("sha256").update(String(value)).digest("hex");
const SYMMETRIC_RELATIONS=new Set(["PATH"]);
const componentId=label=>label?`C${String(label).padStart(4,"0")}`:null;

function forEachNeighbor(i,w,h,offsets,visit){
  const x=i%w,y=Math.floor(i/w);
  for(let d=0;d<offsets.length;d+=1){
    const[dx,dy]=offsets[d],nx=x+dx,ny=y+dy;
    if(nx>=0&&ny>=0&&nx<w&&ny<h)visit(ny*w+nx,d);
  }
}

function degree8(mask,i,w,h,componentLabels=null,componentLabel=0){
  let degree=0;
  forEachNeighbor(i,w,h,N8,ni=>{if(mask[ni]&&(!componentLabels||componentLabels[ni]===componentLabel))degree+=1;});
  return degree;
}

function labelSets(mask,w,h,value=1,offsets=N8){
  const labels=new Int32Array(mask.length),queue=new Int32Array(mask.length),groups=[];
  for(let start=0;start<mask.length;start+=1){
    if(labels[start]||mask[start]!==value)continue;
    const label=groups.length+1;let head=0,tail=0;queue[tail++]=start;labels[start]=label;
    let touchesBorder=false,pixelCount=0,minX=Infinity,minY=Infinity,maxX=-Infinity,maxY=-Infinity,sx=0,sy=0;
    while(head<tail){
      const cur=queue[head++],x=cur%w,y=Math.floor(cur/w);pixelCount+=1;sx+=x;sy+=y;
      if(x===0||y===0||x===w-1||y===h-1)touchesBorder=true;
      if(x<minX)minX=x;if(y<minY)minY=y;if(x>maxX)maxX=x;if(y>maxY)maxY=y;
      forEachNeighbor(cur,w,h,offsets,ni=>{if(!labels[ni]&&mask[ni]===value){labels[ni]=label;queue[tail++]=ni;}});
    }
    groups.push({label,touchesBorder,pixelCount,bbox:{x:minX,y:minY,width:maxX-minX+1,height:maxY-minY+1},centroid:{x:sx/Math.max(1,pixelCount),y:sy/Math.max(1,pixelCount)}});
  }
  return{labels,groups};
}

function thin(input,w,h){
  const pixels=Uint8Array.from(input),remove=new Uint8Array(input.length);
  const at=(x,y)=>(x<0||y<0||x>=w||y>=h?0:pixels[idx(x,y,w)]);
  let changed=true,iterations=0;
  while(changed&&iterations++<120){
    changed=false;
    for(const phase of[0,1]){
      remove.fill(0);let removeCount=0;
      for(let y=1;y<h-1;y+=1)for(let x=1;x<w-1;x+=1){
        if(!at(x,y))continue;
        const p2=at(x,y-1),p3=at(x+1,y-1),p4=at(x+1,y),p5=at(x+1,y+1),p6=at(x,y+1),p7=at(x-1,y+1),p8=at(x-1,y),p9=at(x-1,y-1);
        const n=p2+p3+p4+p5+p6+p7+p8+p9;if(n<2||n>6)continue;
        const ns=[p2,p3,p4,p5,p6,p7,p8,p9];let transitions=0;for(let k=0;k<8;k+=1)if(!ns[k]&&ns[(k+1)%8])transitions+=1;
        if(transitions!==1)continue;
        const ok=phase===0?p2*p4*p6===0&&p4*p6*p8===0:p2*p4*p8===0&&p2*p6*p8===0;
        if(ok){remove[idx(x,y,w)]=1;removeCount+=1;}
      }
      if(removeCount)changed=true;
      for(let i=0;i<remove.length;i+=1)if(remove[i])pixels[i]=0;
    }
  }
  return pixels;
}

function foregroundComponents(mask,w,h){
  const labeled=labelSets(mask,w,h,1,N8);
  return{labels:labeled.labels,components:labeled.groups.map(group=>({id:componentId(group.label),...group}))};
}

function makeCriticalNodes(skeleton,w,h,componentLabels){
  const endpointMask=new Uint8Array(skeleton.length),junctionMask=new Uint8Array(skeleton.length);
  for(let i=0;i<skeleton.length;i+=1){
    if(!skeleton[i])continue;const degree=degree8(skeleton,i,w,h);
    if(degree<=1)endpointMask[i]=1;if(degree>=3)junctionMask[i]=1;
  }
  const endpoint=labelSets(endpointMask,w,h,1,N8),junction=labelSets(junctionMask,w,h,1,N8),nodes=[];
  for(const group of endpoint.groups)nodes.push({kind:"ENDPOINT",sourceLabel:group.label,...group});
  for(const group of junction.groups)nodes.push({kind:"JUNCTION",sourceLabel:group.label,...group});
  nodes.sort((a,b)=>a.centroid.y-b.centroid.y||a.centroid.x-b.centroid.x||a.kind.localeCompare(b.kind));
  nodes.forEach((node,i)=>{node.id=`N${String(i+1).padStart(4,"0")}`;node.nodeIndex=i+1;});
  const endpointToNode=new Int32Array(endpoint.groups.length+1),junctionToNode=new Int32Array(junction.groups.length+1);
  for(const node of nodes)(node.kind==="ENDPOINT"?endpointToNode:junctionToNode)[node.sourceLabel]=node.nodeIndex;
  const nodeByPixel=new Int32Array(skeleton.length),ownerLabel=new Int32Array(nodes.length+1),ownerCount=new Int32Array(nodes.length+1),conflicts=new Map();
  for(let i=0;i<skeleton.length;i+=1){
    const nodeIndex=endpoint.labels[i]?endpointToNode[endpoint.labels[i]]:(junction.labels[i]?junctionToNode[junction.labels[i]]:0);if(!nodeIndex)continue;
    nodeByPixel[i]=nodeIndex;const cid=componentLabels[i];if(!cid)continue;
    if(!ownerLabel[nodeIndex]){ownerLabel[nodeIndex]=cid;ownerCount[nodeIndex]=1;continue;}
    if(ownerLabel[nodeIndex]===cid){ownerCount[nodeIndex]+=1;continue;}
    let votes=conflicts.get(nodeIndex);if(!votes){votes=new Map([[ownerLabel[nodeIndex],ownerCount[nodeIndex]]]);conflicts.set(nodeIndex,votes);}votes.set(cid,(votes.get(cid)??0)+1);
  }
  const componentByNode=new Map();
  for(const node of nodes){
    const votes=conflicts.get(node.nodeIndex);let label=ownerLabel[node.nodeIndex];
    if(votes){label=[...votes.entries()].sort((a,b)=>b[1]-a[1]||a[0]-b[0])[0]?.[0]??label;}
    componentByNode.set(node.id,componentId(label));
  }
  return{nodes,nodeByPixel,componentByNode};
}

function traceSkeletonPaths(skeleton,w,h,criticalNodes,nodeByPixel){
  const idByIndex=new Array(criticalNodes.length+1);for(const node of criticalNodes)idByIndex[node.nodeIndex]=node.id;
  const visited=new Uint8Array(skeleton.length),edges=[];
  const neighborAt=(i,dir)=>{const x=i%w,y=Math.floor(i/w),[dx,dy]=N8[dir],nx=x+dx,ny=y+dy;return nx>=0&&ny>=0&&nx<w&&ny<h?ny*w+nx:-1;};
  const isVisited=(i,dir)=>(visited[i]&(1<<dir))!==0;
  const markVisited=(a,dir,b)=>{visited[a]|=1<<dir;visited[b]|=1<<N8_INVERSE[dir];};
  for(let p=0;p<skeleton.length;p+=1){
    const sourceIndex=nodeByPixel[p];if(!sourceIndex)continue;const sourceId=idByIndex[sourceIndex];
    for(let dir=0;dir<N8.length;dir+=1){
      const ni=neighborAt(p,dir);if(ni<0||!skeleton[ni]||nodeByPixel[ni]===sourceIndex||isVisited(p,dir))continue;
      markVisited(p,dir,ni);let prev=p,cur=ni,length=1,target=null,guard=0;
      while(guard++<skeleton.length+5){
        const owning=nodeByPixel[cur];if(owning&&owning!==sourceIndex){target=idByIndex[owning];break;}
        let next=-1,nextDir=-1;
        for(let d=0;d<N8.length;d+=1){const candidate=neighborAt(cur,d);if(candidate<0||candidate===prev||!skeleton[candidate]||isVisited(cur,d))continue;next=candidate;nextDir=d;break;}
        if(next<0)break;markVisited(cur,nextDir,next);prev=cur;cur=next;length+=1;
      }
      if(target)edges.push({source:sourceId,target,relation:"PATH",pathLength:length});
    }
  }
  return edges;
}

function holeNodes(mask,w,h,componentLabels){
  const labeled=labelSets(mask,w,h,0,N4),interior=labeled.groups.filter(group=>!group.touchesBorder),holeIndexByLabel=new Int32Array(labeled.groups.length+1);
  const ownerLabel=new Int32Array(interior.length+1),ownerCount=new Int32Array(interior.length+1),conflicts=new Map();
  interior.forEach((group,i)=>{group.holeIndex=i+1;holeIndexByLabel[group.label]=i+1;});
  for(let p=0;p<mask.length;p+=1){
    const holeIndex=holeIndexByLabel[labeled.labels[p]];if(!holeIndex)continue;
    forEachNeighbor(p,w,h,N8,ni=>{if(!mask[ni])return;const cid=componentLabels[ni];if(!cid)return;
      if(!ownerLabel[holeIndex]){ownerLabel[holeIndex]=cid;ownerCount[holeIndex]=1;return;}
      if(ownerLabel[holeIndex]===cid){ownerCount[holeIndex]+=1;return;}
      let votes=conflicts.get(holeIndex);if(!votes){votes=new Map([[ownerLabel[holeIndex],ownerCount[holeIndex]]]);conflicts.set(holeIndex,votes);}votes.set(cid,(votes.get(cid)??0)+1);
    });
  }
  return interior.map((group,i)=>{
    const holeIndex=i+1,votes=conflicts.get(holeIndex);let label=ownerLabel[holeIndex];if(votes)label=[...votes.entries()].sort((a,b)=>b[1]-a[1]||a[0]-b[0])[0]?.[0]??label;
    return{id:`H${String(holeIndex).padStart(4,"0")}`,kind:"HOLE",container:componentId(label),pixelCount:group.pixelCount,bbox:group.bbox,centroid:group.centroid};
  });
}

function pureCycleComponentIds(skeleton,componentLabels,components,w,h){
  const counts=new Int32Array(components.length+1),pure=new Uint8Array(components.length+1);pure.fill(1);
  for(let i=0;i<skeleton.length;i+=1){if(!skeleton[i])continue;const cid=componentLabels[i];if(!cid)continue;counts[cid]+=1;if(degree8(skeleton,i,w,h,componentLabels,cid)!==2)pure[cid]=0;}
  return components.filter(component=>counts[component.label]>=3&&pure[component.label]).map(component=>component.id);
}

const graphNodeLabel=node=>node.kind==="COMPONENT"?"COMPONENT":node.kind;
function incidentDescriptors(graph,nodeId,labels){
  const out=[];
  for(const edge of graph.edges){
    if(SYMMETRIC_RELATIONS.has(edge.relation)){
      if(edge.source===nodeId)out.push(`UND:${edge.relation}:${labels.get(edge.target)}`);else if(edge.target===nodeId)out.push(`UND:${edge.relation}:${labels.get(edge.source)}`);continue;
    }
    if(edge.source===nodeId)out.push(`OUT:${edge.relation}:${labels.get(edge.target)}`);
    if(edge.target===nodeId)out.push(`IN:${edge.relation}:${labels.get(edge.source)}`);
  }
  return out.sort();
}

export function canonicalRelationalFingerprint(graph,{iterations=3}={}){
  let labels=new Map(graph.nodes.map(node=>[node.id,hash(`NODE:${graphNodeLabel(node)}`).slice(0,24)]));
  for(let round=0;round<iterations;round+=1){const next=new Map();for(const node of graph.nodes)next.set(node.id,hash(`${labels.get(node.id)}||${incidentDescriptors(graph,node.id,labels).join("|")}`).slice(0,24));labels=next;}
  const nodeMultiset=[...labels.values()].sort();
  const edgeMultiset=graph.edges.map(edge=>{const a=labels.get(edge.source),b=labels.get(edge.target);if(SYMMETRIC_RELATIONS.has(edge.relation)){const pair=[a,b].sort();return`${pair[0]}:${edge.relation}:${pair[1]}`;}return`${a}:${edge.relation}:${b}`;}).sort();
  return hash(`N:${nodeMultiset.join(",")}||E:${edgeMultiset.join(",")}`);
}

export function localRelationalMotifs(graph,{radius=1}={}){
  let labels=new Map(graph.nodes.map(node=>[node.id,graphNodeLabel(node)]));
  for(let round=0;round<radius;round+=1){const next=new Map();for(const node of graph.nodes)next.set(node.id,`${graphNodeLabel(node)}{${incidentDescriptors(graph,node.id,labels).join("|")}}`);labels=next;}
  return graph.nodes.map(node=>({nodeId:node.id,kind:graphNodeLabel(node),signature:hash(labels.get(node.id)).slice(0,24)}));
}

export function relationGrammarPaths(graph){
  const incident=new Map(graph.nodes.map(n=>[n.id,[]]));
  for(const edge of graph.edges){
    if(SYMMETRIC_RELATIONS.has(edge.relation)){incident.get(edge.source)?.push({neighbor:edge.target,token:`UND:${edge.relation}`});incident.get(edge.target)?.push({neighbor:edge.source,token:`UND:${edge.relation}`});}
    else{incident.get(edge.source)?.push({neighbor:edge.target,token:`OUT:${edge.relation}`});incident.get(edge.target)?.push({neighbor:edge.source,token:`IN:${edge.relation}`});}
  }
  const nodeKind=new Map(graph.nodes.map(n=>[n.id,graphNodeLabel(n)])),paths=[];
  for(const center of graph.nodes){const arms=incident.get(center.id)??[];for(let i=0;i<arms.length;i+=1)for(let j=i+1;j<arms.length;j+=1){const a=arms[i],b=arms[j],left=`${nodeKind.get(a.neighbor)}|${a.token}`,right=`${b.token}|${nodeKind.get(b.neighbor)}`,pair=[left,right].sort();paths.push({centerId:center.id,centerKind:nodeKind.get(center.id),signature:`${pair[0]}|CENTER:${nodeKind.get(center.id)}|${pair[1]}`,leftToken:pair[0],rightToken:pair[1]});}}
  return paths.sort((a,b)=>a.signature.localeCompare(b.signature));
}

export function buildRelationalGraph(mask,width,height,{observationId=null,sourceGroupId=null}={}){
  const skeleton=thin(mask,width,height),foreground=foregroundComponents(mask,width,height),components=foreground.components,componentLabels=foreground.labels;
  const criticalField=makeCriticalNodes(skeleton,width,height,componentLabels),critical=criticalField.nodes;
  const holes=holeNodes(mask,width,height,componentLabels),nodes=[];
  for(const component of components)nodes.push({id:component.id,kind:"COMPONENT"});
  for(const node of critical)nodes.push({id:node.id,kind:node.kind});
  const cycleComponents=new Set(pureCycleComponentIds(skeleton,componentLabels,components,width,height));
  let cycleIndex=0;for(const cid of[...cycleComponents].sort())nodes.push({id:`Y${String(++cycleIndex).padStart(4,"0")}`,kind:"CYCLE",componentId:cid});
  for(const hole of holes)nodes.push({id:hole.id,kind:"HOLE"});
  const edges=[];
  for(const node of critical){const cid=criticalField.componentByNode.get(node.id);if(cid)edges.push({source:cid,target:node.id,relation:node.kind==="ENDPOINT"?"HAS_ENDPOINT":"HAS_JUNCTION"});}
  for(const pathEdge of traceSkeletonPaths(skeleton,width,height,critical,criticalField.nodeByPixel))edges.push({source:pathEdge.source,target:pathEdge.target,relation:"PATH"});
  for(const cycle of nodes.filter(n=>n.kind==="CYCLE"))edges.push({source:cycle.componentId,target:cycle.id,relation:"HAS_CYCLE"});
  for(const hole of holes)if(hole.container)edges.push({source:hole.container,target:hole.id,relation:"ENCLOSES"});
  edges.sort((a,b)=>a.source.localeCompare(b.source)||a.relation.localeCompare(b.relation)||a.target.localeCompare(b.target));nodes.sort((a,b)=>a.id.localeCompare(b.id));
  const graph={schema:"mark_relational_graph_v1",observationId,sourceGroupId,nodes,edges};
  graph.fingerprint=canonicalRelationalFingerprint(graph);graph.motifs=localRelationalMotifs(graph,{radius:1});graph.grammarPaths=relationGrammarPaths(graph);
  graph.counts={nodes:nodes.length,edges:edges.length,components:components.length,endpoints:critical.filter(n=>n.kind==="ENDPOINT").length,junctions:critical.filter(n=>n.kind==="JUNCTION").length,holes:holes.length,cycles:nodes.filter(n=>n.kind==="CYCLE").length};
  return graph;
}

export function relationHistogram(graph){const nodes={},edges={};for(const node of graph.nodes)nodes[graphNodeLabel(node)]=(nodes[graphNodeLabel(node)]??0)+1;for(const edge of graph.edges)edges[edge.relation]=(edges[edge.relation]??0)+1;return{nodes,edges};}
export function histogramDelta(from,to){const a=relationHistogram(from),b=relationHistogram(to),nodeKinds=[...new Set([...Object.keys(a.nodes),...Object.keys(b.nodes)])].sort(),edgeKinds=[...new Set([...Object.keys(a.edges),...Object.keys(b.edges)])].sort();return{nodes:Object.fromEntries(nodeKinds.map(k=>[k,(b.nodes[k]??0)-(a.nodes[k]??0)]).filter(([,v])=>v!==0)),edges:Object.fromEntries(edgeKinds.map(k=>[k,(b.edges[k]??0)-(a.edges[k]??0)]).filter(([,v])=>v!==0))};}
export function transformationSignature(from,to){return hash(JSON.stringify(histogramDelta(from,to))).slice(0,32);}
