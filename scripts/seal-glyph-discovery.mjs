import crypto from "node:crypto";
import fs from "node:fs/promises";
import path from "node:path";

const rawPath = process.env.GLYPH_DISCOVERY_RAW ?? "artifacts/glyph-discovery-v1/glyph-discovery-blind-v1.json";
const blindOutDir = process.env.GLYPH_DISCOVERY_SEALED_OUT ?? "artifacts/glyph-discovery-v1-sealed";
const rejoinOutDir = process.env.GLYPH_DISCOVERY_REJOIN_OUT ?? "artifacts/glyph-discovery-rejoin-v1";

const raw = JSON.parse(await fs.readFile(rawPath, "utf8"));
const atlasIds = raw.records.map((record) => record.id).sort();
const salt = crypto.randomBytes(32).toString("hex");
const idMap = new Map(atlasIds.map((atlasId) => [
  atlasId,
  `B${crypto.createHash("sha256").update(`${salt}|${atlasId}`).digest("hex").slice(0, 12).toUpperCase()}`,
]));

function blindId(atlasId) {
  const mapped = idMap.get(atlasId);
  if (!mapped) throw new Error(`missing blind mapping for ${atlasId}`);
  return mapped;
}

function maximalCliques(nodes, edges) {
  const adjacency = new Map(nodes.map((node) => [node, new Set()]));
  for (const [a, b] of edges) {
    adjacency.get(a)?.add(b);
    adjacency.get(b)?.add(a);
  }
  const cliques = [];
  const intersect = (set, allowed) => new Set([...set].filter((value) => allowed.has(value)));
  const bronKerbosch = (r, p, x) => {
    if (!p.size && !x.size) {
      if (r.size >= 3) cliques.push([...r].sort());
      return;
    }
    const union = new Set([...p, ...x]);
    let pivot = null;
    let pivotDegree = -1;
    for (const candidate of union) {
      const degree = [...(adjacency.get(candidate) ?? [])].filter((neighbor) => p.has(neighbor)).length;
      if (degree > pivotDegree) {
        pivot = candidate;
        pivotDegree = degree;
      }
    }
    const excluded = pivot ? adjacency.get(pivot) ?? new Set() : new Set();
    const candidates = [...p].filter((value) => !excluded.has(value)).sort();
    for (const value of candidates) {
      const neighbors = adjacency.get(value) ?? new Set();
      bronKerbosch(new Set([...r, value]), intersect(p, neighbors), intersect(x, neighbors));
      p.delete(value);
      x.add(value);
    }
  };
  bronKerbosch(new Set(), new Set(nodes), new Set());
  const unique = new Map(cliques.map((ids) => [ids.join("::"), ids]));
  return [...unique.values()].sort((a, b) => b.length - a.length || a[0].localeCompare(b[0]));
}

const strictEdges = raw.candidates.stablePairs
  .filter((pair) => pair.representationSupport === 4 && pair.mutualSupport >= 8 && pair.meanRankFraction <= 0.05)
  .map((pair) => pair.ids);
const strictNodes = [...new Set(strictEdges.flat())].sort();
const consensusCliques = maximalCliques(strictNodes, strictEdges)
  .map((ids) => ({ ids: ids.map(blindId).sort(), size: ids.length }))
  .slice(0, 40);

const sealedCore = {
  schema: "mark_glyph_discovery_blind_v1_1",
  corpusKind: raw.corpusKind,
  discoverySemantics: raw.discoverySemantics,
  generatedAt: raw.generatedAt,
  sealedAt: new Date().toISOString(),
  sealedFromBlindSha256: raw.blindSha256,
  runtime: raw.runtime,
  corpus: {
    captured: raw.corpus.captured,
    parsed: raw.corpus.parsed,
    eligible: raw.corpus.eligible,
    excludedByRasterCollisionGuard: raw.corpus.excludedByRasterCollisionGuard,
    suspiciousCollisionGroups: raw.corpus.suspiciousCollisionGroups.map((group) => ({
      rasterHash: group.rasterHash,
      count: group.count,
      ids: group.ids.map(blindId).sort(),
    })),
  },
  representations: raw.representations,
  records: raw.records.map((record) => ({ ...record, id: blindId(record.id) })).sort((a, b) => a.id.localeCompare(b.id)),
  candidates: {
    stablePairs: raw.candidates.stablePairs.map((pair) => ({ ...pair, ids: pair.ids.map(blindId).sort() })),
    central: raw.candidates.central.map((item) => ({ ...item, id: blindId(item.id) })),
    bridges: raw.candidates.bridges.map((item) => ({ ...item, id: blindId(item.id) })),
    rare: raw.candidates.rare.map((item) => ({ ...item, id: blindId(item.id) })),
    consensusCliques,
    recurrentStructuralMotifs: raw.candidates.recurrentStructuralMotifs.map((motif) => ({
      ...motif,
      ids: motif.ids.map(blindId).sort(),
    })),
  },
  limitations: [
    ...raw.limitations,
    "Atlas-order identities are removed from this sealed artifact. The B-identities are random-run opaque handles whose map is stored separately for post-freeze context rejoin.",
    "The v1 transitive co-cluster group output is intentionally discarded. v1.1 reports only strict maximal cliques formed from four-representation, bidirectional top-neighbor agreement.",
  ],
};

const serialized = JSON.stringify(sealedCore);
if (/\bG\d{5}\b/.test(serialized)) throw new Error("sealed blind artifact still contains Atlas G-identities");
for (const forbidden of ["systemLabel", "unicodeLabel", "displayBasis", "sourceUrl", "fontFamily", "char\""]) {
  if (serialized.includes(`\"${forbidden}\"`)) throw new Error(`sealed blind artifact contains forbidden field ${forbidden}`);
}
const digest = crypto.createHash("sha256").update(serialized).digest("hex");
const sealed = { ...sealedCore, blindSha256: digest };

await fs.mkdir(blindOutDir, { recursive: true });
await fs.mkdir(rejoinOutDir, { recursive: true });
await fs.writeFile(path.join(blindOutDir, "glyph-discovery-blind-v1-1.json"), `${JSON.stringify(sealed, null, 2)}\n`, "utf8");
await fs.writeFile(path.join(blindOutDir, "summary.txt"), [
  `schema=${sealed.schema}`,
  `captured=${sealed.corpus.captured}`,
  `eligible=${sealed.corpus.eligible}`,
  `collision_excluded=${sealed.corpus.excludedByRasterCollisionGuard}`,
  `combined_k=${sealed.representations.combined.selectedK}`,
  `combined_silhouette=${sealed.representations.combined.silhouette}`,
  `stable_pairs=${sealed.candidates.stablePairs.length}`,
  `consensus_cliques=${sealed.candidates.consensusCliques.length}`,
  `motifs=${sealed.candidates.recurrentStructuralMotifs.length}`,
  `blind_sha256=${digest}`,
].join("\n") + "\n", "utf8");

const rejoin = {
  schema: "mark_glyph_discovery_rejoin_map_v1",
  sealedBlindSha256: digest,
  mappings: [...idMap.entries()]
    .map(([atlasId, blindIdValue]) => ({ blindId: blindIdValue, atlasId }))
    .sort((a, b) => a.blindId.localeCompare(b.blindId)),
};
await fs.writeFile(path.join(rejoinOutDir, "glyph-id-map-v1.json"), `${JSON.stringify(rejoin, null, 2)}\n`, "utf8");

console.log(`Sealed blind discovery SHA-256: ${digest}`);
console.log(`Strict consensus cliques: ${consensusCliques.length}`);
