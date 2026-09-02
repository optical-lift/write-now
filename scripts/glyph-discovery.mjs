import crypto from "node:crypto";
import fs from "node:fs/promises";
import path from "node:path";
import { createRequire } from "node:module";
import { chromium } from "playwright";

const require = createRequire(import.meta.url);
const playwrightVersion = require("playwright/package.json").version;
const url = process.env.GLYPH_ATLAS_URL ?? "http://127.0.0.1:3000/glyph-atlas";
const outDir = process.env.GLYPH_DISCOVERY_OUT ?? "artifacts/glyph-discovery-v1";
const REPRESENTATIONS = ["topology", "geometry", "symmetry", "combined"];
const FORBIDDEN_KEYS = new Set([
  "char",
  "fontFamily",
  "system",
  "systemLabel",
  "unicodeLabel",
  "context",
  "sourceUrl",
  "displayBasis",
]);

function median(values) {
  const sorted = [...values].sort((a, b) => a - b);
  const middle = Math.floor(sorted.length / 2);
  return sorted.length % 2 ? sorted[middle] : (sorted[middle - 1] + sorted[middle]) / 2;
}

function robustScale(matrix) {
  if (!matrix.length) return [];
  const columns = matrix[0].length;
  const centers = [];
  const scales = [];
  for (let column = 0; column < columns; column += 1) {
    const values = matrix.map((row) => row[column]);
    const center = median(values);
    const mad = median(values.map((value) => Math.abs(value - center)));
    const mean = values.reduce((sum, value) => sum + value, 0) / values.length;
    const variance = values.reduce((sum, value) => sum + (value - mean) ** 2, 0) / values.length;
    const fallback = Math.sqrt(variance) || 1;
    centers.push(center);
    scales.push(mad > 1e-9 ? mad * 1.4826 : fallback);
  }
  return matrix.map((row) => row.map((value, index) => {
    const z = (value - centers[index]) / scales[index];
    return Math.max(-8, Math.min(8, z));
  }));
}

function euclidean(a, b) {
  let total = 0;
  for (let i = 0; i < a.length; i += 1) total += (a[i] - b[i]) ** 2;
  return Math.sqrt(total);
}

function pairwise(matrix) {
  return matrix.map((row, i) => matrix.map((other, j) => (i === j ? 0 : euclidean(row, other))));
}

function mean(values) {
  return values.reduce((sum, value) => sum + value, 0) / Math.max(1, values.length);
}

function vectorFor(record, representation) {
  const angle = (record.orientation * Math.PI) / 180;
  const topology = [record.components, record.holes, record.endpoints, record.junctions];
  const geometry = [Math.log(Math.max(0.05, record.aspect)), Math.cos(2 * angle), Math.sin(2 * angle)];
  const symmetry = [record.verticalSymmetry, record.horizontalSymmetry, Math.abs(record.verticalSymmetry - record.horizontalSymmetry)];
  if (representation === "topology") return topology;
  if (representation === "geometry") return geometry;
  if (representation === "symmetry") return symmetry;
  return [...topology, ...geometry, ...symmetry];
}

function deterministicKMeans(matrix, k, maxIterations = 120) {
  const n = matrix.length;
  if (k <= 0 || k > n) throw new Error(`invalid k=${k}`);
  const norms = matrix.map((row) => row.reduce((sum, value) => sum + value * value, 0));
  const first = norms.indexOf(Math.min(...norms));
  const centroidIndexes = [first];
  while (centroidIndexes.length < k) {
    let bestIndex = -1;
    let bestDistance = -1;
    for (let i = 0; i < n; i += 1) {
      if (centroidIndexes.includes(i)) continue;
      const nearest = Math.min(...centroidIndexes.map((index) => euclidean(matrix[i], matrix[index])));
      if (nearest > bestDistance + 1e-12) {
        bestDistance = nearest;
        bestIndex = i;
      }
    }
    centroidIndexes.push(bestIndex);
  }

  let centroids = centroidIndexes.map((index) => [...matrix[index]]);
  let assignment = new Array(n).fill(-1);

  for (let iteration = 0; iteration < maxIterations; iteration += 1) {
    let changed = false;
    for (let i = 0; i < n; i += 1) {
      let bestCluster = 0;
      let bestDistance = Number.POSITIVE_INFINITY;
      for (let cluster = 0; cluster < k; cluster += 1) {
        const distance = euclidean(matrix[i], centroids[cluster]);
        if (distance < bestDistance - 1e-12) {
          bestDistance = distance;
          bestCluster = cluster;
        }
      }
      if (assignment[i] !== bestCluster) {
        assignment[i] = bestCluster;
        changed = true;
      }
    }
    if (!changed && iteration > 0) break;

    const next = Array.from({ length: k }, () => new Array(matrix[0].length).fill(0));
    const counts = new Array(k).fill(0);
    for (let i = 0; i < n; i += 1) {
      const cluster = assignment[i];
      counts[cluster] += 1;
      for (let column = 0; column < matrix[i].length; column += 1) next[cluster][column] += matrix[i][column];
    }
    for (let cluster = 0; cluster < k; cluster += 1) {
      if (!counts[cluster]) {
        let replacement = 0;
        let farthest = -1;
        for (let i = 0; i < n; i += 1) {
          const distance = euclidean(matrix[i], centroids[assignment[i]]);
          if (distance > farthest) {
            farthest = distance;
            replacement = i;
          }
        }
        next[cluster] = [...matrix[replacement]];
        continue;
      }
      next[cluster] = next[cluster].map((value) => value / counts[cluster]);
    }
    centroids = next;
  }

  return { assignment, centroids };
}

