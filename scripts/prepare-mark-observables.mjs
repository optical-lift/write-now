import crypto from "node:crypto";
import fs from "node:fs/promises";
import path from "node:path";

const packetPath = process.env.MARK_OBSERVABLE_PACKET ?? "research/mark/observable-corpus/ten-boxes-fixture.v1.json";
const outDir = process.env.MARK_OBSERVABLE_INPUT_OUT ?? "artifacts/mark-observable-input-v1";
const rejoinOutDir = process.env.MARK_OBSERVABLE_REJOIN_OUT ?? "artifacts/mark-observable-rejoin-v1";
const packetBytes = await fs.readFile(packetPath);
const packet = JSON.parse(packetBytes);

if (packet.schema !== "mark_observable_corpus_packet_v1") throw new Error(`unsupported packet schema ${packet.schema}`);
if (!Array.isArray(packet.sources) || !Array.isArray(packet.observations)) throw new Error("packet must include sources[] and observations[]");
if (!packet.sources.length || !packet.observations.length) throw new Error("packet cannot be empty");

const salt = process.env.MARK_BLIND_SALT ?? crypto.randomBytes(32).toString("hex");
const opaque = (prefix, value) => `${prefix}${crypto.createHash("sha256").update(`${salt}|${value}`).digest("hex").slice(0, 16).toUpperCase()}`;
const token = (kind, value) => crypto.createHash("sha256").update(`${salt}|${kind}|${value}`).digest("hex");
const blindSourceId = new Map(packet.sources.map((source) => [source.sourceId, opaque("S", source.sourceId)]));
const blindObservationId = new Map(packet.observations.map((observation) => [observation.observationId, opaque("O", observation.observationId)]));
const sourceById = new Map(packet.sources.map((source) => [source.sourceId, source]));

function extensionForMime(mime) {
  if (mime === "image/png") return ".png";
  if (mime === "image/jpeg") return ".jpg";
  if (mime === "image/webp") return ".webp";
  if (mime === "image/svg+xml") return ".svg";
  throw new Error(`unsupported image MIME ${mime}`);
}

function mimeFromPath(filePath) {
  const ext = path.extname(filePath).toLowerCase();
  if (ext === ".png") return "image/png";
  if (ext === ".jpg" || ext === ".jpeg") return "image/jpeg";
  if (ext === ".webp") return "image/webp";
  if (ext === ".svg") return "image/svg+xml";
  throw new Error(`unsupported image file ${filePath}`);
}

