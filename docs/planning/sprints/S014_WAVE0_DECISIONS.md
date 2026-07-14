# Sprint 014 — Wave 0 Architecture Decisions (Strategy Research Dashboard)

## Metadata

```text
Task: S014-T001
Sprint: 014 — Strategy Research Dashboard (Phase 6A Inspection)
Status: PLANNED
Planned Start: 2026-07-14
Branch: sprint/strategy-research-dashboard
Direction: docs/planning/sprints/SPRINT_014.md
Depends on: SPRINT_013 merged to main (ADR-0016); SPRINT_010 on main (ADR-0013 pattern)
Scope: read-only inspection over persisted Strategy Research runs — two-phase delivery
```

---

## 0. Rationale

Sprint 013 delivered batch simulation and minimal `analyze_strategy_research_run` summary metrics.
D-S013-13 deferred HTML inspection to a follow-up sprint.

Sprint 014 adds a **human-facing dashboard** so maintainers can validate strategy behaviour on OHLCV
with TradingView-like interactivity, without over-engineering:

```text
Phase A — static HTML + embedded JSON     fast value, zero infra, CI-friendly
Phase B — FastAPI + lazy Parquet bars     when datasets outgrow embedded payload
```

Post-013 track decision (2026-07-14): **Strategy dashboard** chosen over Phase 6B, 2C.2, 4B and
Phase 7 for the next vertical slice.

---

## 1. Read-only analytics boundary

**Decision D-S014-01:** Dashboard analytics mirror ADR-0013.

Production modules under `research/analytics/` and `application/strategy_research/` for dashboard
**must not**:

```text
write or mutate run storage
call run_strategy_research
call evaluate_models
recompute BarSequentialSimulator
materialize occurrences or forward outcomes
```

Loads use `StrategyResearchDatasetRepository.read` and `query_historical` only.

Spikes and tests may call `run_strategy_research` to produce fixture runs.

---

## 2. Two-phase delivery

**Decision D-S014-02:** Sprint 014 ships in two phases on one sprint branch.

| Phase | Required | Delivers |
|-------|----------|----------|
| **A** | Yes | View model + static HTML + CLI |
| **B** | No (same sprint, separate PRs) | FastAPI inspection server + fetch-mode frontend |

Phase A acceptance is sufficient for sprint closure and integration PR to `main`. Phase B is
time-boxed; incomplete Phase B does not block Phase A merge.

