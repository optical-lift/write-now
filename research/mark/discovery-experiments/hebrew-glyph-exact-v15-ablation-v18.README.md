# Exact V15 Ablation v18

V18 corrects V17's diagnostic mistake: V17 changed the fitting/gating machinery while trying to discover which V16 feature control broke V15.

V18 keeps V15's training thresholds, backoff, operator cap, mutual-nearest matching, support-stratified permutation null, and evaluation gates exact. The only changes are the named stress controls.

Boundary removal and segment restriction are paired with deterministic event-count-matched V15 shams. If both a structural control and its sham lose feasibility, the result is classified as support-thinning confounding rather than evidence that the removed structure carried the correspondence.

Seen/new collapse, proper-name exclusion, and frequency matching change no event count and are tested directly.

The exact V15 baseline must reproduce before any localization claim is allowed.
