include!("../part01.inc.rs");
include!("../part02.inc.rs");
include!("../part03.inc.rs");

use std::collections::{BTreeMap as EdgeBTreeMap, HashMap as EdgeHashMap};

#[derive(Clone)]
struct GraphCenter {
    event_id: String,
    kind: &'static str,
    x: u32,
    y: u32,
    degree: usize,
    arm_histogram: EdgeBTreeMap<String, u64>,
    tile_index: usize,
    pixels: Vec<usize>,
}

fn center_arm_histogram(arms: &[String]) -> EdgeBTreeMap<String, u64> {
    let mut map = EdgeBTreeMap::new();
    for arm in arms {
        *map.entry(arm.clone()).or_default() += 1;
    }
    map
}

fn parse_edge_arg(args: &[String], key: &str, default: Option<&str>) -> Result<String> {
    if let Some(index) = args.iter().position(|arg| arg == key) {
        return args
            .get(index + 1)
            .cloned()
            .ok_or_else(|| anyhow!("missing value for {key}"));
    }
    default
        .map(str::to_string)
        .ok_or_else(|| anyhow!("missing required argument {key}"))
}

fn global_index(rel_x: u32, rel_y: u32, width: usize) -> usize {
    rel_y as usize * width + rel_x as usize
}

fn idx_xy(index: usize, width: usize) -> (u32, u32) {
    ((index % width) as u32, (index / width) as u32)
}

fn edge_neighbor(index: usize, dir: usize, width: usize, height: usize) -> Option<usize> {
    neighbor_index(index, dir, width, height)
}

fn canonical_path_sha(path: &[usize], width: usize) -> String {
    fn digest_path<'a, I: Iterator<Item = &'a usize>>(iter: I, width: usize) -> String {
        let mut hasher = Sha256::new();
        for index in iter {
            let (x, y) = idx_xy(*index, width);
            hasher.update(x.to_le_bytes());
            hasher.update(y.to_le_bytes());
        }
        hex::encode(hasher.finalize())
    }
    let forward = digest_path(path.iter(), width);
    let reverse = digest_path(path.iter().rev(), width);
    if forward <= reverse { forward } else { reverse }
}

fn chord(a: &GraphCenter, b: &GraphCenter) -> f64 {
    let dx = a.x as f64 - b.x as f64;
    let dy = a.y as f64 - b.y as f64;
    (dx * dx + dy * dy).sqrt()
}

