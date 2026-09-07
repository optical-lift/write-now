# V39 Witness-Opening Boundary

The V39 Hebrew-only Phase A representation and primary results are frozen.

**Boundary commit intent:** this file marks the point after which V39 may first query `draft.canon_masoretic_marks` as an external witness.

Before this boundary:
- V39 did not use Masoretic marks in feature construction, thresholds, context definitions, holdout selection, training, or Hebrew outcome interpretation.
- Phase A primary verdict is negative: H2, H3, and H4 all failed to improve H1 on held-out Hebrew prediction.
- No Phase-B result may retroactively modify the V39 Hebrew representation or Phase-A verdict.

The preceding Phase-A result is `research/mark/discovery-experiments/hebrew-relational-field-v39.phase-a.result.md` at commit `edb4138c5493d1a65266d6cab14b82497f192c9e`.
