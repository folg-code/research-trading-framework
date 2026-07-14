# Sprint 014 — Strategy Research Dashboard (Phase 6A Inspection)

## Metadata

```text
Sprint: 014
Phase: Phase 6A follow-up — Strategy Research inspection layer
Status: COMPLETE — Phase A (2026-07-14); Phase B deferred
Planned Start: 2026-07-14
Planned End: 2026-07-14
Sprint Goal Owner: Project Maintainer
Depends On: SPRINT_013 (main), SPRINT_010 (ADR-0013 pattern reference)
Sprint Branch: sprint/strategy-research-dashboard
Task branch convention: feat/ | fix/ | docs/ (separate prefix, not nested under sprint ref)
Wave 0 decisions: docs/planning/sprints/S014_WAVE0_DECISIONS.md
Architecture Sources:
  - docs/planning/ROADMAP.md (§10 Strategy Research)
  - docs/adr/ADR-0013-signal-research-analytics-boundary.md (read-only analytics pattern)
  - docs/adr/ADR-0016-ohlcv-strategy-research-mvp.md
  - docs/planning/sprints/S013_WAVE0_DECISIONS.md (D-S013-16 deferred HTML)
Track choice: Strategy dashboard selected over Phase 6B / 2C.2 / 4B / Phase 7 — 2026-07-14
Delivery model: Two-phase — Phase A static HTML MVP, Phase B optional FastAPI + lazy Parquet bars
```

---

## 0. Slice choice

Sprint 013 delivered **Strategy Research computation and persistence** (ADR-0016). Wave 0 decisions
explicitly deferred the inspection layer (D-S013-13).

Sprint 014 closes the **first human-facing inspection loop** for persisted strategy runs:

```text
StrategyResearchRunEnvelope (manifest + trades + equity)
    ↓
read-only dashboard view model (metrics + chart payloads)
    ↓
Phase A: standalone HTML (Lightweight Charts) — offline, zero server
    ↓
Phase B (optional): FastAPI read API + viewport-scoped bar fetch from source OHLCV Parquet
```

**Out of scope:** walk-forward, robustness, multi-run comparison, Replay Execution, React SPA build
pipeline, production auth, WebSocket live streaming, re-running simulation or `evaluate_models`.

---

## 1. Sprint Goal

```text
StrategyResearchRunRef + storage_root
    ↓
StrategyResearchDatasetRepository.read
    ↓
analyze_strategy_research_run (existing summary)
    ↓
build_strategy_dashboard_view_model (manifest + summary + trades + equity + bar slice)
    ↓
Phase A: render_strategy_research_dashboard → standalone HTML
Phase B: optional inspection server → JSON endpoints + same frontend fetch mode
```

Success: after a Strategy Research run, a maintainer can open a **TradingView-like interactive chart**
(OHLCV + entry/exit markers + equity panel) and read **strategy metrics** without re-running
simulation or loading Python notebooks.

---

## 2. Two-Phase Delivery

| Phase | Goal | When | Infra |
|-------|------|------|-------|
| **A — Static dashboard MVP** | View model + HTML report + CLI | Waves 0–4 (required) | None — open HTML file |
| **B — Inspection API** | FastAPI + lazy `bars?from=&to=` | Waves 5–6 (optional, same sprint or follow-up PR) | Local `uvicorn`, `storage_root` |

Phase A must deliver standalone value on committed fixtures (~1k bars). Phase B activates when OHLCV
payload size or interactive zoom makes embedded JSON impractical.

```text
Phase A                          Phase B
────────                         ────────
embed JSON in HTML      →        fetch /bars on viewport change
full bar load in Python →        Polars scan_parquet + time filter
zero new dependencies   →        optional dependency group: inspection (FastAPI + uvicorn)
```

---

## 3. Three Outcomes

| Outcome | Phase | Deliverable |
|---------|-------|-------------|
| **A — Dashboard view model** | A | `StrategyDashboardViewModel`, builder from persisted run + source bars |
| **B — Static HTML report** | A | `render_strategy_research_dashboard`, Lightweight Charts, trades table |
| **C — Optional inspection server** | B | Read-only FastAPI app, lazy bar endpoint, dual-mode frontend |

---

## 4. Domain Boundary

```text
research/datasets/                StrategyResearchDatasetRepository.read (unchanged write path)
application/strategy_research/      analyze_strategy_research_run (extend orchestration only)
research/analytics/               dashboard view model + HTML renderer (presentation)
research/datasets/query/          query_historical for source OHLCV bars (read-only)
inspection/ (Phase B only)        FastAPI app — thin HTTP over existing read APIs
```

### Read-only boundary (binding)

Mirror ADR-0013. Dashboard and inspection server must **not**:

```text
write or mutate run storage
call run_strategy_research
call evaluate_models
recompute simulation fills or equity
materialize signal occurrences
```

