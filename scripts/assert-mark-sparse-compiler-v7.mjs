import fs from "node:fs/promises";
import { createReadStream } from "node:fs";
import crypto from "node:crypto";

const outDir = process.env.MARK_V7_OUT ?? "artifacts/mark-v7-sparse";
const maxRssKb = Number(process.env.MARK_V7_MAX_RSS_KB ?? 524288);
const summary = JSON.parse(await fs.readFile(`${outDir}/summary.json`, "utf8"));
const custody = JSON.parse(await fs.readFile(`${outDir}/custody.json`, "utf8"));
const evaluation = JSON.parse(await fs.readFile(`${outDir}/evaluation.json`, "utf8"));
const runtime = await fs.readFile(`${outDir}/runtime.txt`, "utf8");

if (summary.schema !== "mark_sparse_compiler_summary_v2") throw new Error(`unexpected summary schema ${summary.schema}`);
if (custody.schema !== "mark_sparse_ledger_custody_v2") throw new Error(`unexpected custody schema ${custody.schema}`);
if (evaluation.schema !== "mark_sparse_transfer_evaluation_v1") throw new Error(`unexpected evaluation schema ${evaluation.schema}`);
if (!/^[a-f0-9]{64}$/.test(custody.physicalLedger?.merkleRoot ?? "")) throw new Error("invalid physical ledger Merkle root");
if (!/^[a-f0-9]{64}$/.test(custody.grammarStatistics?.contributionMerkleRoot ?? "")) throw new Error("invalid grammar contribution Merkle root");
if (summary.physicalLedgerMerkleRoot !== custody.physicalLedger.merkleRoot) throw new Error("summary/custody physical Merkle root mismatch");
if (summary.grammarContributionMerkleRoot !== custody.grammarStatistics.contributionMerkleRoot) throw new Error("summary/custody grammar contribution root mismatch");
if (summary.sources < 3 || summary.observations < 10 || summary.tiles < 1 || summary.events < 1) throw new Error("v7 compiler did not process a meaningful blind corpus");
if (summary.centers < 1) throw new Error("v7 compiler emitted no relational centers");
if (BigInt(summary.observedPairWeight) < 1n) throw new Error("v7 compiler emitted no maskable relational pair weight");
if (summary.grammarRowsMaterialized !== 0) throw new Error(`grammar rows were materialized: ${summary.grammarRowsMaterialized}`);
if (summary.grammarStatRows < 1 || summary.contextStatRows < 1) throw new Error("sufficient-statistics database is empty");
if (summary.grammarContributions !== summary.observations * (summary.nullIterations + 1)) throw new Error("missing per-observation grammar contribution hashes");
if (!custody.contract?.appendOnlyPhysicalEventLedger || custody.contract?.wholeWorldGraphMaterialized || custody.contract?.wholeWorldJsonMaterialized || custody.contract?.grammarPairsMaterialized || custody.contract?.grammarRowsMaterialized) throw new Error("v7 sparse custody contract was violated");
if (!custody.contract?.grammarSufficientStatisticsDiskBacked || !custody.contract?.distinctSourceSupportCommittedAtSourceBoundary || !custody.contract?.perObservationContributionHashes) throw new Error("v7 sufficient-statistics contract is incomplete");
if (evaluation.rules < 1) throw new Error("v7 training lane discovered no recurrent masked-relation rule");

const rssMatch = runtime.match(/Maximum resident set size \(kbytes\):\s*(\d+)/);
if (!rssMatch) throw new Error("could not read maximum RSS from compiler runtime report");
const maxRssObserved = Number(rssMatch[1]);
if (maxRssObserved > maxRssKb) throw new Error(`v7 compiler exceeded memory gate: ${maxRssObserved} KB > ${maxRssKb} KB`);

async function hashFile(file) {
  const hasher = crypto.createHash("sha256");
  for await (const chunk of createReadStream(file)) hasher.update(chunk);
  return hasher.digest("hex");
}

function merkleRoot(hashes) {
  if (!hashes.length) return crypto.createHash("sha256").update(Buffer.alloc(0)).digest("hex");
  let layer = hashes.map(hash => Buffer.from(hash, "hex"));
  while (layer.length > 1) {
    const next = [];
    for (let i = 0; i < layer.length; i += 2) {
      const left = layer[i];
      const right = layer[i + 1] ?? left;
      next.push(crypto.createHash("sha256").update(left).update(right).digest());
    }
    layer = next;
  }
  return layer[0].toString("hex");
}

async function ledgerMerkle(file, chunkLines) {
  const text = await fs.readFile(file, "utf8");
  if (text && !text.endsWith("\n")) throw new Error(`${file} is not newline terminated`);
  const lines = text ? text.slice(0, -1).split("\n") : [];
  const hashes = [];
  for (let i = 0; i < lines.length; i += chunkLines) {
    const hasher = crypto.createHash("sha256");
    for (const line of lines.slice(i, i + chunkLines)) hasher.update(`${line}\n`);
    hashes.push(hasher.digest("hex"));
  }
  return merkleRoot(hashes);
}

const ledgerSha256 = await hashFile(`${outDir}/events.jsonl`);
const databaseSha256 = await hashFile(`${outDir}/grammar-stats.sqlite`);
if (databaseSha256 !== custody.grammarStatistics.databaseSha256) throw new Error("grammar statistics database hash mismatch");
const contributionRoot = await ledgerMerkle(`${outDir}/grammar-contributions.jsonl`, custody.grammarStatistics.contributionChunkLines);
if (contributionRoot !== custody.grammarStatistics.contributionMerkleRoot) throw new Error("grammar contribution ledger Merkle root mismatch");

await fs.writeFile(`${outDir}/assertion.json`, `${JSON.stringify({
  schema:"mark_sparse_architecture_assertion_v2",
  status:"passed",
  sourceBlindInputSha256:summary.sourceBlindInputSha256,
  sources:summary.sources,
  observations:summary.observations,
  centers:summary.centers,
  events:summary.events,
  rules:evaluation.rules,
  grammarRowsMaterialized:summary.grammarRowsMaterialized,
  grammarStatRows:summary.grammarStatRows,
  grammarContributions:summary.grammarContributions,
  maxRssKb:maxRssObserved,
  memoryGateKb:maxRssKb,
  physicalLedgerMerkleRoot:custody.physicalLedger.merkleRoot,
  physicalLedgerFileSha256:ledgerSha256,
  grammarStatisticsDatabaseSha256:databaseSha256,
  grammarContributionMerkleRoot:contributionRoot,
  scientificInterpretationAuthorized:false
}, null, 2)}\n`);
console.log(`Mark v7 rowless architecture gate passed: ${summary.sources} sources, ${summary.observations} observations, ${summary.events} physical events, ${summary.grammarStatRows} grammar statistics, ${evaluation.rules} rules, max RSS ${maxRssObserved} KB`);
