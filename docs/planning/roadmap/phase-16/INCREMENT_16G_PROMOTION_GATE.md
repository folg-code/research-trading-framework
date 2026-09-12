# Increment 16G — Promotion Candidate Gate (directional)

Detailed outcome and criteria from the accepted phase plan. Return to the [Phase 16 index](../PHASE_16_QUANT_WORKBENCH.md).

## 13H.7 — Increment 16G — Promotion Candidate Gate (directional)

### Purpose

Make promotion an explicit, evidenced act. Strong predictive metrics are never
sufficient on their own, and Sprint 049's artifact path is a mechanism, not an
approval.

**This increment is the planned closure route for `PRB-013`** (OPEN, HIGH) —
Research/Runtime parity is not yet measurable. The flow below already names an
"offline/online parity test" step; PRB-013 is the definition of what that step
means, and 16G cannot ship a defensible gate against an undefined parity bar.
Parity is therefore in 16G's scope, not adjacent to it.

**It is also `TD-029`'s owning increment** (§13H.12 Q6, Option B, resolved
2026-09-04): the tree/neural promoted-artifact serialization path that 16C was
explicitly kept clear of lands here, behind its own ADR, or is re-deferred
again by an explicit decision — never lifted implicitly.

### Expected capabilities (directional)

```text
positive research result
  -> analyst diagnostics (16A)
  -> robustness / stability review (Phase 7)
  -> explicit promotion candidate record
  -> offline/online parity test          <- PRB-013's formal suite
  -> optional Market Analysis State or strategy score component
  -> dry-run validation
```

- A promotion-candidate manifest listing required diagnostics, the parity
  checklist, and the human who accepted it.
- Dashboard visibility of candidates and their gate status.
- **A formal parity test suite** (`PRB-013`): canonical decision fixtures,
  the same component implementations exercised across batch backtest, replay
  and paper modes, and a comparison of `SignalOccurrences` and decisions
  between them.
- **`TD-029`'s repayment surface**: a version-pinned joblib/ONNX-style
  promotion path for tree and neural families, designed through its own ADR,
  reusing `infrastructure/ml/promotion.py::require_supported_model_family`'s
  guard ordering (family allow-list check, then version guard, before any
  unpickling) as its starting shape.

### Completion criteria (directional)

- **Nothing is promoted automatically.** No verdict, metric or leaderboard
  position causes promotion; a human act does.
- **`PRB-013`'s resolution criteria are met:**
  - a formal parity test suite exists and runs in CI under the synthetic-only,
    network-free constraint (ADR-0023 §8 untouched);
  - **accepted tolerances are declared numerically and versioned** — a
    tolerance changed after seeing a failure is a visible diff, on the same
    principle as 16A's verdict rule set. **The numbers themselves are NOT set
    by Phase 16's approval** (§13H.12 Q7, deferred by decision): they are a
    16G Wave 0 item requiring maintainer sign-off, once real parity-suite data
    exists to set them against;
  - unavoidable Research/Execution differences are documented as a named,
    finite list, not left as "may differ";
  - a promotion candidate that has not passed the suite cannot reach the
    accepted state — the gate reads the parity result, it does not re-derive
    or waive it.
- **`TD-029` is repaid here, or re-deferred here in writing.** Tree and
  deep-learning families stay gated at runtime until a durable serialization
  and parity story exists. Widening `MODEL_FAMILY_ALLOWLIST` requires an
  accepted ADR; **16G does not lift the deferral implicitly**, and no other
  increment may lift it at all.
- A model may be useful for research and dashboard scoring long before it is
  safe in execution, and the gate says so explicitly.

### Dependencies

- Phase 14 (Sprint 049's mechanism), Phase 7, 16A, 16D.
- **`PRB-013`** — co-requisite, resolved inside this increment. Its accepted
  tolerances are a Wave 0 decision for 16G's sprint and require maintainer
  sign-off (a tolerance is a risk acceptance, not an implementation detail).
- **`TD-029`** — inherited as this increment's scope (Q6 Option B). 16G is
  materially larger than it would have been under the rejected Option A
  ordering, and its sprint should expect at least two waves (parity suite;
  serialization ADR + allow-list widening) or an explicit split.

### Main risks

The gate becomes a rubber stamp; parity testing turns out to be the hard part
and is deferred into invisibility — which is exactly PRB-013's current state
and the reason it is written into completion criteria rather than listed as a
risk; tolerances set wide enough to pass whatever the first candidate does;
16G becoming a two-headed increment (parity + serialization) and needing to be
split — an expected consequence of Q6's Option B, to be handled at planning
time rather than absorbed silently.

### ADR

The candidate-manifest contract and its relationship to ADR-0024/ADR-0029 —
**ADR expected** (§13H.9 row 5). The tree/neural serialization decision is a
**separate** ADR (§13H.9 row 3), now owned by this increment. Parity
tolerances are recorded in the manifest ADR's consequences and in the suite
itself, not as a separate ADR.
