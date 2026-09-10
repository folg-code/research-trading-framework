# Sprint 062: BTC Futures Dry-Run on VPS and Dashboard Status Card

Status: Approved (2026-09-10) — implementation may proceed; the actual VPS
deploy/rollback in T007 requires a separate explicit maintainer go-ahead before
it is executed.
Goal: Run the existing BTCUSDT live-market/simulated-execution `DRY_RUN` safely
on the dashboard VPS, expose one private-network GET-only status service, and
show an unmistakably simulated current-status card in the public dashboard.
Sources:

- `docs/adr/ADR-0021-live-dry-run-execution-demo.md`
- `docs/adr/ADR-0035-vps-dry-run-runtime-and-status-boundary.md` (T001 output)
- `docs/reference/workflows/STRATEGY_EXECUTION.md`
- `docs/reference/runbooks/LOCAL_BTC_FUTURES_DRY_RUN.md`
- `docs/reference/runbooks/AWS_BTC_FUTURES_DRY_RUN.md`
- `docs/reference/runbooks/LIVE_PAPER_PIPELINE_INSPECTION.md`
- `apps/dashboard/docs/RUNBOOK.md`
- `apps/dashboard/src/dashboard_app/datasources/live_paper_http.py`
- `docs/planning/sprints/SPRINT_024.md`
- `docs/planning/sprints/SPRINT_025.md`

Architecture triage: required. This is a deployment/runtime adaptation across
Execution, Infrastructure and Dashboard. It must reuse provider-independent
execution contracts and must not introduce `PAPER`/`LIVE`, authenticated Binance
APIs or a public command surface. A new deployment ADR or a narrowly scoped
ADR-0021 amendment requires maintainer approval before T002.

## Scope

In scope:

- A provider-neutral VPS runtime configuration and entry point for the existing
  BTCUSDT Binance public-feed dry-run.
- Durable local JSON execution-state storage on a dedicated VPS volume.
- Graceful start, stop, restart and crash behavior under Docker Compose.
- A small GET-only status service reading the existing execution read model.
- Internal Compose networking between dashboard and status service.
- Worker/status health checks, resource/log limits, stale-state handling and
  operator rollback/recovery documentation.
- A first-view dashboard card showing runtime/feed health, last heartbeat,
  symbol, paper position/PnL and explicit simulation labels.
- Deployment to the existing VPS and a bounded soak/acceptance observation.

Out of scope:

- Real orders, API keys, private Binance endpoints, broker adapters or capital.
- New strategy logic, strategy validation or claims of trading performance.
- Research-to-runtime promotion, Phase 14B or scorer integration.
- Multiple symbols, multiple accounts, public session history or control buttons.
- Replacing the dashboard deployment stack or shared edge TLS architecture.

## Decisions

| Decision | Recommendation | Status |
|---|---|---|
| D062-01 — runtime mode | Reuse ADR-0021 `DRY_RUN`: live public Binance BTCUSDT data, `PaperBroker`, simulated orders/fills/positions/PnL, no exchange account and no accepted credentials. | Inherited; non-negotiable |
| D062-02 — VPS adapter | Add a provider-neutral VPS config/entry point over the existing application runtime and `JsonExecutionStateRepository`; do not rename or overload the AWS-specific config as the permanent VPS API. | Approved by maintainer (2026-09-10) |
| D062-03 — status exposure | Run a dedicated GET-only status service on the private Compose network. The dashboard calls it internally; do not publish a mutation endpoint or expose raw state files. | Approved by maintainer (2026-09-10) |
| D062-04 — lifecycle | Support an explicit service lifetime suitable for Compose and preserve graceful `STOPPED`/hard-error `FAILED`. Restart must restore compatible paper state or fail visibly; it must never silently reset an open paper position. | Approved by maintainer (2026-09-10) |

Detailed freeze of topology, state ownership, public status schema v1,
lifecycle/recovery and threat model: `docs/adr/ADR-0035-vps-dry-run-runtime-and-status-boundary.md`
(ACCEPTED by maintainer 2026-09-10 — T002/T003 unblocked).

## Tasks

