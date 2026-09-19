# Cross-Source Overlap Graph v1 — Protocol Freeze

Status: **FROZEN BEFORE GRAPH ASSEMBLY**
Date: **2026-09-18**

Protocol commit:

`c876f188a1c8fc2141597ee26aa223679f9d942b`

Graph assembly may now use only:

- certified `BOOK-*` source nodes;
- frozen law nodes `EQC-001` and `EQC-002`;
- `PRESENT` cells as positive edges;
- unresolved cells as open metadata.

The graph may report descriptive overlap and connectivity only.

It may not infer implication, composition, causation, universality, or independent-replication counts from degree or co-presence.
