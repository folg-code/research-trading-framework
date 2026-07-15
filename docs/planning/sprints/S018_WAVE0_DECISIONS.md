# Sprint 018 - Wave 0 Architecture Decisions (BTC Futures Dry-Run Execution)

## Metadata

```text
Task: S018-T001
Sprint: 018 - Live Dry-Run Execution Planning and Contracts
Status: ACCEPTED (planning)
Planned Start: 2026-07-15
Branch: sprint/btc-futures-dry-run-execution
Direction: docs/planning/sprints/SPRINT_018.md
Depends on: SPRINT_013-017 merged to main; Execution and Events packages are skeletons
Scope: provider-independent dry-run Execution contracts for BTCUSDT live-data demo
```

---

## 0. Rationale

The framework has mature historical Research workflows, but Strategy Execution is still a skeleton.
The next useful portfolio increment is not real trading. It is a public, responsible dry-run demo:

```text
live Binance BTCUSDT futures market data
  -> framework runtime loop
  -> simulated orders, fills, positions and PnL
  -> read-only dashboard
```

Sprint 018 starts with contracts only. It creates the Execution vocabulary and safety boundary before
provider code, AWS deployment, persistence or UI are added.

---

## 1. Increment and naming

**Decision D-S018-01:** This increment is named **Phase 8A - BTC Futures Live Dry-Run Execution Demo**.

It is an Execution-track slice, not a Research workflow. It must preserve the architectural rule that
Execution does not depend on Signal Research, Strategy Research, Robustness Research, rankings or reports.

Supported MVP mode:

```text
DRY_RUN - live market data, simulated execution only
```

`PAPER` and `LIVE` modes remain future work.

---

## 2. Instrument and provider direction

**Decision D-S018-02:** The portfolio runtime demo targets **BTCUSDT USD-M futures** on Binance.

Reason:

```text
BTC futures has 24/7 public market data, high liquidity, easy demo availability and no paid CME feed gate.
```

Sprint 018 remains provider-independent. Binance implementation starts in Sprint 019 under
`infrastructure/providers/binance/`.

---

## 3. Safety boundary

**Decision D-S018-03:** Sprint 018 must make real order submission impossible by construction.

Binding rules:

```text
No Binance account API keys.
No private exchange endpoints.
No order submission adapter.
No public write/control endpoint.
All fills are simulated and explicitly marked as simulated.
All positions and PnL are paper state.
```

The public portfolio copy must say: live market data, simulated execution, no exchange account, no real
capital.

---

## 4. Contract shape

**Decision D-S018-04:** Introduce provider-independent Execution contracts before concrete runtime code.

Minimum domain vocabulary:

```text
ExecutionMode
ExecutionEvent
OrderIntent
SimulatedOrder
SimulatedFill
PaperPosition
PaperAccountSnapshot
RuntimeStatusSnapshot
Heartbeat
```

These models reject naive datetimes and use UTC internally.

---

## 5. Event semantics

**Decision D-S018-05:** Execution events are immutable facts about the dry-run runtime.

Examples:

```text
runtime_started
market_event_received
signal_generated
order_intent_created
simulated_order_filled
position_updated
heartbeat_recorded
runtime_stopped
```

Events are not commands. A command or order intent represents requested simulated action; an event records
what happened.

---

## 6. Status model

**Decision D-S018-06:** Public runtime status supports at least:

```text
RUNNING
DEGRADED
STALE
STOPPED
FAILED
```

Sprint 018 defines the status vocabulary only. Sprint 024 refines operational health rules.

---

## 7. Strategy scope

**Decision D-S018-07:** Sprint 018 does not define a trading strategy.

Later sprint direction:

```text
Sprint 020 - transparent BTCUSDT demo strategy
```

The first strategy must be labeled as a demo runtime strategy, not a validated trading edge.

---

## 8. Module ownership

**Decision D-S018-08:** Initial module layout:

```text
execution/
  modes.py
  safety.py
  protocols.py
  models/
    events.py
    orders.py
    positions.py
    account.py
    status.py
```

Infrastructure adapters, AWS adapters and dashboard code are deferred to later sprints.

---

## 9. Persistence and read model

**Decision D-S018-09:** Sprint 018 only defines models needed for a future read model.

Persistence implementation order:

```text
Sprint 021 - local repository/read model
Sprint 022 - DynamoDB adapter and read-only API
Sprint 023 - OVH portfolio dashboard
```

---

## 10. Out of scope

Binding exclusions:

```text
Binance WebSocket client
AWS deployment
OVH dashboard
real exchange orders
authenticated Binance APIs
live broker adapter
order-book reconstruction
partial fills
multi-symbol portfolio
research ranking or robustness consumption
```

---

## 11. Decision index

| ID | Summary |
|----|---------|
| D-S018-01 | Phase 8A is a dry-run Execution demo, not Research |
| D-S018-02 | BTCUSDT USD-M futures is the demo target; Sprint 018 stays provider-independent |
| D-S018-03 | Real order submission is impossible in this slice |
| D-S018-04 | Define provider-independent Execution contracts first |
| D-S018-05 | Execution events are immutable facts, not commands |
| D-S018-06 | Public runtime status includes RUNNING / DEGRADED / STALE / STOPPED / FAILED |
| D-S018-07 | Strategy implementation deferred to Sprint 020 |
| D-S018-08 | Initial contracts live under `execution/` models, modes, safety and protocols |
| D-S018-09 | Persistence/read implementation deferred to Sprints 021-023 |

---

## 12. References

- `docs/planning/sprints/SPRINT_018.md`
- `docs/adr/ADR-0021-live-dry-run-execution-demo.md`
- `docs/planning/ROADMAP.md`
- `docs/vision/ARCHITECTURE_FOUNDATIONS_UPDATED.md`
- `docs/vision/ARCHITECTURE_TECHNICAL_UPDATED.md`
- `docs/planning/PROBLEM_REGISTRY.md` - PRB-013
- `docs/planning/TECHNICAL_DEBT.md` - TD-005, TD-009
