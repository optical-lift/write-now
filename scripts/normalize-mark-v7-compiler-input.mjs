import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import sharp from "sharp";

const sourcePath = process.env.MARK_PROPOSAL_BLIND_INPUT ?? "artifacts/mark-conveyor-input-v1/mark-observable-input-blind-v1.json";
const outputPath = process.env.MARK_V7_COMPILER_INPUT ?? "artifacts/mark-conveyor-input-v1/mark-observable-input-blind-v1.compiler.json";
const custodyPath = process.env.MARK_V7_NORMALIZATION_CUSTODY ?? path.join(path.dirname(outputPath), "compiler-normalization-custody.json");
const source = JSON.parse(fs.readFileSync(sourcePath, "utf8"));
const { blindInputSha256: parentBlindInputSha256, ...sourceCore } = source;
const computedParent = crypto.createHash("sha256").update(JSON.stringify(sourceCore)).digest("hex");
if (!parentBlindInputSha256 || parentBlindInputSha256 !== computedParent) throw new Error("proposal blind input SHA-256 verification failed before compiler normalization");

const sourceDir = path.dirname(sourcePath);
const outputDir = path.dirname(outputPath);
if (path.resolve(sourceDir) !== path.resolve(outputDir)) throw new Error("compiler-normalized blind input must remain beside the sealed proposal input");
const rasterDir = path.join(outputDir, "compiler-captures");
fs.mkdirSync(rasterDir, { recursive: true });

const wholeBySource = new Map(source.observations.filter(o => o.proposalKind === "whole_capture").map(o => [o.sourceGroupId, o]));
const mappings = [];
const normalizedSources = [];
for (const item of source.sources) {
  let capturePath = item.capturePath;
  if (path.extname(capturePath).toLowerCase() === ".svg") {
    const absolute = path.resolve(sourceDir, capturePath);
    const physicalBytes = fs.readFileSync(absolute);
    const { data, info } = await sharp(physicalBytes).greyscale().raw().toBuffer({ resolveWithObject: true });
    const whole = wholeBySource.get(item.sourceGroupId);
    if (!whole || whole.region.x !== 0 || whole.region.y !== 0 || whole.region.width !== info.width || whole.region.height !== info.height) {
      throw new Error(`SVG raster geometry no longer matches sealed proposal for ${item.sourceGroupId}: proposal=${JSON.stringify(whole?.region)} raster=${info.width}x${info.height}`);
    }
    const compilerBytes = await sharp(data, { raw: { width: info.width, height: info.height, channels: info.channels } }).png({ compressionLevel: 9 }).toBuffer();
    const outputName = `${item.sourceGroupId}.png`;
    const output = path.join(rasterDir, outputName);
    fs.writeFileSync(output, compilerBytes);
    capturePath = path.posix.join("compiler-captures", outputName);
    mappings.push({
      sourceGroupId: item.sourceGroupId,
      physicalCapturePath: item.capturePath,
      compilerCapturePath: capturePath,
      width: info.width,
      height: info.height,
      physicalCaptureSha256: crypto.createHash("sha256").update(physicalBytes).digest("hex"),
      compilerCaptureSha256: crypto.createHash("sha256").update(compilerBytes).digest("hex"),
    });
  }
  normalizedSources.push({ ...item, capturePath });
}

const compilerCore = { ...sourceCore, sources: normalizedSources };
const compilerBlindInputSha256 = crypto.createHash("sha256").update(JSON.stringify(compilerCore)).digest("hex");
fs.writeFileSync(outputPath, `${JSON.stringify({ ...compilerCore, blindInputSha256: compilerBlindInputSha256 }, null, 2)}\n`);
const custody = {
  schema: "mark_v7_compiler_capture_normalization_custody_v1",
  parentProposalBlindInputSha256,
  compilerBlindInputSha256,
  vectorPolicy: "svg rendered by the same sharp grayscale raster path used by blind proposal; sealed whole-capture geometry must match exactly",
  originalCapturesRetained: true,
  normalizedVectorCaptures: mappings.length,
  mappings,
};
fs.writeFileSync(custodyPath, `${JSON.stringify(custody, null, 2)}\n`);
console.log(`compiler input ${compilerBlindInputSha256}; normalized ${mappings.length} SVG captures; parent proposal ${parentBlindInputSha256}`);
