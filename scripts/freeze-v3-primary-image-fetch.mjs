import fs from "node:fs/promises";

const manifestPath = process.env.MARK_CANDIDATE_MANIFEST ?? "research/mark/discovery-experiments/white-paint-candidate-mark-projector-v4.images.json";
const manifest = JSON.parse(await fs.readFile(manifestPath, "utf8"));
const imageByObjectId = new Map(manifest.acceptedObjects.map((row) => [String(row.providerObjectId), row.imageURL]));
const originalFetch = globalThis.fetch;

if (typeof originalFetch !== "function") throw new Error("global fetch unavailable");

globalThis.fetch = async (input, init) => {
  const url = typeof input === "string" ? input : input?.url;
  const match = typeof url === "string" ? /collectionapi\.metmuseum\.org\/public\/collection\/v1\/objects\/(\d+)$/.exec(url) : null;
  if (match && imageByObjectId.has(match[1])) {
    return new Response(JSON.stringify({ primaryImage: imageByObjectId.get(match[1]), primaryImageSmall: "" }), {
      status: 200,
      headers: { "content-type": "application/json" },
    });
  }
  return originalFetch(input, init);
};