function silhouette(matrix, assignment, k) {
  const groups = Array.from({ length: k }, () => []);
  assignment.forEach((cluster, index) => groups[cluster].push(index));
  const values = matrix.map((row, index) => {
    const own = assignment[index];
    const ownMembers = groups[own].filter((member) => member !== index);
    if (!ownMembers.length) return 0;
    const a = mean(ownMembers.map((member) => euclidean(row, matrix[member])));
    let b = Number.POSITIVE_INFINITY;
    for (let cluster = 0; cluster < k; cluster += 1) {
      if (cluster === own || !groups[cluster].length) continue;
      b = Math.min(b, mean(groups[cluster].map((member) => euclidean(row, matrix[member]))));
    }
    return (b - a) / Math.max(a, b, 1e-9);
  });
  return mean(values);
}

function chooseK(matrix) {
  const candidates = [];
  const maxK = Math.min(18, Math.max(4, Math.floor(Math.sqrt(matrix.length)) + 4));
  for (let k = 4; k <= maxK; k += 1) {
    const result = deterministicKMeans(matrix, k);
    candidates.push({ k, silhouette: silhouette(matrix, result.assignment, k), ...result });
  }
  candidates.sort((a, b) => b.silhouette - a.silhouette || a.k - b.k);
  return candidates[0];
}

function entropy(values) {
  const counts = new Map();
  for (const value of values) counts.set(value, (counts.get(value) ?? 0) + 1);
  let total = 0;
  for (const count of counts.values()) {
    const p = count / values.length;
    total -= p * Math.log(p);
  }
  return counts.size > 1 ? total / Math.log(counts.size) : 0;
}

function connectedGroups(ids, edges) {
  const adjacency = new Map(ids.map((id) => [id, new Set()]));
  for (const [a, b] of edges) {
    adjacency.get(a)?.add(b);
    adjacency.get(b)?.add(a);
  }
  const seen = new Set();
  const groups = [];
  for (const id of ids) {
    if (seen.has(id)) continue;
    const queue = [id];
    const group = [];
    seen.add(id);
    while (queue.length) {
      const current = queue.shift();
      group.push(current);
      for (const neighbor of adjacency.get(current) ?? []) {
        if (seen.has(neighbor)) continue;
        seen.add(neighbor);
        queue.push(neighbor);
      }
    }
    if (group.length >= 3) groups.push(group.sort());
  }
  return groups;
}

function parseCode(id, code) {
  const match = /^C(\d+)·H(\d+)·T(\d+)·J(\d+)·V([0-9.]+)·X([0-9.]+)·A([0-9.]+)·O(\d+)$/.exec(code);
  if (!match) return null;
  return {
    id,
    components: Number(match[1]),
    holes: Number(match[2]),
    endpoints: Number(match[3]),
    junctions: Number(match[4]),
    verticalSymmetry: Number(match[5]),
    horizontalSymmetry: Number(match[6]),
    aspect: Number(match[7]),
    orientation: Number(match[8]),
  };
}

