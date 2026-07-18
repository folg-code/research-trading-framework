# Sprint 024 - Dry-Run Reliability Wiring (re-scoped)

## Metadata

```text
Sprint: 024
Phase: Phase 8A - BTC Futures Live Dry-Run Execution Demo
Status: PLANNED (RE-SCOPED 2026-07-18)
Planned Start: TBD
Planned End: TBD
Sprint Goal Owner: Project Maintainer
Depends On: SPRINT_022/023 on main; Streamlit Live Paper (S031–S034) as UI surface
Sprint Branch: sprint/dry-run-reliability-polish
Task branch convention: feat/ | fix/ | docs/ | test/
Architecture Sources:
  - docs/reference/AWS_BTC_FUTURES_DRY_RUN.md
  - apps/dashboard/docs/RUNBOOK.md
  - docs/planning/sprints/SPRINT_035.md
Supersedes earlier draft assumptions:
  - OVH HTML “portfolio dashboard” (S023) → legacy; target is apps/dashboard Live Paper
  - Shared branch sprint/btc-futures-dry-run-execution → use dedicated sprint branch
```

---

## 0. Audit vs current project (2026-07-18)

S024 was drafted **before** Streamlit+VPS became the primary UI and **after** much of AWS
ops docs already landed in Sprint 022. Resuming the original checklist as-written would
re-implement delivered work and target the wrong dashboard.

### Already delivered (do not re-open as greenfield)

| Original item | Where it landed |
|---|---|
| CloudWatch stale-heartbeat alarm spec | `docs/reference/AWS_BTC_FUTURES_DRY_RUN.md` (S022-T006) |
| Operator runbook (deploy/stop/restart/inspect/rollback) | same doc (S022-T007/T008) |
| Cost estimate + scheduled vs always-on modes | same doc (S022-T009) |
| Dashboard-side ops runbook | `apps/dashboard/docs/RUNBOOK.md` (S025+) |
| `RuntimeHealth` enum (`RUNNING`/`DEGRADED`/`STALE`/`STOPPED`/`FAILED`) | `execution/models/status.py` |
| Binance WS `reconnect_count` / `last_error` | `infrastructure/providers/binance/` (S019) |
| Local session `stop()` → `STOPPED` on bounded completion | `execution/runtime/session.py` |

### Still open (real remaining work)

| Theme | Gap |
|---|---|
| Feed freshness ≠ heartbeat | Enum exists; nothing assigns `DEGRADED`/`STALE` from feed age. Dashboard stale = heartbeat-only. |
| Wire reconnect / last_error to status API | Built on client; not persisted / not in status JSON / not on Live Paper. |
| Graceful stop under ECS signals | No SIGTERM/SIGINT handler on AWS worker; cancel path may skip final status write. |
| DynamoDB retention / TTL | Single-item doc; no TTL / cleanup policy in code or ops docs. |
| Failure-mode tests | No stale-feed / repository-write-failure tests on the AWS worker path. |
| Live Paper status vocabulary | Streamlit badges partial (`Running`/`Stale`/…); no `DEGRADED`; not driven by feed freshness. |
| Architecture one-pager (optional) | Overview links GitHub README; no dedicated public architecture page. |

---

## 1. Re-scoped sprint goal

```text
AWS dry-run worker + status API + Streamlit Live Paper
  -> feed freshness and heartbeat are separate signals
  -> reconnect / last_error visible on status snapshot
  -> SIGTERM/SIGINT writes STOPPED (or FAILED on hard error)
  -> Live Paper badges use RuntimeHealth vocabulary
  -> DynamoDB retention policy documented (+ TTL if cheap)
  -> failure-mode tests for stale feed and status write failure
```

Success: a recruiter (or maintainer) can tell **process alive vs market feed healthy** on
https://dashboard.filipf.online Live Paper, and an ECS stop leaves a clear terminal status.

