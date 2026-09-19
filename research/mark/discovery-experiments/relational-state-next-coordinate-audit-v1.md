# Relational-State Next-Coordinate Audit v1

Status: **FROZEN WHILE COMPONENT-PLACEMENT HOLDOUT IS STILL UNREAD**  
Date: **2026-09-19**

## Purpose

The component-placement train result has already met its preregistered insufficiency condition: 67 testable degree + masked-placement + arm cells remain MIXED.

Before the current holdout result is read, this audit asks:

> If the placement coordinate remains partial, which already-frozen relational variable should be tested next?

The answer is not an arbitrary new feature. The repository already contains a blind, three-lane result showing that **directed containment state and short relational history have lawful structure**.

## Frozen prior instrument

State Transition Grammar v1:

- successful run: `33773740050`
- frozen artifact: `mark-state-transition-grammar-v1-frozen`
- artifact ID: `9900704251`
- artifact ZIP SHA-256: `2707b04a81fd244ec6ff4d85b90b7e8ccf3cd9363dd2091a998e28bc5ab5089f`
- discovery SHA-256: `979d097dcdfc8df8007f6c3b4ef7d1b16950c56cb2287a46ff77b480cd2635d8`

The experiment used:

- 19,526 eligible observations;
- 18,817 directed containment edges;
- 15,017 length-three containment chains;
- direction defined only as smallest strictly larger containing observation -> contained observation;
- provenance unavailable during discovery;
- a null that preserved source, lane, geometry, proposal scale, region-area stratum and the state multiset while shuffling frozen state labels.

## Already-established directional structure

### Persistence is strongly enriched

The strongest transition edge is:

- `2 -> 2`
- standardized deviation: **+22.08**
- observed beyond all nulls;
- same enrichment direction in train, holdout and control.

`3 -> 3` is also strongly enriched:

- standardized deviation: **+21.02**
- observed beyond all nulls;
- same enrichment direction in all three lanes.

`1 -> 1` is likewise enriched beyond all nulls and in the same direction across all lanes.

### Some cross-state transitions are strongly suppressed

`3 -> 1`:

- standardized deviation: **-20.57**
- observed below all nulls;
- same suppression direction in train, holdout and control.

The state system therefore does not behave as a freely interchangeable set of labels inside the containment hierarchy.

### Short relational history adds structure beyond one edge

Top frozen length-three programs include:

- `2 -> 3 -> 3`: enriched, standardized deviation **+18.41**, same direction across all lanes;
- `2 -> 2 -> 2`: enriched, standardized deviation **+17.22**, same direction across all lanes;
- `2 -> 1 -> 1`: enriched, standardized deviation **+14.45**, same direction across all lanes;
- `2 -> 3 -> 1`: suppressed, standardized deviation **-13.07**, same direction across all lanes;
- `2 -> 3 -> 2`: suppressed, standardized deviation **-12.88**, same direction across all lanes.

The frozen summary reports:

- commitment-to-return ratio: **34.90**
- null commitment-to-return ratio: **5.11**

This is consistent with directional state commitment inside the containment hierarchy rather than unordered co-occurrence.

## Consequence for the current relational-state program

The next coordinate after static masked placement should therefore be tested as:

```
current component state
+ degree
+ structural placement
+ containing-parent state
+ directed parent -> child relation
(+ short prior relational state when support permits)
        ↓
consequence
```

This is more principled than adding arbitrary geometry or source-level features because the parent/child state relation already has an independent blind transfer record.

## Directional interpretation

The prior result supports the stronger working model:

> **Relational role is not only spatial. It is stateful and directional inside a hierarchy.**

A component may occupy the same coarse geometric slot and have the same intrinsic degree while still be in a different relational state because:

- its containing parent is in a different frozen state;
- it lies on a different parent -> child transition;
- its recent containment-state history differs.

Those are candidate state coordinates, not merely descriptive metadata.

## Boundary

This audit does not claim that parent state or history explains the current placement-law contradictions.

That join has not yet been performed.

It establishes only that, if the current placement coordinate remains insufficient after held-out transfer, **directed containment state/history is the next evidence-backed relational coordinate to test**.

No component-placement holdout or control outcome was used to select this direction.
