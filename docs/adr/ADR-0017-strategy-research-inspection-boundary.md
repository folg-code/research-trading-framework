# ADR-0017 — Strategy Research Inspection Boundary

## Status

ACCEPTED

## Context

Sprint 013 delivered **Strategy Research computation and persistence** (ADR-0016). Wave 0 decisions
(D-S013-13) deferred the human-facing inspection layer.

Sprint 014 closes the **first inspection loop** for persisted strategy runs: read-only dashboard view
model, standalone HTML report and CLI. Wave 0 decisions in `S014_WAVE0_DECISIONS.md` define a
two-phase delivery model:

```text
Phase A — static HTML + embedded JSON (required, offline)
Phase B — FastAPI inspection server + lazy bar fetch (optional, deferred)
```

The dashboard must mirror the Signal Research analytics boundary (ADR-0013): interpret immutable
persisted facts without re-running simulation or model evaluation.

## Decision

### Read-only inspection boundary

Dashboard and inspection modules must not:

```text
write or mutate run storage
call run_strategy_research
call evaluate_models
recompute BarSequentialSimulator fills or equity
materialize signal occurrences or forward outcomes
```

Allowed reads:

```text
StrategyResearchDatasetRepository.read
query_historical (source OHLCV DatasetRef from manifest)
analyze_strategy_research_run / summarize_strategy_run (existing summary metrics)
```

Fixture production in spikes and integration tests may call `run_strategy_research`; production
dashboard modules under `research/analytics/` and `application/strategy_research/dashboard.py`
must not.

### Presentation split

Mirror ADR-0013 reporting layer:

```text
build_strategy_dashboard_view_model   — reads envelope + source bars; computes dashboard metrics
render_strategy_research_dashboard    — consumes StrategyDashboardViewModel only; no I/O
```

CLI `render_strategy_dashboard.py` orchestrates build + render; it does not embed HTML logic in
application services.

### Chart stack (Phase A)

OHLCV candlestick chart uses **TradingView Lightweight Charts** (CDN) in standalone HTML.

Plotly is **not** used for OHLCV in this sprint. Plotly remains appropriate for Signal Research
distribution analytics (ADR-0013).

Equity curve and drawdown render in separate panes. Entry/exit markers bind to
`SimulatedTrade.entry_fill_at` / `entry_fill_price` and `exit_fill_at` / `exit_fill_price`.

### View model contract

Ephemeral `StrategyDashboardViewModel` (JSON-serializable) with three sections:

```text
Overview            — 12 KPI cards + equity + OHLCV with markers
Performance         — drawdown, monthly PnL, trade PnL histogram, recent trades table
Conditional         — long/short, session, hour-of-day breakdowns
metric_context      — interpretation warnings (sample size, annualization, short backtest)
```

View model includes source OHLCV bar slice for Phase A embedded mode. Effective chart range follows
equity index bounds from the persisted run.

### Phase A delivery

Phase A must work **offline** — opening the HTML file without a local server.

CLI:

```text
scripts/strategy_research/render_strategy_dashboard.py
```

Embedded JSON payload carries bars for fixture-scale datasets (~1k bars). Document size threshold;
large datasets defer to Phase B fetch mode.

### Phase B (deferred)

Optional `inspection` dependency group (`fastapi`, `uvicorn`) and `inspection/` HTTP layer are
**out of Sprint 014 Phase A closure**. Phase B adds:

```text
GET /runs/{run_id}/summary | trades | equity | bars?from=&to=
lazy Polars scan_parquet on source OHLCV
HTML dual mode: embedded vs api (data-api-base attribute)
```

Core CI must pass without installing the `inspection` group.

### Price semantics on chart

```text
OHLCV candles   — source dataset bars (observed_at, OHLCV, volume)
entry marker    — SimulatedTrade entry fill time and price
exit marker     — SimulatedTrade exit fill time and price
equity curve    — EquityPoint.observed_at + equity (not back-adjusted)
```

## Consequences

### Positive

- Completes Phase 6A human validation loop without re-running simulation,
- reuses Sprint 013 envelope and ADR-0013 boundary pattern,
- offline HTML works on committed fixtures and local research runs,
- Phase B can attach without changing Phase A view model contract.

### Negative

- single-run dashboard only; multi-run comparison deferred,
- Phase A embeds full bar slice — impractical for very large OHLCV without Phase B,
- no walk-forward, robustness or replay execution in this layer,
- chart stack depends on CDN availability for Lightweight Charts (offline after first load).

## References

- `docs/planning/sprints/S014_WAVE0_DECISIONS.md`
- `docs/planning/sprints/SPRINT_014.md`
- `docs/adr/ADR-0013-signal-research-analytics-boundary.md`
- `docs/adr/ADR-0016-ohlcv-strategy-research-mvp.md`
- `src/trading_framework/application/strategy_research/dashboard.py`
- `src/trading_framework/research/analytics/strategy_dashboard_report.py`
- `scripts/strategy_research/render_strategy_dashboard.py`
