# Local BTC Futures Dry-Run

As-implemented operator notes for the local BTCUSDT USD-M futures dry-run demo.

This workflow uses live public Binance market data and simulated execution only. It does not read
Binance account credentials and it cannot place real orders.

---

## Run

```bash
uv run python scripts/execution/run_btc_futures_dry_run.py \
  --symbol BTCUSDT \
  --duration-minutes 30 \
  --event-log user_data/runtime/btc_futures_dry_run/events.jsonl
```

Short smoke run:

```bash
uv run python scripts/execution/run_btc_futures_dry_run.py \
  --duration-minutes 2 \
  --max-messages 20
```

The script prints a JSON summary:

```json
{
  "closed_bars": 2,
  "event": "summary",
  "event_log": "user_data/runtime/btc_futures_dry_run/events.jsonl",
  "ignored_messages": 1,
  "received_messages": 3,
  "runtime_id": "btc-futures-dry-run-local",
  "simulated": true,
  "status": "stopped",
  "symbol": "BTCUSDT"
}
```

---

## Data Flow

```text
Binance BTCUSDT kline_1m WebSocket
  -> Binance DTO parser and mapper
  -> canonical MarketBar
  -> rolling closed-bar history
  -> shared demo StrategyModelDefinition signal evaluation
  -> StrategyModelOrderAdapter
  -> PaperBroker
  -> JSONL execution events
```

The runtime only consumes closed `kline_1m` bars. Open klines, unsupported streams and symbol mismatches
are counted as ignored messages.

---

## Event Log

Default path:

```text
user_data/runtime/btc_futures_dry_run/events.jsonl
```

Expected event types:

- `runtime_started`
- `heartbeat_recorded`
- `market_event_received`
- `order_intent_created`
- `simulated_order_filled`
- `position_updated`
- `runtime_stopped`

Every order/fill/position lifecycle fact is simulated and includes a simulated marker in the payload.

---

## Useful Arguments

| Argument | Purpose |
|----------|---------|
| `--duration-minutes` | Bounded runtime duration. Must be positive. |
| `--heartbeat-seconds` | Heartbeat interval while the run is alive. |
| `--max-messages` | Optional cap for short smoke runs. |
| `--max-closed-bars` | Rolling closed-bar history retained for signal evaluation. |
| `--quantity` | Paper quantity used by the demo Strategy Model risk config. |
| `--ema-period` | EMA period used by the demo Strategy Model. |
| `--exit-after-bars` | Demo fixed-bars exit config. |

---

## Boundaries

- No real exchange orders.
- No Binance private API.
- No credentials.
- No AWS deployment in Sprint 020.
- The demo Strategy Model is unvalidated and must not be presented as a trading edge.

