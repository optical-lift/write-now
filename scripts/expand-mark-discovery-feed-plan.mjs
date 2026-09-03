import fs from "node:fs/promises";
import path from "node:path";
import { spawnSync } from "node:child_process";

const planPath = process.env.MARK_DISCOVERY_FEED_PLAN ?? "research/mark/discovery-experiments/blind-discovery-v1.feeds.json";
const outDir = process.env.MARK_DISCOVERY_FEED_OUT ?? "artifacts/mark-blind-discovery-feed-plan-v1";
const planBytes = await fs.readFile(planPath);
const plan = JSON.parse(planBytes);
if (plan.schema !== "mark_blind_discovery_feed_plan_v1") throw new Error(`unsupported feed plan ${plan.schema}`);
if (!Array.isArray(plan.feedRequests) || plan.feedRequests.length < 3) throw new Error("blind discovery requires at least three feed requests");

await fs.mkdir(outDir, { recursive: true });
const expanded = [];
for (let index = 0; index < plan.feedRequests.length; index += 1) {
  const requestPath = String(plan.feedRequests[index]);
  const request = JSON.parse(await fs.readFile(requestPath, "utf8"));
  const feedOut = path.join(outDir, `feed-${String(index + 1).padStart(3, "0")}`);
  await fs.mkdir(feedOut, { recursive: true });

  let script;
  let requestEnv;
  let outEnv;
  if (request.schema === "mark_open_access_feed_request_v1") {
    script = "scripts/expand-mark-open-access-feed.mjs";
    requestEnv = "MARK_OPEN_ACCESS_FEED_REQUEST";
    outEnv = "MARK_OPEN_ACCESS_FEED_OUT";
  } else if (request.schema === "mark_iiif_feed_request_v1") {
    script = "scripts/expand-mark-iiif-feed.mjs";
    requestEnv = "MARK_IIIF_FEED_REQUEST";
    outEnv = "MARK_IIIF_FEED_OUT";
  } else {
    throw new Error(`${requestPath}: unsupported feed request schema ${request.schema}`);
  }

  const run = spawnSync(process.execPath, [script], {
    stdio: "inherit",
    env: { ...process.env, [requestEnv]: requestPath, [outEnv]: feedOut },
  });
  if (run.status !== 0) throw new Error(`feed expansion failed for ${requestPath}`);

  const manifestPath = path.join(feedOut, "generated-harvest-manifest.v1.json");
  const manifest = JSON.parse(await fs.readFile(manifestPath, "utf8"));
  if (manifest.schema !== "mark_harvest_manifest_v1" || manifest.status !== "physical_evidence") {
    throw new Error(`${requestPath}: expansion did not produce a physical harvest manifest`);
  }
  const lanes = [...new Set(manifest.sources.map(source => source.challengeLane).filter(Boolean))];
  if (lanes.length !== 1 || lanes[0] !== request.lane) throw new Error(`${requestPath}: expanded lane does not match request lane`);

  expanded.push({
    requestPath,
    requestSchema: request.schema,
    feedId: request.feedId ?? null,
    lane: request.lane,
    institution: request.institution ?? null,
    manifestPath,
    sourceObjects: manifest.sources.length,
  });
}

const laneCounts = Object.fromEntries(["train", "holdout", "control"].map(lane => [lane, expanded.filter(row => row.lane === lane).reduce((sum, row) => sum + row.sourceObjects, 0)]));
for (const lane of ["train", "holdout", "control"]) if (!laneCounts[lane]) throw new Error(`feed plan produced no ${lane} sources`);
const result = {
  schema: "mark_blind_discovery_expanded_feed_plan_v1",
  experimentId: plan.experimentId,
  sourcePlanPath: planPath,
  laneCounts,
  feeds: expanded,
};
await fs.writeFile(path.join(outDir, "expanded-feed-plan.json"), `${JSON.stringify(result, null, 2)}\n`);
await fs.writeFile(path.join(outDir, "manifests.txt"), `${expanded.map(row => row.manifestPath).join("\n")}\n`);
console.log(`Expanded blind-discovery feed plan: feeds=${expanded.length} train=${laneCounts.train} holdout=${laneCounts.holdout} control=${laneCounts.control}`);
