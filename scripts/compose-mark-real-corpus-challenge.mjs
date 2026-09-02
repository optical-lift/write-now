import fs from "node:fs/promises";
import path from "node:path";

const inputs = String(process.env.MARK_CHALLENGE_MANIFESTS ?? "").split(",").map(x => x.trim()).filter(Boolean);
const outDir = process.env.MARK_CHALLENGE_OUT ?? "artifacts/mark-real-corpus-challenge-v1";
const challengeId = process.env.MARK_CHALLENGE_ID ?? "mark:real-corpus:open-access-firehose-v1";
if (inputs.length < 3) throw new Error("MARK_CHALLENGE_MANIFESTS must provide at least train, holdout, and control manifests");

const manifests = [];
for (const file of inputs) {
  const manifest = JSON.parse(await fs.readFile(file, "utf8"));
  if (manifest.schema !== "mark_harvest_manifest_v1" || manifest.status !== "physical_evidence") throw new Error(`challenge input must be physical mark_harvest_manifest_v1: ${file}`);
  manifests.push({ file, manifest });
}
const laneInstitutions = new Map([["train", new Set()], ["holdout", new Set()], ["control", new Set()]]);
const sources = [];
for (const { file, manifest } of manifests) {
  for (const source of manifest.sources) {
    const lane = source.challengeLane;
    if (!laneInstitutions.has(lane)) throw new Error(`${file}: source ${source.sourceId} has invalid/missing challengeLane`);
    laneInstitutions.get(lane).add(source.institution);
    sources.push(structuredClone(source));
  }
}
for (const lane of ["train", "holdout", "control"]) if (!sources.some(source => source.challengeLane === lane)) throw new Error(`challenge has no ${lane} sources`);
for (const trainInstitution of laneInstitutions.get("train")) {
  if (laneInstitutions.get("holdout").has(trainInstitution)) throw new Error(`institution ${trainInstitution} appears in both train and holdout; whole-institution holdout was violated`);
  if (laneInstitutions.get("control").has(trainInstitution)) throw new Error(`institution ${trainInstitution} appears in both train and control`);
}
for (const holdoutInstitution of laneInstitutions.get("holdout")) if (laneInstitutions.get("control").has(holdoutInstitution)) throw new Error(`institution ${holdoutInstitution} appears in both holdout and control`);

sources.sort((a,b) => `${a.challengeLane}|${a.institution}|${a.objectId}`.localeCompare(`${b.challengeLane}|${b.institution}|${b.objectId}`));
sources.forEach((source, index) => { source.sourceId = `SRC${String(index + 1).padStart(5, "0")}`; });
const laneSummary = Object.fromEntries(["train", "holdout", "control"].map(lane => [lane, {
  sources: sources.filter(source => source.challengeLane === lane).length,
  institutions: [...laneInstitutions.get(lane)].sort(),
}]));
const manifest = {
  schema: "mark_harvest_manifest_v1",
  harvestId: challengeId,
  status: "physical_evidence",
  purpose: "Hostile real-corpus challenge assembled from machine-enumerated institution feeds. Whole institutions are isolated by train, holdout, and control lane before blind harvesting.",
  challengeContract: { wholeInstitutionHoldout: true, controlNeverLearns: true, individualObjectsHandSelected: false, laneSummary },
  sources,
};
await fs.mkdir(outDir, { recursive: true });
await fs.writeFile(path.join(outDir, "generated-challenge-harvest-manifest.v1.json"), `${JSON.stringify(manifest, null, 2)}\n`);
await fs.writeFile(path.join(outDir, "summary.txt"), [
  `schema=${manifest.schema}`,
  `challenge_id=${challengeId}`,
  `sources=${sources.length}`,
  `train_sources=${laneSummary.train.sources}`,
  `holdout_sources=${laneSummary.holdout.sources}`,
  `control_sources=${laneSummary.control.sources}`,
  `train_institutions=${laneSummary.train.institutions.join("|")}`,
  `holdout_institutions=${laneSummary.holdout.institutions.join("|")}`,
  `control_institutions=${laneSummary.control.institutions.join("|")}`,
].join("\n") + "\n");
console.log(`Composed real-corpus challenge: train=${laneSummary.train.sources}, holdout=${laneSummary.holdout.sources}, control=${laneSummary.control.sources}`);
