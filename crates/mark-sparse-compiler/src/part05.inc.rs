impl StatsStore {
    fn commit_source(&mut self, source: &SourceGrammar) -> Result<u64> {
        let transaction = self.connection.transaction()?;
        let mut contexts = BTreeMap::<(i32, String, String), ()>::new();

        {
            let mut grammar = transaction.prepare(
                "INSERT INTO grammar_stats(iteration,lane,context,outcome,count,source_count)
                 VALUES(?1,?2,?3,?4,?5,1)
                 ON CONFLICT(iteration,lane,context,outcome) DO UPDATE SET
                   count = grammar_stats.count + excluded.count,
                   source_count = grammar_stats.source_count + 1",
            )?;
            for ((iteration, lane, context, outcome), count) in source {
                let count_i64 = i64::try_from(*count).map_err(|_| {
                    anyhow!(
                        "grammar count exceeds SQLite exact integer range for {iteration}/{lane}/{context}/{outcome}"
                    )
                })?;
                grammar.execute(params![iteration, lane, context, outcome, count_i64])?;
                contexts.insert((*iteration, lane.clone(), context.clone()), ());
            }
        }

        {
            let mut context = transaction.prepare(
                "INSERT INTO context_stats(iteration,lane,context,source_count)
                 VALUES(?1,?2,?3,1)
                 ON CONFLICT(iteration,lane,context) DO UPDATE SET
                   source_count = context_stats.source_count + 1",
            )?;
            for ((iteration, lane, context_key), _) in contexts {
                context.execute(params![iteration, lane, context_key])?;
            }
        }

        transaction.commit()?;
        Ok(source.len() as u64)
    }

    fn build_rules(&mut self, out_dir: &Path, min_sources: usize) -> Result<u64> {
        self.connection.execute("DELETE FROM rules", [])?;
        self.connection.execute(
            "INSERT INTO rules(context,outcome,distinct_sources,total_count,context_sources)
             SELECT context,outcome,source_count,count,context_sources
             FROM (
               SELECT
                 g.context AS context,
                 g.outcome AS outcome,
                 g.source_count AS source_count,
                 g.count AS count,
                 c.source_count AS context_sources,
                 ROW_NUMBER() OVER (
                   PARTITION BY g.context
                   ORDER BY g.source_count DESC, g.count DESC, g.outcome ASC
                 ) AS rank
               FROM grammar_stats g
               JOIN context_stats c
                 ON c.iteration=g.iteration AND c.lane=g.lane AND c.context=g.context
               WHERE g.iteration=-1 AND g.lane='train' AND c.source_count>=?1
             ) ranked
             WHERE rank=1",
            params![i64::try_from(min_sources)?],
        )?;

        let mut writer = BufWriter::new(File::create(out_dir.join("rules.jsonl"))?);
        let mut statement = self.connection.prepare(
            "SELECT context,outcome,distinct_sources,total_count,context_sources
             FROM rules ORDER BY context",
        )?;
        let mut rows = statement.query([])?;
        let mut count = 0u64;
        while let Some(row) = rows.next()? {
            let context: String = row.get(0)?;
            let outcome: String = row.get(1)?;
            let distinct_sources: i64 = row.get(2)?;
            let total_count: i64 = row.get(3)?;
            let context_sources: i64 = row.get(4)?;
            serde_json::to_writer(
                &mut writer,
                &json!({
                    "schema":"mark_sparse_rule_v1",
                    "context":context,
                    "predictedOutcome":outcome,
                    "distinctSourceObjects":distinct_sources,
                    "contextSourceObjects":context_sources,
                    "supportCount":total_count.to_string()
                }),
            )?;
            writer.write_all(b"\n")?;
            count += 1;
        }
        writer.flush()?;
        Ok(count)
    }

    fn score_for(&self, lane: &str, iteration: i32) -> Result<Score> {
        let mut statement = self.connection.prepare(
            "SELECT g.count,g.outcome,r.outcome
             FROM grammar_stats g
             LEFT JOIN rules r ON r.context=g.context
             WHERE g.lane=?1 AND g.iteration=?2",
        )?;
        let mut rows = statement.query(params![lane, iteration])?;
        let mut score = Score::default();
        while let Some(row) = rows.next()? {
            let count: i64 = row.get(0)?;
            if count < 0 {
                bail!("negative grammar count in sufficient-statistics database");
            }
            let count = count as u128;
            let actual: String = row.get(1)?;
            let predicted: Option<String> = row.get(2)?;
            score.examples += count;
            if let Some(predicted) = predicted {
                score.covered += count;
                if predicted == actual {
                    score.correct += count;
                }
            }
        }
        Ok(score)
    }

    fn evaluation(&self, null_iterations: usize, rule_count: u64) -> Result<Value> {
        let lane_summary = |lane: &str| -> Result<Value> {
            let observed = self.score_for(lane, -1)?;
            let mut null_accuracy = Vec::with_capacity(null_iterations);
            let mut null_coverage = Vec::with_capacity(null_iterations);
            for iteration in 0..null_iterations {
                let score = self.score_for(lane, iteration as i32)?;
                null_accuracy.push(ratio(score.correct, score.covered));
                null_coverage.push(ratio(score.covered, score.examples));
            }
            let mean_accuracy = mean(&null_accuracy);
            let mean_coverage = mean(&null_coverage);
            Ok(json!({
                "examples":observed.examples.to_string(),
                "covered":observed.covered.to_string(),
                "correct":observed.correct.to_string(),
                "coverage":ratio(observed.covered,observed.examples),
                "accuracy":ratio(observed.correct,observed.covered),
                "nullMeanCoverage":mean_coverage,
                "nullMeanAccuracy":mean_accuracy,
                "accuracyLift":ratio(observed.correct,observed.covered)-mean_accuracy,
                "nullIterations":null_iterations
            }))
        };

        Ok(json!({
            "schema":"mark_sparse_transfer_evaluation_v1",
            "rules":rule_count,
            "holdout":lane_summary("holdout")?,
            "control":lane_summary("control")?,
            "nullContract":"within each observation, arm tokens are deterministically permuted only among centers with identical center kind and degree; center inventory, degree sequence, arm-token inventory, lane, source and observation remain fixed"
        }))
    }

    fn storage_counts(&self) -> Result<(u64, u64)> {
        let grammar: i64 = self
            .connection
            .query_row("SELECT COUNT(*) FROM grammar_stats", [], |row| row.get(0))?;
        let contexts: i64 = self
            .connection
            .query_row("SELECT COUNT(*) FROM context_stats", [], |row| row.get(0))?;
        Ok((grammar as u64, contexts as u64))
    }
}

fn ratio(n: u128, d: u128) -> f64 {
    if d == 0 {
        0.0
    } else {
        n as f64 / d as f64
    }
}

fn mean(values: &[f64]) -> f64 {
    if values.is_empty() {
        0.0
    } else {
        values.iter().sum::<f64>() / values.len() as f64
    }
}

fn parse_arg(args: &[String], name: &str, default: Option<&str>) -> Result<String> {
    if let Some(pos) = args.iter().position(|a| a == name) {
        return args
            .get(pos + 1)
            .cloned()
            .ok_or_else(|| anyhow!("missing value for {name}"));
    }
    default
        .map(str::to_owned)
        .ok_or_else(|| anyhow!("required argument {name}"))
}
