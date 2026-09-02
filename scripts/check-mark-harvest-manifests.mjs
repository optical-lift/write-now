import fs from "node:fs/promises";
import path from "node:path";

const root = process.env.MARK_HARVEST_MANIFEST_DIR ?? "research/mark/harvest-manifests";
const entries = await fs.readdir(root, { withFileTypes: true }).catch(() => []);
const files = entries.filter((entry) => entry.isFile() && entry.name.endsWith(".json")).map((entry) => path.join(root, entry.name));
if (!files.length) throw new Error(`no Mark harvest manifests found in ${root}`);

const sourceIdPattern = /^SRC\d{4,}$/;
const allowedStatus = new Set(["synthetic_fixture", "physical_evidence"]);
let checked = 0;

function nonEmpty(value, label) {
  if (typeof value !== "string" || !value.trim()) throw new Error(`${label} must be a non-empty string`);
}

for (const file of files) {
  const manifest = JSON.parse(await fs.readFile(file, "utf8"));
  if (manifest.schema !== "mark_harvest_manifest_v1") continue;
  checked += 1;
  nonEmpty(manifest.harvestId, `${file}: harvestId`);
  if (!allowedStatus.has(manifest.status)) throw new Error(`${file}: invalid status ${manifest.status}`);
  if (!Array.isArray(manifest.sources) || manifest.sources.length < 2) throw new Error(`${file}: sources[] must contain at least two entries`);
  const sourceIds = new Set();
  for (const source of manifest.sources) {
    nonEmpty(source.sourceId, `${file}: sourceId`);
    if (!sourceIdPattern.test(source.sourceId)) throw new Error(`${file}: sourceId must be opaque SRC#### (${source.sourceId})`);
    if (sourceIds.has(source.sourceId)) throw new Error(`${file}: duplicate sourceId ${source.sourceId}`);
    sourceIds.add(source.sourceId);
    const capture = source.capture ?? {};
    if ((capture.adapter ?? "image_2d") !== "image_2d") throw new Error(`${file}: unsupported capture adapter on ${source.sourceId}`);
    if (manifest.status === "synthetic_fixture") {
      if (!capture.syntheticRecipe && !capture.syntheticSvg && !capture.imagePath) throw new Error(`${file}: fixture source ${source.sourceId} needs syntheticRecipe, syntheticSvg, or imagePath`);
    } else {
      nonEmpty(capture.assetUrl, `${file}: ${source.sourceId}.capture.assetUrl`);
      if (!/^https:\/\//i.test(capture.assetUrl)) throw new Error(`${file}: physical assetUrl must use https (${source.sourceId})`);
      nonEmpty(source.sourceUrl, `${file}: ${source.sourceId}.sourceUrl`);
      nonEmpty(source.institution, `${file}: ${source.sourceId}.institution`);
      nonEmpty(source.objectId, `${file}: ${source.sourceId}.objectId`);
      nonEmpty(source.rightsBasis, `${file}: ${source.sourceId}.rightsBasis`);
      if (capture.syntheticRecipe || capture.syntheticSvg) throw new Error(`${file}: physical evidence cannot contain synthetic capture fields`);
    }
  }
}

if (!checked) throw new Error(`no mark_harvest_manifest_v1 files found in ${root}`);
console.log(`Validated ${checked} Mark harvest manifest(s).`);
