import crypto from "node:crypto";
import fs from "node:fs/promises";
import path from "node:path";

const protocolPath=process.env.MARK_WHITE_PAINT_GLYPH_PROTOCOL??"research/mark/discovery-experiments/white-paint-glyph-transfer-v2.protocol.json";
const blindPath=process.env.MARK_WHITE_PAINT_GLYPH_BLIND??"artifacts/mark-white-paint-glyph-transfer-v2/blind/white-paint-glyph-proxy-blind.json";
const outDir=process.env.MARK_WHITE_PAINT_GLYPH_DISCOVERY_OUT??"artifacts/mark-white-paint-glyph-transfer-v2/frozen";
const sha=v=>crypto.createHash("sha256").update(JSON.stringify(v)).digest("hex");
const protocol=JSON.parse(await fs.readFile(protocolPath,"utf8"));
const blind=JSON.parse(await fs.readFile(blindPath,"utf8"));
const coreBlind={...blind};delete coreBlind.blindSha256;
if(sha(coreBlind)!==blind.blindSha256)throw new Error("blind corpus SHA mismatch");
const serialized=JSON.stringify(blind);
if(/\bG\d{5}\b/.test(serialized))throw new Error("blind packet contains Atlas identity");
for(const forbidden of ["system","character","char","codepoint","font","culture","language","sourceUrl"]){if(serialized.includes(`\"${forbidden}\"`))throw new Error(`blind packet contains forbidden key ${forbidden}`);}
const counts=(key)=>{const m={};for(const r of blind.records){const v=r.features[key];const k=v===null?"null":String(v);m[k]=(m[k]??0)+1;}return m;};
const signatures={};for(const r of blind.records){const f=r.features;const s=[f.operation,f.relation??"none",f.repetitionDegree,f.closure].join("|");signatures[s]=(signatures[s]??0)+1;}
const targetOps=["persist","turn","branch","cross","close","loop_continue"];
const core={schema:"mark_white_paint_glyph_transfer_blind_v2",experimentId:protocol.experimentId,parentWhitePaintGrammarSha256:protocol.parentEvidence.whitePaintGrammarSha256,blindCorpusSha256:blind.blindSha256,eligibleGlyphs:blind.eligible,physicalClasses:{operation:counts("operation"),relation:counts("relation"),degree:counts("repetitionDegree"),closure:counts("closure")},targetOperationCounts:Object.fromEntries(targetOps.map(op=>[op,blind.records.filter(r=>r.features.operation===op).length])),compoundSignatureCount:Object.keys(signatures).length,compoundSignatures:Object.entries(signatures).sort((a,b)=>b[1]-a[1]||a[0].localeCompare(b[0])).slice(0,80).map(([signature,count])=>({signature,count})),claimBoundary:protocol.claimBoundary};
const blindTransferSha256=sha(core);const packet={...core,blindTransferSha256};
await fs.mkdir(outDir,{recursive:true});await fs.writeFile(path.join(outDir,"white-paint-glyph-transfer-blind.json"),JSON.stringify(packet,null,2)+"\n");
const lines=[`blind_transfer_sha256=${blindTransferSha256}`,`blind_corpus_sha256=${blind.blindSha256}`,`eligible=${blind.eligible}`,`compound_signatures=${Object.keys(signatures).length}`,...targetOps.map(op=>`${op}=${core.targetOperationCounts[op]}`)];
await fs.writeFile(path.join(outDir,"blind-summary.txt"),lines.join("\n")+"\n");console.log(JSON.stringify(packet,null,2));
