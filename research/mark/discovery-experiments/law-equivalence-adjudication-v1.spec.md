# Law-Equivalence Adjudication Language v1

Status: **instrument construction — freeze before application**
Date: **2026-09-18**
Parent freeze: `7983c6c8a80dac267a3556a862beb2e1ea5866c0`

## Purpose

This instrument answers a stricter question than the earlier canon constraint match:

> When do two independently recovered constraint structures count as **the same law** rather than merely similar, related, specialized, compositional, or analogous?

The instrument follows the clarified project premise:

> **Law identity lives in the complete relevant relational dependency, not in the substrate nouns, visible objects, visible operation names, or number of physical steps used to express it.**

A genuinely different relevant condition means a different law.

A different physical realization of the same relational condition/consequence dependency does **not** mean a different law.

## Primitive form

A candidate law is represented as:

```text
RELEVANT CONDITION
    +
FORBIDDEN / NON-FREE JOINT POSSIBILITY
    +
CONSEQUENCE-ORDER RELATION
    +
PRESERVED INVARIANTS
```

The word `forbidden` is structural, not automatically moral, legal, deterministic, or absolute.

For statistical evidence it may mean only:

> the candidate consequence cannot be treated as independent/free at the frozen null rate.

The evidence modality must remain visible.

## Surface vs law layer

The following are **surface realization** unless evidence shows they are themselves relevant conditions:

- object names;
- species/material;
- glyph/token identity;
- language;
- culture;
- visual shape;
- domain-specific action verbs;
- number of physical steps;
- distance measured in a substrate-specific unit;
- narrative or document boundaries.

The following can be **law-relevant** when evidence establishes them:

- participant-role relation;
- attachment/membership/containment/custody relation;
- placement;
- jurisdiction/authorization;
- prior state/history;
- ordering relation;
- boundary condition;
- timing relation;
- preserved identity;
- prohibited coexistence;
- required absence/presence;
- consequence ordering;
- reversibility/invariance.

No category above is automatically relevant. Relevance must be evidenced.

## Complete relevant condition

A law identity comparison must use the **smallest currently evidenced sufficient relational condition**, not every descriptive fact in the source.

Two surface conditions may look completely different and still normalize to the same law if they instantiate the same role/relation structure.

Example:

```text
surface A: branch remains attached to vine -> bearing possible
surface B: member remains placed in body -> function available
```

These are not declared equivalent merely because both involve membership.

They become candidates for the same law only if the evidenced relational condition and consequence structure normalize to the same dependency.

Conversely, if one case requires an additional genuinely necessary condition—jurisdiction, timing, prior history, boundary state, etc.—then it is a **different law**, even if the visible transformation is identical.

This implements the user's “same transformation under 11 different relevant conditions = 11 different laws” rule.

## Law signature

Each candidate law is normalized into six layers.

### 1. Roles

Anonymous participant variables:

`P1, P2, P3...`

A role is structural, not semantic.

Examples:

- active participant;
- containing/supporting whole;
- target;
- governing boundary;
- prior-state carrier.

Role names remain provisional aids. Equivalence is evaluated by relation structure.

### 2. Required relational condition

A graph of required relations/predicates.

Each condition records:

- anonymous participants;
- relation predicate;
- polarity/presence;
- whether it is required;
- order/precedence if applicable;
- scope/boundary;
- evidence modality.

The relation vocabulary is expandable.

### 3. Constraint target

The joint possibility that cannot remain free under the condition.

Examples:

- consequence Y cannot be independent of participant identity;
- operation O cannot occur under state S;
- members cannot be treated as an unordered bag;
- connection state cannot change without participation consequence;
- current state cannot fully determine next state without history.

This is the core `cannot` relation.

### 4. Consequence-order structure

How consequence is ordered once the condition is satisfied or the constrained relation is changed.

Order is broader than clock time.

It may be:

- temporal;
- logical;
- spatial;
- jurisdictional;
- dependency;
- containment;
- generational;
- causal only where causality is actually evidenced.

**Order is treated as the physical/observable expression of consequence, not automatically as the deeper law itself.**

### 5. Preserved invariants

What remains the same while the law is expressed:

- participant identity;
- membership carrier;
- supporting whole;
- incoming state;
- source-defined jurisdiction;
- relation class;
- other evidenced invariant.

Invariants are essential for distinguishing “same law, different path” from genuinely different laws.

### 6. Realization path

The visible steps through which the law appears.

A realization path is **not part of law identity** unless the evidence establishes one or more intermediate steps as necessary relational conditions.

Therefore:

- one physical step and five physical steps may instantiate the same law;
- A→B and C may instantiate the same law;
- reversing the viewing direction may still be the same law;
- a composition becomes a different law only when the intermediate relational states are themselves necessary to the dependency.

## Evidence modality

Every law signature must preserve one of these modalities:

- `deterministic_observed`
- `explicit_prohibition`
- `explicit_requirement`
- `statistical_exclusion`
- `statistical_dependency`
- `structural_invariance`
- `structural_dependency`
- `legal_or_jurisdictional_constraint`
- `unknown`