| Task | Outcome | Dependencies | Ownership | Risk | Status | PR |
|---|---|---|---|---|---|---|
| T001 | Freeze VPS topology, public status schema, volume ownership, lifecycle/recovery behavior and threat model in an ADR; inventory VPS prerequisites without recording secrets | approved sprint | architecture + ops | high | Done — `docs/adr/ADR-0035-vps-dry-run-runtime-and-status-boundary.md` (ACCEPTED 2026-09-10) | — |
| T002 | Implement and test the VPS runtime config/entry point, durable JSON repository wiring, continuous service lifetime and graceful recovery semantics while reusing existing execution logic unchanged | T001 (ADR-0035 ACCEPTED) | `application/execution`, `scripts/execution`, storage adapter | high | Implemented, PR open, pending tester/reviewer | [#504](https://github.com/folg-code/research-trading-framework/pull/504) |
| T003 | Implement a bounded GET-only status service over the `ExecutionStateReader` port, with a sanitized versioned response, freshness semantics, health endpoint and no file-path/infrastructure leakage | T001 (ADR-0035 ACCEPTED); parallel with T002 after schema freeze | status application/service + tests | high | Implemented, PR open (based on #504), pending tester/reviewer | [#505](https://github.com/folg-code/research-trading-framework/pull/505) |
| T004 | Package worker and status services and extend VPS Compose with private networking, read/write state volume only for the worker, read-only state access for status, health checks, restart policy and bounded logs/resources | T002–T003 | deploy + infrastructure | high | Ready after T003 | — |
| T005 | Add a current dry-run status card and link to the Live Paper page; remove migration placeholder when configured and preserve explicit stale/offline/failed states and `NO REAL ORDERS` copy | T003; parallel with T004 | dashboard data source + views/content | standard | Ready after T003 | — |
| T006 | Add unit, integration and container smoke tests for restart, stale feed, invalid/corrupt state, status unavailability, schema compatibility and dashboard regression | T002–T005 | tests | high | Ready after implementation | — |
| T007 | Update runbooks and deploy/rollback the stack to the existing VPS; verify public dashboard behavior and observe at least 24 continuous hours or one documented restart cycle | T004–T006 | operations + acceptance | high | Requires explicit sprint/deploy approval | — |

Note (T001): the sprint text originally named `ExecutionStateReadRepository`;
the actual read port in the codebase is `ExecutionStateReader`
(`src/trading_framework/execution/repositories/protocols.py`). T003 targets that.

## Acceptance criteria

- The VPS worker consumes only Binance public BTCUSDT feeds and cannot accept
  exchange credentials or route real orders.
- Docker Compose reports healthy worker, status and dashboard services; a
  graceful stop persists `STOPPED`, and an unrecoverable error persists `FAILED`.
- Restart restores compatible paper account/position state or refuses to start
  with a visible, actionable error; no silent paper-state reset occurs.
- The status service supports GET only, returns the versioned sanitized snapshot,
  exposes no private path/credential/config value and is not a command surface.
- The dashboard card visibly states `LIVE MARKET DATA`, `SIMULATED EXECUTION`
  and `NO REAL ORDERS`, and shows current/stale/offline state honestly.
- The card links to the existing detailed Live Paper surface; no archive of old
  sessions is introduced.
- A network/API outage leaves the dashboard available with an explicit offline
  state and never presents an old snapshot as current.
- Deployment and rollback are reproducible from the runbook, with secrets kept
  outside the repository and logs free of credentials.
- A 24-hour observation or a controlled restart cycle demonstrates fresh
  heartbeat/feed status and recovery; this is operational evidence only, not
  evidence of strategy quality.

## Integration risks

- Sharing JSON state between processes requires atomic writes and compatible
  read behavior; corrupt/partial reads must fail closed.
- A Compose restart loop can hide a deterministic configuration failure. Bound
  retries/visibility and document operator intervention.
- Public copy can accidentally imply live trading. Keep the three-part simulation
  label on the card and detail page.
- VPS deployment is an external-state change and remains gated by explicit
  approval even after the sprint plan is accepted.

## Closeout

- Integrated checks:
- Documentation reconciliation:
- Review:
- Remaining work:
