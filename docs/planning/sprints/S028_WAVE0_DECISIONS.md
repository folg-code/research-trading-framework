# Sprint 028 — Wave 0 Decisions

Binding decisions for Dashboard Application MVP. Date: 2026-07-17.

Source brief: maintainer draft `# Sprint — Dashboard Application MVP.txt`
(Desktop). Inspection: existing HTML/Plotly reports (S014/S016/S017/S023) vs
proposed Streamlit consumer; research storage inventory under `user_data/research/`.

---

## D-S028-01 — Track choice (D1 = A)

**Decision:** Next active sprint is **Dashboard Application MVP**, not Phase 8A
polish (S024/S025).

S024/S025 remain queued for live dry-run operating polish. This sprint builds a
**separate read-only research dashboard application** that consumes persisted
artifacts. Live dry-run integration is contracts-only (see D-S028-07).

---

## D-S028-02 — UI / query stack (D2 = A)

**Decision:** MVP stack is:

```text
Streamlit + Plotly (+ optional AG Grid)
DashboardQueryService
DuckDB over Parquet (+ Polars for light transforms)
Docker Compose + Caddy + read-only storage mount
```

Do **not** evolve the existing generate-once HTML reports into the long-term app.
Those reports may remain as offline export / demo artifacts, but the product path
is `apps/dashboard/`.

New dependencies (dashboard app / optional extra): `streamlit`, `duckdb`. Keep them
out of the core research engine install if practical (separate `apps/dashboard`
`pyproject.toml`).

---

## D-S028-03 — Orderflow out of MVP (D3 = A)

**Decision:** Orderflow M1 overlays and orderflow parquet contracts are **out of
scope** for Sprint 028.

Leave an overlay-type placeholder / registry slot (`orderflow_histogram`) but do
not require orderflow datasets. Full orderflow belongs with Phase 4B.

---

## D-S028-04 — Canonical artifact exports (D4 = B)

**Decision:** Dashboard does **not** only adapt today’s ad-hoc layouts. The
framework must emit **canonical, versioned dashboard-facing artifacts** (and/or
stabilize existing ones) so the app reads a documented contract.

### Current inventory (2026-07-17)

| Area | Already Parquet (facts) | JSON today |
|------|-------------------------|------------|
| Signal / Market Research | `occurrences`, `observations`, `context`, `outcomes` | `manifest.json`, `analytics/summary.json`, HTML report |
| Strategy Research | `trades.parquet`, `equity.parquet` | `manifest.json` |
| Robustness | (child strategy runs reuse Parquet) | experiment `manifest` / `registry` / most `analytics/*.json` / fold+stress+MC results |

### Unification rule (binding)

```text
Manifests / envelopes / small identity metadata  → JSON (OK)
Tabular analytics, metrics, series, overlays     → Parquet
HTML reports                                     → optional export only (not the query source of truth)
```

**Market / Signal Research:** `analytics/summary.json` is the wrong long-term
shape for grouped metrics and series consumed by DuckDB. Sprint 028 must migrate
(or dual-write then cut over) tabular analytics to Parquet tables with a versioned
schema (e.g. `analytics/summary_metrics.parquet`, `analytics/grouped_*.parquet`).

**Strategy Research:** add explicit dashboard KPIs artifact if not already
derivable without recomputation (e.g. `analytics/summary_metrics.parquet` aligned
with the strategy dashboard KPI set). Keep `equity.parquet` / `trades.parquet` as
canonical series/tables.

**Robustness:** tabular sweep / walk-forward / stress / MC result matrices →
Parquet; keep experiment manifest + registry as JSON.

Schema changes require version bumps on research envelopes and tests. Prefer
**dual-write** during transition so existing HTML demos keep working until cutover.

---

## D-S028-05 — Delivery shape (D5 = A)

**Decision:** One sprint (`SPRINT_028`) with **internal waves**, not two sprint
numbers up front.

Suggested waves:

| Wave | Outcome |
|------|---------|
| A | `apps/dashboard` shell, contracts, DuckDB storage adapter, run catalog |
| B | Canonical Parquet exports from research persist + strategy page (KPI/equity/chart/trades) |
| C | Market/signal research page + robustness page MVP |
| D | Cache/perf, Docker/Caddy, docs, dry-run datasource contracts (stubs) |

PR policy: one coherent outcome per working PR into `sprint/dashboard-application-mvp`.

---

## D-S028-06 — Dependency boundary

**Decision:** `apps/dashboard` must not import:

```text
trading_framework.research
trading_framework.application.strategy_research  (engine)
trading_framework.application.robustness_research
trading_framework.execution
trading_framework.infrastructure.providers
trading_framework.infrastructure.importers
```

Allowed:

- read-only access to mounted storage paths,
- a small shared **contracts** package (or `trading_framework.dashboard_contracts`
  / `packages/dashboard_contracts`) for schema DTOs only — no workflow logic,
- DuckDB/Polars/PyArrow/Streamlit/Plotly inside the app.

---

## D-S028-07 — Dry-run preparation (contracts only)

**Decision:** Define shared presentation models (`RunSummary`, `ChartWindow`,
`TradeView`, …) usable later by `HistoricalRunDataSource` and
`AwsDryRunDataSource`. Implement only the historical Parquet source in MVP.
No AWS HTTP client, no live control plane in this sprint.

S023 live dashboard remains the current public dry-run UI until a later sprint
wires the second datasource.

---

## D-S028-08 — Chart / market data access

**Decision:** Market candles for inspection charts are loaded **windowed** via
DuckDB from existing partitioned OHLCV under `user_data/market_data/` (current
layout), not by re-running Market Analysis.

Resolution policy may start as explicit timeframe selection; automatic resolution
ladder is prepared in the query API but need not be fully tuned in Wave A.

---

## Key files (pre-sprint)

| Area | Path |
|------|------|
| Strategy HTML dashboard | `application/strategy_research/dashboard.py`, `research/analytics/strategy_dashboard*` |
| Signal report | signal research reporting packages |
| Robustness report | robustness reporting + `research/datasets/robustness.py` |
| Run storage | `research/datasets/signal_research.py`, `strategy_research.py`, `robustness.py` |
| Paths | `infrastructure/storage/paths.py` |
| Live dry-run UI | `scripts/portfolio_live/serve_live_dry_run_dashboard.py` |
| Maintainer brief | Desktop `# Sprint — Dashboard Application MVP.txt` |
