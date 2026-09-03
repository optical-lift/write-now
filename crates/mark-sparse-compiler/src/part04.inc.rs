fn add_grammar_count(
    aggregated: &mut BTreeMap<(String, String), u64>,
    context: String,
    outcome: String,
    count: u64,
) -> Result<()> {
    if count == 0 {
        return Ok(());
    }
    let slot = aggregated.entry((context, outcome)).or_default();
    *slot = (*slot)
        .checked_add(count)
        .ok_or_else(|| anyhow!("grammar multiplicity overflow while aggregating one observation"))?;
    Ok(())
}

fn grammar_from_centers(
    shards: &mut GrammarShards,
    iteration: i32,
    observation: &Observation,
    centers: &[CenterEvidence],
) -> Result<(u64, u128)> {
    // The reducer only needs the sufficient statistic for one sealed observation:
    // (context, outcome) -> exact multiplicity.  Repeating an identical TSV row
    // once per center carries no additional evidence, so collapse those rows here
    // before touching disk.  This remains bounded by the anonymous relation
    // vocabulary of a single observation rather than its number of centers.
    let mut aggregated = BTreeMap::<(String, String), u64>::new();
    let mut weight = 0u128;

    for center in centers {
        let mut counts = BTreeMap::<String, u64>::new();
        for arm in &center.arms {
            if arm != "UNRESOLVED" {
                *counts.entry(arm.clone()).or_default() += 1;
            }
        }

        let tokens: Vec<_> = counts.into_iter().collect();
        for i in 0..tokens.len() {
            for j in i..tokens.len() {
                let (a, ca) = &tokens[i];
                let (b, cb) = &tokens[j];
                let pair_count = if i == j {
                    ca.saturating_mul(ca.saturating_sub(1)) / 2
                } else {
                    ca.saturating_mul(*cb)
                };
                if pair_count == 0 {
                    continue;
                }

                let context_a = format!("CENTER:{}|ARM:{}", center.kind, a);
                add_grammar_count(&mut aggregated, context_a, b.clone(), pair_count)?;
                weight = weight
                    .checked_add(pair_count as u128)
                    .ok_or_else(|| anyhow!("observed grammar weight overflow"))?;

                // A same-token pair intentionally contributes two masked directions.
                // When a == b this lands on the same aggregate key and doubles the
                // count, exactly matching the former two-row representation.
                let context_b = format!("CENTER:{}|ARM:{}", center.kind, b);
                add_grammar_count(&mut aggregated, context_b, a.clone(), pair_count)?;
                weight = weight
                    .checked_add(pair_count as u128)
                    .ok_or_else(|| anyhow!("observed grammar weight overflow"))?;
            }
        }
    }

    let rows = aggregated.len() as u64;
    for ((context, outcome), count) in aggregated {
        shards.write(
            iteration,
            &observation.lane,
            &observation.source_group_id,
            &observation.id,
            &context,
            &outcome,
            count,
        )?;
    }
    Ok((rows, weight))
}

