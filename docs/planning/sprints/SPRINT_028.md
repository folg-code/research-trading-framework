# Sprint 028 — Dashboard Application MVP

## Metadata

```text
Sprint: 028
Phase: Cross-cutting — Research Visualization / Operator Tools
Status: PLANNED
Planned Start: 2026-07-17
Planned End: TBD
Sprint Goal Owner: Project Maintainer
Depends On: Strategy / Signal / Robustness artifacts on main (S014–S017, S026); storage under user_data/research/
Sprint Branch: sprint/dashboard-application-mvp
Task branch convention: feat/ | fix/ | docs/ | test/ | refactor/
Wave 0 decisions: docs/planning/sprints/S028_WAVE0_DECISIONS.md
Architecture Sources:
  - Maintainer brief: Dashboard Application MVP (2026-07-17)
  - docs/adr/ADR-0011 / ADR-0012 / ADR-0016 / ADR-0017 / ADR-0019 / ADR-0020
  - Existing HTML dashboards (reference only — not the product path)
Track choice: Dashboard Application MVP selected over Phase 8A polish (S024/S025).
```

---

## 0. Slice Choice

Today the framework **generates** standalone HTML/Plotly reports from inside research
workflows. That is fine for demos; it is not a durable operator application.

This sprint builds:

```text
versioned run artifacts (Parquet + JSON manifests)
  → DashboardQueryService + DuckDB
  → Streamlit + Plotly app (apps/dashboard)
  → Docker / Caddy / read-only storage on VPS
```

The app is a **consumer only**: no backtests, no research workflows, no providers.

**Out of scope:** orderflow M1 (Phase 4B), running research from UI, full AWS dry-run UI,
auth, TradingView clone, footprint, WebSocket streaming.

---

## 1. Sprint Goal

```text
Operator can open apps/dashboard against mounted user_data
  → browse MARKET / SIGNAL / STRATEGY / ROBUSTNESS runs
  → inspect strategy KPI + equity + windowed OHLCV + trade overlays
  → inspect market/signal research summaries from Parquet analytics
  → inspect basic robustness tables
  → deploy dashboard-only container with read-only storage
```

Success: useful analytical tool on real artifacts, not a second demo format.

---

## 2. MVP Scope Checklist

### Wave A — App foundation

- [ ] Create `apps/dashboard` with its own `pyproject.toml` (Streamlit, DuckDB, Plotly).
- [ ] Multi-page shell + storage-root config.
- [ ] Shared presentation contracts (`RunSummary`, `RunManifest`, `ChartWindow`, `TradeView`, …)
      with schema versions.
- [ ] `DashboardQueryService` + Parquet/DuckDB adapter (windowed reads, column projection).
- [ ] Run catalog across the four workflow types (tolerate missing/corrupt manifests).

### Wave B — Canonical Parquet exports + Strategy page

- [ ] Migrate / dual-write **tabular** Market/Signal analytics off `analytics/summary.json`
      onto Parquet tables (D-S028-04).
- [ ] Emit strategy `analytics/summary_metrics.parquet` (or equivalent) for KPI cards without
      recomputation.
- [ ] Strategy page: metadata, KPI cards, equity + drawdown, windowed OHLCV chart, trade table,
      entry/exit overlays + prev/next trade.
- [ ] Overlay renderer registry (markers, levels, zones, state background, trade connection) —
      **no orderflow implementation**.

### Wave C — Research + Robustness pages

- [ ] Market / Signal research page: summary + grouped metrics + distributions + inspection chart.
- [ ] Robustness page MVP: summary, IS/OOS, walk-forward table, param sweep table/heatmap.
- [ ] Robustness tabular analytics → Parquet where matrices are queried by DuckDB.

### Wave D — Perf, deploy, docs

- [ ] Streamlit cache keys tied to storage fingerprint / window / timeframe.
- [ ] Dockerfile + Compose + Caddy + read-only mount + healthcheck + runbook.
- [ ] Architecture docs: contracts, adding a page, adding an overlay renderer, publishing runs to VPS.
- [ ] Stub contracts for future `AwsDryRunDataSource` (no live client).

---

## 3. Non-Goals / Explicit Deferrals

| Deferred | Why |
|----------|-----|
| Orderflow M1 overlays | Phase 4B; D-S028-03 |
| Full AWS dry-run dashboard in this app | Contracts only; S023 remains live UI |
| S024/S025 live polish | Separate track |
| Launching research / backtests from UI | Consumer boundary |
| Auth / multi-user | Premature |
| Replacing offline HTML demos immediately | Dual-write until cutover |

---

## 4. Task Breakdown

| Task | Outcome | Wave | Status |
|------|---------|------|--------|
| S028-T001 | Wave 0 decisions + sprint branch | 0 | DONE |
| S028-T002 | `apps/dashboard` scaffold + Streamlit multipage | A | TODO |
| S028-T003 | Presentation contracts + schema versions | A | TODO |
| S028-T004 | DuckDB query layer + windowed OHLCV fixtures tests | A | TODO |
| S028-T005 | Run catalog (4 workflow types) | A | TODO |
| S028-T006 | Signal/Market analytics → Parquet (dual-write) | B | TODO |
| S028-T007 | Strategy summary_metrics Parquet export | B | TODO |
| S028-T008 | Strategy page: KPI + equity + drawdown | B | TODO |
| S028-T009 | Market chart window + trade overlays + nav | B | TODO |
| S028-T010 | Overlay renderer registry (no orderflow) | B | TODO |
| S028-T011 | Market/Signal research page | C | TODO |
| S028-T012 | Robustness Parquet exports + page MVP | C | TODO |
| S028-T013 | Cache / result size limits | D | TODO |
| S028-T014 | Docker / Compose / Caddy / runbook | D | TODO |
| S028-T015 | Docs + dry-run datasource stubs | D | TODO |
| S028-T016 | Test suite (contracts, query, missing artifacts, pagination) | D | TODO |

---

## 5. Acceptance Criteria

1. Dashboard runs without importing research/execution engines.
2. Run catalog lists real artifacts from mounted storage.
3. Strategy KPI, equity/drawdown, windowed candles, trade entry/exit links work.
4. Market/signal and robustness basic pages work from **Parquet** analytics (not by parsing
   Plotly HTML).
5. Queries are windowed; full multi-year M1 is never loaded into memory.
6. Docker deploy with read-only storage works locally (and is documented for VPS).
7. Orderflow is absent but overlay registry leaves a clear extension point.

---

## 6. Suggested PR Boundaries

```text
docs/dashboard-application-mvp-sprint     → main     (Wave 0; this PR)
feat/dashboard-app-scaffold               → sprint
feat/dashboard-contracts-and-catalog      → sprint
feat/dashboard-duckdb-query-layer         → sprint
feat/research-analytics-parquet-export    → sprint
feat/dashboard-strategy-page              → sprint
feat/dashboard-research-robustness-pages  → sprint
feat/dashboard-docker-docs                → sprint
sprint/dashboard-application-mvp          → main     (integration)
```

---

## 7. Relationship to Existing HTML Dashboards

| Existing | Role after S028 |
|----------|-----------------|
| Strategy Lightweight Charts HTML (S014) | Optional offline export; not the app |
| Signal/Model Plotly HTML | Optional export; query source becomes Parquet analytics |
| Robustness HTML | Optional export |
| Portfolio live dry-run server (S023) | Remains live track until datasource merge later |

---

## 8. Status Updates

Update this file when waves complete. Do not treat it as a live stopwatch.
