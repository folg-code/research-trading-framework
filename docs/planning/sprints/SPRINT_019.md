# Sprint 019 - Binance BTC Futures Live Data Adapter

## Metadata

```text
Sprint: 019
Phase: Phase 8A - BTC Futures Live Dry-Run Execution Demo
Status: COMPLETE
Planned Start: TBD
Planned End: TBD
Sprint Goal Owner: Project Maintainer
Depends On: SPRINT_018
Sprint Branch: sprint/btc-futures-dry-run-execution
Task branch convention: feat/ | fix/ | docs/ | test/
Architecture Sources:
  - SPRINT_018.md
  - docs/vision/ARCHITECTURE_TECHNICAL_UPDATED.md (provider schemas normalize at boundaries)
  - docs/reference/DATA_WORKFLOWS.md (Market Data boundary patterns)
External Sources:
  - Binance USD-M Futures public WebSocket market streams
```

---

## 0. Slice Choice

This sprint adds live BTCUSDT USD-M futures market data ingestion without strategy execution. It proves
that the framework can maintain a live provider connection, normalize provider payloads and emit runtime
market facts suitable for a dry-run execution loop.

Target streams for MVP:

```text
btcusdt@kline_1m       -> closed 1m MarketBar candidates
btcusdt@bookTicker     -> best bid/ask snapshot for simulated fill references
```

**Out of scope:** depth book reconstruction, authenticated user streams, order submission, AWS deploy,
strategy runtime, persistence beyond smoke logs.

---

## 1. Sprint Goal

```text
Binance USD-M WebSocket
  -> provider payload DTOs
  -> UTC normalization
  -> provider-independent live market events
  -> feed heartbeat and reconnect policy
  -> local smoke CLI
```

Success: a maintainer can run a local smoke command for BTCUSDT and observe live futures bars and
book ticker snapshots being normalized without leaking Binance-specific schemas into domain logic.

---

## 2. MVP Scope Checklist

- [ ] Implement a small WebSocket client wrapper for Binance USD-M public streams.
- [ ] Parse combined or raw stream payloads for `kline_1m` and `bookTicker`.
- [ ] Convert exchange timestamps to UTC-aware datetimes.
- [ ] Emit provider-independent live bar and quote snapshot objects.
- [ ] Track feed status: connected, last message time, reconnect count, last error.
- [ ] Add reconnect with bounded exponential backoff.
- [ ] Add a local smoke CLI that runs for a bounded duration.
- [ ] Add unit tests for payload parsing using committed fixture payloads.
- [ ] Add integration-style smoke test that can be skipped by default if network is unavailable.

---

## 3. Module Boundary

```text
infrastructure/providers/binance/
  futures_streams.py         routed stream specs and combined-stream URL building
  aiohttp_websocket.py       aiohttp transport adapter
  futures_websocket.py       transport-agnostic client with reconnect
  futures_payloads.py        provider DTO parsing
  futures_mapper.py          provider -> framework runtime market facts
  futures_reconnect.py       bounded reconnect policy
  futures_smoke.py           bounded local smoke runner

execution/models/market_data.py
                              provider-independent live market facts and feed status
application/execution/       still minimal; no strategy runtime yet
```

### Binding Rules

```text
Provider payload models stay in infrastructure.
Domain/application code sees canonical runtime market facts only.
No private Binance API endpoint is used.
No Binance account credentials are read.
Network-dependent tests are opt-in.
```

---

## 4. Task Breakdown

| Task | Outcome | Status |
|------|---------|--------|
| S019-T001 | Add Binance futures provider package skeleton | DONE |
| S019-T002 | Add payload fixtures for `kline_1m` and `bookTicker` | DONE |
| S019-T003 | Implement payload parsing and UTC normalization | DONE |
| S019-T004 | Implement WebSocket subscription client with reconnect | DONE |
| S019-T005 | Add feed status and heartbeat model | DONE |
| S019-T006 | Add local smoke CLI for BTCUSDT feed | DONE |
| S019-T007 | Add unit tests for parser and mapper | DONE |
| S019-T008 | Add opt-in network smoke test marker | DONE |
| S019-T009 | Update docs/reference for provider boundary | DONE |

---

## 5. Acceptance Criteria

1. `btcusdt@kline_1m` closed-bar events can be normalized into UTC canonical bar facts.
2. `btcusdt@bookTicker` can be normalized into a best bid/ask snapshot.
3. The client reconnects after connection loss and records reconnect count.
4. The smoke CLI runs for a bounded duration and exits cleanly.
5. No test in standard CI requires network access.
6. Quality gates pass.

---

## 6. Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Binance schema changes | Keep fixtures, mapper tests and provider boundary narrow |
| Network flakiness in CI | Opt-in smoke marker only |
| Too much order-book scope | Use bookTicker only; defer depth streams |
| Runtime blocked by WebSocket library choice | Use a minimal adapter and keep interface small |

---

## 7. Post-Sprint Direction

Sprint 020 consumes the live BTCUSDT market facts in a local dry-run execution loop with a basic
strategy and simulated broker.

---

## 8. Completion Notes

Sprint 019 delivered a Binance USD-M futures live-data adapter for public BTCUSDT streams.
Provider-specific payloads, routed endpoints and `aiohttp` transport stay under
`infrastructure/providers/binance/`. The normalized boundary is provider-independent:

```text
Binance combined stream payload
  -> Binance DTO parser
  -> mapper
  -> MarketBar / BestBidAskSnapshot / MarketFeedStatusSnapshot
```

Local smoke command:

```bash
uv run python scripts/live_data/run_binance_futures_smoke.py \
  --symbol BTCUSDT --duration-seconds 10 --max-messages 20
```

Network smoke test is opt-in and skipped by default:

```bash
TRADING_FRAMEWORK_RUN_BINANCE_NETWORK_SMOKE=1 \
  uv run pytest tests/integration/live_data/test_binance_futures_network_smoke.py
```
