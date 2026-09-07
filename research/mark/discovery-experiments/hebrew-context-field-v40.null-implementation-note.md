# V40 context-destruction null implementation note

**Date:** 2026-09-07  
**Timing:** written after real C0–C3 and unseen-subset Phase-A scores were opened, but **before any V40 context-destruction null outcome was computed**.

The preregistration says to replace the four-token right context with the four-token right context "beginning at" offset 11–30 tokens later, otherwise use the corresponding negative offset. The exact four-token indexing was not written algebraically.

For reproducibility, the frozen implementation is:

- null `k=1..20` uses `d=10+k`.
- preferred mismatched right context is tokens `[CENTER+d, CENTER+d+1, CENTER+d+2, CENTER+d+3]`.
- it is used only when all four tokens are in the center's same book, five-chapter block, and V40 split side.
- otherwise the fallback mismatched right context is `[CENTER-d, CENTER-d+1, CENTER-d+2, CENTER-d+3]`, again requiring all four to be in the same book/block/split side.
- the real left context `[-4,-3,-2,-1]` remains unchanged.
- the center target remains unchanged and center consonants remain excluded from input features.
- all right-side summaries, cross-side same-skeleton count, and boundary bridge are recomputed from the mismatched right context.
- the already frozen V40 training quintile cutpoints and Naive Bayes parameters are reused without refitting.
- if neither positive nor negative mismatched four-token context is available, that center is excluded for that null and the null's N is reported.

No Masoretic witness data is involved.