# V36 Preregistration — Glyph Path → Hidden Hebrew Operator Path

**Status:** preregistered before outcome inspection  
**Date:** 2026-09-06  
**Research line:** Mark / canon cross-modal structure  
**Predecessor:** V35-P glyph-form → Hebrew transition-direction proxy test  

## Purpose

This record freezes the reading of V35-P and the expected outcome of the next experiment before V36 is run.

The hypothesis under pressure is stronger than simple correspondence between Masoretic marks and Hebrew grammar. The working possibility is that computer-readable glyph form and glyph sequence carry operational information about the structural process realized in the Hebrew text.

V36 asks whether that information reaches far enough to constrain the **actual hidden lexical-morphological operator path**, not merely an abstract pre/post transition class.

---

## I. Frozen reading of V35-P

V35-P used canon-aligned Masoretic graphic marks as a Tier-0 proxy because the governed physical Mark corpus does not yet contain enough physical glyph instances linked to exact canonical Hebrew coordinates for the full physical-witness experiment.

Glyphs were represented without conventional names or meanings using computer-derived physical properties. Independent representations included:

- topology;
- geometry / orientation;
- symmetry;
- combined structural features.

The shape clusters were frozen before Hebrew outcomes were opened.

The fresh held-out books were:

- Isaiah;
- Hosea;
- 2 Chronicles;
- Ezekiel.

### 1. Full neighboring-morphology reconstruction was not the successful endpoint

When asked to predict the complete raw morphology of neighboring Hebrew tokens, none of the four shape representations beat the unconditional morphology model in mean held-out log score:

- topology: −0.129 nats;
- geometry: −0.123;
- symmetry: −0.115;
- combined: −0.127.

Exact anonymous mark identity was worse at approximately −0.212 nats.

This result is not read as “glyph form carries no Hebrew structural information.” It shows that the glyph representation used here does not uniquely specify the complete morphology of neighboring tokens.

The comparison between exact conventional mark identity and physical-form grouping is itself relevant: the physical abstractions generalized better than treating every mark identity as an unrelated category.

### 2. Real physical grouping retained more information than the completed arbitrary-group controls

For the symmetry representation, the real physical grouping scored approximately −0.115 nats on the harder raw-morphology endpoint, while two frequency-stratified scrambled groupings scored approximately:

- −0.148;
- −0.137.

These two controls are insufficient for a permutation significance claim, but the observed direction is consistent with physical grouping preserving non-random structural information.

### 3. Directional transition was the positive endpoint

When the question was changed from “which complete morphology belongs here?” to “which side of the local pre/post transition does this morphology belong on?”, all four independently defined physical representations added held-out directional information beyond the general asymmetry around marked tokens:

- topology: +0.0220 nats;
- geometry / orientation: +0.0355;
- symmetry: +0.0347;
- combined: +0.0366.

The symmetry result replicated without sign reversal in all four untouched books:

- 2 Chronicles: +0.0473;
- Ezekiel: +0.0279;
- Hosea: +0.0249;
- Isaiah: +0.0338.

### 4. Current interpretation

The strongest supported reading of V35-P is:

> Computer-readable graphical form carries information about the **directional organization of local Hebrew morphological transitions**. The evidence is more consistent with glyph form marking or encoding an operation / transition class than with glyph form acting as a complete label for the neighboring linguistic state.

The operational picture under consideration is therefore:

```text
        GLYPH FORM
            ↓
   transition / operation
            ↓
      STATE A → STATE B
```

rather than:

```text
GLYPH FORM → complete neighboring morphology
```

This is a positive cross-modal result at the proxy level, not a demonstration that glyphs generate Hebrew.

### 5. Epistemic limits that remain frozen

V35-P does **not** establish:

- causation;
- that glyphs are historically upstream of Hebrew;
- that glyphs generate lexical text;
- that normalized font proxies preserve all relevant physical properties of manuscript marks;
- that the directional effect has yet survived a full dependence-aware shuffled-form null;
- that physical manuscript glyphs linked to canonical text will reproduce the result.

Those limitations remain active regardless of the V36 outcome.

---

## II. V36 question

### Primary question

> If a short glyph sequence is left visible while the corresponding Hebrew operators are completely hidden, can the glyph sequence rank the true hidden Hebrew lexical-morphological operator path above legitimate alternatives?

The primary form is:

```text
VISIBLE GLYPH PATH
G1 → G2 → G3

        ↓

HIDDEN HEBREW PATH
[ O1 ] [ O2 ] [ O3 ]
```

where each Hebrew operator is the same joint object used in the preceding canon experiments:

```text
lexical identity × realized morphology
```

The primary condition must not expose the surrounding Hebrew morphology, lemma, surface text, translation, inherited syntactic label, or conventional glyph name/function.

The visible signal should be limited to the frozen computer-readable glyph representation and glyph order.

---

## III. Frozen expectation before V36

### Primary expected result

**I expect the real glyph path to contain enough information to rank the true hidden Hebrew operator path above frequency-only, book-conditioned, and shape-scrambled controls, but I do not expect high absolute exact-path top-1 recovery.**

The expected signal hierarchy is:

```text
strongest:
transition trajectory / direction
        ↓
realized morphology sequence
        ↓
joint lexical-morphological operator identity
        ↓
weakest:
exact lexical sequence / surface realization
```

