# Mark Conveyor Intake v3

Mark v3 turns the Universal Observable World Engine into a corpus-manufacturing system.

The governing rule is simple: **humans may choose where to harvest, but they do not choose the pieces that enter the world.** Source discovery and custody remain auditable; observable boundaries are proposed by Mark from anonymous captures.

## Conveyor

```text
institutional feed / source manifest
        ↓
exact-byte harvester + custody split
        ↓
anonymous source captures
        ↓
multiscale observable proposer
        ↓
whole objects + components + neighborhoods + fields
        ↓
blind structural measurement
        ↓
train-only world → frozen holdout prediction
        ↓
appendable blind measurement ledger
        ↓
rebuild entire accumulated blind world
        ↓
appendable contextual custody ledger (separate)
        ↓
post-freeze context rejoin
        ↓
surprise ranking
```

## What humans are allowed to decide

Humans may identify trustworthy repositories, record provenance, define rights/access constraints, and reject unusable captures for objective custody or quality reasons.

Humans do not select candidate glyphs, knots, symbols, or other supposedly interesting regions for the conveyor lane. A physical source enters as a capture. Mark proposes its own candidate observables.

Manual observation packets remain supported by v2 for controlled experiments, but they are not the preferred route for large discovery corpora.

## Harvest custody

`mark_harvest_manifest_v1` supports direct physical image assets and synthetic CI fixtures. A physical source must carry its public provenance in the contextual manifest, including institution, object identifier, source page, exact asset URL, and rights basis.

The harvester writes two products:

- `mark_harvested_sources_blind_v1`: opaque source handles, local capture bytes, salted capture token, and a keyed continuity token;
- `mark_harvest_custody_rejoin_v1`: exact capture SHA-256 plus the source metadata required to audit where the bytes came from.

The blind continuity token is HMAC-SHA256 over the exact capture hash using `MARK_CONTINUITY_KEY`. That lets separate harvest runs recognize the same physical bytes without publishing a directly look-up-able source hash into the blind world.

Physical runs fail closed if `MARK_CONTINUITY_KEY` is absent.

## Machine-proposed observables

The v3 `image_2d` proposer deliberately keeps multiple scales:

- `whole_capture` — complete source view;
- `connected_component` — local connected foreground body;
- `adjacent_component_neighborhood` — pairwise local field;
- `three_component_field` — larger local field.

These are technical proposal modes, not semantic classes. The world learner does not receive an object category.

The proposal system is intentionally extensible. Future proposers can add repeated-pattern windows, line/row structures, nested regions, graph-native structures, sequence units, 3D topology, knot graphs, or temporal configurations while emitting the same observable contract.

## Continuous blind ledger

Every measured source and machine-proposed observation receives a stable anonymous continuity identity derived from the private keyed source fingerprint. New runs can therefore be appended to `mark_observable_measurement_ledger_blind_v1`.

Repeated evidence is not allowed to manufacture recurrence. If the exact same stable observation reappears, the newest verified measurement replaces the earlier row rather than increasing its evidentiary weight.

The continuous world is rebuilt from the complete ledger. This is slower than an approximate online update but preserves an important property: every world snapshot is a deterministic interpretation of the full currently admitted blind field rather than an order-dependent sequence of local updates.

## Separate contextual ledger

The custody side accumulates independently as `mark_context_ledger_v1`. It is keyed by the same stable anonymous continuity IDs but contains source identity, institution, catalog records, rights basis, contextual categories, and the technical provenance needed for rejoin.

This ledger is never an input to world learning.

## Surprise engine

Only after a continuous blind world is sealed may context be rejoined. `mark_postfreeze_surprise_ranking_v1` then ranks candidates for human inspection.

The score rewards combinations of:

- structural recurrence;
- structural tightness;
- independent source count;
- number of prior contextual boxes crossed;
- institution diversity;
- proposal-scale diversity.

This is triage, not proof. A high surprise score means: **the blind machine repeatedly organized together things humans had filed apart, and the relationship is worth inspecting.** It does not decide whether the cause is inheritance, diffusion, convergence, motor constraint, cognitive economy, or another mechanism.

## Institutional feed direction

Direct asset manifests are the minimum universal adapter. The next harvesting adapters should enumerate assets from institutional collection feeds rather than require humans to list objects individually.

IIIF is the preferred first feed surface because its Presentation API exposes Collections, Manifests, Canvases, and image content in a repository-neutral structure, while the Image API provides standardized image retrieval. Provider-specific search adapters can sit before the same exact-byte custody boundary.

The feed adapter is allowed to know collection metadata while enumerating source objects. Once bytes cross the harvest boundary, categories are stripped exactly as in direct-source ingestion.

## Evidence rule

The conveyor is designed to reduce selection bias, not to erase provenance. Every admitted source must remain recoverable through custody after freeze.

A recurrence becomes interesting because it survives **despite** heterogeneous acquisition and contextual classification. It becomes evidence only through replication, prediction, source independence, and subsequent mechanism testing.
