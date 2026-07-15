# Sprint 021 - Execution Persistence and Read Model

## Metadata

```text
Sprint: 021
Phase: Phase 8A - BTC Futures Live Dry-Run Execution Demo
Status: PLANNED
Planned Start: TBD
Planned End: TBD
Sprint Goal Owner: Project Maintainer
Depends On: SPRINT_020
Sprint Branch: sprint/btc-futures-dry-run-execution
Task branch convention: feat/ | fix/ | docs/ | test/
Architecture Sources:
  - docs/vision/ARCHITECTURE_TECHNICAL_UPDATED.md (Execution persistence, Event System)
  - docs/planning/TECHNICAL_DEBT.md (TD-005 in-memory event bus)
```

---

## 0. Slice Choice

The local dry-run runtime needs a read model for dashboards and future cloud deployment. This sprint adds
persistence ports and a local adapter first, then shapes the model so DynamoDB can implement it in Sprint
022.

**Out of scope:** AWS infrastructure, public API Gateway, frontend dashboard, historical analytics,
full event sourcing.

---

## 1. Sprint Goal

```text
Dry-run runtime events
  -> ExecutionStateRepository port
  -> local JSON/SQLite adapter
  -> latest status read model
  -> recent event read model
  -> restart-safe local state
```

Success: the runtime can restart and expose current status, recent events, orders, fills, position and
paper equity through a read-only query interface.

---

## 2. MVP Scope Checklist

- [ ] Define write-side repository protocol for execution events and snapshots.
- [ ] Define read-side query protocol for dashboard status.
- [ ] Persist heartbeats, runtime status, recent events, orders, fills and position snapshots.
- [ ] Add a local JSON or SQLite adapter for development.
- [ ] Add retention policy for recent events.
- [ ] Add runtime restart behavior for last known position/equity.
- [ ] Add tests for repository round trip and read model freshness.
- [ ] Add CLI command to print latest read model as JSON.

---

## 3. Read Model Shape

```text
RuntimeStatusView
  mode
  provider
  symbol
  status
  last_heartbeat_at
  last_market_event_at
  last_price
  current_signal
  current_position
  paper_equity
  realized_pnl
  unrealized_pnl
  recent_orders
  recent_fills
  recent_events
```

Every field that describes trading activity must be labeled as simulated when applicable.

---

## 4. Module Boundary

```text
execution/repositories/       protocols and read models
infrastructure/storage/       local execution state adapter
application/execution/        write/read orchestration
scripts/execution/            inspect latest status CLI
```

### Binding Rules

```text
Dashboard reads through read model only.
Runtime write-side does not expose control actions.
Persistence is operational state, not Research output.
Local adapter is replaceable by DynamoDB in Sprint 022.
```

---

## 5. Task Breakdown

| Task | Outcome | Status |
|------|---------|--------|
| S021-T001 | Define execution repository protocols | TODO |
| S021-T002 | Define runtime status and recent-events read model | TODO |
| S021-T003 | Implement local persistence adapter | TODO |
| S021-T004 | Wire runtime event sink to repository | TODO |
| S021-T005 | Add restart restoration for position/equity | TODO |
| S021-T006 | Add read-model CLI JSON output | TODO |
| S021-T007 | Add repository and freshness tests | TODO |
| S021-T008 | Document persistence layout and retention | TODO |

---

## 6. Acceptance Criteria

1. Read model can be generated without running strategy logic.
2. Runtime can restart and continue from last simulated position snapshot.
3. Recent events retention is bounded.
4. Query code cannot submit orders or mutate runtime state.
5. Quality gates pass.

---

## 7. Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Local storage design does not map to DynamoDB | Keep repository item shapes simple and explicit |
| Dashboard needs too many ad hoc queries | Build one latest-status view and one recent-events view |
| Event log grows without bound | Retention policy in adapter |
| Read model hides stale runtime | Include freshness and heartbeat timestamps |

---

## 8. Post-Sprint Direction

Sprint 022 implements the AWS runtime MVP using ECS/Fargate, DynamoDB, CloudWatch and a read-only API.
