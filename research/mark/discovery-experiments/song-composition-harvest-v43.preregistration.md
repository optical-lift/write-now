# Mark V43 preregistration — Song composition-rule harvest

**Experiment ID:** `mark:song-composition-harvest:v43`  
**Status:** frozen before V43 outcome inspection  
**Base repository:** `optical-lift/write-now`  
**Base main SHA:** `76f7eedbc5a6d154d3bfea3c5bea044317b703ae`

## Purpose

V43 is not another test of whether Mark has structure and it is not an attempt to translate glyphs.

Its job is narrower:

> harvest a small set of physically grounded, machine-testable composition rules that can be handed to the Song compiler reconstruction track.

The unit of progress is a **composition rule**, not a glyph label, cluster, state name, or semantic gloss.

## Prior evidence boundary

V43 begins after the V42 witness-opening boundary on main. All earlier Mark experiments remain immutable evidence.

Prior positive or negative experiments may motivate candidate features, but V43 may not silently adopt their interpretations as truth.

Especially relevant prior work includes:

- blind physical/topological discovery and sparse compiler work;
- local state / state transition experiments;
- masked-slot, critical-center, edge, and local-wiring correspondence work;
- operator composition algebra v9, where ordinary composition of anonymous two-port operators transferred to Bavaria for selected laws;
- later fine-physical and Hebrew field experiments through V42, including negative results.

V43 does not reopen or rescore those experiments.

## Phase separation

### Phase A — blind composition harvest

Phase A may use only physical/structural observables, anonymous source/corpus lanes, and previously frozen machine outputs needed to derive those observables.

Phase A must not use:

- Song relation-family names;
- theological or historical meanings;
- translations;
- semantic glosses;
- named glyph meanings;
- a claim that a feature “means” containment, authority, source, etc.

Candidate rules receive neutral IDs `CR-001`, `CR-002`, ... and are described operationally.

### Phase B — Song rejoin

Only after the Phase-A candidate file, result, and freeze SHA are committed may Phase B read the Song compiler reconstruction files in `optical-lift/song-ontology`.

Phase B asks whether each frozen operational rule can be represented by the current Song IR/composition vocabulary. It may conclude:

- maps cleanly to existing Song structure;
- maps compositionally to several existing structures;
- remains unresolved;
- exposes a missing composition rule;
- appears surface-only/non-structural.

Phase B may not rewrite Phase A.

## Existing corpus first

V43 must begin with the existing Mark corpus and current main artifacts. No new source acquisition is required to obtain the first candidate set.

New acquisition is a later step only if the current corpus cannot produce discriminating contrast sets for a promising rule.

## Candidate feature families

The following are starting search dimensions, not presumed meanings:

1. enclosure / boundary relation;
2. adjacency / contact / connectivity;
3. orientation / direction / reorientation;
4. junction / branching / port / arity;
5. repetition / multiplicity / count;
6. nesting / depth / recursive embedding;
7. split / join / topology edit;
8. ordered sequential composition of local operators;
9. symmetry / mirror / reversal;
10. endpoint / terminal / open-vs-closed path structure.

The harvest is not required to return one rule per family. Strong evidence for fewer rules is preferable to weak coverage of all ten.

## Rule test contract

A V43 composition candidate is not merely an association. For each candidate, attempt all applicable tests:

### T1 — positive witnesses

Find repeated physical instances where the candidate feature occurs together with a stable anonymous structural consequence.

### T2 — near-counterexamples

Find physically similar instances lacking the candidate feature or differing in exactly the proposed dimension. Record whether the consequence changes.

### T3 — ablation

Remove, mask, break, reverse, or otherwise neutralize only the proposed feature while holding the rest of the observable structure as fixed as the data permits.

A structural feature earns support only when the predicted consequence changes or becomes unresolved in a reproducible way.

### T4 — invariance control

Change a surface property judged irrelevant to the candidate rule while preserving the proposed structural feature. The anonymous consequence should remain stable.

### T5 — matched/null control

Compare the observed candidate/consequence relation against matched alternatives or deterministic null worlds that preserve obvious nuisance structure.

### T6 — held-out transfer

Freeze the rule on an induction lane and test it on at least one source-separated or corpus-separated lane when the existing evidence permits this.

### T7 — downstream preservation

Where the rule is compositional, test whether applying it preserves the downstream anonymous consequences predicted by the frozen local/operator representation.

## Required evidence per candidate

Every candidate record must contain:

- neutral rule ID;
- exact physical feature definition;
- preconditions;
- proposed operational delta stated without semantic labels;
- positive witnesses with provenance;
- near-counterexamples with provenance;
- ablation result;
- invariance result;
- null/matched result;
- held-out result if available;
- downstream preservation result if applicable;
- known failure modes;
- residual unexplained features;
- status.

Allowed Phase-A statuses:

- `HARVESTED_RULE`
- `OPEN_RULE`
- `REJECTED_RULE`
- `SURFACE_ONLY`
- `INSUFFICIENT_CONTRAST`

## Minimum harvest target

V43 should attempt to return **5–10 serious candidate rules**.

A rule may be `HARVESTED_RULE` only when it has:

1. more than one independent physical witness;
2. at least one meaningful contrast or near-counterexample;
3. an ablation or natural-ablation result;
4. an invariance control;
5. provenance sufficient to return to the physical evidence;
6. no unresolved contradiction that directly defeats the claimed operational delta.

Held-out transfer strengthens the rule but is not mandatory when no valid independent lane exists; absence must be explicit.

## Priority rule for compiler handoff

The first rule sent to the Song compiler is selected by **evidence quality**, not by semantic importance or visual drama.

Prefer the candidate with the cleanest:

- contrast pair;
- ablation;
- invariance result;
- cross-source support;
- minimal confounding;
- deterministic operational delta.

## Broad-research stopping condition

After V43, broad Mark discovery should no longer be the default.

Later broad acquisition is justified only when compiler residuals or rule conflicts require it.

A practical saturation signal is reached when two genuinely fresh source additions produce new surface forms but no new structural distinction or composition failure. At that point Mark becomes primarily a targeted residual resolver for the Song compiler.

## Required V43 artifacts

Before Phase B:

- `song-composition-harvest-v43.phase-a.candidates.json`
- `song-composition-harvest-v43.phase-a.result.md`
- `song-composition-harvest-v43.phase-a.freeze.md`

After Phase B:

- `song-composition-harvest-v43.phase-b.song-handoff.json`
- `song-composition-harvest-v43.phase-b.result.md`

## Do not do

V43 must not:

- add Song primitives;
- declare historical meanings from geometry alone;
- merge old experimental branches wholesale;
- overwrite V1–V42 artifacts;
- force every candidate into an existing Song family;
- discard failed candidates;
- treat lack of current interpretation as failure;
- touch Atlas, Noel, or Write Now product runtime.

The desired output is an excavation packet for the compiler: a few rules we can attack mechanically, plus a clear pile of shards that still do not fit.
