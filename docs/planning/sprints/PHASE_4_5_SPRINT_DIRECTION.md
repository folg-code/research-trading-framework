# Phase 4–5 — Corrected Sprint Direction (post Sprint 004)

> **Planning doc** — binding direction for Sprints 005–010.  
> Task boards: individual `SPRINT_00N.md` files. Status snapshot: `CURRENT_STATUS.md`.

**Status:** ACCEPTED (2026-07-12)  
**Supersedes:** informal Sprint 005 preview in `SPRINT_004.md` § Sprint 006 Preview where they conflict.

---

## 1. Purpose

Order development after Sprint 004 (MTF foundation complete) toward the first real research workflow — not toward a full component catalog, dashboard, or model engine upfront.

```text
Sprint 004: multitimeframe foundation — DONE
Sprint 005: time context, first Structure, visual inspection
Sprint 006: declarative Market Model and Signal Model
Sprint 007: minimal research-enabling component catalog (as needed)
Sprint 008: first Signal Research computation MVP
Sprint 009: Market Model and combined research scopes
Sprint 010: Signal Research analytics on stored datasets
```

**Core principle:**

```text
Do not build a full component catalog, production dashboard, or full model engine
before the first real research workflow works end-to-end.
```

**Target capability (shortest path):**

```text
Published data
  → Market Analysis results
  → Market Model / Signal Model
  → chart inspection
  → SignalOccurrence
  → forward returns, MFE, MAE
  → persistent research dataset
```

---

## 2. Cross-cutting rules (Sprints 005–010)

### Polars-first batch I/O

```text
Prefer Polars Series / DataFrame / LazyFrame for batch mapping and research outputs.
Avoid per-row Python object lists for events and outcomes.
```

### Event vs state outputs

| Kind | Examples | Projection |
|------|----------|------------|
| Point events | pivot detection, SignalOccurrence | sparse; explicit projection policy on dense grid |
| Stateful | last HH/LL, Volatility State, Session Range in progress | `LAST_CLOSED_BAR` + backward join; forward fill intentional |

Do not apply one projection policy to all output types.

### Lookahead-free integration

Detectors may be lookahead-free while integration introduces bias if:

- results are written back to historical pivot rows,
- `pivot_at` is treated as `available_at`,
- HTF output is exposed before detection bar close,
- point events are interpreted as persistent state.

### Visualization as validation

Charts are **inspection tooling** for temporal, domain, alignment, and session correctness — not a production dashboard.

Visualization must **not** compute pivots, resample, align, or change `available_at`. It consumes finished results only.

First prototype location: `user_data/development/` or `user_data/notebooks/`.  
Future: thin `src/trading_framework/inspection/` selectors; layouts stay in `user_data/`.

### Outcome-based PRs

Each PR delivers a working capability (~100–400 lines). No PR-per-value-object fragmentation.

### Research before catalog expansion

Add components only when required for a concrete research question, not because they appear on a generic indicator list.

---

## 3. Sprint sequence summary

| Sprint | Goal | Key deliverable |
|--------|------|-----------------|
| **005** | Calendar + Pivot + first chart | CME ES RTH resolver, Pivot Structure (events + HH/HL/LH/LL state), local inspection chart |
| **006** | Declarative models | `ComponentOutputReference`, minimal `MarketFieldReference`, one-condition Market/Signal Model |
| **007** | Research-enabling catalog | slope, wick ratio, distance-to-level, Session Range, Trend State — **only if needed before 008** |
| **008** | Signal Research MVP | `SignalOccurrence` table, forward outcomes, persistent Parquet research dataset |
| **009** | Combined scopes | `MARKET_MODEL_ONLY`, `MARKET_AND_SIGNAL` |
| **010** | Analytics on stored runs | distributions, grouping, inspection charts without recompute |

**Minimum set before first Signal Research experiment:**

```text
Feature:  ATR or EMA
Structure: Pivot + HH/HL/LH/LL (from Pivot Structure outputs)
State:    Volatility State
Model:    one Signal Model
```

Sprint 007 may be trimmed or partially skipped if Sprint 005–006 outputs suffice for the first experiment.

---

## 4. Sprint 005 — highlights

Three outcomes (independently testable):

```text
A: CME ES RTH session resolution (batch TradingSessionResolver)
B: Pivot Structure (detection semantics + HH/HL/LH/LL state outputs)
C: Local visual inspection prototype
```

Calendar MVP fields: `trading_day`, `session_id`, `is_rth` — **not** full `is_market_open` / ETH semantics.

Pivot temporal semantics:

```text
pivot_at      — historical pivot bar (t - pivot_range)
detected_at   — confirmation bar index (output row)
available_at  — close of detection bar
```

Framework must **not** back-write pivot results onto `pivot_at` rows.

Point events vs stateful HH/HL/LH/LL: different MTF projection policies (see `SPRINT_005.md` § Pivot outputs).

Full task breakdown: `SPRINT_005.md`.

---

## 5. Sprint 006 — highlights

Declarative composition without Strategy/Exit/Risk:

```text
Operators: REFERENCE, COMPARE, AND, OR, NOT
Outputs: Polars tables (timestamp, available_at, model_id, model_result)
Signal Model: detected_at, direction, metadata
```

`MarketFieldReference` narrowly scoped — no arbitrary Polars expressions or repository access.

Visualization increment: model state overlay and signal markers.

Full outline: `SPRINT_006.md`.

---

## 6. Sprints 007–010 — highlights

**007:** Small catalog (Features/Structures/States) + Session Range consuming Sprint 005 session metadata. Liquidity Sweep deferred until levels + reclaim semantics exist.

**008:** `SIGNAL_MODEL_ONLY` pipeline → `SignalOccurrence` → forward return / MFE / MAE → immutable Parquet research dataset.

**009:** Market Model context evaluated at Signal `available_at` (MVP safety default).

**010:** Analytics on stored datasets; local HTML/Plotly/notebook — no web app.

Full outlines: `SPRINT_007.md` … `SPRINT_010.md`.

---

## 7. Explicit non-goals (until post-010)

```text
Production FastAPI/React dashboard
General chart DSL
Full TA catalog
Session-boundary resampling (until driven by use case)
Persistent derived market datasets (until research path proven)
TA-Lib optional extra (carry-forward)
Full TD-011 / TD-015 columnar migration
```

---

## 8. References

- Sprint 004 ADR: `docs/adr/ADR-MA-012-batch-multitimeframe-computation-with-polars.md`
- Architecture simplification: `docs/planning/retrospectives/ARCHITECTURE_SIMPLIFICATION_REVIEW_S002_S003.md`
- Vision: `docs/vision/ARCHITECTURE_FOUNDATIONS_UPDATED.md`, `docs/vision/MARKET_ANALYSIS_WITH_DECISIONS.md`
- Roadmap Phase 4–5: `docs/planning/ROADMAP.md` §8–9

---

## Revision History

| Date | Change |
|------|--------|
| 2026-07-12 | Initial corrected direction (post Sprint 004 merge); supersedes narrow Sprint 005 calendar-only plan |
