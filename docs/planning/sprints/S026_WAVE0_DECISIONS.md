# Sprint 026 — Wave 0 Decisions

Binding decisions for Research Hot-Path Performance. Date: 2026-07-17.

Inspection basis: Signal / Market Research vs Strategy Research vs Robustness code paths and
`docs/reference/RESEARCH_METHODOLOGIES.md` methodology boundaries.

---

## D-S026-01 — Problem statement

Strategy Research on NQ half-year (~177k 1m bars) is ~6 s after columnar OHLCV + shared Polars
evaluation + Numba kernel.

Signal / Market Research and Robustness are **not** slow because of a different model-evaluation
engine. They share `evaluate_models`. They are slow because of post-evaluation Python work
(Signal) and N× full strategy pipelines without shared inputs (Robustness).

---

## D-S026-02 — Signal / Market Research root cause (CRITICAL)

`resolve_reference_price` rebuilds:

```python
{timestamp: index for index, timestamp in enumerate(frame.timestamps)}
```

on **every** occurrence / observation. Combined with `iter_rows` materialization and per-horizon
Python forward-outcome windows, cost scales approximately as:

```text
O(occurrences × bars) + O(occurrences × horizons × window)
```

**Decision:** amortize timestamp indexing once per run; vectorize reference-price resolution and
forward outcomes. Methodology (occurrences → forward outcomes → persist → analyze) is unchanged.

---

## D-S026-03 — Robustness root cause (HIGH)

Robustness kinds call `run_strategy_research` per grid cell / fold / non-post-process stress
scenario. Resume only skips identical completed fingerprints. There is no reuse of OHLCV load or
`evaluate_models` when only exit / risk / simulation assumptions change.

**Decision:** keep “repeated Strategy Research runs” as the methodology. Add an optional shared
evaluation context so unchanged market/signal evaluation is not repeated. Do not replace
robustness with a different research question.

---

## D-S026-04 — Correctness gate

Performance changes must not silently alter research facts:

- Signal outcomes: same schema; fixture equivalence required.
- Robustness child run fingerprints: still reflect variant-specific inputs.
- No schema migration unless separately justified and versioned.

---

## D-S026-05 — Priority vs Phase 8A polish

Sprints 024–025 (dry-run reliability / visualization polish) remain valid Phase 8A work.

**Decision:** Sprint 026 is the **next recommended active research-track sprint**. Phase 8A polish
may proceed in parallel only if it does not starve Wave A (Signal hot path).

---

## D-S026-06 — Out of scope for Wave 0 / MVP

- Distributed or multi-process robustness execution
- Changing Monte Carlo to resimulate bars
- Automatic parameter optimization
- Rewriting HTML analytics pipelines
- Family-run MA cache (follow-up unless Wave A measurements require it)

---

## Key files (pre-sprint)

| Area | Path |
|------|------|
| Reference price | `src/trading_framework/strategy/reference_price.py` |
| Occurrences | `src/trading_framework/strategy/signal_occurrence.py` |
| Market observations | `src/trading_framework/research/observations/market_model_observation.py` |
| Forward outcomes | `src/trading_framework/research/outcomes/calculator.py` |
| Shared eval | `src/trading_framework/application/model_evaluation/evaluate_models.py` |
| Strategy fast path | `src/trading_framework/application/strategy_research/run_strategy_research.py` |
| Robustness batch | `src/trading_framework/application/robustness_research/run_robustness_experiment.py` |
| Walk-forward | `src/trading_framework/application/robustness_research/run_walk_forward_experiment.py` |
| Stress | `src/trading_framework/application/robustness_research/run_stress_experiment.py` |
