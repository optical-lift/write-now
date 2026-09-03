import crypto from "node:crypto";
import fs from "node:fs/promises";
import path from "node:path";
import sharp from "sharp";

const manifestPath = process.env.MARK_HARVEST_MANIFEST ?? "research/mark/harvest-manifests/ten-boxes-attic-fixture.v1.json";
const outDir = process.env.MARK_HARVEST_OUT ?? "artifacts/mark-harvest-v1";
const rejoinOutDir = process.env.MARK_HARVEST_REJOIN_OUT ?? "artifacts/mark-harvest-rejoin-v1";
const maxBytes = Number(process.env.MARK_HARVEST_MAX_BYTES ?? 25 * 1024 * 1024);
const nearDuplicateBits = Math.max(0, Number(process.env.MARK_NEAR_DUPLICATE_BITS ?? 2));
const minPerLane = Math.max(1, Number(process.env.MARK_HARVEST_MIN_PER_LANE ?? 2));
const manifestBytes = await fs.readFile(manifestPath);
const manifest = JSON.parse(manifestBytes);
if (manifest.schema !== "mark_harvest_manifest_v1") throw new Error(`unsupported harvest manifest ${manifest.schema}`);

const salt = process.env.MARK_BLIND_SALT ?? crypto.randomBytes(32).toString("hex");
const continuityKey = process.env.MARK_CONTINUITY_KEY ?? (manifest.status === "synthetic_fixture" ? "mark-synthetic-continuity-fixture-v1" : null);
if (!continuityKey) throw new Error("physical harvesting requires MARK_CONTINUITY_KEY so repeated source bytes can be deduplicated without exposing their public hash");
const opaque = (value) => `S${crypto.createHash("sha256").update(`${salt}|${value}`).digest("hex").slice(0, 16).toUpperCase()}`;
const token = (kind, value) => crypto.createHash("sha256").update(`${salt}|${kind}|${value}`).digest("hex");
const continuityToken = (exactSha256) => crypto.createHmac("sha256", continuityKey).update(exactSha256).digest("hex");
const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));