fn trace_graph_edges(
    observation: &Observation,
    width: usize,
    height: usize,
    adjacency: &[u8],
    owner: &[u32],
    centers: &[GraphCenter],
) -> (Vec<Value>, u64, u64, u64) {
    let mut visited = vec![0u8; adjacency.len()];
    let mut edges = Vec::<Value>::new();
    let mut resolved = 0u64;
    let mut unresolved = 0u64;
    let mut self_loops = 0u64;

    fn mark(visited: &mut [u8], a: usize, dir: usize, b: usize) {
        visited[a] |= 1u8 << dir;
        visited[b] |= 1u8 << inverse_dir(dir);
    }

    for (center_index, center) in centers.iter().enumerate() {
        let source_owner = center_index as u32 + 1;
        for &start_pixel in &center.pixels {
            if owner[start_pixel] != source_owner { continue; }
            for dir in 0..8usize {
                if adjacency[start_pixel] & (1u8 << dir) == 0 || visited[start_pixel] & (1u8 << dir) != 0 {
                    continue;
                }
                let Some(next_pixel) = edge_neighbor(start_pixel, dir, width, height) else { continue; };
                if owner[next_pixel] == source_owner {
                    mark(&mut visited, start_pixel, dir, next_pixel);
                    continue;
                }

                let mut prev = start_pixel;
                let mut cur = next_pixel;
                let mut directions = vec![dir];
                let mut path = vec![start_pixel, next_pixel];
                mark(&mut visited, start_pixel, dir, next_pixel);
                let mut target_owner = 0u32;
                let mut failed = false;
                let mut guard = 0usize;

                loop {
                    guard += 1;
                    if guard > adjacency.len() + 8 {
                        failed = true;
                        break;
                    }
                    let current_owner = owner[cur];
                    if current_owner != 0 {
                        if current_owner == source_owner {
                            if path.len() > 2 {
                                target_owner = current_owner;
                                break;
                            }
                        } else {
                            target_owner = current_owner;
                            break;
                        }
                    }

                    let mut candidates = Vec::<(usize, usize)>::new();
                    for nd in 0..8usize {
                        if adjacency[cur] & (1u8 << nd) == 0 {
                            continue;
                        }
                        let Some(candidate) = edge_neighbor(cur, nd, width, height) else { continue; };
                        if candidate == prev {
                            continue;
                        }
                        candidates.push((candidate, nd));
                    }
                    if candidates.len() != 1 {
                        failed = true;
                        break;
                    }
                    let (candidate, nd) = candidates[0];
                    if visited[cur] & (1u8 << nd) != 0 {
                        failed = true;
                        break;
                    }
                    mark(&mut visited, cur, nd, candidate);
                    prev = cur;
                    cur = candidate;
                    path.push(candidate);
                    directions.push(nd);
                }

                if failed || target_owner == 0 {
                    unresolved += 1;
                    continue;
                }
                let target_index = target_owner as usize - 1;
                if target_index >= centers.len() {
                    unresolved += 1;
                    continue;
                }
                let target = &centers[target_index];
                if target_owner == source_owner {
                    self_loops += 1;
                }
                let mut turns = 0u64;
                for pair in directions.windows(2) {
                    if pair[0] != pair[1] {
                        turns += 1;
                    }
                }
                let path_steps = directions.len() as u64;
                let chord_pixels = chord(center, target);
                let tortuosity = path_steps as f64 / chord_pixels.max(1.0);
                let turn_rate = turns as f64 / (path_steps.saturating_sub(1).max(1) as f64);
                let path_sha = canonical_path_sha(&path, width);
                let (a, b) = if center.event_id <= target.event_id {
                    (center.event_id.clone(), target.event_id.clone())
                } else {
                    (target.event_id.clone(), center.event_id.clone())
                };
                let edge_id = format!(
                    "G{}",
                    &sha256_hex(
                        format!(
                            "{}|{}|EDGE|{}|{}|{}",
                            observation.source_group_id, observation.id, a, b, path_sha
                        )
                        .as_bytes()
                    )[..20]
                );
                edges.push(json!({
                    "edgeId": edge_id,
                    "a": a,
                    "b": b,
                    "pathSha256": path_sha,
                    "pathSteps": path_steps,
                    "chordPixels": chord_pixels,
                    "tortuosity": tortuosity,
                    "turnCount": turns,
                    "turnRate": turn_rate,
                    "selfLoop": target_owner == source_owner
                }));
                resolved += 1;
            }
        }
    }

    edges.sort_by(|a, b| {
        let aa = a.get("edgeId").and_then(Value::as_str).unwrap_or("");
        let bb = b.get("edgeId").and_then(Value::as_str).unwrap_or("");
        aa.cmp(bb)
    });
    (edges, resolved, unresolved, self_loops)
}