function structuralMotif(record) {
  const endpointBand = record.endpoints <= 1 ? "E0-1" : record.endpoints <= 3 ? "E2-3" : record.endpoints <= 6 ? "E4-6" : "E7+";
  const junctionBand = record.junctions === 0 ? "J0" : record.junctions <= 2 ? "J1-2" : "J3+";
  const symmetryBand = Math.max(record.verticalSymmetry, record.horizontalSymmetry) >= 0.85 ? "SYM-H" : Math.max(record.verticalSymmetry, record.horizontalSymmetry) >= 0.65 ? "SYM-M" : "SYM-L";
  const aspectBand = record.aspect < 0.65 ? "TALL" : record.aspect > 1.55 ? "WIDE" : "BAL";
  return `C${record.components}:H${record.holes}:${endpointBand}:${junctionBand}:${symmetryBand}:${aspectBand}`;
}

function assertBlind(value, pathParts = []) {
  if (Array.isArray(value)) {
    value.forEach((item, index) => assertBlind(item, [...pathParts, String(index)]));
    return;
  }
  if (!value || typeof value !== "object") return;
  for (const [key, nested] of Object.entries(value)) {
    if (FORBIDDEN_KEYS.has(key)) throw new Error(`blind artifact contains forbidden key ${[...pathParts, key].join(".")}`);
    assertBlind(nested, [...pathParts, key]);
  }
}

await fs.mkdir(outDir, { recursive: true });
const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1440, height: 1200 } });
await page.goto(url, { waitUntil: "networkidle", timeout: 120_000 });
await page.waitForFunction(() => {
  const cards = [...document.querySelectorAll(".glyphCard")];
  return cards.length === 300 && cards.every((card) => !card.textContent?.includes("ANALYZING"));
}, { timeout: 120_000 });
await page.evaluate(() => document.fonts?.ready);

const captured = await page.$$eval(".glyphCard", (cards) => cards.map((card) => {
  const id = card.querySelector(".glyphIdentity strong")?.textContent?.trim() ?? "";
  const code = card.querySelector(".glyphIdentity span")?.textContent?.trim() ?? "";
  const mark = card.querySelector(".glyphMark");
  return {
    id,
    code,
    char: mark?.textContent ?? "",
    fontFamily: mark ? getComputedStyle(mark).fontFamily : "serif",
  };
}));

const hashes = await page.evaluate((records) => {
  const hashMask = (bytes, width, height) => {
    let hash = 2166136261 >>> 0;
    const mix = (value) => {
      hash ^= value & 0xff;
      hash = Math.imul(hash, 16777619) >>> 0;
    };
    mix(width); mix(width >>> 8); mix(height); mix(height >>> 8);
    for (const byte of bytes) mix(byte);
    return hash.toString(16).padStart(8, "0");
  };
  return records.map((record) => {
    const canvas = document.createElement("canvas");
    canvas.width = 112;
    canvas.height = 112;
    const context = canvas.getContext("2d", { willReadFrequently: true });
    if (!context) return { id: record.id, rasterHash: "none" };
    context.clearRect(0, 0, 112, 112);
    context.fillStyle = "#111";
    context.textAlign = "center";
    context.textBaseline = "middle";
    context.font = `76px ${record.fontFamily}`;
    context.fillText(record.char, 56, 58);
    const data = context.getImageData(0, 0, 112, 112).data;
    const mask = [];
    for (let i = 3; i < data.length; i += 4) mask.push(data[i] >= 96 ? 1 : 0);
    return { id: record.id, rasterHash: hashMask(mask, 112, 112) };
  });
}, captured);

await browser.close();

const hashById = new Map(hashes.map((item) => [item.id, item.rasterHash]));
const hashGroups = new Map();
for (const item of hashes) {
  if (!hashGroups.has(item.rasterHash)) hashGroups.set(item.rasterHash, []);
  hashGroups.get(item.rasterHash).push(item.id);
}
const suspiciousCollisionGroups = [...hashGroups.entries()]
  .filter(([hash, ids]) => hash === "none" || ids.length >= 4)
  .map(([rasterHash, ids]) => ({ rasterHash, ids: [...ids].sort(), count: ids.length }))
  .sort((a, b) => b.count - a.count || a.rasterHash.localeCompare(b.rasterHash));
const suspiciousIds = new Set(suspiciousCollisionGroups.flatMap((group) => group.ids));

const parsed = captured
  .map((item) => parseCode(item.id, item.code))
  .filter(Boolean)
  .map((item) => ({ ...item, rasterHash: hashById.get(item.id) ?? "missing" }));