function mimeFromPath(filePath) {
  const ext = path.extname(filePath).toLowerCase();
  if (ext === ".png") return { mime: "image/png", ext: ".png" };
  if (ext === ".jpg" || ext === ".jpeg") return { mime: "image/jpeg", ext: ".jpg" };
  if (ext === ".webp") return { mime: "image/webp", ext: ".webp" };
  if (ext === ".svg") return { mime: "image/svg+xml", ext: ".svg" };
  throw new Error(`unsupported image file type ${filePath}`);
}
function extForMime(mime) {
  if (mime.includes("png")) return ".png";
  if (mime.includes("jpeg") || mime.includes("jpg")) return ".jpg";
  if (mime.includes("webp")) return ".webp";
  if (mime.includes("svg")) return ".svg";
  throw new Error(`unsupported image MIME ${mime}`);
}
function syntheticSvg(recipe = {}) {
  if (recipe.template === "nine_dots") {
    const nonce=String(recipe.nonce ?? "0");
    const circles=[];
    for(const y of [25,50,75])for(const x of [40,80,120,160,200])circles.push(`<circle cx="${x}" cy="${y}" r="7"/>`);
    return `<svg xmlns="http://www.w3.org/2000/svg" width="260" height="100" viewBox="0 0 260 100" data-fixture-nonce="${nonce}"><rect width="260" height="100" fill="white"/><g fill="black" stroke="none">${circles.join("")}</g></svg>`;
  }
  const strokeWidth = Number(recipe.strokeWidth ?? 4);
  const dx = Number(recipe.dx ?? 0);
  const linecap = recipe.linecap === "square" ? "square" : "round";
  const dy = Number(recipe.dy ?? 0);
  return `<svg xmlns="http://www.w3.org/2000/svg" width="260" height="100" viewBox="0 0 260 100"><rect width="260" height="100" fill="white"/><g stroke="black" stroke-width="${strokeWidth}" fill="none" stroke-linecap="${linecap}" stroke-linejoin="round"><path d="M ${18+dx} ${78+dy} L ${20+dx} ${18+dy} L ${50+dx} ${62+dy}"/><path d="M ${82+dx} ${78+dy} L ${84+dx} ${18+dy} L ${114+dx} ${62+dy} M ${84+dx} ${46+dy} L ${111+dx} ${32+dy}"/><path d="M ${160+dx} ${16+dy} L ${160+dx} ${80+dy} M ${134+dx} ${47+dy} L ${186+dx} ${47+dy}"/><path d="M ${224+dx} ${16+dy} L ${224+dx} ${80+dy} M ${198+dx} ${47+dy} L ${250+dx} ${47+dy}"/><ellipse cx="${224+dx}" cy="47" rx="13" ry="16"/></g></svg>`;
}
async function perceptualHash(bytes) {
  const { data } = await sharp(bytes).greyscale().resize(9, 8, { fit: "fill" }).raw().toBuffer({ resolveWithObject: true });
  let hash = 0n;
  for (let y = 0; y < 8; y += 1) for (let x = 0; x < 8; x += 1) hash = (hash << 1n) | (data[y * 9 + x] > data[y * 9 + x + 1] ? 1n : 0n);
  return hash;
}
function hamming64(a, b) {
  let x = a ^ b, count = 0;
  while (x) { count += Number(x & 1n); x >>= 1n; }
  return count;
}
async function fetchImage(source, attempts = 3) {
  const capture = source.capture ?? {};
  let lastStatus = null;
  for (let attempt = 1; attempt <= attempts; attempt += 1) {
    const headers = {
      "user-agent": "Mozilla/5.0 (compatible; MarkResearchHarvester/2.0; research image custody)",
      "accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
      "accept-language": "en-US,en;q=0.8",
    };
    if (/^https:\/\//i.test(source.sourceUrl ?? "")) headers.referer = source.sourceUrl;
    const response = await fetch(capture.assetUrl, { redirect: "follow", headers });
    if (response.ok) return response;
    lastStatus = response.status;
    const retryable = response.status === 403 || response.status === 408 || response.status === 425 || response.status === 429 || response.status >= 500;
    if (!retryable || attempt === attempts) break;
    await sleep(attempt * 900);
  }
  const error = new Error(`harvest failed ${lastStatus ?? "network"} for ${source.sourceId}`);
  error.harvestStatus = lastStatus;
  throw error;
}

async function bytesFor(source) {
  const capture = source.capture ?? {};
  if (capture.syntheticRecipe) {
    if (manifest.status !== "synthetic_fixture") throw new Error(`syntheticRecipe forbidden for physical source ${source.sourceId}`);
    return { bytes: Buffer.from(syntheticSvg(capture.syntheticRecipe)), mime: "image/svg+xml", ext: ".svg", retrieval: "synthetic_fixture" };
  }
  if (capture.syntheticSvg) {
    if (manifest.status !== "synthetic_fixture") throw new Error(`syntheticSvg forbidden for physical source ${source.sourceId}`);
    return { bytes: Buffer.from(String(capture.syntheticSvg)), mime: "image/svg+xml", ext: ".svg", retrieval: "synthetic_fixture" };
  }
  if (capture.imagePath) {
    const absolute = path.resolve(path.dirname(manifestPath), capture.imagePath);
    const type = mimeFromPath(absolute);
    return { bytes: await fs.readFile(absolute), ...type, retrieval: "local_file" };
  }
  const response = await fetchImage(source);
  const bytes = Buffer.from(await response.arrayBuffer());
  if (bytes.length > maxBytes) throw new Error(`capture exceeds ${maxBytes} bytes (${source.sourceId})`);
  const mime = (response.headers.get("content-type") ?? "").split(";")[0].trim().toLowerCase();
  if (!mime.startsWith("image/")) throw new Error(`capture is not an image (${source.sourceId}: ${mime || "unknown"})`);
  return { bytes, mime, ext: extForMime(mime), retrieval: "https" };
}

await fs.mkdir(path.join(outDir, "captures"), { recursive: true });
await fs.mkdir(rejoinOutDir, { recursive: true });
const blindSources = [];
const custodySources = [];
const excludedSources = [];
const exactHashes = new Map();
const perceptualHashes = [];
for (const source of manifest.sources) {
  const sourceGroupId = opaque(source.sourceId);
  const contextual = structuredClone(source);
  delete contextual.capture?.syntheticRecipe;
  delete contextual.capture?.syntheticSvg;
  let captureResult;
  try {
    captureResult = await bytesFor(source);
  } catch (error) {
    if (manifest.status !== "physical_evidence") throw error;
    excludedSources.push({
      sourceGroupId,
      retrieval: "failed",
      exclusion: {
        reason: "retrieval_failed",
        status: error?.harvestStatus ?? null,
        message: String(error?.message ?? error),
      },
      ...contextual,
    });
    continue;
  }
  const { bytes, mime, ext, retrieval } = captureResult;
  const exactSha256 = crypto.createHash("sha256").update(bytes).digest("hex");
  if (manifest.status === "physical_evidence") {
    const exactMatch = exactHashes.get(exactSha256);
    if (exactMatch) {
      excludedSources.push({ sourceGroupId, exactCaptureSha256: exactSha256, retrieval, exclusion: { reason: "exact_duplicate", matchedSourceGroupId: exactMatch }, ...contextual });
      continue;
    }
    const pHash = await perceptualHash(bytes);
    const nearMatch = perceptualHashes.map(row => ({ ...row, distance: hamming64(pHash, row.hash) })).sort((a,b)=>a.distance-b.distance)[0];
    if (nearMatch && nearMatch.distance <= nearDuplicateBits) {
      excludedSources.push({ sourceGroupId, exactCaptureSha256: exactSha256, retrieval, exclusion: { reason: "perceptual_near_duplicate", matchedSourceGroupId: nearMatch.sourceGroupId, hammingDistance: nearMatch.distance, thresholdBits: nearDuplicateBits }, ...contextual });
      continue;
    }
    exactHashes.set(exactSha256, sourceGroupId);
    perceptualHashes.push({ sourceGroupId, hash: pHash });
  }
  const stableContinuityToken = continuityToken(exactSha256);
  const capturePath = path.posix.join("captures", `${sourceGroupId}${ext}`);
  await fs.writeFile(path.join(outDir, capturePath), bytes);
  const lane = source.challengeLane ?? null;
  if (lane && !new Set(["train", "holdout", "control"]).has(lane)) throw new Error(`invalid challenge lane ${lane} on ${source.sourceId}`);
  blindSources.push({ sourceGroupId, adapter: "image_2d", capturePath, captureMime: mime, captureToken: token("capture", exactSha256), continuityToken: stableContinuityToken, ...(lane ? { lane } : {}) });
  custodySources.push({ sourceGroupId, exactCaptureSha256: exactSha256, continuityToken: stableContinuityToken, retrieval, ...contextual });
}
const laneCounts = Object.fromEntries(["train", "holdout", "control"].map(lane => [lane, blindSources.filter(source => source.lane === lane).length]));
const expectedLanes = [...new Set(manifest.sources.map(source => source.challengeLane).filter(Boolean))].sort();
const retrievalFailedCount = excludedSources.filter(source => source.exclusion?.reason === "retrieval_failed").length;
const blindCore = {
  schema: "mark_harvested_sources_blind_v1",
  corpusKind: manifest.status === "synthetic_fixture" ? "synthetic_pipeline_fixture_not_evidence" : "physical_observable_evidence",
  generatedAt: new Date().toISOString(),
  sources: blindSources.sort((a,b)=>a.sourceGroupId.localeCompare(b.sourceGroupId)),
  deduplicationContract: manifest.status === "physical_evidence" ? { exactBytes: true, perceptualDHash64: true, maxHammingDistance: nearDuplicateBits, excludedCount: excludedSources.length, retrievalFailedCount } : { exactBytes: false, perceptualDHash64: false, fixtureBypass: true },
  retrievalContract: manifest.status === "physical_evidence" ? { failedSourcesAuditedBeforeBlindAnalysis: true, minimumRetainedPerDeclaredLane: minPerLane, retainedLaneCounts: laneCounts } : { syntheticFixture: true },
  blindnessContract: { contextualMetadataPresent: false, unit: "source_capture", categoryLabelsAvailable: false, continuityToken: "HMAC-SHA256 over exact source bytes with private MARK_CONTINUITY_KEY", challengeLaneMayBePresent: true },
};
const blindSha256 = crypto.createHash("sha256").update(JSON.stringify(blindCore)).digest("hex");
const blind = { ...blindCore, blindSha256 };
await fs.writeFile(path.join(outDir, "mark-harvested-sources-blind-v1.json"), `${JSON.stringify(blind, null, 2)}\n`);
const rejoin = {
  schema: "mark_harvest_custody_rejoin_v1",
  sealedHarvestBlindSha256: blindSha256,
  manifestSha256: crypto.createHash("sha256").update(manifestBytes).digest("hex"),
  harvestId: manifest.harvestId,
  status: manifest.status,
  retrievalGate: { minimumRetainedPerDeclaredLane: minPerLane, retainedLaneCounts: laneCounts, retrievalFailedCount },
  sources: custodySources.sort((a,b)=>a.sourceGroupId.localeCompare(b.sourceGroupId)),
  excludedSources: excludedSources.sort((a,b)=>a.sourceGroupId.localeCompare(b.sourceGroupId)),
};
await fs.writeFile(path.join(rejoinOutDir, "mark-harvest-custody-rejoin-v1.json"), `${JSON.stringify(rejoin, null, 2)}\n`);
if (blindSources.length < 2) throw new Error(`harvest retained too few independent sources after audited exclusions: ${blindSources.length}`);
if (manifest.status === "physical_evidence") {
  const failedLanes = expectedLanes.filter(lane => (laneCounts[lane] ?? 0) < minPerLane);
  if (failedLanes.length) throw new Error(`harvest retained-lane gate failed: ${failedLanes.map(lane => `${lane}=${laneCounts[lane] ?? 0}<${minPerLane}`).join(", ")}; retrieval_failed=${retrievalFailedCount}`);
}
console.log(`Harvested ${blind.sources.length} independent source objects; excluded ${excludedSources.length} unavailable/exact/perceptual witnesses`);
console.log(`Retained lanes: ${Object.entries(laneCounts).map(([lane,count]) => `${lane}=${count}`).join(", ")}`);
console.log(`Harvest blind SHA-256: ${blindSha256}`);
