# Live Paper / AWS Dry-Run Pipeline Inspection

Sprint 031 + Sprint 032 notes. Confirms execution vs read-only boundaries and
Strategy Model evaluation for paper trading visible in `apps/dashboard`.

## Architecture verdict

| Component | Full paper execution? | Notes |
|-----------|----------------------|-------|
| ECS worker (`run_aws_btc_futures_worker`) | **Yes** | Same engine as local: closed bar → signal → `PaperBroker` → persist |
| Status Lambda (`aws_status_api_handler`) | **No (read-only)** | `GetItem` only; rejects non-GET |
| `apps/dashboard` Live Paper | Read-only | GET status API via `HttpAwsDryRunDataSource` |
| `portfolio_live` aiohttp | Read-only UI | Proxies status API; separate from Streamlit |

```text
Binance REST bootstrap (warmup bars)
  → Binance WS closed 1m bars (append)
  → StrategyModelLiveSignalEvaluator (AnalysisFrame + SignalModelEvaluator)
  → PaperBroker → DynamoDB PutItem
  → Status Lambda GetItem → GET /status → dashboard (read-only)
```

## Code path (worker)

1. [`scripts/execution/run_aws_btc_futures_worker.py`](../../scripts/execution/run_aws_btc_futures_worker.py)
2. `run_aws_btc_futures_dry_run_sync` → `run_local_btc_futures_binance_dry_run`
3. Bootstrap: `fetch_closed_klines` sized to `required_closed_bars_for_strategy`
4. Per closed 1m bar: append to rolling buffer → `run_local_btc_futures_closed_bar_step`
5. Signal: `StrategyModelLiveSignalEvaluator` (Market Analysis + `SignalModelEvaluator`)
6. Orders: `StrategyModelOrderAdapter` + `PaperBroker`
7. Persist: DynamoDB (`PutItem`) or local JSON

## Strategy Model evaluation (S032)

**Object:** live/AWS paper trading uses domain `StrategyModelDefinition` (same as
Strategy Research).

**Warmup:** `required_closed_bars_for_strategy` aggregates component
`history_requirement` via `max_history_requirement` and adds firing lookback
(+1 for `ON_TRUE_EDGE`). Under-warm buffers do not emit entries.

**Bootstrap:** Binance USD-M REST closed klines at start. If REST fails, the
buffer starts empty and signals stay gated until WebSocket history reaches the
required size.

**Append + recompute:** each closed WS bar is appended; the rolling window is
`max(required_bars, configured_cap)`. Each step fully recomputes the
`AnalysisFrame` over that window (no incremental component kernels yet).

**Exit:** still `_fixed_bar_exit_active` for `FixedBarsExitModel`.

**Follow-up debt:** true per-component incremental state if window recompute
becomes a bottleneck.

## Local smoke (no AWS credentials)

```powershell
uv run python scripts/execution/run_btc_futures_dry_run.py `
  --duration-minutes 0.5 `
  --max-messages 30 `
  --event-log user_data/runtime/btc_futures_dry_run/events.jsonl
```

Pass criteria:

- process exits 0 with `"simulated": true`
- bootstrap may seed closed bars before the first WS close
- event log / state directory updated under `user_data/runtime/...`

## Live AWS checklist (operator)

1. ECS task or EventBridge schedule running for the worker image.
2. DynamoDB item `pk=RUNTIME#<runtime_id>`, `sk=STATE` — fresh `last_heartbeat_at`.
3. `GET {STATUS_URL}` returns JSON with `simulated: true`, equity, bars.
4. If heartbeat is fresh but `recent_fills` stay empty for a long trend window,
   inspect worker logs — that is an **execution** issue, not a dashboard issue.
5. Never grant the status Lambda `PutItem`.

## Status API fields consumed by `apps/dashboard`

`runtime_id`, `status`, `symbol`, `last_heartbeat_at`, `last_market_event_at`,
`last_price`, `current_signal`, `current_position`, `paper_equity`,
`realized_pnl`, `unrealized_pnl`, `recent_orders`, `recent_fills`,
`recent_events`, `recent_bars`, `simulated`.
