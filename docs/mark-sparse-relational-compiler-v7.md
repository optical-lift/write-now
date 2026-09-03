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

## Live architecture gate — passed

The first v7 gate reran the exact live acquisition that repeatedly exhausted v6. It composed 96 source records and, after audited retrieval exclusions, retained 72 independent witnesses: 24 train, 24 holdout and 24 control. Those witnesses produced the same 2,497 machine-proposed blind observations.

Under a hard 512 MB virtual-memory ceiling, the release compiler completed all 2,497 observations in 1 minute 37.50 seconds with a measured maximum resident set size of **32,316 KB**. It processed 5,118 bounded tiles, emitted 1,601,035 anonymous centers and 1,651,131 append-only events, reduced 36,081,360 sharded grammar rows representing 8,034,004 observed pair-weight without materializing those pairs, and sealed the ledger with Merkle root `8b1b1588d74dcffd18032cbbf94e773e8f34ace45413d9f3b5b92d55eb483c48`.

The architecture assertion passed. This is a scalability result, not historical evidence.

The smoke discovered two recurrent training rules. Observed transfer accuracy exceeded the degree/kind-preserving null by only about 0.00188 in holdout and 0.00248 in control. Those tiny lifts are explicitly **not** treated as support for any historical hypothesis; the live run exists to prove the compiler can carry real heterogeneous physical evidence through the blind machinery without a memory model that collapses at world scale.

## Permanent CI contract

Pull-request CI uses the custody-safe synthetic fixture with a fixture-sized lane-retention minimum. Live heterogeneous acquisition is now explicit `workflow_dispatch` only and retains the 12-witness-per-lane minimum. Both routes compile through the same Rust binary and the same hard 512 MB memory gate.

The next scale gates are 10× and 100× before the genuinely heterogeneous world conveyor is treated as a scientific experiment.
