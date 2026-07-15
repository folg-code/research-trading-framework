# ADR-0021 - Live Dry-Run Execution Demo

## Status

ACCEPTED (Sprint 018)

## Context

The framework has completed historical market data, Market Analysis, Signal Research, Strategy Research,
Robustness Research and Model Research Methodology increments. Strategy Execution remains a future
capability.

The project also needs a public portfolio demonstration that shows cloud/runtime engineering without
claiming real trading readiness. Static HTML reports show research depth, but they do not show a live
runtime loop.

The first runtime demo should therefore be:

```text
live market data
  -> runtime evaluation
  -> simulated order lifecycle
  -> read-only status
```

It must not connect to a real account or place orders.

## Decision

### Increment identity

Introduce **Phase 8A - BTC Futures Live Dry-Run Execution Demo** as the first Strategy Execution
increment.

This increment is separate from Strategy Research. It may reuse Strategy Model definitions later, but it
must not consume Research workflow state, rankings, reports or robustness verdicts at runtime.

### Runtime mode

Sprint 018 introduces one supported execution mode:

```text
DRY_RUN
```

Meaning:

```text
market data: live
orders: simulated
fills: simulated
positions: paper state
PnL: paper state
exchange account: none
real capital: none
```

Future `PAPER` and `LIVE` modes require separate ADRs or phase-entry decisions.

### Demo provider and instrument

The live-data demo targets Binance USD-M futures `BTCUSDT`.

Rationale:

- public market data is available without paid CME infrastructure,
- BTCUSDT trades continuously, which is useful for public demos,
- it avoids exposing proprietary NQ datasets or paid market-data credentials,
- it exercises live runtime boundaries while keeping the data-provider adapter replaceable.

Provider schemas remain infrastructure concerns. Domain and application Execution code must depend on
provider-independent contracts.

### Safety boundary

The dry-run increment must not contain a real order path.

Binding rules:

```text
No Binance account API keys are required or accepted.
No private exchange endpoint is needed.
No real order adapter exists in Sprint 018.
No public endpoint can mutate runtime state.
Every simulated order, fill, position and PnL value is explicitly marked as simulated or paper.
```

### Contract vocabulary

Sprint 018 defines provider-independent contracts for:

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

All timestamps are UTC-aware. Naive datetimes are rejected.

### Status and read model direction

The public status vocabulary includes:

```text
RUNNING
DEGRADED
STALE
STOPPED
FAILED
```

Sprint 018 defines the vocabulary. Later sprints implement:

```text
Sprint 021 - local persistence and read model
Sprint 022 - AWS runtime and DynamoDB adapter
Sprint 023 - OVH public dashboard
Sprint 024 - operational hardening
```

### Module layout

Initial target layout:

```text
src/trading_framework/execution/
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

Concrete Binance and AWS code belongs to infrastructure or deployment-specific modules in later sprints.

## Consequences

### Positive

- Creates a responsible live-runtime portfolio path without real trading risk.
- Keeps Execution separate from Research outputs.
- Allows AWS runtime work to build on stable provider-independent contracts.
- Makes simulated execution explicit in code, tests and public dashboard language.

### Negative / trade-offs

- The first runtime strategy will be a demo strategy, not a validated edge.
- BTCUSDT differs from the framework's NQ research narrative, so docs must explain the provider choice.
- Dry-run fills may be useful for runtime demonstration but not for execution-quality claims.
- Additional ADRs may be needed before true Paper or Live Execution.

### Out of scope

```text
real exchange order submission
authenticated Binance trading APIs
broker adapters
order-book reconstruction
partial fills
portfolio execution
AWS deployment
public dashboard implementation
research-to-execution promotion policy
```

## References

- `docs/planning/sprints/SPRINT_018.md`
- `docs/planning/sprints/S018_WAVE0_DECISIONS.md`
- `docs/planning/ROADMAP.md`
- `docs/vision/ARCHITECTURE_FOUNDATIONS_UPDATED.md`
- `docs/vision/ARCHITECTURE_TECHNICAL_UPDATED.md`
- `docs/planning/PROBLEM_REGISTRY.md` - PRB-013
- `docs/planning/TECHNICAL_DEBT.md` - TD-005, TD-009