fn project_observation(image: &GrayImage, observation: &Observation, tile_size: u32, overlap: u32) -> Result<Value> {
    validate_region(image, observation.region, &observation.id)?;
    let threshold = resolved_threshold(image, observation)?;
    let width = observation.region.width as usize;
    let height = observation.region.height as usize;
    let mut adjacency = vec![0u8; width * height];
    let mut owner = vec![0u32; width * height];
    let mut centers = Vec::<GraphCenter>::new();
    let mut owner_conflicts = 0u64;

    for (tile_index, tile) in tiles(observation.region, tile_size, overlap).into_iter().enumerate() {
        let mask = tile_mask(image, observation.region, tile, threshold);
        let tw = tile.ext_w as usize;
        let th = tile.ext_h as usize;
        let skeleton = thin(&mask, tw, th);
        let (labels, clusters) = critical_clusters(&skeleton, tw, th);
        let arms = trace_center_arms(&skeleton, &labels, &clusters, tw, th);

        let core_left = (tile.core_x - tile.ext_x) as usize;
        let core_top = (tile.core_y - tile.ext_y) as usize;
        let core_right = core_left + tile.core_w as usize;
        let core_bottom = core_top + tile.core_h as usize;

        for y in core_top..core_bottom {
            for x in core_left..core_right {
                let local = y * tw + x;
                if skeleton[local] == 0 { continue; }
                let rel_x = tile.ext_x + x as u32;
                let rel_y = tile.ext_y + y as u32;
                let global = global_index(rel_x, rel_y, width);
                for d in 0..8usize {
                    let Some(local_neighbor) = neighbor_index(local, d, tw, th) else { continue; };
                    if skeleton[local_neighbor] == 0 { continue; }
                    let nx = local_neighbor % tw;
                    let ny = local_neighbor / tw;
                    let nrel_x = tile.ext_x + nx as u32;
                    let nrel_y = tile.ext_y + ny as u32;
                    if nrel_x >= observation.region.width || nrel_y >= observation.region.height { continue; }
                    let nglobal = global_index(nrel_x, nrel_y, width);
                    adjacency[global] |= 1u8 << d;
                    adjacency[nglobal] |= 1u8 << inverse_dir(d);
                }
            }
        }

        for cluster in clusters {
            if !point_in_core(&cluster, tile) { continue; }
            let gx = observation.region.x + tile.ext_x + cluster.cx.round() as u32;
            let gy = observation.region.y + tile.ext_y + cluster.cy.round() as u32;
            let event_id = format!(
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
            let center_owner = centers.len() as u32 + 1;
            let mut pixels = Vec::<usize>::new();
            for local in cluster.pixels {
                let lx = local % tw;
                let ly = local / tw;
                let rel_x = tile.ext_x + lx as u32;
                let rel_y = tile.ext_y + ly as u32;
                if rel_x >= observation.region.width || rel_y >= observation.region.height { continue; }
                let global = global_index(rel_x, rel_y, width);
                if owner[global] == 0 || owner[global] == center_owner {
                    owner[global] = center_owner;
                    pixels.push(global);
                } else {
                    owner_conflicts += 1;
                    owner[global] = 0;
                }
            }
            pixels.sort_unstable();
            pixels.dedup();
            centers.push(GraphCenter {
                event_id,
                kind: cluster.kind,
                x: gx,
                y: gy,
                degree: center_arms.len(),
                arm_histogram: center_arm_histogram(&center_arms),
                tile_index,
                pixels,
            });
        }
    }

    let (edges, resolved_paths, unresolved_paths, self_loops) = trace_graph_edges(
        observation,
        width,
        height,
        &adjacency,
        &owner,
        &centers,
    );

    let center_rows: Vec<Value> = centers.iter().map(|center| json!({
        "eventId": center.event_id.clone(),
        "kind": center.kind,
        "x": center.x,
        "y": center.y,
        "degree": center.degree,
        "armHistogram": center.arm_histogram.clone(),
        "tileIndex": center.tile_index
    })).collect();

    let center_identity_sha256 = sha256_hex(&serde_json::to_vec(&center_rows)?);
    let trace_total = resolved_paths + unresolved_paths;
    let resolution_fraction = if trace_total == 0 { 1.0 } else { resolved_paths as f64 / trace_total as f64 };

    Ok(json!({
        "schema": "mark_critical_edge_graph_observation_v5",
        "observationId": observation.id,
        "sourceGroupId": observation.source_group_id,
        "lane": observation.lane,
        "region": {"x": observation.region.x, "y": observation.region.y, "width": observation.region.width, "height": observation.region.height},
        "threshold": threshold,
        "centerCount": centers.len(),
        "centerIdentitySha256": center_identity_sha256,
        "ownerConflicts": owner_conflicts,
        "resolvedPaths": resolved_paths,
        "unresolvedPaths": unresolved_paths,
        "traceResolutionFraction": resolution_fraction,
        "selfLoops": self_loops,
        "centers": center_rows,
        "edges": edges
    }))
}

fn main() -> Result<()> {
    let args: Vec<String> = std::env::args().collect();
    let input_path = PathBuf::from(parse_edge_arg(&args, "--input", None)?);
    let out_dir = PathBuf::from(parse_edge_arg(&args, "--out", Some("artifacts/mark-critical-edge-world-v5"))?);
    let tile_size: u32 = parse_edge_arg(&args, "--tile", Some("512"))?.parse()?;
    let overlap: u32 = parse_edge_arg(&args, "--overlap", Some("32"))?.parse()?;
    if tile_size < 64 || overlap * 2 >= tile_size {
        bail!("tile must be >=64 and overlap must be less than half the tile size");
    }
    fs::create_dir_all(&out_dir)?;
    let bytes = fs::read(&input_path)?;
    let input: BlindInput = serde_json::from_slice(&bytes)?;
    if input.schema != "mark_observable_input_blind_v1" || input.blind_input_sha256.len() != 64 {
        bail!("unsupported or unsealed blind input");
    }
    let source_by_id: EdgeHashMap<String, BlindSource> = input.sources.iter().cloned().map(|s| (s.source_group_id.clone(), s)).collect();
    let mut observations_by_source: EdgeHashMap<String, Vec<Observation>> = EdgeHashMap::new();
    for observation in input.observations.iter().cloned() {
        if !source_by_id.contains_key(&observation.source_group_id) {
            bail!("unknown source {}", observation.source_group_id);
        }
        observations_by_source.entry(observation.source_group_id.clone()).or_default().push(observation);
    }
    for rows in observations_by_source.values_mut() { rows.sort_by(|a,b| a.id.cmp(&b.id)); }
    let base_dir = input_path.parent().unwrap_or_else(|| Path::new("."));
    let output_path = out_dir.join("critical-edge-observations.jsonl");
    let mut writer = BufWriter::new(File::create(&output_path)?);
    let mut rows_hasher = Sha256::new();
    let mut observations = 0u64;
    let mut centers = 0u64;
    let mut edges = 0u64;
    let mut unresolved = 0u64;
    let mut resolved = 0u64;
    let mut conflicts = 0u64;
    let mut min_resolution = 1.0f64;
    let mut sources = input.sources.clone();
    sources.sort_by(|a,b| a.source_group_id.cmp(&b.source_group_id));

    for source in sources {
        let capture = base_dir.join(&source.capture_path);
        let image = image::open(&capture).with_context(|| format!("decode {}", capture.display()))?.to_luma8();
        for observation in observations_by_source.get(&source.source_group_id).map(Vec::as_slice).unwrap_or(&[]) {
            if observation.lane != source.lane { bail!("lane mismatch for {}", observation.id); }
            let row = project_observation(&image, observation, tile_size, overlap)?;
            let mut line = serde_json::to_vec(&row)?;
            line.push(b'\n');
            writer.write_all(&line)?;
            rows_hasher.update(&line);
            observations += 1;
            centers += row["centerCount"].as_u64().unwrap_or(0);
            edges += row["edges"].as_array().map(|x| x.len() as u64).unwrap_or(0);
            unresolved += row["unresolvedPaths"].as_u64().unwrap_or(0);
            resolved += row["resolvedPaths"].as_u64().unwrap_or(0);
            conflicts += row["ownerConflicts"].as_u64().unwrap_or(0);
            min_resolution = min_resolution.min(row["traceResolutionFraction"].as_f64().unwrap_or(0.0));
        }
    }
    writer.flush()?;
    let rows_sha256 = hex::encode(rows_hasher.finalize());
    let total_traces = resolved + unresolved;
    let summary = json!({
        "schema": "mark_critical_edge_projector_summary_v5",
        "sourceBlindInputSha256": input.blind_input_sha256,
        "observations": observations,
        "centers": centers,
        "edges": edges,
        "resolvedPaths": resolved,
        "unresolvedPaths": unresolved,
        "traceResolutionFraction": if total_traces == 0 {1.0} else {resolved as f64 / total_traces as f64},
        "minimumObservationTraceResolutionFraction": min_resolution,
        "ownerConflicts": conflicts,
        "rowsSha256": rows_sha256,
        "tileSize": tile_size,
        "overlap": overlap,
        "contract": {
            "sourcePixelsConsumed": true,
            "semanticLabelsConsumed": false,
            "stateVocabularyConsumed": false,
            "transitionGrammarConsumed": false,
            "provenanceConsumed": false,
            "criticalCentersUseExactCompilerIdentity": true,
            "pixelAdjacencyStitchedAcrossCompilerCoreBoundaries": true,
            "parallelPathsPreserved": true,
            "pathGeometryHashed": true
        }
    });
    fs::write(out_dir.join("summary.json"), serde_json::to_vec_pretty(&summary)?)?;
    println!("{}", serde_json::to_string_pretty(&summary)?);
    Ok(())
}