Fixture production in spikes/tests may use `run_strategy_research`; production dashboard modules
must not.

### Presentation boundary (binding)

```text
build_strategy_dashboard_view_model   — may read Parquet (envelope + source bars)
render_strategy_research_dashboard    — consumes view model only; no I/O
FastAPI handlers (Phase B)            — delegate to repository / query_historical; no HTML logic in routes
```

### Price semantics on chart

```text
OHLCV candles     — source dataset bars (observed_at, open, high, low, close, volume)
entry marker      — SimulatedTrade.entry_filled_at + entry_fill_price
exit marker       — SimulatedTrade.exit_filled_at + exit_fill_price
equity curve      — EquityPoint.observed_at + equity (separate pane or overlay per Wave 0)
```

---

## 5. Logical View Model (Phase A contract)

Ephemeral JSON-serializable structure organized in **three dashboard sections**:

### Overview

Twelve KPI cards:

| KPI | Meaning |
|-----|---------|
| Net PnL | Final result |
| Total Return | Return rate vs initial equity |
| Max Drawdown | Largest peak-to-trough loss |
| Current Drawdown | Latest underwater state |
| Sharpe | Return vs volatility (daily, sqrt(252)) |
| Sortino | Return vs downside volatility |
| Profit Factor | Gross wins / gross losses |
| Expectancy | Mean trade net PnL |
| Number of Trades | Sample size |
| Win Rate | Winning trades / total |
| Average Win / Loss | Payoff profile |
| Total Costs | Commission impact |

Plus: **equity curve**, **OHLCV chart** with entry/exit markers.

### Performance Analysis

```text
drawdown curve
monthly PnL
trade PnL histogram
recent trades table (last 20)
```

### Conditional Analysis

```text
long vs short breakdown
session breakdown (RTH / OUTSIDE_RTH)
hour-of-day breakdown (NY 60m buckets)
market_model_id / signal_model_id (manifest constants)
volatility_regime — deferred
```

### Metric context

`metric_context.warnings` surfaces interpretation risks (low sample, Sharpe annualization, short
backtest, win rate without payoff, drawdown without duration, cost assumptions).

```text
StrategyDashboardViewModel
  overview: StrategyDashboardOverviewKpis
  performance: StrategyDashboardPerformancePanels
  metric_context: StrategyDashboardMetricContext
  trades, equity, bars, metadata
```

Phase B: `bars` may be empty when `data_mode=fetch`; frontend loads via API.

---

## 6. Task Board

### Wave 0 — Decisions and spike

| Task | Description | Status |
|------|-------------|--------|
| S014-T001 | Wave 0 decisions (`S014_WAVE0_DECISIONS.md`) + dashboard spike script | DONE |

### Phase A — Wave 1: View model and metrics

| Task | Description | Status |
|------|-------------|--------|
| S014-T002 | `StrategyDashboardViewModel` types + JSON serialization | DONE |
| S014-T003 | `build_strategy_dashboard_view_model` — envelope + `query_historical` bars | DONE |
| S014-T004 | Overview KPIs (12 cards) + performance/conditional panels + metric warnings | DONE |

### Phase A — Wave 2: Static HTML dashboard

| Task | Description | Status |
|------|-------------|--------|
| S014-T005 | `render_strategy_research_dashboard` — Lightweight Charts (CDN) | DONE |
| S014-T006 | Entry/exit markers, crosshair, trade table click-to-focus | DONE |
| S014-T007 | Equity pane + summary metrics panel | DONE |

### Phase A — Wave 3: Workflow and tests

| Task | Description | Status |
|------|-------------|--------|
| S014-T008 | `analyze_strategy_research_dashboard` application orchestration (optional thin wrapper) | DONE |
| S014-T009 | CLI `scripts/strategy_research/render_strategy_dashboard.py` | DONE |
| S014-T010 | Unit + integration tests (fixture run → HTML smoke, view model round-trip) | DONE |

### Phase A — Wave 4: ADR and closure

| Task | Description | Status |
|------|-------------|--------|
| S014-T011 | ADR-0017 — Strategy Research inspection boundary + stack | DONE |
| S014-T012 | `MODULE_MAP.md`, `DATA_WORKFLOWS.md`, `CURRENT_STATUS.md` | DONE |
| S014-T013 | Sprint closure | DONE |

### Phase B — Wave 5: Inspection API (optional)

| Task | Description | Status |
|------|-------------|--------|
| S014-T014 | Optional `inspection` dependency group (`fastapi`, `uvicorn`) | PLANNED |
| S014-T015 | `StrategyResearchInspectionApp` — summary / trades / equity / bars endpoints | PLANNED |
| S014-T016 | Lazy bars: `scan_parquet` + `observed_at` range filter | PLANNED |

### Phase B — Wave 6: Fetch-mode frontend (optional)

