# V36 Result — Glyph Path → Hidden Hebrew Operator Path

**Status:** frozen result  
**Date:** 2026-09-06  
**Protocol:** `glyph-hidden-operator-path-v36.protocol.json`  
**Preregistration:** `glyph-hidden-operator-path-v36.preregistration.md`

## Frozen holdout

The V36 holdout was selected before outcome inspection by excluding the V35-P holdout books and taking the four lowest `md5('v36-holdout|' || canonical_book_code)` values among the remaining books:

- Deuteronomy
- Judges
- Psalms
- Job

The primary analysis retained tokens carrying exactly one qualifying Masoretic mark and required three consecutive canonical tokens, each with one retained mark. Hidden operator identity was `lemma_raw × morph`.

Training support gates were frozen at:

- operator type ≥20 training occurrences;
- exact three-operator candidate path ≥5 training occurrences.

The resulting corpus contained:

- 140,771 eligible training three-mark paths;
- 25,654 eligible held-out three-mark paths before support filtering;
- 400 supported candidate operator paths after the ≥5 path gate;
- 145 held-out path occurrences whose true operator path was present in the strict candidate inventory and deterministic sample.

## Primary combined physical-form result

The primary representation used the frozen V35-P combined topology/geometry/symmetry cluster assignment and no operator-frequency prior in the structural score.

Among the 145 supported held-out occurrences:

| Endpoint | Combined physical form | Frequency baseline |
|---|---:|---:|
| top-1 | 0.0% | 0.0% |
| top-5 | 4.14% | 0.69% |
| top-10 | 6.21% | 9.66% |
| top-50 | 46.21% | 37.24% |
| median rank | 62 | 108 |

### Reading

The primary result is **broad ranking enrichment, not exact path decoding**.

Physical form moves the true operator path substantially upward in the candidate space overall, as seen in the median rank and top-50 enrichment, but it does not produce strong exact top-k recovery. The top-10 cutoff is worse than the frequency baseline even while the median rank is much better.

This mixed pattern rejects a simplistic claim that the current physical-form representation directly specifies the exact three-operator Hebrew path.

## Glyph-order control

The strongest V36 result is order sensitivity.

Across all 145 supported held-out paths:

| Glyph-path condition | Median true-path rank | top-10 |
|---|---:|---:|
| real order | 62 | 6.21% |
| reversed order | 142 | 2.76% |
| deterministic shuffle | 117 | 1.38% |

Book-level results where strict-support sample size was meaningful:

### Deuteronomy, n=94

- real median rank: 64; top-10: 6.38%
- reversed median rank: 122.5; top-10: 3.19%
- shuffled median rank: 108; top-10: 2.13%

### Judges, n=43

- real median rank: 40; top-10: 6.98%
- reversed median rank: 230; top-10: 0%
- shuffled median rank: 138; top-10: 0%

Psalms (n=7) and Job (n=1) were too sparse under the strict support gate for independent interpretation.

### Reading

The real glyph sequence contains information that is not invariant to order. Reversing or shuffling the same visible glyphs substantially degrades recovery of the true hidden Hebrew operator path.

This is evidence for **sequence-sensitive structural information**, not merely unordered mark co-occurrence.

It does not establish causation or prove that the glyph sequence is historically upstream of the Hebrew.

## Morphology versus lemma decomposition

Using the same combined physical-form score and candidate inventory:

| Hidden path level | top-1 | top-5 | top-10 | median rank |
|---|---:|---:|---:|---:|
| morphology path | 0.0% | 6.21% | 10.34% | 46 |
| lemma path | 1.38% | 6.21% | 7.59% | 60 |

### Reading

Morphological path recovery is better overall than lemma-path recovery by median rank and top-10 rate, broadly consistent with the preregistered expectation that structural/morphological information should be easier to recover than lexical identity.

The hierarchy is not perfectly monotonic at every cutoff: lemma has a small top-1 tail while morphology has none. The result therefore should not be described as a clean lexical-decoding ladder.

## Exact mark identity control

The preregistered exact-mark-identity emission model was substantially stronger than the coarse combined physical-form representation:

| Endpoint | Exact mark identity | Combined physical form |
|---|---:|---:|
| top-1 | 2.07% | 0.0% |
| top-5 | 8.97% | 4.14% |
| top-10 | 20.69% | 6.21% |
| top-50 | 61.38% | 46.21% |
| median rank | 41 | 62 |

### Reading

This result weakens the strongest current version of the geometry-as-code claim.

The current topology/geometry/symmetry compression does not preserve all of the predictive information carried by exact anonymous mark identity. Therefore V36 does **not** justify saying that the present physical-form feature system is itself the complete operative code-bearing layer.

At the same time, the combined physical representation still carries non-random operator-path information and, most importantly, order-sensitive information. The result is therefore not an identity-only null for physical form.

## Comparison with preregistered expectations

The preregistration predicted:

1. strong transition/morphology recovery;
2. smaller but real enrichment toward joint lexical-morphological operator identity;
3. low absolute exact-path top-1 recovery;
4. real glyph order outperforming reversed or scrambled order;
5. physical-form representation performing at least as well as, and potentially better than, exact mark identity.

Observed:

- **Supported:** exact-path top-1 is low.
- **Supported:** physical form enriches the true joint operator path broadly above frequency ranking by median rank and top-50.
- **Supported:** morphology is easier overall than lemma recovery.
- **Strongly supported:** real glyph order outperforms reversed and shuffled order.
- **Not supported:** coarse physical-form representation does not outperform exact mark identity; exact identity is substantially stronger.

## Frozen conclusion

> A three-mark Masoretic glyph sequence carries reproducible information about which hidden Hebrew lexical-morphological operator path occupies the same location, and that information is strongly sequence-order dependent. The current coarse topology/geometry/symmetry representation captures part of this signal but loses substantial predictive information relative to exact anonymous mark identity. V36 therefore supports an order-sensitive glyph/operator relationship while rejecting the stronger claim that the present physical-form compression is already an adequate description of the full code-bearing variable.

## Epistemic ceiling

V36 does not establish:

- that glyphs generate Hebrew;
- that glyphs are historically upstream of Hebrew;
- that a glyph sequence can reconstruct Hebrew surface text;
- that exact mark identity is itself the fundamental variable rather than a proxy for finer physical or relational features not yet measured;
- that normalized Masoretic Unicode forms reproduce physical manuscript behavior;
- that the result has yet survived physical-witness replication.

The fact that exact identity outperforms coarse form leaves at least two live explanations:

1. conventional mark identity contains relevant information not reducible to the current physical descriptors;
2. the current physical descriptors are too coarse and exact identity is indirectly preserving finer physical/relational structure that has not yet been decomposed.

The next experiment should distinguish those explanations rather than assuming either one.