async function captureBytes(source) {
  const capture = source.capture ?? {};
  if ((capture.adapter ?? "image_2d") !== "image_2d") throw new Error(`unsupported capture adapter ${capture.adapter} on ${source.sourceId}`);
  if (capture.syntheticRecipe) {
    if (packet.status !== "synthetic_fixture") throw new Error(`syntheticRecipe allowed only in synthetic fixtures (${source.sourceId})`);
    const strokeWidth = Number(capture.syntheticRecipe.strokeWidth ?? 4);
    const dx = Number(capture.syntheticRecipe.dx ?? 0);
    const linecap = capture.syntheticRecipe.linecap === "square" ? "square" : "round";
    const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="240" height="90" viewBox="0 0 240 90"><rect width="240" height="90" fill="white"/><g stroke="black" stroke-width="${strokeWidth}" fill="none" stroke-linecap="${linecap}" stroke-linejoin="round"><path d="M ${18+dx} 70 L ${20+dx} 18 L ${48+dx} 57"/><path d="M ${78+dx} 70 L ${80+dx} 18 L ${108+dx} 57 M ${80+dx} 43 L ${106+dx} 31"/><path d="M ${150+dx} 15 L ${150+dx} 72 M ${126+dx} 43 L ${174+dx} 43"/><path d="M ${210+dx} 15 L ${210+dx} 72 M ${186+dx} 43 L ${234+dx} 43"/><ellipse cx="${210+dx}" cy="43" rx="12" ry="14"/></g></svg>`;
    return { bytes: Buffer.from(svg), mime: "image/svg+xml", ext: ".svg" };
  }
  if (capture.syntheticSvg != null) {
    if (packet.status !== "synthetic_fixture") throw new Error(`syntheticSvg allowed only in synthetic fixtures (${source.sourceId})`);
    return { bytes: Buffer.from(String(capture.syntheticSvg)), mime: "image/svg+xml", ext: ".svg" };
  }
  if (capture.imageDataUri) {
    if (packet.status !== "synthetic_fixture") throw new Error(`imageDataUri allowed only in synthetic fixtures (${source.sourceId})`);
    const match = /^data:([^;,]+);base64,(.+)$/.exec(capture.imageDataUri);
    if (!match) throw new Error(`invalid base64 imageDataUri on ${source.sourceId}`);
    return { bytes: Buffer.from(match[2], "base64"), mime: match[1], ext: extensionForMime(match[1]) };
  }
  if (!capture.imagePath) throw new Error(`source ${source.sourceId} has no capture.imagePath`);
  const absolute = path.resolve(path.dirname(packetPath), capture.imagePath);
  const mime = mimeFromPath(absolute);
  return { bytes: await fs.readFile(absolute), mime, ext: extensionForMime(mime) };
}

function deterministicLanes() {
  const explicitAllowed = packet.status === "synthetic_fixture";
  if (explicitAllowed && packet.sources.every((source) => source.blindLane)) {
    return new Map(packet.sources.map((source) => [source.sourceId, source.blindLane]));
  }
  const scored = packet.sources.map((source) => ({
    sourceId: source.sourceId,
    score: crypto.createHash("sha256").update(`mark-holdout-v1|${packet.corpusId}|${source.sourceId}`).digest("hex"),
  })).sort((a, b) => a.score.localeCompare(b.score));
  const holdoutCount = packet.sources.length >= 5 ? Math.max(1, Math.round(packet.sources.length * 0.2)) : 0;
  const holdout = new Set(scored.slice(0, holdoutCount).map((entry) => entry.sourceId));
  return new Map(packet.sources.map((source) => [source.sourceId, holdout.has(source.sourceId) ? "holdout" : "train"]));
}

const laneBySource = deterministicLanes();
await fs.mkdir(path.join(outDir, "captures"), { recursive: true });
await fs.mkdir(rejoinOutDir, { recursive: true });

const blindSources = [];
const custodySources = [];
const exactPhysicalHashes = new Set();
for (const source of packet.sources) {
  const { bytes, mime, ext } = await captureBytes(source);
  const exactSha256 = crypto.createHash("sha256").update(bytes).digest("hex");
  if (packet.status === "physical_evidence") {
    if (exactPhysicalHashes.has(exactSha256)) throw new Error(`duplicate physical capture bytes cannot count as independent source objects (${source.sourceId})`);
    exactPhysicalHashes.add(exactSha256);
  }
  const sourceGroupId = blindSourceId.get(source.sourceId);
  const relativePath = path.posix.join("captures", `${sourceGroupId}${ext}`);
  await fs.writeFile(path.join(outDir, relativePath), bytes);
  blindSources.push({
    sourceGroupId,
    lane: laneBySource.get(source.sourceId),
    adapter: "image_2d",
    capturePath: relativePath,
    captureMime: mime,
    captureToken: token("capture", exactSha256),
  });
  const contextual = structuredClone(source);
  if (contextual.capture) {
    delete contextual.capture.syntheticRecipe;
    delete contextual.capture.syntheticSvg;
    delete contextual.capture.imageDataUri;
  }
  custodySources.push({ sourceGroupId, exactCaptureSha256: exactSha256, ...contextual });
}

const blindObservations = packet.observations.map((observation) => {
  if (!sourceById.has(observation.sourceId)) throw new Error(`unknown source ${observation.sourceId} on ${observation.observationId}`);
  return {
    id: blindObservationId.get(observation.observationId),
    sourceGroupId: blindSourceId.get(observation.sourceId),
    lane: laneBySource.get(observation.sourceId),
    region: observation.region ?? null,
    segmentation: {
      polarity: observation.segmentation?.polarity ?? "dark_on_light",
      threshold: observation.segmentation?.threshold ?? "otsu",
    },
  };
});

const blindCore = {
  schema: "mark_observable_input_blind_v1",
  corpusKind: packet.status === "synthetic_fixture" ? "synthetic_pipeline_fixture_not_evidence" : "physical_observable_evidence",
  generatedAt: new Date().toISOString(),
  lanePolicy: packet.status === "synthetic_fixture" && packet.sources.every((source) => source.blindLane)
    ? "fixture_explicit_source_lane"
    : "deterministic_source_level_80_20_holdout",
  sources: blindSources.sort((a, b) => a.sourceGroupId.localeCompare(b.sourceGroupId)),
  observations: blindObservations.sort((a, b) => a.id.localeCompare(b.id)),
  blindnessContract: {
    unit: "observable_configuration",
    permitted: ["opaque_ids", "source_independence", "technical_capture_adapter", "local_capture_path", "salted_capture_token", "region", "segmentation", "train_or_holdout_lane"],
    forbidden: ["object_category", "culture", "language", "sign_name", "reading", "meaning", "chronology", "geography", "institution", "catalog_identity", "scholarly_interpretation"],
  },
};

const forbiddenKeys = new Set(["boxLabel", "objectCategory", "culture", "system", "language", "signName", "reading", "meaning", "chronology", "geography", "institution", "sourceUrl", "objectId", "interpretation", "context"]);
function assertBlind(value, trail = []) {
  if (Array.isArray(value)) return value.forEach((item, index) => assertBlind(item, [...trail, String(index)]));
  if (!value || typeof value !== "object") return;
  for (const [key, nested] of Object.entries(value)) {
    if (forbiddenKeys.has(key)) throw new Error(`blind input contains forbidden field ${[...trail, key].join(".")}`);
    assertBlind(nested, [...trail, key]);
  }
}
assertBlind(blindCore);
const blindInputSha256 = crypto.createHash("sha256").update(JSON.stringify(blindCore)).digest("hex");
const blind = { ...blindCore, blindInputSha256 };
await fs.writeFile(path.join(outDir, "mark-observable-input-blind-v1.json"), `${JSON.stringify(blind, null, 2)}\n`);

const rejoin = {
  schema: "mark_observable_custody_rejoin_v1",
  sealedBlindInputSha256: blindInputSha256,
  packetSha256: crypto.createHash("sha256").update(packetBytes).digest("hex"),
  corpusId: packet.corpusId,
  status: packet.status,
  sources: custodySources.sort((a, b) => a.sourceGroupId.localeCompare(b.sourceGroupId)),
  observations: packet.observations.map((observation) => ({ blindId: blindObservationId.get(observation.observationId), ...observation })).sort((a, b) => a.blindId.localeCompare(b.blindId)),
};
await fs.writeFile(path.join(rejoinOutDir, "mark-observable-custody-rejoin-v1.json"), `${JSON.stringify(rejoin, null, 2)}\n`);
console.log(`Prepared ${blind.observations.length} observable configurations from ${blind.sources.length} source objects`);
console.log(`Blind observable input SHA-256: ${blindInputSha256}`);