const eligible = parsed.filter((item) => !suspiciousIds.has(item.id));
if (eligible.length < 120) throw new Error(`too few eligible glyphs after collision guard: ${eligible.length}`);

const scaled = {};
const distances = {};
const clusterings = {};
for (const representation of REPRESENTATIONS) {
  scaled[representation] = robustScale(eligible.map((record) => vectorFor(record, representation)));
  distances[representation] = pairwise(scaled[representation]);
  const selected = chooseK(scaled[representation]);
  clusterings[representation] = {
    k: selected.k,
    silhouette: Number(selected.silhouette.toFixed(6)),
    assignment: selected.assignment,
  };
}

const idToIndex = new Map(eligible.map((record, index) => [record.id, index]));
const topK = Math.min(10, eligible.length - 1);
const neighborRanks = {};
for (const representation of REPRESENTATIONS) {
  neighborRanks[representation] = eligible.map((_, i) => {
    const order = eligible.map((record, j) => ({ id: record.id, j, distance: distances[representation][i][j] }))
      .filter((item) => item.j !== i)
      .sort((a, b) => a.distance - b.distance || a.id.localeCompare(b.id));
    const ranks = new Map();
    order.forEach((item, rank) => ranks.set(item.id, rank + 1));
    return { order, ranks };
  });
}

const pairConsensus = new Map();
for (const representation of REPRESENTATIONS) {
  for (let i = 0; i < eligible.length; i += 1) {
    const id = eligible[i].id;
    const top = neighborRanks[representation][i].order.slice(0, topK);
    for (const neighbor of top) {
      const pair = [id, neighbor.id].sort();
      const key = pair.join("::");
      if (!pairConsensus.has(key)) pairConsensus.set(key, { ids: pair, representations: new Set(), mutual: 0, rankFractions: [] });
      const entry = pairConsensus.get(key);
      entry.representations.add(representation);
      const reverseRank = neighborRanks[representation][neighbor.j].ranks.get(id) ?? eligible.length;
      if (reverseRank <= topK) entry.mutual += 1;
      entry.rankFractions.push((neighborRanks[representation][i].ranks.get(neighbor.id) ?? eligible.length) / (eligible.length - 1));
    }
  }
}

const stablePairs = [...pairConsensus.values()]
  .map((entry) => ({
    ids: entry.ids,
    representationSupport: entry.representations.size,
    representations: [...entry.representations].sort(),
    mutualSupport: entry.mutual,
    meanRankFraction: Number(mean(entry.rankFractions).toFixed(6)),
  }))
  .filter((entry) => entry.representationSupport >= 3)
  .sort((a, b) => b.representationSupport - a.representationSupport || b.mutualSupport - a.mutualSupport || a.meanRankFraction - b.meanRankFraction)
  .slice(0, 80);

const combined = distances.combined;
const combinedAssignment = clusterings.combined.assignment;
const centrality = [];
const rarity = [];
const bridges = [];
for (let i = 0; i < eligible.length; i += 1) {
  const ordered = eligible.map((record, j) => ({ id: record.id, j, distance: combined[i][j] }))
    .filter((item) => item.j !== i)
    .sort((a, b) => a.distance - b.distance || a.id.localeCompare(b.id));
  const near10 = ordered.slice(0, Math.min(10, ordered.length));
  const near20 = ordered.slice(0, Math.min(20, ordered.length));
  const local = ordered.slice(0, Math.min(12, ordered.length));
  const mean10 = mean(near10.map((item) => item.distance));
  const mean20 = mean(near20.map((item) => item.distance));
  const localEntropy = entropy(local.map((item) => combinedAssignment[item.j]));
  centrality.push({ id: eligible[i].id, score: Number((1 / (1 + mean20)).toFixed(6)), mean20Distance: Number(mean20.toFixed(6)) });
  rarity.push({ id: eligible[i].id, score: Number(mean10.toFixed(6)) });
  bridges.push({ id: eligible[i].id, score: Number((localEntropy / (1 + mean10)).toFixed(6)), neighborClusterEntropy: Number(localEntropy.toFixed(6)), mean10Distance: Number(mean10.toFixed(6)) });
}
centrality.sort((a, b) => b.score - a.score || a.id.localeCompare(b.id));
rarity.sort((a, b) => b.score - a.score || a.id.localeCompare(b.id));
bridges.sort((a, b) => b.score - a.score || a.id.localeCompare(b.id));

