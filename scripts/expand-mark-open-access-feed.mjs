import crypto from "node:crypto";
import fs from "node:fs/promises";
import path from "node:path";

const requestPath = process.env.MARK_OPEN_ACCESS_FEED_REQUEST ?? "research/mark/harvest-feeds/open-access-fixture.v1.json";
const outDir = process.env.MARK_OPEN_ACCESS_FEED_OUT ?? "artifacts/mark-open-access-feed-v1";
const request = JSON.parse(await fs.readFile(requestPath, "utf8"));
if (request.schema !== "mark_open_access_feed_request_v1") throw new Error(`unsupported open-access feed request ${request.schema}`);
if (!new Set(["train", "holdout", "control"]).has(request.lane)) throw new Error(`invalid challenge lane ${request.lane}`);
const maxSources = Math.max(2, Number(request.maxSources ?? 50));
const seed = String(request.seed ?? request.feedId);
const userAgent = "MarkResearchHarvester/2.0";

function hashInt(value) {
  return Number.parseInt(crypto.createHash("sha256").update(String(value)).digest("hex").slice(0, 12), 16);
}
function deterministicSpread(total, count, salt) {
  if (!total || !count) return [];
  const start = hashInt(`${seed}|${salt}|start`) % total;
  let step = (hashInt(`${seed}|${salt}|step`) % Math.max(1, total - 1)) + 1;
  const gcd = (a, b) => { while (b) [a, b] = [b, a % b]; return a; };
  while (total > 1 && gcd(step, total) !== 1) step = (step % total) + 1;
  const out = [];
  for (let i = 0; i < Math.min(count, total); i += 1) out.push((start + i * step) % total);
  return out;
}
function normalizeHttpsUrl(value) {
  if (typeof value !== "string") return null;
  if (/^https:\/\//i.test(value)) return value;
  if (/^http:\/\//i.test(value)) return `https://${value.slice(7)}`;
  if (/^\/\//.test(value)) return `https:${value}`;
  return null;
}
const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
async function fetchJson(url, { attempts = 3 } = {}) {
  let lastError;
  for (let attempt = 1; attempt <= attempts; attempt += 1) {
    try {
      const response = await fetch(url, { redirect: "follow", headers: { accept: "application/json", "user-agent": userAgent } });
      if (response.ok) return response.json();
      const retryable = response.status === 429 || response.status >= 500;
      if (!retryable || attempt === attempts) throw new Error(`feed fetch failed ${response.status}: ${url}`);
      await sleep(attempt * 1200);
    } catch (error) {
      lastError = error;
      if (attempt === attempts) throw error;
      await sleep(attempt * 1200);
    }
  }
  throw lastError ?? new Error(`feed fetch failed: ${url}`);
}
function sourceFrom(item, index) {
  return {
    sourceId: `SRC${String(index + 1).padStart(4, "0")}`,
    challengeLane: request.lane,
    capture: { adapter: "image_2d", assetUrl: item.assetUrl },
    sourceUrl: item.sourceUrl,
    institution: request.institution,
    objectId: String(item.objectId),
    rightsBasis: item.rightsBasis ?? request.rightsBasis,
    context: { feedKind: "open_access_collection", feedId: request.feedId, provider: request.provider, ...(item.context ?? {}) },
  };
}

async function fixtureItems() {
  const absolute = path.resolve(path.dirname(requestPath), request.fixturePath);
  const fixture = JSON.parse(await fs.readFile(absolute, "utf8"));
  if (!Array.isArray(fixture.items)) throw new Error("open-access fixture requires items[]");
  return fixture.items.slice(0, maxSources);
}

async function articItems() {
  const fields = "id,title,image_id,is_public_domain,classification_titles,department_title,date_display,place_of_origin,medium_display,main_reference_number";
  const base = "https://api.artic.edu/api/v1/artworks";
  const pageSize = 100;
  const first = await fetchJson(`${base}?page=1&limit=${pageSize}&fields=${encodeURIComponent(fields)}`);
  const totalPages = Math.max(1, Number(first.pagination?.total_pages ?? Math.ceil(Number(first.pagination?.total ?? 0) / pageSize) ?? 1));
  const pages = deterministicSpread(totalPages, Math.min(totalPages, Math.ceil(maxSources / 20) + 8), "artic-pages").map(x => x + 1);
  const items = [];
  for (const page of pages) {
    const payload = page === 1 ? first : await fetchJson(`${base}?page=${page}&limit=${pageSize}&fields=${encodeURIComponent(fields)}`);
    const iiif = payload.config?.iiif_url ?? "https://www.artic.edu/iiif/2";
    for (const row of payload.data ?? []) {
      if (!row?.image_id || row.is_public_domain !== true) continue;
      items.push({
        assetUrl: `${String(iiif).replace(/\/$/, "")}/${row.image_id}/full/843,/0/default.jpg`,
        sourceUrl: `https://api.artic.edu/api/v1/artworks/${row.id}`,
        objectId: row.id,
        context: { title: row.title, classification: row.classification_titles, department: row.department_title, date: row.date_display, origin: row.place_of_origin, medium: row.medium_display, accession: row.main_reference_number },
      });
      if (items.length >= maxSources) return items;
    }
  }
  return items;
}

async function clevelandItems() {
  const base = "https://openaccess-api.clevelandart.org/api/artworks/";
  const first = await fetchJson(`${base}?cc0&has_image=1&skip=0&limit=1`);
  const total = Number(first.info?.total ?? 0);
  const pageSize = 100;
  const pageCount = Math.max(1, Math.ceil(total / pageSize));
  const pages = deterministicSpread(pageCount, Math.min(pageCount, Math.ceil(maxSources / 25) + 8), "cleveland-pages");
  const items = [];
  for (const page of pages) {
    const payload = await fetchJson(`${base}?cc0&has_image=1&skip=${page * pageSize}&limit=${pageSize}`);
    for (const row of payload.data ?? []) {
      const assetUrl = row?.images?.web?.url ?? row?.images?.print?.url ?? row?.images?.full?.url;
      if (!assetUrl || row.share_license_status !== "CC0") continue;
      items.push({
        assetUrl,
        sourceUrl: row.url ?? `${base}${row.id}`,
        objectId: row.id,
        context: { title: row.title, type: row.type, department: row.department, culture: row.culture, creationDate: row.creation_date, technique: row.technique, accession: row.accession_number },
      });
      if (items.length >= maxSources) return items;
    }
  }
  return items;
}

async function metItems() {
  const base = "https://collectionapi.metmuseum.org/public/collection/v1";
  const listing = await fetchJson(`${base}/objects`);
  const ids = Array.isArray(listing.objectIDs) ? listing.objectIDs : [];
  const candidateIndexes = deterministicSpread(ids.length, Math.min(ids.length, Math.max(maxSources * 12, 200)), "met-objects");
  const items = [];
  for (const index of candidateIndexes) {
    const id = ids[index];
    const row = await fetchJson(`${base}/objects/${id}`).catch(() => null);
    // The Met API is currently protected by a burst-sensitive WAF despite its documented higher limit.
    // Keep deterministic enumeration deliberately below the observed burst threshold instead of retry-hammering.
    await sleep(1250);
    if (!row || row.isPublicDomain !== true) continue;
    const assetUrl = row.primaryImageSmall || row.primaryImage;
    if (!assetUrl) continue;
    items.push({
      assetUrl,
      sourceUrl: row.objectURL ?? `${base}/objects/${row.objectID}`,
      objectId: row.objectID,
      context: { title: row.title, objectName: row.objectName, department: row.department, classification: row.classification, culture: row.culture, period: row.period, date: row.objectDate, medium: row.medium, country: row.country },
    });
    if (items.length >= maxSources) return items;
  }
  return items;
}

function locRows(payload, pageOrdinal) {
  const rows = Array.isArray(payload.results) ? payload.results : [];
  const order = deterministicSpread(rows.length, rows.length, `loc-photo-page-${pageOrdinal}-items`);
  return order.map(index => rows[index]);
}
async function locItems() {
  const pageSize = 100;
  let nextUrl = `https://www.loc.gov/photos/?fo=json&at=results,pagination&c=${pageSize}&sp=1`;
  const items = [];
  const seenIds = new Set();
  const maxPages = 4;
  for (let pageOrdinal = 1; pageOrdinal <= maxPages && nextUrl && items.length < maxSources; pageOrdinal += 1) {
    const payload = await fetchJson(nextUrl);
    for (const row of locRows(payload, pageOrdinal)) {
      const rawUrls = Array.isArray(row?.image_url) ? row.image_url : typeof row?.image_url === "string" ? [row.image_url] : [];
      const urls = rawUrls.map(normalizeHttpsUrl).filter(Boolean);
      const assetUrl = [...urls].reverse().find(url => /\.(jpe?g|png)(\?|#|$)/i.test(url)) ?? urls[0];
      const sourceUrl = normalizeHttpsUrl(row?.id);
      if (!assetUrl || !sourceUrl || seenIds.has(sourceUrl)) continue;
      seenIds.add(sourceUrl);
      items.push({
        assetUrl,
        sourceUrl,
        objectId: row.id,
        rightsBasis: request.rightsBasis ?? "source_rights_govern_research_analysis_only",
        context: { title: row.title, date: row.date, originalFormat: row.original_format, subject: row.subject, location: row.location, collection: row.partof, enumeration: "official_pagination_next_with_deterministic_within_page_spread", pageOrdinal },
      });
      if (items.length >= maxSources) return items;
    }
    nextUrl = typeof payload.pagination?.next === "string" ? payload.pagination.next : null;
    if (nextUrl) await sleep(3200);
  }
  return items;
}

let items;
if (request.fixturePath) items = await fixtureItems();
else if (request.provider === "artic") items = await articItems();
else if (request.provider === "cleveland") items = await clevelandItems();
else if (request.provider === "met") items = await metItems();
else if (request.provider === "loc_photos") items = await locItems();
else throw new Error(`unsupported open-access provider ${request.provider}`);

items = items.filter(item => /^https:\/\//i.test(item.assetUrl ?? "") && /^https:\/\//i.test(item.sourceUrl ?? ""));
if (items.length < 2) throw new Error(`feed ${request.feedId} produced only ${items.length} usable sources`);
const sources = items.slice(0, maxSources).map(sourceFrom);
const manifest = {
  schema: "mark_harvest_manifest_v1",
  harvestId: `mark:open-access:${request.feedId}`,
  status: "physical_evidence",
  purpose: `Machine-enumerated open-access collection slice ${request.feedId}; no individual object was hand-selected.`,
  sources,
};
await fs.mkdir(outDir, { recursive: true });
await fs.writeFile(path.join(outDir, "generated-harvest-manifest.v1.json"), `${JSON.stringify(manifest, null, 2)}\n`);
await fs.writeFile(path.join(outDir, "summary.txt"), [
  `schema=${manifest.schema}`,
  `feed_id=${request.feedId}`,
  `provider=${request.provider}`,
  `lane=${request.lane}`,
  `sources=${sources.length}`,
  `max_sources=${maxSources}`,
].join("\n") + "\n");
console.log(`Expanded ${request.feedId} (${request.provider}) into ${sources.length} machine-enumerated ${request.lane} sources`);
