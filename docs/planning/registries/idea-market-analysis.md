# Market Analysis — idea entries

Return to the [Idea Inbox index](../IDEA_INBOX.md).

# 6. Market Analysis

<a id="idea-010"></a>
## IDEA-010 — Component Scaffolding CLI

```text
Status: INBOX
Category: Developer Experience
Added: 2026-06-19
```

### Summary

Generate a local working component structure with:

- component file,
- tests,
- manifest,
- notes,
- example configuration.

### Potential Value

Encourages consistent local component development.

### Promotion Criteria

The component contract and local directory pattern are stable.

---

<a id="idea-011"></a>
## IDEA-011 — Automatic Candidate Promotion Report

```text
Status: INBOX
Category: Governance / Market Analysis
Added: 2026-06-19
```

### Summary

Evaluate whether a local component meets candidate or framework-promotion criteria.

Possible checks:

- tests,
- documentation,
- strategy independence,
- stable output schema,
- dependency declaration,
- proprietary thresholds,
- compatibility readiness.

### Important Rule

The tool may recommend promotion.

It must never promote automatically.

---

<a id="idea-012"></a>
## IDEA-012 — Order-Flow Component Pack

```text
Status: DEFERRED
Category: Market Analysis
Added: 2026-06-19
```

### Summary

Add reusable components for:

- volume delta,
- imbalance,
- footprint structures,
- absorption,
- DOM-derived states.

### Dependencies

- tick/trade/quote data models,
- high-volume storage,
- order-flow dataset contracts.

### Promotion Criteria

Market Data support for required source facts is stable.

---

<a id="idea-013"></a>
## IDEA-013 — Options-Derived Context Components

```text
Status: DEFERRED
Category: Market Analysis
Added: 2026-06-19
```

### Summary

Support Features and States derived from:

- gamma exposure,
- zero gamma,
- options positioning,
- implied volatility structures.

### Dependencies

- OptionsSnapshot model,
- provider data,
- timestamp and availability semantics.

---

<a id="idea-014"></a>
## IDEA-014 — Machine-Learned State Classifiers

```text
Status: GATED (ADR-0024 accepted, Sprint 044) — promotion not yet approved
Category: Market Analysis / ML
Added: 2026-06-19
Updated: 2026-08-28
```

### Summary

Allow trained statistical or ML models to produce Market Analysis States.

### Main Questions

- training artifact identity,
- data leakage,
- feature lineage,
- offline/online parity,
- model registry.

### Promotion Criteria

Rule-based Market Analysis and Research infrastructure are mature.

### Status Note (2026-08-28) — gate outcome

`ADR-0024` (`docs/adr/ADR-0024-machine-learned-state-promotion.md`) is **ACCEPTED**. It answers all
five questions above with testable conditions rather than principles, expanded into entry criteria
and a parity-test design sketch in `docs/archive/phases/phase-10-predictive-research/S044_GATE.md`:

1. **Training artifact identity** — a fingerprint over dataset, spec, seed and library versions,
   already computed as `run_fingerprint`, must be recorded in the `Lineage` of every State a
   promoted model produces. Durable serialization (replacing today's opaque `joblib` blobs, TD-022)
   is priced as a promotion sprint's first cost, not chosen here.
2. **Data leakage** — training-time leakage is already solved (purge/embargo, Sprint 039).
   Inference-time feature availability must be enforced by the component contract (the same
   `available_at` executor validation rule-based components already get), not by convention.
3. **Feature lineage** — already solved by Sprint 039's `OutputRef`-declared features; no new
   mechanism needed.
4. **Offline/online parity** — the hard condition. Batch research and the dry-run runtime must
   produce identical State values for identical inputs, which requires the fitted preprocessing
   transform to ship as part of the promoted artifact. A parity test on recorded data is the
   minimum, non-negotiable acceptance bar.
5. **Model registry** — deliberately not required. Promotion needs only a content-addressed
   artifact store (the layout Predictive Research already uses); TD-021 (no registry product)
   is restated, not repaid.

Strong out-of-sample metrics alone are explicitly **not sufficient** for promotion — a promoted
model becomes a Market Analysis input, so downstream strategies must still pass Phase 7 robustness
validation.

**This idea is still not approved for implementation.** The gate is now written and accepted; a
future promotion sprint that satisfies all five conditions would be the next step, and is not
scheduled by default (`docs/planning/ROADMAP.md` §13A, Phase 10 closure).

---
