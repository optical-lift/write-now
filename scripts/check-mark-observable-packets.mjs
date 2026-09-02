import fs from "node:fs/promises";
import path from "node:path";

const root=process.env.MARK_OBSERVABLE_PACKET_DIR ?? "research/mark/observable-corpus";
const entries=await fs.readdir(root,{withFileTypes:true}).catch(()=>[]);
const files=entries.filter(entry=>entry.isFile()&&entry.name.endsWith(".json")).map(entry=>path.join(root,entry.name));
if(!files.length)throw new Error(`no Mark observable packets found in ${root}`);
const sourcePattern=/^SRC\d{4}$/;const observationPattern=/^OBS\d{6}$/;let checked=0;
const required=(value,label)=>{if(typeof value!=="string"||!value.trim())throw new Error(`${label} must be a non-empty string`);};
for(const file of files){
  const packet=JSON.parse(await fs.readFile(file,"utf8"));if(packet.schema!=="mark_observable_corpus_packet_v1")continue;checked+=1;
  required(packet.corpusId,`${file}: corpusId`);if(!["synthetic_fixture","physical_evidence"].includes(packet.status))throw new Error(`${file}: invalid status ${packet.status}`);
  if(!Array.isArray(packet.sources)||packet.sources.length<1)throw new Error(`${file}: sources[] required`);if(!Array.isArray(packet.observations)||packet.observations.length<4)throw new Error(`${file}: at least four observations required`);
  const sourceIds=new Set();for(const source of packet.sources){required(source.sourceId,`${file}: sourceId`);if(!sourcePattern.test(source.sourceId))throw new Error(`${file}: sourceId must be opaque SRC####`);if(sourceIds.has(source.sourceId))throw new Error(`${file}: duplicate sourceId ${source.sourceId}`);sourceIds.add(source.sourceId);
    const capture=source.capture??{};if((capture.adapter??"image_2d")!=="image_2d")throw new Error(`${file}: current adapter must be image_2d`);
    if(packet.status==="synthetic_fixture"){if(!capture.syntheticRecipe&&!capture.syntheticSvg&&!capture.imageDataUri&&!capture.imagePath)throw new Error(`${file}: fixture ${source.sourceId} needs a capture`);if(source.blindLane&&!['train','holdout'].includes(source.blindLane))throw new Error(`${file}: invalid fixture blindLane`);}
    else{required(capture.imagePath,`${file}: ${source.sourceId}.capture.imagePath`);for(const key of ["sourceUrl","institution","objectId","rightsBasis"])required(source[key],`${file}: ${source.sourceId}.${key}`);if(capture.syntheticRecipe||capture.syntheticSvg||capture.imageDataUri)throw new Error(`${file}: physical evidence cannot inline synthetic captures`);if(source.blindLane)throw new Error(`${file}: physical evidence holdout assignment is automatic, not author-selected`);}
  }
  const observationIds=new Set();for(const observation of packet.observations){required(observation.observationId,`${file}: observationId`);if(!observationPattern.test(observation.observationId))throw new Error(`${file}: observationId must be opaque OBS######`);if(observationIds.has(observation.observationId))throw new Error(`${file}: duplicate observationId ${observation.observationId}`);observationIds.add(observation.observationId);if(!sourceIds.has(observation.sourceId))throw new Error(`${file}: ${observation.observationId} references unknown source ${observation.sourceId}`);
    if(observation.region)for(const key of ["x","y","width","height"]){if(!Number.isFinite(observation.region[key]))throw new Error(`${file}: ${observation.observationId}.region.${key} must be numeric`);}if(observation.region&&(observation.region.width<=0||observation.region.height<=0))throw new Error(`${file}: observation region dimensions must be positive`);
  }
  if(packet.status==="physical_evidence"){const objects=new Set(packet.sources.map(source=>`${source.institution}::${source.objectId}`));if(objects.size!==packet.sources.length)throw new Error(`${file}: physical source objects must be unique institution/objectId pairs`);}
}
if(!checked)throw new Error(`no mark_observable_corpus_packet_v1 packets found in ${root}`);console.log(`Validated ${checked} Mark observable corpus packet(s).`);