**Decision D-S014-03:** Phase A must work **offline** (file:// or static file open). No localhost
server required for MVP acceptance.

---

## 3. Chart stack

**Decision D-S014-04:** OHLCV candlestick chart uses **TradingView Lightweight Charts** loaded
from CDN in standalone HTML.

Rationale: Sprint 010 Plotly reports suit distribution analytics; candlestick pan/zoom/crosshair UX
targets TradingView-like behaviour. Plotly is **not** used for OHLCV in this sprint.

**Decision D-S014-05:** Equity curve and drawdown use a **second Lightweight Charts pane** (or
price-scale overlay only if spike proves readable — default: separate pane).

**Decision D-S014-06:** Vanilla JavaScript only in HTML shell. No React, Vite or Node build step.

---

## 4. View model contract

**Decision D-S014-07:** Introduce ephemeral `StrategyDashboardViewModel` (dataclass or typed dict)
built by `build_strategy_dashboard_view_model`.

Inputs:

```text
StrategyResearchRunEnvelope   — manifest, trades, equity
source OHLCV bars             — via query_historical(manifest.source_dataset_ref, effective range)
```

Outputs: JSON-serializable structure consumed by renderer and (Phase B) API serializers.

**Decision D-S014-08:** Renderer `render_strategy_research_dashboard` accepts the view model only —
no filesystem or repository access (same split as `render_signal_research_report` / D-S010-20).

**Decision D-S014-09:** Bar rows use canonical OHLCV fields aligned with `query_historical` output:

```text
observed_at   — UTC ISO-8601 in JSON
open, high, low, close, volume
```

Trade markers:

```text
trade_id
entry_filled_at, entry_fill_price
exit_filled_at, exit_fill_price
direction, net_pnl, bars_held, exit_reason
```

---

## 5. Dashboard information architecture (MVP)

**Decision D-S014-10:** Phase A dashboard uses **three sections**:

```text
Overview              — 12 KPI cards + equity curve + OHLCV chart with trade markers
Performance Analysis  — drawdown curve, monthly PnL, trade PnL histogram, costs context
Conditional Analysis  — long vs short, session (RTH), hour-of-day; model ids in header
```

**Decision D-S014-11:** Overview shows **twelve primary KPI cards**:

| KPI | Field | Source |
|-----|-------|--------|
| Net PnL | `net_pnl` | sum trade `net_pnl` |
| Total Return | `total_return` | `(final_equity - initial_equity) / initial_equity` |
| Max Drawdown | `max_drawdown` | min equity `drawdown` (≤ 0) |
| Current Drawdown | `current_drawdown` | last equity `drawdown` |
| Sharpe | `sharpe_ratio` | daily equity returns × sqrt(252) |
| Sortino | `sortino_ratio` | daily returns / downside std × sqrt(252) |
| Profit Factor | `profit_factor` | gross wins / abs(gross losses) |
| Expectancy | `expectancy` | mean trade `net_pnl` |
| Number of Trades | `trade_count` | trade row count |
| Win Rate | `win_rate` | winning trades / trade count |
| Average Win / Loss | `avg_win`, `avg_loss` | mean net PnL of wins / losses |
| Total Costs | `total_costs` | sum `commission_paid` |

**Decision D-S014-12:** Performance Analysis panels (below KPI row):

```text
equity curve            — equity series (Overview also shows primary chart)
drawdown curve          — equity drawdown series
monthly PnL             — trades grouped by exit month
trade PnL histogram     — distribution of trade net_pnl
recent trades table     — last 20 trades by exit time
```

**Decision D-S014-13:** Conditional Analysis panels (MVP):

```text
long vs short           — direction breakdown
session breakdown       — RTH vs OUTSIDE_RTH (CmeEsRthSessionResolver on exit_fill_at)
hour-of-day breakdown   — 60-minute NY buckets on exit_fill_at
market_model_id         — manifest constant (header + conditional metadata)
signal_model_id         — manifest constant (header + conditional metadata)
volatility_regime       — deferred (requires market-model state recompute)
```

**Decision D-S014-14:** Metrics that require context must surface **`metric_context.warnings`** in
HTML (not hidden footnotes only):

```text
win rate without payoff ratio
Sharpe/Sortino without annualization method
total return on short backtests (< 60 calendar days)
profit factor below recommended trade count (30)
max drawdown without underwater duration
costs without slippage/fill assumption reminder
```

**Decision D-S014-15:** Zero-trade runs render a valid dashboard: empty conditional panels, equity
and drawdown charts from envelope, OHLCV without markers, KPI cards show zeros / nulls appropriately.

---

## 6. Phase A — embedded data mode

**Decision D-S014-16:** Phase A embeds the full view model as JSON in a `<script type="application/json">`
block (or equivalent) inside generated HTML.

Effective bar range:

```text
min(equity.observed_at) … max(equity.observed_at)
```

aligned to the simulated period. Do not embed bars outside the run's equity index unless spike shows
alignment gaps — then clip to intersection.

**Decision D-S014-17:** Document practical size guidance:

```text
≤ ~10k bars  — embedded mode OK for local research
> ~10k bars  — prefer Phase B fetch mode
```

Not a hard code enforcement in Phase A; advisory in ADR-0017 and report header note.

---

## 7. Phase B — inspection API

**Decision D-S014-18:** Phase B adds optional package location:

```text
src/trading_framework/inspection/strategy_research_server.py
```

Thin FastAPI app; domain logic stays in existing read APIs.

**Decision D-S014-15:** FastAPI and uvicorn live in optional uv dependency group:

```text
[dependency-groups]
inspection = ["fastapi>=0.115.0", "uvicorn[standard]>=0.32.0", "httpx>=0.28.0"]
```

Core `dependencies` in `pyproject.toml` remain unchanged. CI default job does not install `inspection`.

**Decision D-S014-16:** Endpoints (read-only):

```text
GET /health
GET /runs/{run_id}/meta              — manifest subset
GET /runs/{run_id}/summary           — StrategyRunSummary + extensions
GET /runs/{run_id}/trades            — full trades JSON (always small)
GET /runs/{run_id}/equity            — full equity JSON
GET /runs/{run_id}/bars?from=&to=    — OHLCV slice, max row cap (e.g. 5000)
```

Query parameters `from` and `to` are UTC ISO-8601 inclusive bounds on `observed_at`.

**Decision D-S014-17:** Bar endpoint implementation uses Polars lazy scan:

```text
pl.scan_parquet(bars_path).filter(observed_at between from and to).collect()
```

Do **not** stream raw Parquet bytes to the browser. Response format is JSON array of bar rows.

Optional chunked NDJSON is out of scope unless profiling proves JSON array insufficient.

**Decision D-S014-18:** Server configuration:

```text
storage_root   — required startup argument (Path)
host/port      — CLI defaults 127.0.0.1:8765
auth           — none (local research tool)
CORS           — allow localhost origins only for dev
```

**Decision D-S014-19:** HTML `data-mode="api"` + `data-api-base` attribute switches frontend to
fetch summary/trades/equity on load and bars on visible range change (debounced).

---

## 8. Application layout

```text
application/strategy_research/
  analyze_strategy_research.py          — existing; may export dashboard orchestration
  dashboard.py (or analytics module)    — build_strategy_dashboard_view_model

research/analytics/
  strategy_summarize.py               — StrategyRunSummary (Sprint 013 metrics)
  strategy_dashboard_metrics.py       — 12 KPIs, panels, warnings
  strategy_dashboard.py               — view model types + render (Wave 2)

inspection/                             — Phase B only
  strategy_research_server.py
```

Prefer `research/analytics/strategy_dashboard.py` over bloating `reports.py` — Signal and Strategy
dashboards differ in chart stack and data shape.

---

## 9. CLI and spike

**Decision D-S014-20:** Phase A CLI:

```text
scripts/strategy_research/render_strategy_dashboard.py
  --storage-root
  --run-id
  --output path/to/report.html
```

**Decision D-S014-21:** Phase B CLI:

```text
scripts/strategy_research/serve_strategy_dashboard.py
  --storage-root
  --run-id
  --port
```

Serves HTML shell in `api` mode plus API routes.

**Decision D-S014-22:** Spike script:

```text
tests/spike/run_strategy_dashboard_spike.py
```

Validates: fixture run → view model → HTML written; optional local open instruction; Phase B smoke
when `inspection` group installed. Opt-in, not CI-gated initially.

Completes deferred S013-T001 spike gap for dashboard path (simulation spike remains separate).

---

## 10. UX interactions (MVP)

**Decision D-S014-23:** Minimum interactivity:

```text
pan and zoom on OHLCV chart
crosshair with OHLCV tooltip
entry markers (arrow/up) and exit markers (arrow/down or color split)
click trade row → chart scroll/zoom to entry time window
equity pane synced time scale
```

**Decision D-S014-24:** Out of scope for MVP:

```text
drawing tools, indicators, multiple symbols
order ticket simulation
multi-run tabs
WebSocket streaming
```

---

## 11. Testing strategy

| Tier | Scope |
|------|--------|
| Unit | view model builder, metric extensions, JSON serialization, renderer smoke (HTML contains markers) |
| Integration | fixture run → dashboard HTML; zero-trade run; bars aligned to equity range |
| API (Phase B) | TestClient bar filter, 404 on missing run, row cap |
| Spike | opt-in local manual validation |

Dashboard modules must not import `run_strategy_research` or `evaluate_models` (lint or import test).

---

## 12. Out of scope

- Multi-run comparison and run discovery UI (PRB-004),
- Auth, TLS, production deployment,
- DuckDB / SQL analytics layer,
- Changes to simulation assumptions or envelope schema,
- Signal Research dashboard rework,
- Full TradingView widget (licensed product),
- WebSocket / SSE streaming,
- Writing dashboard state back to storage.

---

## 13. ADR and documentation deliverables

- **ADR-0017** — Strategy Research inspection boundary, Phase A/B split, Lightweight Charts, optional FastAPI.
- Update `MODULE_MAP.md`, `DATA_WORKFLOWS.md`, `docs/adr/README.md`, `CURRENT_STATUS.md` on closure.
- Optional ROADMAP note under §10 that Phase 6A inspection increment is Sprint 014.

---

## 14. Spike validation checklist

```text
[ ] Fixture Strategy Research run loads via repository.read
[ ] query_historical returns bars for manifest.source_dataset_ref
[ ] View model JSON round-trips without datetime serialization errors
[ ] HTML renders candles + markers when trades > 0
[ ] HTML renders cleanly when trades == 0
[ ] Renderer module imports exclude run_strategy_research / evaluate_models
[ ] Phase B (optional): bars endpoint returns subset for narrow from/to window
[ ] Phase B (optional): full-dataset scan not loaded when serving 500-bar window
```

---

## 15. Decision index

| ID | Summary |
|----|---------|
| D-S014-01 | Read-only boundary mirrors ADR-0013 |
| D-S014-02 | Two-phase delivery: A required, B optional |
| D-S014-03 | Phase A offline static HTML |
| D-S014-04 | Lightweight Charts for OHLCV |
| D-S014-05 | Separate equity pane (default) |
| D-S014-06 | Vanilla JS, no SPA build |
| D-S014-07 | StrategyDashboardViewModel builder |
| D-S014-08 | Renderer consumes view model only |
| D-S014-09 | Bar and trade marker field contract |
| D-S014-10 | Three-section dashboard IA (Overview / Performance / Conditional) |
| D-S014-11 | Twelve Overview KPI cards |
| D-S014-12 | Performance Analysis panels |
| D-S014-13 | Conditional Analysis panels (MVP scope) |
| D-S014-14 | Metric context warnings surfaced in UI |
| D-S014-15 | Zero-trade runs render valid dashboard |
| D-S014-16 | Phase A embedded JSON payload |
| D-S014-17 | ~10k bar embedded size guidance |
| D-S014-18 | inspection/ module for FastAPI |
| D-S014-15 | Optional inspection dependency group |
| D-S014-16 | Read-only REST endpoint set |
| D-S014-17 | Lazy Polars scan; JSON response not Parquet stream |
| D-S014-18 | Local server config, no auth |
| D-S014-19 | HTML dual mode embedded vs api |
| D-S014-20 | render_strategy_dashboard CLI |
| D-S014-21 | serve_strategy_dashboard CLI |
| D-S014-22 | Dashboard spike script |
| D-S014-23 | MVP chart UX interactions |
| D-S014-24 | Explicit UX out of scope |

---

## Revision History

| Date | Change |
|------|--------|
| 2026-07-14 | Initial binding decisions D-S014-01 … D-S014-24 |
