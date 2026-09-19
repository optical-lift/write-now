# Canon Constraint Adjudication v1

Status: **canon-only inventory construction before blind matching**
Date: **2026-09-18**

## Independence protocol

1. The Mark constraint re-reading is already frozen.
2. Twenty-eight eligible Mark constraints were converted into anonymized `CCA-###` packets.
3. The Mark↔CCA mapping is stored separately in `canon-constraint-adjudication-v1.sealed-map.json` and must remain unopened during canon adjudication.
4. Before matching CCA packets, build and freeze a canon-only rule inventory from Noel's existing evidence.
5. Match only after the canon inventory is frozen.
6. Freeze canon adjudications.
7. Only then open the sealed map and compare back to Mark.

This is procedural blinding, not true cognitive blinding: the same research system created the packets. The separation is designed to prevent explicit label leakage and post-hoc editing, not to claim independent human raters.

## Canon rule admission

A canon rule may enter the inventory only if Noel already contains direct or promoted evidence for the condition/consequence relation.

Each rule must preserve:

- canon-defined condition;
- actor/participant jurisdiction if relevant;
- relation or placement if relevant;
- allowed/prohibited operation;
- consequence or state transition;
- reverse-inference guard / interpretation ceiling;
- source reference and Noel record reference.

Do not invent a rule from general theology.

## Adjudication outcomes

For each anonymous CCA packet, return exactly one:

- **direct** — canon already states/demonstrates substantially the same constraint structure;
- **partial** — canon has a related constraint but one or more required dimensions are missing/different;
- **ambiguous** — multiple canon rules fit at the current abstraction and evidence cannot choose;
- **no_match** — current Noel evidence does not establish a sufficiently corresponding rule.

A direct match is **not yet proof of universal law identity**. It means Mark and canon independently expose compatible constraint structure under the frozen criteria.

## Matching criteria

Surface nouns and visible actions do not count.

Compare:

- what part of the condition must be present;
- what cannot be omitted or substituted;
- whether relation/placement/jurisdiction matters;
- whether prior history matters;
- whether order matters;
- whether operation availability changes with condition;
- whether consequence is invariant, reversible, restorative or exclusionary;
- whether a state/action is prohibited under one configuration but permitted under another.