In other words, the prediction is not that three glyphs will simply spell three Hebrew words.

The expectation is that the glyph path will constrain the **space of permissible Hebrew realizations**, with the strongest constraint appearing first in morphology and transition structure and a weaker but measurable enrichment reaching lexical identity.

### Expected exact-path behavior

I expect:

1. The true three-operator path will rank substantially above random chance.
2. The true path will beat a frequency-only operator-path baseline.
3. Exact top-1 recovery will remain relatively low because the candidate path space is large.
4. Top-k enrichment should be clearer than exact top-1 recovery.
5. Individual operator morphology should be recovered more reliably than individual operator lemma.
6. The correct joint operator path should nevertheless receive more probability/rank than would be explained by morphology frequency alone if the V35-P signal reaches into lexical realization.

### Expected order result

I expect glyph **order** to matter.

The real path:

```text
G1 → G2 → G3
```

should predict the true Hebrew operator trajectory better than:

```text
G3 → G2 → G1
```

or a within-path shuffle.

If order does not materially affect recovery, the stronger claim that glyph sequences behave like instruction sequences is weakened even if individual glyph shapes remain associated with local transition classes.

### Expected physical-form result

Based on V35-P, I expect computer-readable structural form to generalize at least as well as, and potentially better than, exact conventional mark identity.

If exact mark identity succeeds but topology / geometry / symmetry representations do not, the result would support a mark-identity association but would **not** support the stronger claim that physical form itself is the operative code-bearing level.

### Expected counterfactual result

When the real glyph path is replaced with a frequency-matched unrelated or shape-scrambled path, I expect recovery of the true Hebrew operator path to deteriorate.

When glyph order is reversed, I expect the predicted Hebrew transition trajectory to change rather than remain invariant.

The most important counterfactual is therefore not simply “accuracy falls,” but:

> changing the glyph program should systematically alter which Hebrew operator path the model prefers.

---

## IV. Required controls

At minimum, V36 should compare the real glyph path against:

1. no-glyph operator-path frequency baseline;
2. book-conditioned operator-path frequency baseline;
3. same glyphs in scrambled order;
4. same glyphs in reversed order where distinct from the original;
5. frequency-matched unrelated glyph paths;
6. shape-scrambled assignments preserving approximate glyph frequency;
7. exact mark identity versus computer-readable physical-form representation;
8. morphology-only recovery versus joint lexical-morphological operator recovery.

Where support permits, the analysis should distinguish:

- exact three-operator path rank;
- top-5 / top-10 / top-k path recovery;
- each individual operator rank;
- morphology recovery;
- lemma recovery;
- transition-trajectory recovery;
- path-order sensitivity.

Fresh held-out material must not be used to tune feature selection, smoothing, candidate thresholds, or scoring rules after the outcomes are opened.

---

## V. Outcomes that would change the hypothesis

### Outcome A — strong support

The strongest expected positive result would be:

> glyph form and order recover the actual hidden joint operator path above all frequency and shuffled-form controls, with order perturbation producing systematic changes in the preferred Hebrew path.

This would justify testing whether the glyph system constrains lexical realization rather than merely local morphology.

### Outcome B — structural-only support

If glyphs recover transition trajectory and morphology but provide no lexical advantage beyond morphology-conditioned frequency, the conclusion should be:

> the glyph system carries structural / grammatical operation information, but there is no evidence yet that it specifies lexical realization.

This is currently the **most likely** outcome.

### Outcome C — identity-only support

If exact conventional mark identity predicts hidden operators but physical-form representations do not, the conclusion should be:

> the mark inventory is associated with Hebrew structure, but V36 does not support the claim that geometry/topology itself is the code-bearing variable.

### Outcome D — null

If the real glyph path does not outperform frequency baselines and properly matched shuffled-form controls, the hypothesis that the V35-P directional signal scales into hidden-operator recovery is rejected at this level.

### Outcome E — unexpectedly strong lexical recovery

If glyph form alone substantially recovers exact lexical-morphological paths, especially across fresh whole-book holdouts and after morphology/frequency controls, that result should be treated as **unexpectedly stronger than the preregistered prediction** and subjected to additional leakage audits and fresh replication before interpretation.

---

## VI. Prediction stated plainly before the test

> **My prediction is that glyph paths will recover the hidden Hebrew structural trajectory and morphology above baseline, and will provide a smaller but real enrichment toward the correct joint lexical-morphological operator path. I expect exact three-operator lexical recovery to be substantially above chance but not high in absolute terms. I expect real glyph order to outperform reversed or scrambled order. I do not yet expect glyph form alone to reconstruct exact Hebrew surface text.**

The most likely scientifically useful result is therefore not “the glyphs spell the Hebrew,” but:

> **the glyph sequence constrains which Hebrew operator sequence can occupy the corresponding structural path.**

This expectation is frozen before V36 outcomes are inspected.

---

## VII. Preservation rule

If V36 requires any material change to the primary question, visible inputs, hidden targets, candidate inventory, holdout partition, or scoring endpoint after outcome inspection, that change must be recorded as a new protocol/version rather than silently editing this preregistration.

A null or contradictory result remains part of the research record.