| Task | Description | Status |
|------|-------------|--------|
| S014-T017 | HTML dual mode: `embedded` vs `api` (`data-api-base` attribute) | PLANNED |
| S014-T018 | CLI `scripts/strategy_research/serve_strategy_dashboard.py` | PLANNED |
| S014-T019 | API tests (`httpx` / `TestClient`) + size-threshold documentation | PLANNED |

**Progress:** 13 / 19 tasks — Phase A complete (T001–T013); Phase B deferred (T014–T019)

---

## 7. Recommended PR sequence

### Phase A (required)

| PR | Branch (example) | Outcome |
|----|------------------|---------|
| 1 | `docs/sprint-014-planning` | Wave 0 decisions + sprint doc |
| 2 | `feat/strategy-dashboard-view-model` | T002–T004 view model + metrics |
| 3 | `feat/strategy-dashboard-static-html` | T005–T007 Lightweight Charts report |
| 4 | `feat/strategy-dashboard-workflow` | T008–T010 orchestration, CLI, tests |
| 5 | `docs/strategy-dashboard-closure` | T011–T013 ADR-0017, docs, closure |

### Phase B (optional — after Phase A merges to sprint branch)

| PR | Branch (example) | Outcome |
|----|------------------|---------|
| 6 | `feat/strategy-dashboard-inspection-api` | T014–T016 FastAPI + lazy bars |
| 7 | `feat/strategy-dashboard-api-frontend` | T017–T019 fetch mode + serve CLI |

Each PR targets `sprint/strategy-research-dashboard`. Final sprint integration PR → `main` when
Phase A tasks complete. Phase B may ship in the same sprint integration PR or a fast-follow if time
boxed.

---

## 8. Acceptance criteria

### Phase A (required)

1. Canonical Strategy Research fixture run renders standalone HTML with OHLCV candles and visible
   entry/exit markers when trades exist.
2. Summary panel shows Sprint 013 metrics plus Wave 0 extensions (profit factor, average bars held).
3. `render_strategy_research_dashboard` accepts a built view model only — no Parquet reads inside
   renderer (ADR-0013 presentation split).
4. CLI writes HTML to user-specified path; opening file works offline without a server.
5. CI green: `ruff check`, `ruff format --check`, `mypy`, `pytest`.
6. ADR-0017 ACCEPTED; module map and data flows updated.

### Phase B (optional)

7. `GET /runs/{run_id}/bars?from=&to=` returns JSON bar slice without loading full dataset into RAM
   (Polars lazy scan).
8. Same HTML shell operates in `api` mode against local server; zoom/pan triggers bounded bar fetch.
9. Inspection server is read-only; no write endpoints; `storage_root` configured at startup only.

---

## 9. Risks and mitigations

| Risk | Mitigation |
|------|------------|
| Large HTML from embedded bars | Document size threshold; Phase B fetch mode; cap Phase A to effective run date range |
| Plotly used for candles (poor TV UX) | Binding: Lightweight Charts for OHLCV (D-S014-03) |
| Dashboard re-runs simulation | Hard boundary in ADR-0017; tests assert no `run_strategy_research` import in renderer |
| FastAPI added to core deps | Optional `inspection` dependency group only (D-S014-07) |
| Scope creep into multi-run UI | Single-run MVP; multi-run comparison deferred |
| Source bars mismatch vs simulation range | View model carries effective range from manifest / equity index |

---

## 10. Dependencies

**Required on main:**

- Sprint 013 Strategy Research envelope, repository, `analyze_strategy_research_run`
- Phase 2A `query_historical` for source OHLCV `DatasetRef` in manifest

**Not required:**

- Signal Research runs or analytics changes
- Phase 6B multi-data
- Phase 7 robustness
- React / Node build toolchain

---

## 11. Quality gates

Every implementation PR must pass:

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run pytest
```

Phase B PRs additionally run API tests. Core CI must pass **without** installing the `inspection`
group.

---

## 12. Post-sprint direction

After Sprint 014 merges to `main`:

- **Phase 7** — robustness on persisted strategy runs,
- **Phase 6B** — multi-data strategy research when 2C/4B data exists,
- **Multi-run dashboard** — comparison grid (new sprint),
- **Replay Execution** — separate sprint family under `execution/`.

See `ROADMAP.md` §10–§11 and `CURRENT_STATUS.md`.

---

## 13. Sprint closure (Phase A)

```text
Closed: 2026-07-14
Phase A: COMPLETE on main
Phase B: DEFERRED (T014–T019)
ADR: ADR-0017 ACCEPTED
```

Implementation commits on `main`:

```text
3808d1d — feat: add strategy dashboard view model for Sprint 014 wave 1
9c14c7a — feat: add static strategy dashboard HTML report and CLI
```

Closure deliverables: ADR-0017, `MODULE_MAP.md`, `DATA_WORKFLOWS.md`, `CURRENT_STATUS.md`.
