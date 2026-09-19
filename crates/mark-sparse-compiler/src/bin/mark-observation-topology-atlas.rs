use anyhow::{anyhow, bail, Context, Result};
use serde::{Deserialize, Serialize};
use serde_json::json;
use sha2::{Digest, Sha256};
use std::collections::BTreeMap;
use std::fs::{self, File};
use std::io::{BufRead, BufReader, BufWriter, Write};
use std::path::{Path, PathBuf};

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
struct BlindInput {
    schema: String,
    blind_input_sha256: String,
    observations: Vec<Observation>,
}

#[derive(Debug, Clone, Deserialize)]
#[serde(rename_all = "camelCase")]
struct Observation {
    id: String,
    source_group_id: String,
    lane: String,
    region: Region,
    #[serde(default)]
    proposal_kind: String,
    #[serde(default)]
    proposal_scale: String,
}

#[derive(Debug, Clone, Copy, Deserialize, Serialize)]
struct Region {
    x: u32,
    y: u32,
    width: u32,
    height: u32,
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
struct CompilerCustody {
    schema: String,
    source_blind_input_sha256: String,
    physical_ledger: PhysicalLedgerCustody,
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
struct PhysicalLedgerCustody {
    lines: u64,
    chunk_lines: u64,
    chunk_hashes: Vec<String>,
    merkle_root: String,
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
struct CenterEvent {
    schema: String,
    source_group_id: String,
    observation_id: String,
    kind: String,
    center_kind: String,
    arm_histogram: BTreeMap<String, u64>,
}

#[derive(Debug, Clone)]
struct Profile {
    source_group_id: String,
    lane: String,
    region: Region,
    proposal_kind: String,
    proposal_scale: String,
    center_count: u64,
    count_features: BTreeMap<String, u64>,
}

#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
struct OutputRow<'a> {
    schema: &'static str,
    observation_id: &'a str,
    source_group_id: &'a str,
    lane: &'a str,
    region: Region,
    proposal_kind: &'a str,
    proposal_scale: &'a str,
    center_count: u64,
    count_features: &'a BTreeMap<String, u64>,
}

fn arg(args: &[String], name: &str) -> Result<String> {
    let pos = args.iter().position(|v| v == name).ok_or_else(|| anyhow!("missing required argument {name}"))?;
    args.get(pos + 1).cloned().ok_or_else(|| anyhow!("missing value for {name}"))
}

fn sha256_hex(bytes: &[u8]) -> String { hex::encode(Sha256::digest(bytes)) }

fn contains_bytes(haystack: &[u8], needle: &[u8]) -> bool {
    !needle.is_empty() && haystack.windows(needle.len()).any(|window| window == needle)
}

fn merkle_root(hex_hashes: &[String]) -> Result<String> {
    if hex_hashes.is_empty() { return Ok(sha256_hex(&[])); }
    let mut layer: Vec<Vec<u8>> = hex_hashes.iter().map(hex::decode).collect::<std::result::Result<_, _>>()?;
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

fn degree_bucket(degree: u64) -> &'static str {
    match degree {
        0 => "0",
        1 => "1",
        2 => "2",
        3 => "3",
        4 => "4",
        _ => "5plus",
    }
}

fn signature(center_kind: &str, histogram: &BTreeMap<String, u64>) -> String {
    let e = histogram.get("PATH_TO_ENDPOINT").copied().unwrap_or(0);
    let j = histogram.get("PATH_TO_JUNCTION").copied().unwrap_or(0);
    let u = histogram.get("UNRESOLVED").copied().unwrap_or(0);
    let other: u64 = histogram.iter()
        .filter(|(arm, _)| !matches!(arm.as_str(), "PATH_TO_ENDPOINT" | "PATH_TO_JUNCTION" | "UNRESOLVED"))
        .map(|(_, count)| *count)
        .sum();
    format!("{center_kind}|E={e}|J={j}|U={u}|O={other}")
}

fn add(profile: &mut Profile, key: String, value: u64) {
    if value == 0 { return; }
    *profile.count_features.entry(key).or_default() += value;
}

fn absorb_center(profile: &mut Profile, event: &CenterEvent) {
    profile.center_count += 1;
    add(profile, format!("center:{}", event.center_kind), 1);
    let degree: u64 = event.arm_histogram.values().sum();
    add(profile, format!("degree:{}:{}", event.center_kind, degree_bucket(degree)), 1);
    for (arm, count) in &event.arm_histogram {
        add(profile, format!("arm:{}:{}", event.center_kind, arm), *count);
    }
    add(profile, format!("signature:{}", signature(&event.center_kind, &event.arm_histogram)), 1);
}

fn verify_and_stream(
    events_path: &Path,
    custody: &PhysicalLedgerCustody,
    expected_merkle: &str,
    profiles: &mut BTreeMap<String, Profile>,
) -> Result<(u64, u64)> {
    if custody.merkle_root != expected_merkle {
        bail!("physical ledger Merkle root differs from frozen parent: {} != {}", custody.merkle_root, expected_merkle);
    }
    if custody.chunk_lines == 0 { bail!("physical ledger chunkLines must be positive"); }
    let mut reader = BufReader::with_capacity(1024 * 1024, File::open(events_path)?);
    let mut buffer = Vec::<u8>::with_capacity(512);
    let mut line_count = 0u64;
    let mut center_count = 0u64;
    let mut chunk_line_count = 0u64;
    let mut chunk_hasher = Sha256::new();
    let mut observed_chunk_hashes = Vec::<String>::new();
    let marker = b"\"kind\":\"CENTER\"";
    loop {
        buffer.clear();
        let read = reader.read_until(b'\n', &mut buffer)?;
        if read == 0 { break; }
        line_count += 1;
        chunk_line_count += 1;
        chunk_hasher.update(&buffer);
        if chunk_line_count == custody.chunk_lines {
            observed_chunk_hashes.push(hex::encode(std::mem::replace(&mut chunk_hasher, Sha256::new()).finalize()));
            chunk_line_count = 0;
        }
        if !contains_bytes(&buffer, marker) { continue; }
        let event: CenterEvent = serde_json::from_slice(&buffer)
            .with_context(|| format!("decode center event at line {line_count}"))?;
        if event.schema != "mark_sparse_event_v1" || event.kind != "CENTER" { continue; }
        let profile = profiles.get_mut(&event.observation_id)
            .ok_or_else(|| anyhow!("unknown observation {}", event.observation_id))?;
        if profile.source_group_id != event.source_group_id {
            bail!("observation/source mismatch for {}", event.observation_id);
        }
        center_count += 1;
        absorb_center(profile, &event);
    }
    if chunk_line_count > 0 { observed_chunk_hashes.push(hex::encode(chunk_hasher.finalize())); }
    if line_count != custody.lines { bail!("physical ledger line count mismatch {line_count} != {}", custody.lines); }
    if observed_chunk_hashes != custody.chunk_hashes { bail!("physical ledger chunk hashes do not match compiler custody"); }
    if merkle_root(&observed_chunk_hashes)? != custody.merkle_root { bail!("physical ledger Merkle verification failed"); }
    Ok((line_count, center_count))
}

fn main() -> Result<()> {
    let args: Vec<String> = std::env::args().collect();
    let events_path = PathBuf::from(arg(&args, "--events")?);
    let custody_path = PathBuf::from(arg(&args, "--custody")?);
    let input_path = PathBuf::from(arg(&args, "--input")?);
    let expected_merkle = arg(&args, "--expected-merkle")?;
    let out_dir = PathBuf::from(arg(&args, "--out")?);
    fs::create_dir_all(&out_dir)?;

    let input: BlindInput = serde_json::from_slice(&fs::read(&input_path)?)?;
    let custody: CompilerCustody = serde_json::from_slice(&fs::read(&custody_path)?)?;
    if input.schema != "mark_observable_input_blind_v1" || custody.schema != "mark_sparse_ledger_custody_v2" {
        bail!("unexpected parent schema");
    }
    if custody.source_blind_input_sha256 != input.blind_input_sha256 { bail!("blind input hash chain mismatch"); }

    let mut profiles = BTreeMap::<String, Profile>::new();
    for observation in input.observations {
        let id = observation.id.clone();
        if profiles.insert(id.clone(), Profile {
            source_group_id: observation.source_group_id,
            lane: observation.lane,
            region: observation.region,
            proposal_kind: observation.proposal_kind,
            proposal_scale: observation.proposal_scale,
            center_count: 0,
            count_features: BTreeMap::new(),
        }).is_some() { bail!("duplicate observation {id}"); }
    }

    let (physical_lines, centers) = verify_and_stream(
        &events_path,
        &custody.physical_ledger,
        &expected_merkle,
        &mut profiles,
    )?;

    let rows_path = out_dir.join("observation-topology-atlas.jsonl");
    let mut writer = BufWriter::new(File::create(&rows_path)?);
    let mut rows_hasher = Sha256::new();
    let mut feature_keys = BTreeMap::<String, u64>::new();
    let mut row_count = 0u64;
    for (id, profile) in &profiles {
        for key in profile.count_features.keys() { *feature_keys.entry(key.clone()).or_default() += 1; }
        let row = OutputRow {
            schema: "mark_observation_topology_row_v1",
            observation_id: id,
            source_group_id: &profile.source_group_id,
            lane: &profile.lane,
            region: profile.region,
            proposal_kind: &profile.proposal_kind,
            proposal_scale: &profile.proposal_scale,
            center_count: profile.center_count,
            count_features: &profile.count_features,
        };
        let mut bytes = serde_json::to_vec(&row)?;
        bytes.push(b'\n');
        writer.write_all(&bytes)?;
        rows_hasher.update(&bytes);
        row_count += 1;
    }
    writer.flush()?;
    let rows_sha = hex::encode(rows_hasher.finalize());
    let summary = json!({
        "schema":"mark_observation_topology_atlas_summary_v1",
        "sourceBlindInputSha256":custody.source_blind_input_sha256,
        "physicalLedgerLines":physical_lines,
        "physicalLedgerMerkleRoot":custody.physical_ledger.merkle_root,
        "centerEvents":centers,
        "observations":row_count,
        "featureKeys":feature_keys.len(),
        "featureObservationSupport":feature_keys,
        "rowsSha256":rows_sha,
        "contract":{
            "physicalLedgerFullyStreamVerified":true,
            "noProvenanceConsumed":true,
            "rawFrozenRuleAccuracyFeaturesNotComputed":true,
            "topologyCountsOnly":true
        }
    });
    fs::write(out_dir.join("summary.json"), serde_json::to_vec_pretty(&summary)?)?;
    println!("{}", serde_json::to_string_pretty(&summary)?);
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn signature_is_deterministic() {
        let mut h = BTreeMap::new();
        h.insert("PATH_TO_JUNCTION".to_string(), 2);
        h.insert("PATH_TO_ENDPOINT".to_string(), 1);
        assert_eq!(signature("JUNCTION", &h), "JUNCTION|E=1|J=2|U=0|O=0");
    }

    #[test]
    fn degree_buckets_are_bounded() {
        assert_eq!(degree_bucket(0), "0");
        assert_eq!(degree_bucket(4), "4");
        assert_eq!(degree_bucket(12), "5plus");
    }
}
