import crypto from "node:crypto";
import fs from "node:fs/promises";
import path from "node:path";
import sharp from "sharp";

const inputPath=process.env.MARK_OBSERVABLE_INPUT ?? "artifacts/mark-conveyor-input-v1/mark-observable-input-blind-v1.json";
const predictionPath=process.env.MARK_WORLD_PREDICTION ?? "artifacts/mark-world-prediction-v1/mark-blind-world-holdout-prediction-v2.json";
const controlPath=process.env.MARK_CONTROL_EVALUATION ?? "artifacts/mark-control-evaluation-v1/mark-blind-control-evaluation-v1.json";
const outDir=process.env.MARK_VISUAL_BASELINE_OUT ?? "artifacts/mark-visual-baseline-v1";
const trivialThreshold=Math.max(0,Number(process.env.MARK_VISUAL_TRIVIAL_DHASH_BITS??8));
const input=JSON.parse(await fs.readFile(inputPath,"utf8"));
const prediction=JSON.parse(await fs.readFile(predictionPath,"utf8"));
const control=JSON.parse(await fs.readFile(controlPath,"utf8"));
if(input.schema!=="mark_observable_input_blind_v1")throw new Error(`unsupported input ${input.schema}`);
if(prediction.schema!=="mark_blind_world_holdout_prediction_v2")throw new Error(`unsupported prediction ${prediction.schema}`);
if(control.schema!=="mark_blind_control_evaluation_v1")throw new Error(`unsupported control evaluation ${control.schema}`);
for(const[name,value,field]of[["input",input,"blindInputSha256"],["prediction",prediction,"blindSha256"],["control",control,"blindSha256"]]){const supplied=value[field];const rest={...value};delete rest[field];const computed=crypto.createHash("sha256").update(JSON.stringify(rest)).digest("hex");if(!supplied||supplied!==computed)throw new Error(`${name} SHA-256 verification failed`);}
async function dHash64(bytes){const{data}=await sharp(bytes).greyscale().resize(9,8,{fit:"fill"}).raw().toBuffer({resolveWithObject:true});let hash=0n;for(let y=0;y<8;y+=1)for(let x=0;x<8;x+=1)hash=(hash<<1n)|(data[y*9+x]>data[y*9+x+1]?1n:0n);return hash;}
function hamming(a,b){let x=a^b,count=0;while(x){count+=Number(x&1n);x>>=1n;}return count;}
const hashes=new Map();
for(const source of input.sources){const absolute=path.resolve(path.dirname(inputPath),source.capturePath);hashes.set(source.sourceGroupId,await dHash64(await fs.readFile(absolute)));}
const train=input.sources.filter(source=>source.lane==="train");
if(!train.length)throw new Error("visual baseline has no train sources");
const nearestTrain=(sourceGroupId)=>train.filter(source=>source.sourceGroupId!==sourceGroupId).map(source=>({sourceGroupId:source.sourceGroupId,distance:hamming(hashes.get(sourceGroupId),hashes.get(source.sourceGroupId))})).sort((a,b)=>a.distance-b.distance||a.sourceGroupId.localeCompare(b.sourceGroupId))[0]??null;
const wholeBySource=new Map(input.observations.filter(row=>row.proposalKind==="whole_capture").map(row=>[row.sourceGroupId,row]));
const holdoutPredById=new Map(prediction.familyPredictions.map(row=>[row.id,row]));
const controlPredById=new Map(control.wholeObjectPredictions.map(row=>[row.id,row]));
function evaluateLane(lane,predById){return input.sources.filter(source=>source.lane===lane).map(source=>{const observation=wholeBySource.get(source.sourceGroupId),structural=observation?predById.get(observation.id):null,visual=nearestTrain(source.sourceGroupId);return{sourceGroupId:source.sourceGroupId,observationId:observation?.id??null,structuralStatus:structural?.status??"missing",acceptedFamilyId:structural?.acceptedFamilyId??null,nearestVisualTrainSource:visual?.sourceGroupId??null,dHashDistance:visual?.distance??null,visualExplanation:visual&&visual.distance<=trivialThreshold?"ordinary_visual_similarity_plausible":"visually_nontrivial"};});}
const holdout=evaluateLane("holdout",holdoutPredById),controls=evaluateLane("control",controlPredById);
const acceptedHoldout=holdout.filter(row=>row.structuralStatus==="accepted"),nontrivialAccepted=acceptedHoldout.filter(row=>row.visualExplanation==="visually_nontrivial");
const acceptedControl=controls.filter(row=>row.structuralStatus==="accepted"),nontrivialControl=acceptedControl.filter(row=>row.visualExplanation==="visually_nontrivial");
const core={schema:"mark_blind_visual_baseline_evaluation_v1",generatedAt:new Date().toISOString(),sealedInputSha256:input.blindInputSha256,sealedPredictionSha256:prediction.blindSha256,sealedControlEvaluationSha256:control.blindSha256,baselineContract:{method:"64-bit difference hash over 9x8 grayscale whole capture",trivialThresholdBits:trivialThreshold,role:"flag structural acceptances that ordinary whole-image similarity may already explain",contextLabelsAvailable:false},summary:{holdoutWholeObjects:holdout.length,holdoutAccepted:acceptedHoldout.length,holdoutAcceptedVisuallyNontrivial:nontrivialAccepted.length,controlWholeObjects:controls.length,controlAccepted:acceptedControl.length,controlAcceptedVisuallyNontrivial:nontrivialControl.length},holdout,control:controls};
const blindSha256=crypto.createHash("sha256").update(JSON.stringify(core)).digest("hex"),artifact={...core,blindSha256};
await fs.mkdir(outDir,{recursive:true});await fs.writeFile(path.join(outDir,"mark-blind-visual-baseline-evaluation-v1.json"),`${JSON.stringify(artifact,null,2)}\n`);
await fs.writeFile(path.join(outDir,"summary.txt"),[`schema=${artifact.schema}`,`visual_trivial_threshold_bits=${trivialThreshold}`,`holdout_whole_objects=${holdout.length}`,`holdout_accepted=${acceptedHoldout.length}`,`holdout_accepted_visually_nontrivial=${nontrivialAccepted.length}`,`control_accepted=${acceptedControl.length}`,`control_accepted_visually_nontrivial=${nontrivialControl.length}`,`blind_sha256=${blindSha256}`].join("\n")+"\n");
if((process.env.MARK_REQUIRE_VISUAL_BASELINE_GATE??"0")==="1"&&nontrivialAccepted.length<1)throw new Error("no accepted whole-institution holdout object survived the ordinary visual-similarity baseline");
console.log(`Visual baseline: ${nontrivialAccepted.length}/${acceptedHoldout.length} accepted holdout whole objects are visually nontrivial at dHash>${trivialThreshold}`);