const coClusterEdges = [];
for (let i = 0; i < eligible.length; i += 1) {
  for (let j = i + 1; j < eligible.length; j += 1) {
    let support = 0;
    for (const representation of REPRESENTATIONS) {
      if (clusterings[representation].assignment[i] === clusterings[representation].assignment[j]) support += 1;
    }
    if (support >= 3) coClusterEdges.push([eligible[i].id, eligible[j].id]);
  }
}
const stableGroups = connectedGroups(eligible.map((record) => record.id), coClusterEdges)
  .map((ids) => ({ ids, size: ids.length }))
  .sort((a, b) => b.size - a.size || a.ids[0].localeCompare(b.ids[0]))
  .slice(0, 40);

const motifMap = new Map();
for (const record of eligible) {
  const signature = structuralMotif(record);
  if (!motifMap.has(signature)) motifMap.set(signature, []);
  motifMap.get(signature).push(record.id);
}
const motifs = [...motifMap.entries()]
  .map(([signature, ids]) => ({ signature, ids: ids.sort(), count: ids.length }))
  .filter((item) => item.count >= 3)
  .sort((a, b) => b.count - a.count || a.signature.localeCompare(b.signature))
  .slice(0, 80);

const blindRecords = eligible.map((record) => ({
  id: record.id,
  components: record.components,
  holes: record.holes,
  endpoints: record.endpoints,
  junctions: record.junctions,
  verticalSymmetry: record.verticalSymmetry,
  horizontalSymmetry: record.horizontalSymmetry,
  aspect: record.aspect,
  orientation: record.orientation,
  rasterHash: record.rasterHash,
}));

const result = {
  schema: "mark_glyph_discovery_blind_v1",
  corpusKind: "standardized_display_proxy_hypothesis_generator",
  discoverySemantics: "blind_presemantic",
  generatedAt: new Date().toISOString(),
  runtime: {
    node: process.version,
    playwright: playwrightVersion,
    browser: "chromium",
    atlasUrl: url,
  },
  corpus: {
    captured: captured.length,
    parsed: parsed.length,
    eligible: eligible.length,
    excludedByRasterCollisionGuard: parsed.length - eligible.length,
    suspiciousCollisionGroups,
  },
  representations: Object.fromEntries(REPRESENTATIONS.map((representation) => [representation, {
    dimensions: scaled[representation][0]?.length ?? 0,
    selectedK: clusterings[representation].k,
    silhouette: clusterings[representation].silhouette,
  }])),
  records: blindRecords,
  candidates: {
    stablePairs,
    central: centrality.slice(0, 30),
    bridges: bridges.slice(0, 30),
    rare: rarity.slice(0, 30),
    stableGroups,
    recurrentStructuralMotifs: motifs,
  },
  limitations: [
    "These are standardized Unicode/font display proxies, not archaeological witness forms.",
    "No candidate may be promoted to historical evidence until it survives physical-witness replication.",
    "Raster measurements are implementation-sensitive; collision guards reduce but do not eliminate font/rendering artifacts.",
    "Discovery uses no historical system, language, sign-name, reading, meaning, geography, or chronology labels.",
  ],
};

assertBlind(result);
const canonical = JSON.stringify(result);
const digest = crypto.createHash("sha256").update(canonical).digest("hex");
const frozen = { ...result, blindSha256: digest };
await fs.writeFile(path.join(outDir, "glyph-discovery-blind-v1.json"), `${JSON.stringify(frozen, null, 2)}\n`, "utf8");
await fs.writeFile(path.join(outDir, "summary.txt"), [
  `schema=${frozen.schema}`,
  `captured=${frozen.corpus.captured}`,
  `eligible=${frozen.corpus.eligible}`,
  `collision_excluded=${frozen.corpus.excludedByRasterCollisionGuard}`,
  `combined_k=${frozen.representations.combined.selectedK}`,
  `combined_silhouette=${frozen.representations.combined.silhouette}`,
  `stable_pairs=${frozen.candidates.stablePairs.length}`,
  `stable_groups=${frozen.candidates.stableGroups.length}`,
  `motifs=${frozen.candidates.recurrentStructuralMotifs.length}`,
  `blind_sha256=${digest}`,
].join("\n") + "\n", "utf8");

console.log(`Glyph discovery complete: ${eligible.length}/${captured.length} eligible`);
console.log(`Blind SHA-256: ${digest}`);
