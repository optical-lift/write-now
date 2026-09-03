use anyhow::{anyhow, bail, Context, Result};
use serde::{Deserialize, Serialize};
use serde_json::json;
use sha2::{Digest, Sha256};
use std::collections::{BTreeMap, HashMap};
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
struct DiscoveryPacket {
    schema: String,
    blind_discovery_sha256: String,
    source_blind_input_sha256: String,
    rules: Vec<FrozenRule>,
}

#[derive(Debug, Clone, Deserialize)]
#[serde(rename_all = "camelCase")]
struct FrozenRule {
    context: String,
    predicted_outcome: String,
    blind_rank: u64,
    candidate_tier: String,
}

#[derive(Debug, Clone)]
struct RuleSpec {
    context: String,
    predicted_outcome: String,
    blind_rank: u64,
    candidate_tier: String,
    center_kind: String,
    context_arm: String,
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

#[derive(Debug, Clone, Default)]
struct RuleCount {
    context_count: u128,
    predicted_count: u128,
}

#[derive(Debug, Clone)]
struct ObservationProfile {
    source_group_id: String,
    lane: String,
    region: Region,
    proposal_kind: String,
    proposal_scale: String,
    rules: Vec<RuleCount>,
}

#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
struct ObservationRuleRow<'a> {
    schema: &'static str,
    observation_id: &'a str,
    source_group_id: &'a str,
    lane: &'a str,
    region: Region,
    proposal_kind: &'a str,
    proposal_scale: &'a str,
    blind_rank: u64,
    candidate_tier: &'a str,
    context: &'a str,
    predicted_outcome: &'a str,
    context_count: String,
    predicted_outcome_count: String,
    accuracy: f64,
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

fn parse_rule(rule: FrozenRule) -> Result<RuleSpec> {
    let context = rule.context;
    let rest = context.strip_prefix("CENTER:").ok_or_else(|| anyhow!("unsupported context {context}"))?;
    let (center_kind, context_arm) = rest.split_once("|ARM:").ok_or_else(|| anyhow!("unsupported context {context}"))?;
    if center_kind.is_empty() || context_arm.is_empty() || rule.predicted_outcome.is_empty() { bail!("incomplete frozen rule {context}"); }
    Ok(RuleSpec {
        context,
        predicted_outcome: rule.predicted_outcome,
        blind_rank: rule.blind_rank,
        candidate_tier: rule.candidate_tier,
        center_kind: center_kind.to_string(),
        context_arm: context_arm.to_string(),
    })
}

fn center_contribution(histogram: &BTreeMap<String, u64>, context_arm: &str, predicted_outcome: &str) -> (u128, u128) {
    let context_arm_count = *histogram.get(context_arm).unwrap_or(&0) as u128;
    if context_arm_count == 0 { return (0, 0); }
    let resolved_degree: u128 = histogram.iter().filter(|(arm, _)| arm.as_str() != "UNRESOLVED").map(|(_, count)| *count as u128).sum();
    if resolved_degree < 2 { return (0, 0); }
    let context_count = context_arm_count * (resolved_degree - 1);
    let predicted_count = if predicted_outcome == context_arm {
        context_arm_count * context_arm_count.saturating_sub(1)
    } else {
        context_arm_count * (*histogram.get(predicted_outcome).unwrap_or(&0) as u128)
    };
    (context_count, predicted_count)
}

fn ratio(n: u128, d: u128) -> f64 { if d == 0 { 0.0 } else { n as f64 / d as f64 } }

fn verify_and_stream(
    events_path: &Path,
    custody: &PhysicalLedgerCustody,
    expected_merkle: &str,
    rules: &[RuleSpec],
    profiles: &mut BTreeMap<String, ObservationProfile>,
) -> Result<(u64, u64)> {
    if custody.merkle_root != expected_merkle { bail!("recompiled physical ledger Merkle root differs from frozen parent: {} != {}", custody.merkle_root, expected_merkle); }
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
        let event: CenterEvent = serde_json::from_slice(&buffer).with_context(|| format!("decode center event at line {line_count}"))?;
        if event.schema != "mark_sparse_event_v1" || event.kind != "CENTER" { continue; }
        center_count += 1;
        let profile = profiles.get_mut(&event.observation_id).ok_or_else(|| anyhow!("unknown observation {}", event.observation_id))?;
        if profile.source_group_id != event.source_group_id { bail!("observation/source mismatch for {}", event.observation_id); }
        for (index, rule) in rules.iter().enumerate() {
            if rule.center_kind != event.center_kind { continue; }
            let (context_count, predicted_count) = center_contribution(&event.arm_histogram, &rule.context_arm, &rule.predicted_outcome);
            profile.rules[index].context_count = profile.rules[index].context_count.checked_add(context_count).ok_or_else(|| anyhow!("observation context overflow"))?;
            profile.rules[index].predicted_count = profile.rules[index].predicted_count.checked_add(predicted_count).ok_or_else(|| anyhow!("observation predicted overflow"))?;
        }
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
    let discovery_path = PathBuf::from(arg(&args, "--blind-discovery")?);
    let custody_path = PathBuf::from(arg(&args, "--custody")?);
    let input_path = PathBuf::from(arg(&args, "--input")?);
    let expected_merkle = arg(&args, "--expected-merkle")?;
    let out_dir = PathBuf::from(arg(&args, "--out")?);
    fs::create_dir_all(&out_dir)?;

    let discovery: DiscoveryPacket = serde_json::from_slice(&fs::read(&discovery_path)?)?;
    let input: BlindInput = serde_json::from_slice(&fs::read(&input_path)?)?;
    let custody: CompilerCustody = serde_json::from_slice(&fs::read(&custody_path)?)?;
    if discovery.schema != "mark_v7_blind_discovery_packet_v1" || input.schema != "mark_observable_input_blind_v1" || custody.schema != "mark_sparse_ledger_custody_v2" { bail!("unexpected parent schema"); }
    if discovery.source_blind_input_sha256 != input.blind_input_sha256 || custody.source_blind_input_sha256 != input.blind_input_sha256 { bail!("blind input hash chain mismatch"); }
    let mut rules: Vec<RuleSpec> = discovery.rules.into_iter().map(parse_rule).collect::<Result<_>>()?;
    rules.sort_by_key(|rule| rule.blind_rank);
    if rules.len() != 2 { bail!("local-state-field v1 expects the two frozen parent rules, got {}", rules.len()); }

    let mut profiles = BTreeMap::<String, ObservationProfile>::new();
    let mut lanes = HashMap::<String, u64>::new();
    for observation in input.observations {
        *lanes.entry(observation.lane.clone()).or_default() += 1;
        let id = observation.id.clone();
        if profiles.insert(id.clone(), ObservationProfile {
            source_group_id: observation.source_group_id,
            lane: observation.lane,
            region: observation.region,
            proposal_kind: observation.proposal_kind,
            proposal_scale: observation.proposal_scale,
            rules: vec![RuleCount::default(); rules.len()],
        }).is_some() { bail!("duplicate observation {id}"); }
    }

    let (physical_lines, centers) = verify_and_stream(&events_path, &custody.physical_ledger, &expected_merkle, &rules, &mut profiles)?;
    let rows_path = out_dir.join("observation-rule-atlas.jsonl");
    let mut writer = BufWriter::new(File::create(&rows_path)?);
    let mut rows_hasher = Sha256::new();
    let mut row_count = 0u64;
    let mut observations_with_context = 0u64;
    for (observation_id, profile) in &profiles {
        let mut any = false;
        for (index, rule) in rules.iter().enumerate() {
            let count = &profile.rules[index];
            if count.context_count == 0 { continue; }
            any = true;
            let row = ObservationRuleRow {
                schema: "mark_observation_rule_atlas_row_v1",
                observation_id,
                source_group_id: &profile.source_group_id,
                lane: &profile.lane,
                region: profile.region,
                proposal_kind: &profile.proposal_kind,
                proposal_scale: &profile.proposal_scale,
                blind_rank: rule.blind_rank,
                candidate_tier: &rule.candidate_tier,
                context: &rule.context,
                predicted_outcome: &rule.predicted_outcome,
                context_count: count.context_count.to_string(),
                predicted_outcome_count: count.predicted_count.to_string(),
                accuracy: ratio(count.predicted_count, count.context_count),
            };
            let mut bytes = serde_json::to_vec(&row)?;
            bytes.push(b'\n');
            writer.write_all(&bytes)?;
            rows_hasher.update(&bytes);
            row_count += 1;
        }
        if any { observations_with_context += 1; }
    }
    writer.flush()?;
    let rows_sha256 = hex::encode(rows_hasher.finalize());
    let preimage = format!("mark_observation_rule_atlas_v1|{}|{}|{}|{}|{}|{}", discovery.blind_discovery_sha256, input.blind_input_sha256, expected_merkle, rows_sha256, profiles.len(), row_count);
    let atlas_sha256 = sha256_hex(preimage.as_bytes());
    let summary = json!({
        "schema":"mark_observation_rule_atlas_summary_v1",
        "observationAtlasSha256":atlas_sha256,
        "sealedBlindDiscoverySha256":discovery.blind_discovery_sha256,
        "sourceBlindInputSha256":input.blind_input_sha256,
        "physicalLedgerMerkleRoot":expected_merkle,
        "physicalLedgerLines":physical_lines,
        "centerEvents":centers,
        "observations":profiles.len(),
        "observationsWithRuleContext":observations_with_context,
        "rules":rules.len(),
        "observationRuleRows":row_count,
        "rowsSha256":rows_sha256,
        "lanes":lanes,
        "contract":{
            "frozenParentRulesOnly":true,
            "physicalLedgerReproducesFrozenParent":true,
            "provenanceAvailable":false,
            "projectionUnit":"observation",
            "projectionBasis":"exact v7 directed-pair multiplicity from frozen CENTER events"
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
    fn directed_multiplicity_matches_v7() {
        let h = BTreeMap::from([
            ("PATH_TO_JUNCTION".to_string(), 2),
            ("PATH_TO_ENDPOINT".to_string(), 3),
            ("UNRESOLVED".to_string(), 5),
        ]);
        assert_eq!(center_contribution(&h, "PATH_TO_JUNCTION", "PATH_TO_ENDPOINT"), (8, 6));
        assert_eq!(center_contribution(&BTreeMap::from([("PATH_TO_JUNCTION".to_string(), 4)]), "PATH_TO_JUNCTION", "PATH_TO_JUNCTION"), (12, 12));
    }
}
