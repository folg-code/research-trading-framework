# Live Paper / AWS Dry-Run Pipeline Inspection

Sprint 031 inspection notes. Confirms execution vs read-only boundaries and
Strategy Model ownership for paper trading visible in `apps/dashboard`.

## Architecture verdict

| Component | Full paper execution? | Notes |
|-----------|----------------------|-------|
| ECS worker (`run_aws_btc_futures_worker`) | **Yes** | Same engine as local: closed bar → signal → `PaperBroker` → persist |
| Status Lambda (`aws_status_api_handler`) | **No (read-only)** | `GetItem` only; rejects non-GET |
| `apps/dashboard` (before S031) | N/A | Stub `AwsDryRunDataSource` only |
| `portfolio_live` aiohttp | Read-only UI | Proxies status API; separate from Streamlit |

**User suspicion “AWS only listens”:** incorrect for the **worker**. Correct for the
**status API** (by design). Dashboard must stay read-only visualization.

```text
Binance WS → Worker (StrategyModel + PaperBroker + DynamoDB PutItem)
                 ↓
            DynamoDB state
                 ↓
         Status Lambda GetItem → GET /status → dashboard (read-only)
```

## Code path (worker)

1. [`scripts/execution/run_aws_btc_futures_worker.py`](../../scripts/execution/run_aws_btc_futures_worker.py)
2. `run_aws_btc_futures_dry_run_sync` → `run_local_btc_futures_binance_dry_run`
3. Per closed 1m bar: `run_local_btc_futures_closed_bar_step` in
   [`local_btc_futures.py`](../../src/trading_framework/application/execution/local_btc_futures.py)
4. Signal: `StrategyModelLiveSignalEvaluator` over `StrategyModelDefinition`
5. Orders: `StrategyModelOrderAdapter` + `PaperBroker`
6. Persist: DynamoDB (`PutItem`) or local JSON

## Strategy Model ownership (known bubel → S031 Wave D)

**Required:** live/AWS paper trading must use the domain
`StrategyModelDefinition` (Market × Signal × Exit × Risk) — the same object
Strategy Research simulates with `BarSequentialSimulator`.

**Before S031:** assembly already called `build_btc_futures_demo_strategy_model()`,
but live signal evaluation lived in a hand-specialized
`EmaMomentumLiveSignalEvaluator` that only understands one expression shape
(close > EMA). That is **not** a second AWS-only strategy type, but it is a
narrow live adapter rather than the full research evaluation stack
(`SignalModelEvaluator` + `AnalysisFrame`).

**S031 direction:**

- Canonical live type: `StrategyModelLiveSignalEvaluator(strategy_model=...)`.
- `EmaMomentumLiveSignalEvaluator` kept as a compatibility alias.
- Exit still driven from `FixedBarsExitModel` on the Strategy Model (via
  `_fixed_bar_exit_active` in the runtime assembly).
- Follow-up (not blocking Live Paper UI): incremental live eval via shared
  `SignalModelEvaluator` / AnalysisFrame for arbitrary signal expressions.

## Local smoke (no AWS credentials)

```powershell
uv run python scripts/execution/run_btc_futures_dry_run.py `
  --duration-minutes 0.5 `
  --max-messages 30 `
  --event-log user_data/runtime/btc_futures_dry_run/events.jsonl
```

Pass criteria:

- process exits 0 with `"simulated": true`
- `closed_bars` ≥ 0 (may be 0 if no closed 1m bar in the short window)
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
