fn main() -> Result<()> {
    let args: Vec<String> = std::env::args().collect();
    if args.get(1).map(String::as_str) != Some("compile") {
        bail!("usage: mark-sparse-compiler compile --input <blind.json> --out <dir> [--tile 512] [--overlap 32] [--null-iterations 16]");
    }

    let input_path = PathBuf::from(parse_arg(&args, "--input", None)?);
    let out_dir = PathBuf::from(parse_arg(
        &args,
        "--out",
        Some("artifacts/mark-v7-sparse"),
    )?);
    let tile_size: u32 = parse_arg(&args, "--tile", Some("512"))?.parse()?;
    let overlap: u32 = parse_arg(&args, "--overlap", Some("32"))?.parse()?;
    let null_iterations: usize =
        parse_arg(&args, "--null-iterations", Some("16"))?.parse()?;
    let min_sources: usize = parse_arg(&args, "--min-sources", Some("3"))?.parse()?;
    if tile_size < 64 || overlap * 2 >= tile_size {
        bail!("tile must be >=64 and overlap must be less than half the tile size");
    }

    fs::create_dir_all(&out_dir)?;
    let bytes = fs::read(&input_path)?;
    let input: BlindInput = serde_json::from_slice(&bytes)?;
    if input.schema != "mark_observable_input_blind_v1" {
        bail!("unsupported input schema {}", input.schema);
    }
    if input.blind_input_sha256.len() != 64 {
        bail!("blind input is missing its sealed SHA-256");
    }
    let input_blind_sha256 = input.blind_input_sha256.clone();

    let source_by_id: HashMap<String, BlindSource> = input
        .sources
        .iter()
        .cloned()
        .map(|source| (source.source_group_id.clone(), source))
        .collect();
    let mut observations_by_source: HashMap<String, Vec<Observation>> = HashMap::new();
    for observation in input.observations.iter().cloned() {
        if !source_by_id.contains_key(&observation.source_group_id) {
            bail!("unknown source {}", observation.source_group_id);
        }
        observations_by_source
            .entry(observation.source_group_id.clone())
            .or_default()
            .push(observation);
    }
    for observations in observations_by_source.values_mut() {
        observations.sort_by(|a, b| a.id.cmp(&b.id));
    }

    let mut ledger = ChunkedLedger::create(&out_dir.join("events.jsonl"))?;
    let mut contribution_ledger =
        ChunkedLedger::create(&out_dir.join("grammar-contributions.jsonl"))?;
    let stats_db_path = out_dir.join("grammar-stats.sqlite");
    let mut store = StatsStore::create(&stats_db_path)?;
    let mut stats = CompilerStats::default();
    let base_dir = input_path.parent().unwrap_or_else(|| Path::new("."));
    let mut sources = input.sources.clone();
    sources.sort_by(|a, b| a.source_group_id.cmp(&b.source_group_id));

    for (source_index, source) in sources.iter().enumerate() {
        let capture = base_dir.join(&source.capture_path);
        let image = image::open(&capture)
            .with_context(|| format!("decode {}", capture.display()))?
            .to_luma8();
        let observations = observations_by_source
            .get(&source.source_group_id)
            .map(Vec::as_slice)
            .unwrap_or(&[]);
        let mut source_grammar = SourceGrammar::new();

        for observation in observations {
            if observation.lane != source.lane {
                bail!(
                    "lane mismatch for {}: source={} observation={}",
                    observation.id,
                    source.lane,
                    observation.lane
                );
            }
            compile_observation(
                &image,
                observation,
                tile_size,
                overlap,
                null_iterations,
                &mut ledger,
                &mut contribution_ledger,
                &mut source_grammar,
                &mut stats,
            )?;
        }

        stats.grammar_stat_commits += store.commit_source(&source_grammar)?;
        stats.sources += 1;
        eprintln!(
            "v7 sufficient-statistics compile: {}/{} sources, {} observations, {} centers, {} source-stat commits",
            source_index + 1,
            sources.len(),
            stats.observations,
            stats.centers,
            stats.grammar_stat_commits
        );
        drop(image);
    }

    let (ledger_lines, chunk_hashes, merkle_root) = ledger.finish()?;
    let (contribution_lines, contribution_chunks, contribution_root) =
        contribution_ledger.finish()?;
    let rule_count = store.build_rules(&out_dir, min_sources)?;
    let evaluation = store.evaluation(null_iterations, rule_count)?;
    let (grammar_stat_rows, context_stat_rows) = store.storage_counts()?;
    drop(store);

    let stats_db_sha256 = sha256_file(&stats_db_path)?;
    let stats_db_bytes = fs::metadata(&stats_db_path)?.len();

    let custody = json!({
        "schema":"mark_sparse_ledger_custody_v2",
        "sourceBlindInputSha256":input_blind_sha256.clone(),
        "physicalLedger":{
            "path":"events.jsonl",
            "lines":ledger_lines,
            "chunkLines":LEDGER_CHUNK_LINES,
            "chunkHashes":chunk_hashes,
            "merkleRoot":merkle_root.clone()
        },
        "grammarStatistics":{
            "database":"grammar-stats.sqlite",
            "databaseSha256":stats_db_sha256,
            "databaseBytes":stats_db_bytes,
            "statRows":grammar_stat_rows,
            "contextRows":context_stat_rows,
            "contributionLedger":"grammar-contributions.jsonl",
            "contributionLines":contribution_lines,
            "contributionChunkLines":LEDGER_CHUNK_LINES,
            "contributionChunkHashes":contribution_chunks,
            "contributionMerkleRoot":contribution_root.clone()
        },
        "contract":{
            "appendOnlyPhysicalEventLedger":true,
            "semanticLabelsAvailable":false,
            "wholeWorldGraphMaterialized":false,
            "wholeWorldJsonMaterialized":false,
            "grammarPairsMaterialized":false,
            "grammarRowsMaterialized":false,
            "grammarSufficientStatisticsDiskBacked":true,
            "distinctSourceSupportCommittedAtSourceBoundary":true,
            "perObservationContributionHashes":true,
            "sourcePixelsRetainedInCustodyNotLedger":true
        }
    });
    fs::write(
        out_dir.join("custody.json"),
        serde_json::to_vec_pretty(&custody)?,
    )?;
    fs::write(
        out_dir.join("evaluation.json"),
        serde_json::to_vec_pretty(&evaluation)?,
    )?;

    let summary = json!({
        "schema":"mark_sparse_compiler_summary_v2",
        "sourceBlindInputSha256":input_blind_sha256,
        "sources":stats.sources,
        "observations":stats.observations,
        "tiles":stats.tiles,
        "centers":stats.centers,
        "events":stats.events,
        "grammarRowsMaterialized":0,
        "grammarStatRows":grammar_stat_rows,
        "contextStatRows":context_stat_rows,
        "sourceStatCommits":stats.grammar_stat_commits,
        "grammarContributions":stats.grammar_contributions,
        "observedPairWeight":stats.observed_pair_weight.to_string(),
        "unresolvedArms":stats.unresolved_arms,
        "tileSize":tile_size,
        "overlap":overlap,
        "nullIterations":null_iterations,
        "physicalLedgerMerkleRoot":merkle_root,
        "grammarContributionMerkleRoot":contribution_root,
        "grammarStorage":"sqlite_sufficient_statistics_v1",
        "evaluation":evaluation
    });
    fs::write(
        out_dir.join("summary.json"),
        serde_json::to_vec_pretty(&summary)?,
    )?;
    println!("{}", serde_json::to_string_pretty(&summary)?);
    Ok(())
}
