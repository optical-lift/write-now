import fs from "node:fs/promises";
import path from "node:path";

const requestPath=process.env.MARK_IIIF_FEED_REQUEST ?? "research/mark/harvest-feeds/iiif-fixture.v1.json";
const outDir=process.env.MARK_IIIF_FEED_OUT ?? "artifacts/mark-iiif-feed-v1";
const request=JSON.parse(await fs.readFile(requestPath,"utf8"));
if(request.schema!=="mark_iiif_feed_request_v1")throw new Error(`unsupported IIIF feed request ${request.schema}`);
if(request.lane&&!new Set(["train","holdout","control"]).has(request.lane))throw new Error(`invalid challenge lane ${request.lane}`);
const maxSources=Number(request.maxSources??500);
const maxCapturesPerManifest=Math.max(1,Number(request.maxCapturesPerManifest??maxSources));
const iiifCaptureWidth=Math.max(256,Number(request.captureWidth??1600));
const seenResources=new Set(),seenAssets=new Set(),sources=[];
const capturesByManifest=new Map();

const textValue=(value)=>{
  if(typeof value==="string")return value;
  if(Array.isArray(value))return value.map(textValue).filter(Boolean).join(" | ");
  if(value&&typeof value==="object")return Object.values(value).flatMap(v=>Array.isArray(v)?v:[v]).map(textValue).filter(Boolean).join(" | ");
  return "";
};
async function fetchJson(url){const response=await fetch(url,{redirect:"follow",headers:{accept:"application/ld+json, application/json","user-agent":"MarkResearchHarvester/2.0"}});if(!response.ok)throw new Error(`IIIF fetch failed ${response.status}: ${url}`);return response.json();}
async function rootResource(){
  if(request.fixturePath){const absolute=path.resolve(path.dirname(requestPath),request.fixturePath);return JSON.parse(await fs.readFile(absolute,"utf8"));}
  if(!request.collectionUrl)throw new Error("IIIF feed request needs collectionUrl or fixturePath");
  return fetchJson(request.collectionUrl);
}
function imageServiceUrl(body){
  const services=Array.isArray(body?.service)?body.service:(body?.service?[body.service]:[]);const service=services[0];const id=service?.id??service?.["@id"];
  if(!id)return null;
  // A width-only IIIF request is valid in Image API 2.x and 3.x and avoids institution-specific raw delivery URLs.
  return `${String(id).replace(/\/$/,"")}/full/${iiifCaptureWidth},/0/default.jpg`;
}
function addSource(assetUrl,manifest,canvas,index){
  const manifestId=manifest.id??manifest["@id"]??request.collectionUrl??"iiif-manifest";
  const currentCount=capturesByManifest.get(manifestId)??0;
  if(currentCount>=maxCapturesPerManifest||!assetUrl||!/^https:\/\//i.test(assetUrl)||seenAssets.has(assetUrl)||sources.length>=maxSources)return;
  seenAssets.add(assetUrl);capturesByManifest.set(manifestId,currentCount+1);const sourceId=`SRC${String(sources.length+1).padStart(4,"0")}`;
  const canvasId=canvas?.id??canvas?.["@id"]??`canvas-${index}`;
  sources.push({
    sourceId,
    ...(request.lane?{challengeLane:request.lane}:{}),
    capture:{adapter:"image_2d",assetUrl},
    sourceUrl:manifestId,
    institution:request.institution,
    objectId:`${manifestId}#${canvasId}`,
    rightsBasis:request.rightsBasis,
    context:{feedKind:"iiif",feedId:request.feedId,manifestLabel:textValue(manifest.label),canvasLabel:textValue(canvas?.label),manifestId,canvasId,captureBasis:assetUrl.includes("/iiif/")?"iiif_image_service":"manifest_image_body"},
  });
}
function extractManifest(manifest){
  const canvases=Array.isArray(manifest.items)?manifest.items:[];
  canvases.forEach((canvas,canvasIndex)=>{
    const pages=Array.isArray(canvas.items)?canvas.items:[];
    for(const page of pages)for(const annotation of Array.isArray(page.items)?page.items:[]){
      const bodies=Array.isArray(annotation.body)?annotation.body:[annotation.body].filter(Boolean);
      for(const body of bodies){const assetUrl=imageServiceUrl(body)??body?.id??body?.["@id"];addSource(assetUrl,manifest,canvas,canvasIndex);}
    }
  });
  for(const sequence of Array.isArray(manifest.sequences)?manifest.sequences:[])for(const [canvasIndex,canvas] of (sequence.canvases??[]).entries())for(const image of canvas.images??[]){
    const body=image.resource??{},assetUrl=imageServiceUrl(body)??body["@id"]??body.id;addSource(assetUrl,manifest,canvas,canvasIndex);
  }
}
async function walk(resource){
  if(!resource||sources.length>=maxSources)return;const id=resource.id??resource["@id"];
  if(id&&seenResources.has(id))return;if(id)seenResources.add(id);
  const type=resource.type??resource["@type"]??"";
  if(String(type).toLowerCase().includes("manifest")){extractManifest(resource);return;}
  if(String(type).toLowerCase().includes("collection")||Array.isArray(resource.items)||Array.isArray(resource.manifests)||Array.isArray(resource.collections)){
    const children=[...(resource.items??[]),...(resource.manifests??[]),...(resource.collections??[])];
    for(const child of children){if(sources.length>=maxSources)break;const childType=child?.type??child?.["@type"]??"";const embedded=Array.isArray(child?.items)||Array.isArray(child?.sequences)||String(childType).toLowerCase().includes("manifest")&&child?.items;
      if(embedded)await walk(child);else{const childId=child?.id??child?.["@id"];if(childId)await walk(await fetchJson(childId));}
    }
  }
}
const root=await rootResource();await walk(root);
if(!sources.length)throw new Error("IIIF feed produced no image sources");
const manifest={schema:"mark_harvest_manifest_v1",harvestId:`mark:iiif:${request.feedId}`,status:"physical_evidence",purpose:`Machine-enumerated IIIF feed ${request.feedId}; individual source objects were not hand-selected.`,sources};
await fs.mkdir(outDir,{recursive:true});await fs.writeFile(path.join(outDir,"generated-harvest-manifest.v1.json"),`${JSON.stringify(manifest,null,2)}\n`);
await fs.writeFile(path.join(outDir,"summary.txt"),[`schema=${manifest.schema}`,`feed_id=${request.feedId}`,`lane=${request.lane??"none"}`,`sources=${sources.length}`,`max_sources=${maxSources}`,`max_captures_per_manifest=${maxCapturesPerManifest}`,`capture_width=${iiifCaptureWidth}`].join("\n")+"\n");
console.log(`Expanded IIIF feed ${request.feedId} into ${sources.length} machine-enumerated ${request.lane??"unlaned"} source captures`);
