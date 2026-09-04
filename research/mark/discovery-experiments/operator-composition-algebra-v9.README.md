# Mark operator composition algebra v9

This experiment implements the semantic correction that a glyph is **not assumed to be a container of labels**.

The tested object is consequence. A directed graph interface is treated as an anonymous state. A transit through a critical center is treated as an anonymous two-port operator. The operator fingerprint deliberately omits the incoming and outgoing edge-state values, so the operator cannot contain the answer it is asked to predict.

For an observed simple path `u-v-w-x`:

- `A` is the operation at `v` from the `u` port to the `w` port;
- `B` is the operation at `w` from the `v` port to the `x` port;
- `s0`, `s1`, `s2` are the three directed boundary-interface states.

Cleveland learns one-step kernels `K_A` and freezes them. Bavaria then asks whether the consequence of `A` followed by `B` is predicted by ordinary composition:

`K_AB = K_A K_B`.

The experiment also freezes candidate idempotent, cancelling, order-sensitive, and input-conditional laws in Cleveland and tests those exact candidates in Bavaria without reselection.

A positive result is evidence for machine-readable **operational structure**, not a translation. A failure of simple composition is also informative: it means the state representation is missing context or the system is genuinely higher-order.
