# Sprint 020 - Local BTC Futures Dry-Run Runtime

## Metadata

```text
Sprint: 020
Phase: Phase 8A - BTC Futures Live Dry-Run Execution Demo
Status: PLANNED
Planned Start: TBD
Planned End: TBD
Sprint Goal Owner: Project Maintainer
Depends On: SPRINT_018, SPRINT_019
Sprint Branch: sprint/btc-futures-dry-run-execution
Task branch convention: feat/ | fix/ | docs/ | test/
Architecture Sources:
  - docs/vision/ARCHITECTURE_FOUNDATIONS_UPDATED.md (Execution owns runtime state)
  - docs/vision/ARCHITECTURE_TECHNICAL_UPDATED.md (Clock, Event System, Execution modes)
  - docs/planning/TECHNICAL_DEBT.md (TD-005, TD-009)
```

---

## 0. Slice Choice

This sprint creates the first local runtime loop: live Binance BTCUSDT futures market data drives a
basic strategy and simulated broker. It is intentionally dry-run only.

**Out of scope:** AWS deployment, durable cloud persistence, real exchange account integration,
advanced strategy research, order-book fills, partial fills, portfolio support, web dashboard.

---

## 1. Sprint Goal

```text
Binance live BTCUSDT 1m bars
  -> LiveExecutionRuntime
  -> basic demo strategy
  -> OrderIntent
  -> SimulatedBroker
  -> SimulatedFill
  -> PaperPosition and PnL snapshot
  -> local event log
```

Success: a maintainer can run a local CLI for 30-60 minutes and observe a dry-run strategy producing
simulated orders, fills, positions, PnL snapshots and heartbeat events.

---

## 2. MVP Scope Checklist

- [ ] Implement `LiveExecutionRuntime` orchestration loop.
- [ ] Implement `SimulatedBroker` with marketable simulated fills.
- [ ] Implement a minimal BTCUSDT demo strategy.
- [ ] Consume closed 1m kline events for strategy decisions.
- [ ] Use `bookTicker` or last close as simulated reference fill price.
- [ ] Emit event log entries for signal, order intent, fill, position and heartbeat.
- [ ] Add local JSONL event sink for development.
- [ ] Add bounded runtime CLI with `--duration-minutes`.
- [ ] Add tests for order lifecycle and position accounting.

---

## 3. Strategy Choice

MVP strategy should be deliberately simple and transparent:

```text
BTCUSDT 1m demo momentum:
  - maintain short rolling close window
  - go long when close crosses above rolling mean by threshold
  - flatten when close crosses below rolling mean
  - max one position
  - fixed notional paper size
```

This is a runtime demo strategy, not a validated trading edge.

---

## 4. Module Boundary

```text
execution/runtime/            runtime loop and state machine
execution/broker_sim/         simulated broker and fill policy
execution/strategies/         demo strategy only if generic enough; otherwise application example
application/execution/        run BTC dry-run use case
scripts/execution/            local CLI
```

### Binding Rules

```text
Strategy is for demonstration only and must be labeled as unvalidated.
All fills are simulated and marked as such.
Runtime state is separate from Research datasets.
No real order API exists.
```

---

## 5. Task Breakdown

| Task | Outcome | Status |
|------|---------|--------|
| S020-T001 | Add runtime loop contract and implementation | TODO |
| S020-T002 | Add simulated broker with simple market-fill policy | TODO |
| S020-T003 | Add paper position and PnL accounting | TODO |
| S020-T004 | Add transparent BTCUSDT demo strategy | TODO |
| S020-T005 | Wire Binance feed -> runtime -> simulated broker | TODO |
| S020-T006 | Add local JSONL event sink | TODO |
| S020-T007 | Add CLI `run_btc_futures_dry_run.py` | TODO |
| S020-T008 | Add unit tests for lifecycle and accounting | TODO |
| S020-T009 | Add local operator documentation | TODO |

---

## 6. Acceptance Criteria

1. Runtime can run locally for a bounded duration without manual interaction.
2. Every order and fill in logs includes `simulated=true` or equivalent explicit marker.
3. Position accounting is deterministic in unit tests.
4. Runtime exposes heartbeat and current status.
5. The strategy is labeled as a demo strategy, not a research-validated model.
6. Quality gates pass.

---

## 7. Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Demo strategy appears like investment advice | Explicit unvalidated/demo labeling |
| Fill model becomes too realistic too soon | Keep simple market fill; document assumptions |
| Runtime loop accumulates responsibilities | Keep broker, strategy and event sink separate |
| Live feed outages break local demo | Status becomes DEGRADED; reconnect from Sprint 019 |

---

## 8. Post-Sprint Direction

Sprint 021 adds persistence and read-model APIs so the runtime can feed a dashboard without exposing the
write-side process.
