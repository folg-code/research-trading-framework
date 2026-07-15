# Sprint 018 - Live Dry-Run Execution Planning and Contracts

## Metadata

```text
Sprint: 018
Phase: Phase 8A - BTC Futures Live Dry-Run Execution Demo
Status: PLANNED
Planned Start: TBD
Planned End: TBD
Sprint Goal Owner: Project Maintainer
Depends On: SPRINT_013-017 merged to main; Execution and Events packages are skeletons
Sprint Branch: sprint/btc-futures-dry-run-execution
Task branch convention: feat/ | fix/ | docs/ | test/ (separate prefix, not nested under sprint ref)
Wave 0 decisions: docs/planning/sprints/S018_WAVE0_DECISIONS.md (to be created)
Architecture Sources:
  - docs/planning/ROADMAP.md (Phase 8 - Replay and Paper Execution)
  - docs/vision/ARCHITECTURE_FOUNDATIONS_UPDATED.md (Execution domain)
  - docs/vision/ARCHITECTURE_TECHNICAL_UPDATED.md (Replay, Event System, Execution config)
  - docs/planning/PROBLEM_REGISTRY.md (PRB-013 research/runtime parity)
  - docs/planning/TECHNICAL_DEBT.md (TD-005 in-memory event bus, TD-009 limited fills)
External Sources:
  - Binance USD-M Futures public WebSocket market streams
```

---

## 0. Slice Choice

The framework has mature Research workflows but no implemented Strategy Execution runtime. This sprint
starts the smallest responsible Execution increment: a **live-data, simulated-execution dry run** for
BTCUSDT USD-M futures.

The sprint does not connect to a real exchange account. It creates contracts and boundaries that make
that impossible by default.

```text
Live market data
  -> execution runtime contracts
  -> simulated orders and fills
  -> read-only status
```

**Out of scope:** AWS deployment, Binance WebSocket implementation, real order submission, API keys,
paper account integration, live broker adapters, position sizing research, dashboard UI.

---

## 1. Sprint Goal

```text
ExecutionMode.DRY_RUN
  -> ExecutionEvent contracts
  -> OrderIntent / SimulatedOrder / SimulatedFill
  -> PaperPosition / PaperAccountSnapshot
  -> explicit no-real-orders safety boundary
  -> unit tests and architecture docs
```

Success: a maintainer can inspect the Execution contracts and see exactly how live market data will be
converted into simulated order lifecycle events without coupling Execution to Research artifacts or real
exchange credentials.

---

## 2. MVP Scope Checklist

- [ ] Define `ExecutionMode` with `DRY_RUN` as the only supported runtime mode in this increment.
- [ ] Define immutable execution event base contracts.
- [ ] Define order intent, simulated order, simulated fill and position snapshots.
- [ ] Define a minimal account/equity snapshot for simulated PnL.
- [ ] Define runtime status and heartbeat contracts for public read models.
- [ ] Add negative safety tests proving no real order adapter exists in this slice.
- [ ] Add architecture boundary tests for Execution not importing Research workflows.
- [ ] Document dry-run semantics: live market data, simulated execution, no funds at risk.
- [ ] Record open questions for Phase 8B Paper Execution.

---

## 3. Domain Boundary

```text
execution/
  models/                 execution events, orders, fills, positions, account snapshots
  modes.py                DRY_RUN mode contract
  safety.py               explicit no-real-order policy
  protocols.py            runtime and repository protocols

events/
  models/                 optional generic immutable event primitives

application/execution/    deferred until runtime orchestration sprint
infrastructure/           no Binance or AWS implementation in this sprint
```

### Binding Rules

```text
Execution must not read Signal Research, Strategy Research or Robustness outputs.
Dry-run execution may consume Strategy Model definitions, not research rankings.
No Binance account API keys are required or accepted.
All orders, fills, positions and PnL are simulated.
Domain contracts must remain provider-independent.
```

---

## 4. Task Breakdown

| Task | Outcome | Status |
|------|---------|--------|
| S018-T001 | Create Wave 0 decisions document for BTC futures dry-run scope | TODO |
| S018-T002 | Create ADR draft for Live Dry-Run Execution Demo | TODO |
| S018-T003 | Add Execution mode and safety contracts | TODO |
| S018-T004 | Add execution event, order, fill and position models | TODO |
| S018-T005 | Add runtime status and heartbeat read-model contracts | TODO |
| S018-T006 | Add unit tests for lifecycle invariants and UTC timestamps | TODO |
| S018-T007 | Add architecture boundary tests for Execution dependencies | TODO |
| S018-T008 | Update MODULE_MAP / DATA_WORKFLOWS only for new public contracts | TODO |

---

## 5. Acceptance Criteria

1. Execution models reject naive datetimes.
2. Dry-run contracts contain no real exchange order submission path.
3. Execution domain does not import `research`, concrete `infrastructure`, or `user_data`.
4. Public status model can represent RUNNING, DEGRADED, STOPPED and STALE states.
5. Quality gates pass:

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run pytest
```

---

## 6. Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Execution contracts become too broad | Keep only dry-run lifecycle needed by BTCUSDT demo |
| Research/Execution coupling sneaks in | Boundary tests and explicit dependency review |
| Simulated execution is confused with real trading | Naming, docs and status model label every fill as simulated |
| Runtime design overfits Binance | Provider-independent domain models; Binance only in later infrastructure sprint |

---

## 7. Post-Sprint Direction

Sprint 019 implements the Binance USD-M futures live data adapter for BTCUSDT and maps provider
payloads into the provider-independent contracts established here.
