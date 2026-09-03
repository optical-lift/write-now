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
    sources: Vec<BlindSource>,
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
struct BlindSource {
    source_group_id: String,
    #[serde(default)]
    lane: String,
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
struct DiscoveryPacket {
    schema: String,
    blind_discovery_sha256: String,
    source_blind_input_sha256: String,
    #[serde(default)]
    source_harvest_sha256: Option<String>,
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
struct SourceProfile {
    lane: String,
    rules: Vec<RuleCount>,
}

#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
struct AtlasRow<'a> {
    schema: &'static str,
    source_group_id: &'a str,
    lane: &'a str,
    blind_rank: u64,
    candidate_tier: &'a str,
    context: &'a str,
    predicted_outcome: &'a str,
    context_count: String,
    predicted_outcome_count: String,
    accuracy: f64,
}

fn arg(args: &[String], name: &str) -> Result<String> {
    let pos = args
        .iter()
        .position(|value| value == name)
        .ok_or_else(|| anyhow!("missing required argument {name}"))?;
    args.get(pos + 1)
        .cloned()
        .ok_or_else(|| anyhow!("missing value for {name}"))
}

fn sha256_hex(bytes: &[u8]) -> String {
    hex::encode(Sha256::digest(bytes))
}

fn contains_bytes(haystack: &[u8], needle: &[u8]) -> bool {
    !needle.is_empty() && haystack.windows(needle.len()).any(|window| window == needle)
}

fn merkle_root(hex_hashes: &[String]) -> Result<String> {
    if hex_hashes.is_empty() {
        return Ok(sha256_hex(&[]));
    }
    let mut layer: Vec<Vec<u8>> = hex_hashes
        .iter()
        .map(hex::decode)
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

fn parse_rule(rule: FrozenRule) -> Result<RuleSpec> {
    let context = rule.context;
    let (center_kind, context_arm) = {
        let rest = context
            .strip_prefix("CENTER:")
            .ok_or_else(|| anyhow!("unsupported frozen rule context {context}"))?;
        let (center_kind, context_arm) = rest
            .split_once("|ARM:")
            .ok_or_else(|| anyhow!("unsupported frozen rule context {context}"))?;
        if center_kind.is_empty() || context_arm.is_empty() || rule.predicted_outcome.is_empty() {
            bail!("incomplete frozen rule {context}");
        }
        (center_kind.to_string(), context_arm.to_string())
    };
    Ok(RuleSpec {
        context,
        predicted_outcome: rule.predicted_outcome,
        blind_rank: rule.blind_rank,
        candidate_tier: rule.candidate_tier,
        center_kind,
        context_arm,
    })
}

fn center_contribution(
    histogram: &BTreeMap<String, u64>,
    context_arm: &str,
    predicted_outcome: &str,
) -> (u128, u128) {
    let context_arm_count = *histogram.get(context_arm).unwrap_or(&0) as u128;
    if context_arm_count == 0 {
        return (0, 0);
    }
    let resolved_degree: u128 = histogram
        .iter()
        .filter(|(arm, _)| arm.as_str() != "UNRESOLVED")
        .map(|(_, count)| *count as u128)
        .sum();
    if resolved_degree < 2 {
        return (0, 0);
    }
    let context_count = context_arm_count * (resolved_degree - 1);
    let predicted_count = if predicted_outcome == context_arm {
        context_arm_count * context_arm_count.saturating_sub(1)
    } else {
        let outcome_count = *histogram.get(predicted_outcome).unwrap_or(&0) as u128;
        context_arm_count * outcome_count
    };
    (context_count, predicted_count)
}

fn ratio(numerator: u128, denominator: u128) -> f64 {
    if denominator == 0 {
        0.0
    } else {
        numerator as f64 / denominator as f64
    }
}

fn verify_and_stream(
    events_path: &Path,
    custody: &PhysicalLedgerCustody,
    rules: &[RuleSpec],
    profiles: &mut BTreeMap<String, SourceProfile>,
) -> Result<(u64, u64)> {
    if custody.chunk_lines == 0 {
        bail!("physical ledger custody chunkLines must be positive");
    }
    let mut reader = BufReader::with_capacity(1024 * 1024, File::open(events_path)?);
    let mut buffer = Vec::<u8>::with_capacity(512);
    let mut line_count = 0u64;
    let mut center_count = 0u64;
    let mut chunk_line_count = 0u64;
    let mut chunk_hasher = Sha256::new();
    let mut observed_chunk_hashes = Vec::<String>::new();
    let center_marker = b"\"kind\":\"CENTER\"";

    loop {
        buffer.clear();
        let read = reader.read_until(b'\n', &mut buffer)?;
        if read == 0 {
            break;
        }
        line_count += 1;
        chunk_line_count += 1;
        chunk_hasher.update(&buffer);
        if chunk_line_count == custody.chunk_lines {
            observed_chunk_hashes.push(hex::encode(std::mem::replace(&mut chunk_hasher, Sha256::new()).finalize()));
            chunk_line_count = 0;
        }

        if !contains_bytes(&buffer, center_marker) {
            continue;
        }
        let event: CenterEvent = serde_json::from_slice(&buffer)
            .with_context(|| format!("decode physical ledger center event at line {line_count}"))?;
        if event.schema != "mark_sparse_event_v1" || event.kind != "CENTER" {
            continue;
        }
        center_count += 1;
        let profile = profiles
            .get_mut(&event.source_group_id)
            .ok_or_else(|| anyhow!("physical ledger contains unknown blind source {}", event.source_group_id))?;
        for (index, rule) in rules.iter().enumerate() {
            if rule.center_kind != event.center_kind {
                continue;
            }
            let (context_count, predicted_count) = center_contribution(
                &event.arm_histogram,
                &rule.context_arm,
                &rule.predicted_outcome,
            );
            profile.rules[index].context_count = profile.rules[index]
                .context_count
                .checked_add(context_count)
                .ok_or_else(|| anyhow!("source-rule context multiplicity overflow"))?;
            profile.rules[index].predicted_count = profile.rules[index]
                .predicted_count
                .checked_add(predicted_count)
                .ok_or_else(|| anyhow!("source-rule predicted multiplicity overflow"))?;
        }
    }

    if chunk_line_count > 0 {
        observed_chunk_hashes.push(hex::encode(chunk_hasher.finalize()));
    }
    if line_count != custody.lines {
        bail!("physical ledger line count mismatch: observed={line_count} expected={}", custody.lines);
    }
    if observed_chunk_hashes != custody.chunk_hashes {
        bail!("physical ledger chunk hashes do not match frozen compiler custody");
    }
    let observed_root = merkle_root(&observed_chunk_hashes)?;
    if observed_root != custody.merkle_root {
        bail!("physical ledger Merkle root mismatch");
    }
    Ok((line_count, center_count))
}

fn write_rows(
    path: &Path,
    rules: &[RuleSpec],
    profiles: &BTreeMap<String, SourceProfile>,
) -> Result<(u64, String, u64)> {
    let mut writer = BufWriter::new(File::create(path)?);
    let mut hasher = Sha256::new();
    let mut rows = 0u64;
    let mut sources_with_context = 0u64;
    for (source_group_id, profile) in profiles {
        let mut source_has_context = false;
        for (index, rule) in rules.iter().enumerate() {
            let count = &profile.rules[index];
            if count.context_count == 0 {
                continue;
            }
            source_has_context = true;
            let row = AtlasRow {
                schema: "mark_source_rule_atlas_row_v1",
                source_group_id,
                lane: &profile.lane,
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
            hasher.update(&bytes);
            rows += 1;
        }
        if source_has_context {
            sources_with_context += 1;
        }
    }
    writer.flush()?;
    Ok((rows, hex::encode(hasher.finalize()), sources_with_context))
}

fn main() -> Result<()> {
    let args: Vec<String> = std::env::args().collect();
    let events_path = PathBuf::from(arg(&args, "--events")?);
    let discovery_path = PathBuf::from(arg(&args, "--blind-discovery")?);
    let custody_path = PathBuf::from(arg(&args, "--custody")?);
    let input_path = PathBuf::from(arg(&args, "--input")?);
    let out_dir = PathBuf::from(arg(&args, "--out")?);
    fs::create_dir_all(&out_dir)?;

    let discovery: DiscoveryPacket = serde_json::from_slice(&fs::read(&discovery_path)?)?;
    if discovery.schema != "mark_v7_blind_discovery_packet_v1" || discovery.blind_discovery_sha256.len() != 64 {
        bail!("invalid frozen blind discovery packet");
    }
    let input: BlindInput = serde_json::from_slice(&fs::read(&input_path)?)?;
    if input.schema != "mark_observable_input_blind_v1" || input.blind_input_sha256.len() != 64 {
        bail!("invalid sealed blind compiler input");
    }
    let custody: CompilerCustody = serde_json::from_slice(&fs::read(&custody_path)?)?;
    if custody.schema != "mark_sparse_ledger_custody_v2" {
        bail!("invalid compiler custody schema");
    }
    if discovery.source_blind_input_sha256 != input.blind_input_sha256
        || custody.source_blind_input_sha256 != input.blind_input_sha256
    {
        bail!("blind input hash chain mismatch between discovery, compiler input, and custody");
    }
    if discovery.rules.is_empty() {
        bail!("frozen blind discovery packet contains no rules");
    }

    let mut rules: Vec<RuleSpec> = discovery
        .rules
        .into_iter()
        .map(parse_rule)
        .collect::<Result<_>>()?;
    rules.sort_by_key(|rule| rule.blind_rank);
    for pair in rules.windows(2) {
        if pair[0].blind_rank == pair[1].blind_rank {
            bail!("duplicate blind rule rank {}", pair[0].blind_rank);
        }
    }

    let mut profiles = BTreeMap::<String, SourceProfile>::new();
    let mut lanes = HashMap::<String, u64>::new();
    for source in input.sources {
        *lanes.entry(source.lane.clone()).or_default() += 1;
        if profiles
            .insert(
                source.source_group_id.clone(),
                SourceProfile {
                    lane: source.lane,
                    rules: vec![RuleCount::default(); rules.len()],
                },
            )
            .is_some()
        {
            bail!("duplicate blind source {}", source.source_group_id);
        }
    }

    let (physical_lines, centers) = verify_and_stream(
        &events_path,
        &custody.physical_ledger,
        &rules,
        &mut profiles,
    )?;
    let rows_path = out_dir.join("source-rule-atlas.jsonl");
    let (row_count, rows_sha256, sources_with_context) = write_rows(&rows_path, &rules, &profiles)?;

    let preimage = format!(
        "mark_source_rule_atlas_v1|{}|{}|{}|{}|{}|{}|{}",
        discovery.blind_discovery_sha256,
        input.blind_input_sha256,
        custody.physical_ledger.merkle_root,
        rows_sha256,
        profiles.len(),
        rules.len(),
        row_count
    );
    let atlas_sha256 = sha256_hex(preimage.as_bytes());
    let summary = json!({
        "schema":"mark_source_rule_atlas_summary_v1",
        "atlasSha256":atlas_sha256,
        "hashPreimageContract":"sha256(mark_source_rule_atlas_v1|blindDiscoverySha256|sourceBlindInputSha256|physicalLedgerMerkleRoot|rowsSha256|sourceObjects|rules|sourceRuleRows)",
        "sealedBlindDiscoverySha256":discovery.blind_discovery_sha256,
        "sourceBlindInputSha256":input.blind_input_sha256,
        "sourceHarvestSha256":discovery.source_harvest_sha256,
        "physicalLedgerMerkleRoot":custody.physical_ledger.merkle_root,
        "physicalLedgerLines":physical_lines,
        "centerEvents":centers,
        "sourceObjects":profiles.len(),
        "sourceObjectsWithRuleContext":sources_with_context,
        "rules":rules.len(),
        "sourceRuleRows":row_count,
        "rowsSha256":rows_sha256,
        "lanes":lanes,
        "contract":{
            "allFrozenRulesProjected":true,
            "postHocRuleFiltering":false,
            "sourceUniverseFromSealedBlindInput":true,
            "physicalLedgerVerifiedWhileStreaming":true,
            "provenanceAvailable":false,
            "sourcePixelsRemeasured":false,
            "projectionBasis":"frozen physical CENTER events using the exact v7 directed-pair multiplicity contract"
        }
    });
    fs::write(out_dir.join("summary.json"), serde_json::to_vec_pretty(&summary)?)?;
    fs::write(
        out_dir.join("summary.txt"),
        format!(
            "schema=mark_source_rule_atlas_summary_v1\natlas_sha256={}\nsealed_blind_discovery_sha256={}\nsource_objects={}\nrules={}\nsource_rule_rows={}\nsources_with_rule_context={}\nphysical_ledger_lines={}\ncenter_events={}\nrows_sha256={}\n",
            summary["atlasSha256"].as_str().unwrap_or(""),
            summary["sealedBlindDiscoverySha256"].as_str().unwrap_or(""),
            profiles.len(),
            rules.len(),
            row_count,
            sources_with_context,
            physical_lines,
            centers,
            summary["rowsSha256"].as_str().unwrap_or("")
        ),
    )?;
    println!("{}", serde_json::to_string_pretty(&summary)?);
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn reproduces_distinct_arm_pair_multiplicity() {
        let histogram = BTreeMap::from([
            ("PATH_TO_JUNCTION".to_string(), 2),
            ("PATH_TO_ENDPOINT".to_string(), 3),
            ("UNRESOLVED".to_string(), 7),
        ]);
        let (context, predicted) = center_contribution(
            &histogram,
            "PATH_TO_JUNCTION",
            "PATH_TO_ENDPOINT",
        );
        assert_eq!(context, 8);
        assert_eq!(predicted, 6);
    }

    #[test]
    fn reproduces_same_arm_directed_pair_multiplicity() {
        let histogram = BTreeMap::from([("PATH_TO_JUNCTION".to_string(), 4)]);
        let (context, predicted) = center_contribution(
            &histogram,
            "PATH_TO_JUNCTION",
            "PATH_TO_JUNCTION",
        );
        assert_eq!(context, 12);
        assert_eq!(predicted, 12);
    }
}
