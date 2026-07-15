# Sprint 023 - OVH Portfolio Live Dry-Run Dashboard

## Metadata

```text
Sprint: 023
Phase: Phase 8A - BTC Futures Live Dry-Run Execution Demo
Status: PLANNED
Planned Start: TBD
Planned End: TBD
Sprint Goal Owner: Project Maintainer
Depends On: SPRINT_022
Sprint Branch: sprint/btc-futures-dry-run-execution
Task branch convention: feat/ | fix/ | docs/ | test/
Architecture Sources:
  - scripts/demo/README.md
  - docs/reference/RESEARCH_METHODOLOGIES.md
  - SPRINT_022.md
```

---

## 0. Slice Choice

Static reports remain hosted on OVH/VPS as the public portfolio hub. This sprint adds a live read-only
dashboard page that fetches AWS dry-run status and makes the simulated nature of the execution explicit.

**Out of scope:** AWS runtime changes except API compatibility fixes, authenticated control panel,
real-time trading controls, private account views.

---

## 1. Sprint Goal

```text
OVH portfolio page
  -> fetch AWS read-only dry-run status
  -> render runtime health
  -> render live BTCUSDT market and strategy state
  -> render simulated orders/fills/positions/PnL
  -> label dry-run execution clearly
```

Success: a visitor can open the portfolio site and see that the BTC futures dry-run is using live market
data while all orders, fills, positions and PnL are simulated.

---

## 2. MVP Scope Checklist

- [ ] Add `live-dry-run` page to the portfolio/demo hub.
- [ ] Fetch AWS read-only status endpoint on an interval.
- [ ] Show runtime status: RUNNING, DEGRADED, STOPPED, STALE.
- [ ] Show provider, symbol, mode and last heartbeat.
- [ ] Show last price/current bar and latest strategy signal.
- [ ] Show current paper position and paper PnL.
- [ ] Show recent simulated orders/fills/events.
- [ ] Add prominent dry-run disclaimer.
- [ ] Add stale-data UI state when heartbeat is old.
- [ ] Add graceful fallback when AWS endpoint is unavailable.

---

## 3. Public Copy Requirement

The page must include clear visible text equivalent to:

```text
This demo uses live Binance BTCUSDT futures market data.
All orders, fills, positions and PnL are simulated.
No exchange account, API keys or real capital are connected.
```

---

## 4. Delivery Options

Choose one implementation path during the sprint:

| Option | Description | Notes |
|--------|-------------|-------|
| Static HTML/JS | Add a standalone page under generated `demo/output/` | Fastest path; simple OVH hosting |
| Small app shell | Add a lightweight frontend page for portfolio hub | Better polish if demo hub evolves |

No backend should run on OVH for MVP unless needed for CORS or caching.

---

## 5. Task Breakdown

| Task | Outcome | Status |
|------|---------|--------|
| S023-T001 | Define public status JSON contract consumed by UI | TODO |
| S023-T002 | Add live dry-run page shell | TODO |
| S023-T003 | Add polling client with stale/offline handling | TODO |
| S023-T004 | Add runtime status and market cards | TODO |
| S023-T005 | Add simulated execution cards and event log | TODO |
| S023-T006 | Add dry-run disclaimer and architecture link | TODO |
| S023-T007 | Add local fixture JSON for UI testing | TODO |
| S023-T008 | Add deployment notes for OVH/VPS static hosting | TODO |

---

## 6. Acceptance Criteria

1. Dashboard is read-only and has no controls.
2. Simulated execution is obvious on first view.
3. UI handles stale heartbeat and API outage.
4. Page can be hosted statically on OVH/VPS.
5. Public status payload contains no secrets or private infrastructure details.
6. Quality checks for touched code/assets pass.

---

## 7. Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Visitor mistakes dry-run for real trading | Prominent disclaimer and simulated labels on every relevant card |
| AWS outage makes portfolio look broken | Stale/offline state with explanatory copy |
| Static page needs secrets | Public read-only endpoint only; no credentials in browser |
| UI overpromises strategy quality | Copy says demo strategy is unvalidated |

---

## 8. Post-Sprint Direction

Sprint 024 hardens reliability, safety and operating documentation so the demo can stay online without
constant manual babysitting.
