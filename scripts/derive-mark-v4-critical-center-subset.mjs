#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";

const pairDir=process.env.MARK_V4_UNLABELED ?? "artifact-staging/v4-unlabeled";
const sealedDir=process.env.MARK_SEALED_EVIDENCE ?? "artifact-staging/sealed-evidence";
const outDir=process.env.MARK_V4_SUBSET_OUT ?? "artifacts/mark-critical-center-subset-v4";

function locate(root,name){
  const hits=[];
  function walk(p){
    for(const ent of fs.readdirSync(p,{withFileTypes:true})){
      const q=path.join(p,ent.name);
      if(ent.isDirectory()) walk(q); else if(ent.name===name) hits.push(q);
    }
  }
  walk(root);
  if(hits.length!==1) throw new Error(`expected one ${name}, found ${hits.length}`);
  return hits[0];
}
const freeze=JSON.parse(fs.readFileSync(locate(pairDir,"pair-world-freeze.json"),"utf8"));
const obsIds=new Set(fs.readFileSync(locate(pairDir,"observation-ids.txt"),"utf8").trim().split(/\n+/).filter(Boolean));
if(obsIds.size!==freeze.uniqueObservations) throw new Error("observation-id freeze count mismatch");
const inputPath=locate(sealedDir,"mark-observable-input-blind-v1.compiler.json");
const input=JSON.parse(fs.readFileSync(inputPath,"utf8"));
if(input.blindInputSha256!==freeze.parentSourceBlindInputSha256) throw new Error("sealed compiler input is not v3 parent");
const selectedObs=input.observations.filter(o=>obsIds.has(o.id));
if(selectedObs.length!==obsIds.size) {
  const found=new Set(selectedObs.map(o=>o.id));
  const missing=[...obsIds].filter(x=>!found.has(x));
  throw new Error(`missing frozen observations from sealed input: ${missing.slice(0,10).join(",")}`);
}
const neededSources=new Set(selectedObs.map(o=>o.sourceGroupId));
const selectedSources=input.sources.filter(s=>neededSources.has(s.sourceGroupId));
if(selectedSources.length!==neededSources.size) throw new Error("missing source rows for selected observations");
for(const o of selectedObs){
  const s=selectedSources.find(x=>x.sourceGroupId===o.sourceGroupId);
  if(!s || s.lane!==o.lane) throw new Error(`source/observation lane mismatch ${o.id}`);
}
const {blindInputSha256:parentBlind,...rest}=input;
const core={...rest,sources:selectedSources,observations:selectedObs};
const derivedBlindInputSha256=crypto.createHash("sha256").update(JSON.stringify(core)).digest("hex");
const derived={...core,blindInputSha256:derivedBlindInputSha256};
fs.mkdirSync(outDir,{recursive:true});
const derivedPath=path.join(path.dirname(inputPath),"mark-v4-critical-center-subset.compiler.json");
fs.writeFileSync(derivedPath,JSON.stringify(derived));
const bytes=fs.readFileSync(derivedPath);
const ids=[...obsIds].sort();
const custody={
  schema:"mark_critical_center_subset_custody_v4",
  pairWorldFreezeSha256:freeze.pairWorldFreezeSha256,
  parentBlindInputSha256:parentBlind,
  derivedBlindInputSha256,
  derivedInputSha256:crypto.createHash("sha256").update(bytes).digest("hex"),
  observations:selectedObs.length,
  sources:selectedSources.length,
  observationIdsSha256:crypto.createHash("sha256").update(ids.join("\n")+"\n").digest("hex"),
  originalCompilerInputPath:path.relative(sealedDir,inputPath),
  derivedCompilerInputPath:derivedPath,
  contract:{
    observationIdsFrozenBeforeSealedEvidenceAvailable:true,
    sourceCapturePathsUnchanged:true,
    observationRegionsUnchanged:true,
    segmentationUnchanged:true,
    laneAssignmentsUnchanged:true,
    provenanceAvailable:false
  }
};
fs.writeFileSync(path.join(outDir,"subset-custody.json"),JSON.stringify(custody,null,2)+"\n");
fs.writeFileSync(path.join(outDir,"derived-input-path.txt"),derivedPath+"\n");
console.log(JSON.stringify(custody,null,2));