**Out of scope:** new strategies, real trading, multi-symbol portfolio, dashboard shell redesign,
re-writing CloudWatch/runbook/cost docs already in `AWS_BTC_FUTURES_DRY_RUN.md` (extend only).

---

## 2. MVP checklist (re-scoped)

- [ ] Persist feed freshness (and/or derive `DEGRADED`/`STALE`) separately from process heartbeat.
- [ ] Surface Binance `reconnect_count` / `last_error` on the status snapshot consumed by the dashboard.
- [ ] AWS worker handles SIGTERM/SIGINT with final status write (`STOPPED` / `FAILED`).
- [ ] Streamlit Live Paper distinguishes RUNNING / DEGRADED / STALE / STOPPED / FAILED using status fields (not heartbeat-only heuristic).
- [ ] Document DynamoDB retention (and implement TTL if it fits the single-item model).
- [ ] Add failure-mode tests: stale feed transition; status repository write failure.
- [ ] Extend existing AWS runbook with DEGRADED/reconnect investigation notes (do not rewrite from scratch).
- [ ] Optional: short architecture one-pager linked from Project Overview.

---

## 3. Failure states (unchanged contract — need behaviour)

```text
RUNNING       process healthy, feed fresh
DEGRADED      process healthy, feed delayed/reconnecting
STALE         no recent heartbeat or no recent market data (policy-defined)
STOPPED       graceful shutdown recorded
FAILED        unrecoverable error recorded
```

---

## 4. Task breakdown (re-scoped)

| Task | Outcome | Status |
|------|---------|--------|
| S024-T001 | Feed freshness policy → RuntimeHealth transitions | DONE (Wave 1: `resolve_runtime_health` + heartbeat wiring) |
| S024-T002 | AWS worker SIGTERM/SIGINT + final status write | DONE (Wave 1: cancel→STOPPED, exception→FAILED, signal handlers) |
| S024-T003 | Persist/expose reconnect_count + last_error on status API | DONE (Wave 2) |
| S024-T004 | CloudWatch alarm docs | DONE (S022) — verify only; optional feed-specific alarm note |
| S024-T005 | DynamoDB retention / TTL policy | TODO |
| S024-T006 | Operator runbook | DONE (S022) — extend for DEGRADED/reconnect |
| S024-T007 | Architecture one-pager / Overview link | OPTIONAL |
| S024-T008 | Failure-mode tests (stale feed, status write failure) | PARTIAL (cancel→STOPPED + health policy tests; write-failure still open) |
| S024-T009 | Streamlit Live Paper status vocabulary (replace OVH portfolio target) | DONE (Wave 2) |

Suggested PR waves into `sprint/dry-run-reliability-polish`:

1. Worker: feed freshness + SIGTERM/SIGINT final status + tests  
2. Status API / snapshot fields: reconnect + last_error + health  
3. Live Paper badges + captions driven by those fields  
4. Docs: retention + runbook addendum (+ optional architecture page)

---

## 5. Acceptance criteria (re-scoped)

1. ECS-style stop results in persisted `STOPPED` (or `FAILED` on hard error).  
2. Live Paper can show feed-vs-heartbeat distinction (at least DEGRADED or explicit feed-age caption).  
3. Status snapshot exposes reconnect/last_error when available.  
4. Existing CloudWatch heartbeat alarm + runbook remain valid; retention policy is documented.  
5. Failure-mode unit/integration tests cover stale-feed transition and status write failure.  
6. Quality gates pass.

---

## 6. Risks

| Risk | Mitigation |
|------|------------|
| Rebuilding delivered S022 docs | Mark T004/T006 DONE; only extend |
| Dashboard still heartbeat-only | Treat T009 as required for public demo honesty |
| Cost of always-on worker | Keep scheduled mode from existing cost section |

---

## 7. Post-sprint direction

Further Phase 8 Replay foundation (roadmap §12) remains a **separate** larger track.
Do not bundle orderflow (4B) or multi-data strategy (6B) into this sprint.
