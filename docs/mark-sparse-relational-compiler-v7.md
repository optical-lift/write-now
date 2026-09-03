# Mark v7 — Sparse Relational Compiler

Mark v7 is the scalability break after the v6 relational-program experiment.

## Why v7 exists

v6 established useful scientific contracts—physical custody before interpretation, anonymous multiscale observations, sealed train/holdout/control lanes, relational rather than whole-object identity, masked transfer testing, audited nulls, and provenance reopening only after the blind world is frozen. Its live smoke also established an implementation failure: repeatedly materializing large raster-derived graphs and grammar paths in Node exhausted the hosted runner heap on 72 real witnesses / 2,497 machine-proposed observations.

v7 preserves the contracts and discards the in-memory world representation.

## Compiler contract

The Rust compiler receives `mark_observable_input_blind_v1` directly. It may see opaque source/observation IDs, local capture paths, sealed lanes, regions, segmentation settings, proposal scale/kind and custody hashes. It may not receive institution, culture, language, sign name, reading, meaning, chronology, geography, catalog identity or scholarly interpretation.

For each observation it computes the sealed threshold, scans bounded 512×512 core windows with overlap, thins only the active window, emits anonymous critical centers and continuation stubs, records arm multiplicities rather than materializing every two-arm pair, and discards the window before moving on.

Tile boundaries are computational, not scientific. Paths that leave a computation window are recorded as unresolved for custody and excluded from grammar. Cross-core skeleton edges receive deterministic continuation-stub keys so later passes can reconcile longer continuations without inventing tile-edge semantics.

## Disk-backed world

The compiler never creates a whole-page graph, whole-corpus graph, or whole-world JSON object. Blind structural evidence is appended to `events.jsonl`. The ledger is hashed every 4,096 lines and the chunk hashes are reduced to a Merkle root. Grammar evidence is written into 64 deterministic disk shards keyed by context. Reduction reads one shard at a time.

Masked grammar is computed from exact multiplicities. If a center has `a` arms of type A and `b` arms of type B, the A/B pair contributes `a × b`; identical-token pairs contribute `n choose 2`. No array of those pairs is ever created.

## Null

Within each observation and null iteration, arm tokens are deterministically permuted only among centers having the same center kind and degree. This preserves center inventory, center kind, degree sequence, arm-token inventory, source, observation and lane while breaking which arm tokens co-occur at a particular center.

## Acceptance gate

The first v7 gate is architectural, not historical. The exact live v6 smoke acquisition is rerun. After audited retrieval exclusions, the compiler must process the surviving blind corpus under a hard 512 MB virtual-memory ceiling. CI also records maximum resident set size and fails if it exceeds 512 MB.

Passing this gate does not authorize a historical interpretation. It only establishes that Mark can ingest real heterogeneous physical evidence without requiring memory proportional to a fully materialized relational world.

After the live gate passes, the one-shot `research/mark/live-v7-smoke.flag` is removed and ordinary PR CI returns to the custody-safe synthetic fixture. The next scale gates are 10× and 100× before the genuinely heterogeneous world conveyor is treated as a scientific experiment.
