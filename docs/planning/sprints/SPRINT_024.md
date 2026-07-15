# Sprint 024 - Dry-Run Reliability, Safety and Operating Polish

## Metadata

```text
Sprint: 024
Phase: Phase 8A - BTC Futures Live Dry-Run Execution Demo
Status: PLANNED
Planned Start: TBD
Planned End: TBD
Sprint Goal Owner: Project Maintainer
Depends On: SPRINT_023
Sprint Branch: sprint/btc-futures-dry-run-execution
Task branch convention: feat/ | fix/ | docs/ | test/
Architecture Sources:
  - docs/vision/ARCHITECTURE_TECHNICAL_UPDATED.md (Execution reliability and event handling)
  - docs/planning/ROADMAP.md (Phase 8 risks)
  - SPRINT_022.md
  - SPRINT_023.md
```

---

## 0. Slice Choice

After the live dry-run dashboard exists, this sprint turns it from a fragile demo into an operated
showcase: visible health, restart behavior, alarms, runbook and cost discipline.

**Out of scope:** new strategy features, real trading, multi-symbol portfolio, complex UI redesign,
distributed messaging.

---

## 1. Sprint Goal

```text
AWS dry-run worker
  -> resilient reconnects
  -> stale feed detection
  -> graceful shutdown
  -> CloudWatch alarms
  -> clear runbook
  -> portfolio architecture documentation
```

Success: the demo can be left running in AWS and failures become visible in logs, metrics, alarms and
the public dashboard.

---

## 2. MVP Scope Checklist

- [ ] Add stale feed detection separate from process heartbeat.
- [ ] Add graceful shutdown and final status write.
- [ ] Add reconnect metrics and last error reporting.
- [ ] Add CloudWatch alarm definitions for stale heartbeat/feed.
- [ ] Add operational runbook: deploy, stop, restart, inspect, rollback.
- [ ] Add public architecture page or section linked from dashboard.
- [ ] Add cost estimate and recommended schedule/always-on mode.
- [ ] Add retention/cleanup policy for DynamoDB events.
- [ ] Add failure-mode tests for stale feed and repository write failure.

---

## 3. Failure States

The runtime and dashboard must distinguish:

```text
RUNNING       process healthy, feed fresh
DEGRADED      process healthy, feed delayed/reconnecting
STALE         no recent heartbeat or no recent market data
STOPPED       graceful shutdown recorded
FAILED        unrecoverable error recorded
```

---

## 4. Task Breakdown

| Task | Outcome | Status |
|------|---------|--------|
| S024-T001 | Add feed freshness policy | TODO |
| S024-T002 | Add graceful shutdown status write | TODO |
| S024-T003 | Add reconnect and last-error metrics | TODO |
| S024-T004 | Add CloudWatch alarm definitions or documentation | TODO |
| S024-T005 | Add DynamoDB retention/cleanup policy | TODO |
| S024-T006 | Add operator runbook | TODO |
| S024-T007 | Add cloud architecture documentation page/section | TODO |
| S024-T008 | Add failure-mode tests | TODO |
| S024-T009 | Update portfolio dashboard for refined status states | TODO |

---

## 5. Acceptance Criteria

1. Runtime writes STOPPED on graceful shutdown.
2. Dashboard distinguishes process heartbeat freshness from market feed freshness.
3. CloudWatch alarm plan exists for stale runtime/feed.
4. Runbook lets a maintainer deploy, stop, restart and verify the demo.
5. Cost and retention policy are documented.
6. Quality gates pass.

---

## 6. Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Demo becomes expensive | Document always-on vs scheduled modes and retention |
| Failure states are ambiguous | Separate heartbeat, feed and repository health |
| Public dashboard hides real failures | Surface DEGRADED/STALE clearly |
| Operational docs drift | Keep runbook close to deployment scripts/config |

---

## 7. Post-Sprint Direction

Sprint 025 is optional and adds visual polish: charting, trade markers and a richer public narrative.