Two signatures with different modalities may share a dependency pattern, but they cannot be called the same law unless the evidence supports normalization to the same modality-independent constraint.

Example:

A statistical suppression and an explicit legal prohibition are **not automatically the same law**.

## Equivalence classes

The adjudicator may return only one primary relation.

### SAME_LAW

Use only when there exists a bijective role mapping such that:

1. required relational conditions are isomorphic;
2. the same abstract joint possibility is constrained;
3. consequence-order structures are isomorphic;
4. preserved invariants correspond;
5. evidence does not reveal an additional necessary condition on either side.

Different nouns, substrates, visible outcomes, and path lengths are allowed.

### SAME_LAW_OPPOSITE_VIEW

Use when the two observations are the same ordered relation viewed from opposite participant/state directions.

Reversing the viewpoint must not change the underlying required condition or constraint.

This is not ordinary causal reversal.

### SAME_LAW_DIFFERENT_PATH

Use when input relational condition, constrained possibility, consequence-order structure, and invariants are the same, but the visible physical realization uses different numbers or kinds of intermediate steps.

The extra steps must be demonstrated to be realization detail rather than necessary conditions.

### DISTINCT_LAW_SHARED_PATTERN

Use when the cases share a dependency template but differ in at least one **relevant necessary condition**, constrained joint possibility, consequence-order relation, or invariant.

This is the default result for “specialization/generalization” when the specialized condition is genuinely required.

Do not collapse it into SAME_LAW merely because one can be described as a special case of the other.

### COMPOSED_RELATION

Use when the consequence of one or more distinct laws forms an ordered path whose composite resembles another law, but the intermediate law states are themselves necessary.

The composite may later prove to be another realization of one law, but not without evidence that the intermediates are nonessential.

### ANALOGOUS_ONLY

Use when surface or thematic similarity exists but the normalized relational dependency is not isomorphic.

### UNDERDETERMINED

Use when current evidence is insufficient to know whether an apparent mismatch is a real condition difference or merely an unmeasured surface realization.

This is preferred over forced equivalence.

### CONTRADICTORY

Use when the candidate laws make incompatible constraint claims over a genuinely equivalent normalized condition.

## Equality test

Two candidate laws A and B are `SAME_LAW` only if a mapping `f` exists such that:

```text
Roles(A)                ≅ Roles(B)
RequiredCondition(A)    ≅ RequiredCondition(B)
ConstraintTarget(A)     ≅ ConstraintTarget(B)
ConsequenceOrder(A)     ≅ ConsequenceOrder(B)
Invariants(A)           ≅ Invariants(B)
```

and:

```text
NecessaryExtra(A) = ∅
NecessaryExtra(B) = ∅
```

after substrate-specific realization details are removed.

The symbol `≅` means structure-preserving correspondence, not same words.

## Dependency topology is decisive

If two cases use different physical nouns and visible consequences but normalize to the same complete dependency topology, they are **required to be adjudicated as the same law** unless a relevant condition difference is evidenced.

The analyst is not permitted to keep them separate merely because the domains look different.

Likewise, if two cases look almost identical physically but have different relevant conditions, they are required to remain different laws.

## Inverse-view rule

If:

```text
A: P1 relation R to P2 -> constrained consequence
B: P2 relation inverse(R) to P1 -> same constrained relation viewed from P2
```

then adjudicate `SAME_LAW_OPPOSITE_VIEW` when the relational graph is the same under role reversal.

Do not infer this merely because observed transformations point in opposite temporal directions.

## Path-independence rule

Suppose:

```text
Path A: X -> a -> b -> Y
Path B: X -> Y
```

They are `SAME_LAW_DIFFERENT_PATH` only if:

- X and Y normalize to the same law-relevant states;
- a and b are not separately required conditions;
- the same constrained possibility and invariants hold;
- removing a and b does not alter the law signature.

Otherwise use `COMPOSED_RELATION` or `DISTINCT_LAW_SHARED_PATTERN`.

## Strict condition rule

An additional condition is **relevant** only if evidence shows consequence changes when that condition changes while the rest of the normalized structure is adequately controlled.

Unmeasured descriptive detail is not automatically a new law.

This prevents both errors:

- collapsing 11 genuinely condition-different laws into one;
- exploding one law into thousands of substrate-specific descriptions.

## Canon/Mark custody

The law-equivalence language is symmetric.

Canon does not define the ontology for Mark.

Mark does not define the ontology for canon.

The comparison receives two already-frozen signatures and may only adjudicate their relation.

It may not rewrite either signature to improve the match.

## No universality claim

`SAME_LAW` means:

> the currently evidenced relational constraint structures are the same under the frozen equivalence language.

It does not by itself establish:

- metaphysical universality;
- divine origin;
- historical contact;
- common authorship;
- exhaustive law identity across all possible conditions.

Universality requires additional independent substrates and held-out prediction.

## Freeze-before-application rule

This language must be frozen before it is applied to the 28 existing Mark↔canon comparisons.

The earlier labels `direct`, `partial`, and `no_match` are not answers to the stricter law-identity question.

They are input evidence only.