fn seeded_u64(seed: &str) -> u64 {
    let digest = Sha256::digest(seed.as_bytes());
    u64::from_le_bytes(digest[0..8].try_into().unwrap())
}
fn shuffle<T>(items: &mut [T], mut state: u64) {
    if state == 0 {
        state = 0x9E3779B97F4A7C15;
    }
    for i in (1..items.len()).rev() {
        state ^= state << 13;
        state ^= state >> 7;
        state ^= state << 17;
        let j = (state as usize) % (i + 1);
        items.swap(i, j);
    }
}
fn null_centers(
    observation: &Observation,
    centers: &[CenterEvidence],
    iteration: usize,
) -> Vec<CenterEvidence> {
    let mut result = centers.to_vec();
    let mut buckets: BTreeMap<(&'static str, usize), Vec<usize>> = BTreeMap::new();
    for (i, center) in centers.iter().enumerate() {
        buckets
            .entry((center.kind, center.arms.len()))
            .or_default()
            .push(i);
    }
    for ((kind, degree), indexes) in buckets {
        if degree == 0 || indexes.len() < 2 {
            continue;
        }
        let mut pool = Vec::with_capacity(indexes.len() * degree);
        for &index in &indexes {
            pool.extend(centers[index].arms.iter().cloned());
        }
        shuffle(
            &mut pool,
            seeded_u64(&format!(
                "mark-v7-null|{}|{}|{}|{}|{}",
                observation.source_group_id, observation.id, iteration, kind, degree
            )),
        );
        let mut cursor = 0usize;
        for index in indexes {
            result[index].arms.clear();
            result[index]
                .arms
                .extend(pool[cursor..cursor + degree].iter().cloned());
            cursor += degree;
        }
    }
    result
}

fn compile_observation(
    image: &GrayImage,
    observation: &Observation,
    tile_size: u32,
    overlap: u32,
    null_iterations: usize,
    ledger: &mut ChunkedLedger,
    shards: &mut GrammarShards,
    stats: &mut CompilerStats,
) -> Result<()> {
    validate_region(image, observation.region, &observation.id)?;
    let threshold = resolved_threshold(image, observation)?;
    let mut centers = Vec::<CenterEvidence>::new();
    for (tile_index, tile) in tiles(observation.region, tile_size, overlap)
        .into_iter()
        .enumerate()
    {
        stats.tiles += 1;
        let mask = tile_mask(image, observation.region, tile, threshold);
        let w = tile.ext_w as usize;
        let h = tile.ext_h as usize;
        let skeleton = thin(&mask, w, h);
        let (labels, clusters) = critical_clusters(&skeleton, w, h);
        let arms = trace_center_arms(&skeleton, &labels, &clusters, w, h);
        stats.events += emit_continuation_stubs(ledger, &skeleton, observation, tile, w, h)?;
        for cluster in clusters {
            if !point_in_core(&cluster, tile) {
                continue;
            }
            let gx = observation.region.x + tile.ext_x + cluster.cx.round() as u32;
            let gy = observation.region.y + tile.ext_y + cluster.cy.round() as u32;
            let center_id = format!(
                "E{}",
                &sha256_hex(
                    format!(
                        "{}|{}|CENTER|{}|{}|{}",
                        observation.source_group_id, observation.id, cluster.kind, gx, gy
                    )
                    .as_bytes()
                )[..20]
            );
            let center_arms = arms.get(&cluster.label).cloned().unwrap_or_default();
            stats.unresolved_arms += center_arms
                .iter()
                .filter(|a| a.as_str() == "UNRESOLVED")
                .count() as u64;
            ledger.write_json(&json!({"schema":"mark_sparse_event_v1","eventId":center_id,"sourceGroupId":observation.source_group_id,"observationId":observation.id,"lane":observation.lane,"kind":"CENTER","centerKind":cluster.kind,"x":gx,"y":gy,"armHistogram":arm_histogram(&center_arms),"tileIndex":tile_index}))?;
            stats.events += 1;
            stats.centers += 1;
            centers.push(CenterEvidence {
                kind: cluster.kind,
                arms: center_arms,
            });
        }
    }
    let (rows, weight) = grammar_from_centers(shards, -1, observation, &centers)?;
    stats.grammar_rows += rows;
    stats.observed_pair_weight += weight;
    for iteration in 0..null_iterations {
        let null = null_centers(observation, &centers, iteration);
        let (rows, _) = grammar_from_centers(shards, iteration as i32, observation, &null)?;
        stats.grammar_rows += rows;
    }
    ledger.write_json(&json!({"schema":"mark_sparse_observation_boundary_v1","sourceGroupId":observation.source_group_id,"observationId":observation.id,"lane":observation.lane,"proposalKind":observation.proposal_kind,"proposalScale":observation.proposal_scale,"region":observation.region,"threshold":threshold,"centers":centers.len()}))?;
    stats.events += 1;
    stats.observations += 1;
    Ok(())
}
fn arm_histogram(arms: &[String]) -> BTreeMap<String, u64> {
    let mut map = BTreeMap::new();
    for arm in arms {
        *map.entry(arm.clone()).or_default() += 1;
    }
    map
}
impl Serialize for Region {
    fn serialize<S>(&self, serializer: S) -> std::result::Result<S::Ok, S::Error>
    where
        S: serde::Serializer,
    {
        json!({"x":self.x,"y":self.y,"width":self.width,"height":self.height})
            .serialize(serializer)
    }
}
#[derive(Default)]
struct OutcomeAgg {
    count: u128,
    sources: HashSet<String>,
}
#[derive(Clone)]
struct Rule {
    outcome: String,
    distinct_sources: usize,
    total_count: u128,
    context_sources: usize,
}
