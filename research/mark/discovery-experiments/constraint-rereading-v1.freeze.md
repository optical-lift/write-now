# Mark Constraint Re-Reading v1 — Freeze

Status: **FROZEN**
Date: **2026-09-18**
Branch: `mark-constraint-rereading-v1`
Parent harvest freeze: `48a952fa39f686aefcc6a41f2b8d2f144aa759e8`

## Freeze boundary

This checkpoint closes the Mark-only constraint re-reading.

The next checkpoint may take eligible anonymized constraint signatures to the canon, but it must not rewrite these Mark constraints after seeing canon results.

## Pre-freeze branch head

`bc03591ee41d5a790c326aa7382d63f4f0be68ab`

## Frozen artifacts

| Artifact | Git blob SHA |
|---|---|
| `constraint-rereading-v1.schema.json` | `8956ce57ffb95162a7c2a3734658c89c6b7716a3` |
| `constraint-rereading-v1.spec.md` | `f0c1a024595437b6b7fd8c56037d2719c1e56df8` |
| `constraint-rereading-v1.part1.jsonl` | `931a93b587f456abed9189e238511a9a17d295aa` |
| `constraint-rereading-v1.part2.jsonl` | `bc2a1d4655fa177bd6152559b65c08385f111d77` |
| `constraint-rereading-v1.part3.jsonl` | `e6191f00341ff9909fdbdf933dc3b6c895a4519c` |
| `constraint-rereading-v1.part4.jsonl` | `cb4162601baf8a1aae2f6b39ab37c096cfb5c85a` |
| `constraint-rereading-v1.manifest.json` | `1a2ff92334256629e79ad9bdf91191129cd7f2cd` |
| `constraint-rereading-v1.assessment.md` | `ab6945a19386acfc80f562b5d55f0c244542b7ee` |
| `scripts/validate-mark-constraint-rereading-v1.py` | `c02bfb205663f9b3e6dcb3f71e75a712ab94d18e` |
| `WHOLE_SYSTEM_RECONSTRUCTION_ROADMAP.md` | `4c3f9c651d6c0a7311582d3c548a25dff18b55a5` |

## Inventory

- Source corpus: **84 canonical active RLOP packets**, `RLOP-007..RLOP-090`
- Constraint projections: **84**, `MCR-007..MCR-090`
- Eligible observed-system law candidates: **28**
- Supporting-only representation/cross-system constraints: **51**
- Deferred/underidentified: **3**
- Ineligible calibration/measurement-only: **2**

## Scientific result of the re-reading

The strongest defensible Mark-only synthesis is:

> **Consequence is relationally conditioned. It is not fully determined by isolated state, isolated object identity, unordered constituents, or a fixed finite label vocabulary. Changing relevant order, placement, topology, history, operator identity, or composition can change or constrain consequence while other properties remain fixed.**

The re-reading also establishes that the word **constraint** must not be used indiscriminately.

A failed classifier is not automatically a law of reality.

Only observed-system constraints are eligible for future law adjudication.

## Direct high-leverage demonstrations

The frozen manifest identifies:

- `MCR-007` — order cannot be discarded while preserving consequence/path information;
- `MCR-016` — feature inventory cannot replace actual relational placement;
- `MCR-021` — supported repetition cannot materially alter the one-step consequence kernel;
- `MCR-022` — supported ordered pairs constrain the composite state back toward the incoming state;
- `MCR-029` — a local relational condition reproducibly suppresses a candidate consequence;
- `MCR-034` — local-state organization cannot be independent of spatial placement;
- `MCR-059` — incoming state alone cannot determine consequence when operator identity is changed;
- `MCR-083` — recurrence cannot survive destruction of spatial topology while identity/statistics are preserved.

These are not declared to be the same law.

## Validation

The exact committed constraint set was reread before freeze.

Validation passed:

- 84 records;
- IDs continuous and unique from `MCR-007` through `MCR-090`;
- exactly 28 eligible candidates;
- every eligible candidate is an `observed_system` constraint;
- every projection preserves an evidence ceiling;
- no cross-source matching was performed;
- no canon matching was performed;
- no universal-law labels were assigned.

## Next checkpoint

**Canon Constraint Adjudication.**

The canon lane should receive anonymized eligible Mark constraint signatures without Mark nouns, experiment names, glyph labels, proposed biblical labels, or candidate matches.

For each signature, the canon lane should ask:

> What rule does the canon itself state or demonstrate that explains this condition/consequence constraint, if any?

The canon result must be independently frozen before comparison back to Mark.

