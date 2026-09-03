use anyhow::{anyhow, bail, Context, Result};
use image::GrayImage;
use rusqlite::{params, Connection};
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use sha2::{Digest, Sha256};
use std::collections::{BTreeMap, HashMap};
use std::fs::{self, File};
use std::io::{BufWriter, Read, Write};
use std::path::{Path, PathBuf};

const LEDGER_CHUNK_LINES: u64 = 4096;

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
struct BlindInput {
    schema: String,
    #[serde(default)]
    blind_input_sha256: String,
    sources: Vec<BlindSource>,
    observations: Vec<Observation>,
}

#[derive(Debug, Clone, Deserialize)]
#[serde(rename_all = "camelCase")]
struct BlindSource {
    source_group_id: String,
    capture_path: String,
    #[serde(default)]
    lane: String,
}

#[derive(Debug, Clone, Deserialize)]
#[serde(rename_all = "camelCase")]
struct Observation {
    id: String,
    source_group_id: String,
    lane: String,
    region: Region,
    segmentation: Segmentation,
    #[serde(default)]
    proposal_kind: String,
    #[serde(default)]
    proposal_scale: String,
}

#[derive(Debug, Clone, Copy, Deserialize)]
struct Region {
    x: u32,
    y: u32,
    width: u32,
    height: u32,
}

#[derive(Debug, Clone, Deserialize)]
struct Segmentation {
    #[serde(default = "default_polarity")]
    polarity: String,
    #[serde(default = "default_threshold")]
    threshold: Value,
}

fn default_polarity() -> String {
    "dark_on_light".into()
}

fn default_threshold() -> Value {
    Value::String("otsu".into())
}

#[derive(Debug, Clone)]
struct CenterEvidence {
    kind: &'static str,
    arms: Vec<String>,
}

#[derive(Default, Debug, Clone)]
struct Score {
    examples: u128,
    covered: u128,
    correct: u128,
}

#[derive(Default)]
struct CompilerStats {
    sources: u64,
    observations: u64,
    tiles: u64,
    centers: u64,
    events: u64,
    grammar_stat_commits: u64,
    grammar_contributions: u64,
    unresolved_arms: u64,
    observed_pair_weight: u128,
}

type LocalGrammar = BTreeMap<(String, String), u128>;
type SourceGrammar = BTreeMap<(i32, String, String, String), u128>;

struct ChunkedLedger {
    writer: BufWriter<File>,
    chunk_hasher: Sha256,
    chunk_lines: u64,
    total_lines: u64,
    chunk_hashes: Vec<String>,
}

impl ChunkedLedger {
    fn create(path: &Path) -> Result<Self> {
        Ok(Self {
            writer: BufWriter::new(File::create(path)?),
            chunk_hasher: Sha256::new(),
            chunk_lines: 0,
            total_lines: 0,
            chunk_hashes: Vec::new(),
        })
    }

    fn write_json(&mut self, value: &Value) -> Result<()> {
        let mut bytes = serde_json::to_vec(value)?;
        bytes.push(b'\n');
        self.writer.write_all(&bytes)?;
        self.chunk_hasher.update(&bytes);
        self.chunk_lines += 1;
        self.total_lines += 1;
        if self.chunk_lines >= LEDGER_CHUNK_LINES {
            self.finish_chunk();
        }
        Ok(())
    }

    fn finish_chunk(&mut self) {
        if self.chunk_lines == 0 {
            return;
        }
        let digest = std::mem::replace(&mut self.chunk_hasher, Sha256::new()).finalize();
        self.chunk_hashes.push(hex::encode(digest));
        self.chunk_lines = 0;
    }

    fn finish(mut self) -> Result<(u64, Vec<String>, String)> {
        self.finish_chunk();
        self.writer.flush()?;
        let root = merkle_root(&self.chunk_hashes)?;
        Ok((self.total_lines, self.chunk_hashes, root))
    }
}

struct StatsStore {
    connection: Connection,
}

impl StatsStore {
    fn create(path: &Path) -> Result<Self> {
        if path.exists() {
            fs::remove_file(path)?;
        }
        let connection = Connection::open(path)?;
        connection.execute_batch(
            "PRAGMA journal_mode=DELETE;
             PRAGMA synchronous=FULL;
             PRAGMA temp_store=FILE;
             PRAGMA cache_size=-8192;
             PRAGMA foreign_keys=ON;
             CREATE TABLE grammar_stats (
               iteration INTEGER NOT NULL,
               lane TEXT NOT NULL,
               context TEXT NOT NULL,
               outcome TEXT NOT NULL,
               count INTEGER NOT NULL CHECK(count >= 0),
               source_count INTEGER NOT NULL CHECK(source_count >= 0),
               PRIMARY KEY(iteration,lane,context,outcome)
             ) WITHOUT ROWID;
             CREATE TABLE context_stats (
               iteration INTEGER NOT NULL,
               lane TEXT NOT NULL,
               context TEXT NOT NULL,
               source_count INTEGER NOT NULL CHECK(source_count >= 0),
               PRIMARY KEY(iteration,lane,context)
             ) WITHOUT ROWID;
             CREATE TABLE rules (
               context TEXT PRIMARY KEY,
               outcome TEXT NOT NULL,
               distinct_sources INTEGER NOT NULL,
               total_count INTEGER NOT NULL,
               context_sources INTEGER NOT NULL
             ) WITHOUT ROWID;",
        )?;
        Ok(Self { connection })
    }
}

fn clean_tsv(s: &str) -> String {
    s.replace('\t', " ").replace('\n', " ").replace('\r', " ")
}

fn sha256_hex(bytes: &[u8]) -> String {
    hex::encode(Sha256::digest(bytes))
}

fn sha256_file(path: &Path) -> Result<String> {
    let mut file = File::open(path)?;
    let mut hasher = Sha256::new();
    let mut buffer = [0u8; 64 * 1024];
    loop {
        let read = file.read(&mut buffer)?;
        if read == 0 {
            break;
        }
        hasher.update(&buffer[..read]);
    }
    Ok(hex::encode(hasher.finalize()))
}

fn merkle_root(hex_hashes: &[String]) -> Result<String> {
    if hex_hashes.is_empty() {
        return Ok(sha256_hex(&[]));
    }
    let mut layer: Vec<Vec<u8>> = hex_hashes
        .iter()
        .map(|h| hex::decode(h))
        .collect::<std::result::Result<_, _>>()?;
    while layer.len() > 1 {
        let mut next = Vec::with_capacity((layer.len() + 1) / 2);
        for pair in layer.chunks(2) {
            let left = &pair[0];
            let right = if pair.len() == 2 { &pair[1] } else { &pair[0] };
            let mut hasher = Sha256::new();
            hasher.update(left);
            hasher.update(right);
            next.push(hasher.finalize().to_vec());
        }
        layer = next;
    }
    Ok(hex::encode(&layer[0]))
}
