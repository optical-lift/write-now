# START HERE — Mark V43 Song composition-rule harvest

You are continuing an already-governed Mark research program. Do not redesign it from memory.

## Working location

Repository: `optical-lift/write-now`  
Branch: `mark-song-composition-harvest-v43`

The branch was created from sealed main SHA:

`76f7eedbc5a6d154d3bfea3c5bea044317b703ae`

V43 preregistration commit:

`f60d7e9c5cabd54559b9ed5eb8208700d136754f`

## Read first

Read these four files completely before changing code:

1. `research/mark/discovery-experiments/song-composition-harvest-v43.preregistration.md`
2. `research/mark/discovery-experiments/song-composition-harvest-v43.protocol.json`
3. `research/mark/discovery-experiments/song-composition-harvest-v43.candidate-template.json`
4. `research/mark/discovery-experiments/song-composition-harvest-v43.result-template.md`

## Your job

Run **Phase A** of V43.

The deliverable is 5–10 serious, physically grounded candidate **composition rules**, not glyph meanings.

Examples of search dimensions already preregistered:

- enclosure/boundary;
- adjacency/connectivity;
- direction/reorientation;
- junction/port/arity;
- repetition/count;
- nesting;
- split/join topology edit;
- sequential operator composition;
- symmetry/reversal;
- endpoint/open-closed structure.

For each candidate attempt:

- positive witnesses;
- near-counterexamples;
- ablation or natural ablation;
- surface-invariance control;
- matched/null control;
- source/corpus holdout if available;
- downstream consequence preservation if applicable;
- exact physical provenance.

Use neutral IDs such as `CR-001`. Do not assign Song meanings during Phase A.

## Important prior work

Do not restart the Mark architecture.

Main already contains the physical custody/discovery pipeline, sparse compiler infrastructure, local-state/state-transition work, physical-glyph experiments, and the later V38–V42 research line.

The older branch `mark-operator-composition-algebra-v9` is particularly relevant as a **reference**, because it tested anonymous two-port operators and sequential composition. Reuse its ideas/code only narrowly and explicitly; do not merge that branch wholesale.

V42's negative result remains negative and is not to be reinterpreted.

## First action

Audit the current main scripts and frozen experiment artifacts to determine which preregistered candidate dimensions are already measurable with existing data.

Then implement the **smallest** V43 runner needed to harvest candidates from the existing corpus.

Before looking at V43 outcomes:

1. commit the runner;
2. record the exact input artifacts/corpus lanes;
3. freeze seeds/null generation/candidate construction;
4. record the implementation SHA.

Only then execute Phase A.

## Phase-A closure

When complete, commit:

- `song-composition-harvest-v43.phase-a.candidates.json`
- `song-composition-harvest-v43.phase-a.result.md`
- `song-composition-harvest-v43.phase-a.freeze.md`

Do not open or use Song compiler semantics before that freeze exists.

## After Phase A only

Then switch to `optical-lift/song-ontology` and read:

- `compiler/excavation/MARK_V43_HANDOFF.md`
- `compiler/RECONSTRUCTION_CRITERIA_V0.1.md`
- `compiler/COVERAGE_V0.1.md`

That begins Phase B.

## Hard constraints

Do not:

- touch Atlas, Noel, or production systems;
- modify prior V1–V42 artifacts;
- add Song primitives;
- translate glyphs;
- hide failed candidates;
- force a candidate into a known category;
- acquire new sources before exhausting the existing corpus for the first V43 harvest.

A clean failed rule is useful evidence. Preserve it.
