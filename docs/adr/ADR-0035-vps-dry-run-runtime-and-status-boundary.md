# ADR-0035 — VPS Dry-Run Runtime Boundary: Topology, State Ownership, Public Status Schema, Lifecycle and Threat Model

## Status

ACCEPTED (2026-09-10)

Date: 2026-09-10
Owners: architecture triage (Claude Code session), for
`docs/planning/sprints/SPRINT_062.md` (T001).

This document records decisions D062-01 through D062-04 as stated in
`SPRINT_062.md` (all four marked approved/inherited by the maintainer on
2026-09-10) and freezes the topology, schema, lifecycle and threat-model
details those decisions left open. The maintainer accepted this ADR as
drafted on 2026-09-10, with the following explicit rulings on its open
questions:

- `feed_last_error_code` (closed vocabulary, no raw message) is sufficient;
  no sanitized free-text field is added. Detailed troubleshooting uses
  container logs.
- The existing AWS Lambda status payload is left untouched by this sprint;
  the AWS and VPS status shapes are allowed to diverge for this increment.
- No automatic expiry/retention policy is added for the VPS execution-state
  volume; reset remains a documented manual operator action (T007).

T002–T007 may proceed.

## Context

`ADR-0021` established the one supported execution mode, `DRY_RUN`: live
public Binance USD-M `BTCUSDT` market data, `PaperBroker`, simulated
orders/fills/positions/PnL, no exchange account, no accepted credentials, no
public endpoint that can mutate runtime state. Sprint 062 does not change any
of that — it changes *where* that runtime runs and *how* its read model
reaches the public dashboard.

Facts that constrain the design:

- **The runtime already works and must not be rewritten.** `SPRINT_062.md`
  T002 requires reusing existing execution logic unchanged. The runtime
  assembly lives in
  `src/trading_framework/application/execution/local_btc_futures.py` and
  `binance_local_btc_futures.py`; `PaperBroker` state restoration already
  exists (`LocalBtcFuturesDryRunConfig.restore_previous_state`, default
  `True`, `_restore_broker_state`).

- **The existing AWS entry point is provider-specific, not a general VPS
  API.** `AwsBtcFuturesRuntimeConfig`
  (`application/execution/aws_btc_futures_runtime.py`) *requires*
  `TRADING_FRAMEWORK_AWS_REGION` and `TRADING_FRAMEWORK_EXECUTION_STATE_TABLE`
  even when `EXECUTION_STATE_BACKEND=local`, defaults the state path under
  `/tmp`, defaults `duration_seconds=3600` (a bounded ECS task, not a
  long-lived service), and selects a DynamoDB backend by default. D062-02
  forbids renaming or overloading it as the permanent VPS API.

- **The durable state adapter already exists and is nearly, but not fully,
  safe for cross-process sharing.** `JsonExecutionStateRepository`
  (`infrastructure/storage/execution_state.py`) writes one
  `<base>/<runtime_id>/state.json` per runtime via a `.tmp` file plus
  `Path.replace()` (atomic rename on the same filesystem), and rejects an
  unknown `version` with `ValidationError`. It does not fsync, does not lock,
  and every write is a full read-modify-write of the whole document.

- **The read port is `ExecutionStateReader`, not
  `ExecutionStateReadRepository`.** `SPRINT_062.md` T003 names a type that
  does not exist in the codebase; the actual protocols are
  `ExecutionStateWriter` / `ExecutionStateReader` / `ExecutionStateRepository`
  in `execution/repositories/protocols.py`.

- **The dashboard is already an HTTP-only consumer.**
  `HttpLivePaperStatusDataSource`
  (`apps/dashboard/src/dashboard_app/datasources/live_paper_http.py`) issues
  a GET against one configured `DASHBOARD_STATUS_URL`, parses a JSON object,
  and never writes. `pages/5_Live_Paper_Trading.py` and
  `views/live_paper.py` consume a specific set of top-level keys. Under
  ADR-0022 rule 2, `apps/*` must not import `trading_framework` execution or
  infrastructure — so the dashboard cannot read the state file directly even
  if it were mounted, and the status service cannot live inside
  `apps/dashboard`.

- **The current AWS status payload is the de-facto public shape.**
  `scripts/execution/aws_status_api_handler.py` returns an unversioned,
  hand-assembled JSON object. It is GET-only, sends `Cache-Control: no-store`
  and omits table names — but it also passes `status.feed_last_error` through
  verbatim and carries no `schema_version`.

- **The VPS already runs the dashboard Compose stack.**
  `apps/dashboard/deploy/docker-compose.yml` runs `dashboard` (Streamlit,
  `expose: 8501`, health `GET /_stcore/health`) behind `caddy` published on
  host `${DASHBOARD_HTTP_PORT:-8080}`, with TLS terminated by a shared edge
  proxy outside this repository (`apps/dashboard/docs/RUNBOOK.md`).

## Decision

### 1. VPS topology (D062-02, D062-03)

Three Compose services on the existing dashboard stack. No new host, no new
published port, no change to the shared edge.

```text
                    public internet
                          │  https://dashboard.<domain>
                          ▼
                 shared VPS edge proxy          (outside this repository)
                          │  127.0.0.1:${DASHBOARD_HTTP_PORT}
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│ Compose project (this repository)                               │
│                                                                 │
│   caddy ──► dashboard ──HTTP GET──► dry-run-status              │
│  (published)  (expose 8501)          (expose only, NOT published)│
│                                            │ read-only          │
│                                            ▼                    │
│                                   ┌──────────────────┐          │
│   dry-run-worker ──read/write────►│ execution-state  │          │
│  (no ports at all)                │ named volume     │          │
│         │                         └──────────────────┘          │
└─────────┼───────────────────────────────────────────────────────┘
          │ outbound TLS only
          ▼
   Binance public USD-M market-data stream (no authentication)
```

Binding rules:

1. **`dry-run-worker`** publishes no port and exposes no port. It is
   outbound-only: one public Binance market-data stream. It never listens.
2. **`dry-run-status`** is `expose`-only on an internal Compose network. It
   is never mapped to a host port and never reachable from the internet.
   Only `dashboard` may reach it, over the Compose DNS name.
3. **`dashboard`** keeps its current shape. `DASHBOARD_STATUS_URL` points at
   the internal service name (e.g. `http://dry-run-status:<port>/status`),
   not at a public URL. No dashboard code change to the datasource contract
   is required by this ADR.
4. **Network segmentation.** At minimum two Compose networks: a
   `frontend`-style network joining `caddy` + `dashboard`, and a
   `status`-style network joining `dashboard` + `dry-run-status`. The worker
   joins neither (it needs only default egress). `caddy` must not be able to
   route to `dry-run-status`, so the public edge cannot proxy the status
   service by misconfiguration.
5. **No status route is added to the Caddyfile.** The public surface stays
   exactly what it is today: the Streamlit dashboard.
6. **The status service is framework-side code**, not `apps/dashboard` code:
   it may import `trading_framework.execution` / `infrastructure` (ADR-0022
   rule 2 forbids the reverse). Its module/package placement is a T003
   task-level decision within this rule.

### 2. Execution-state storage and ownership

1. **One dedicated Docker named volume** holds execution state, mounted at a
   stable in-container path. It is not the dashboard's `user_data` mount and
   not a `/tmp` path (unlike the current AWS default). Research storage
   (ADR-0002 `user_data`) and operational execution state stay separate
   volumes with separate lifecycles.
2. **Single writer.** `dry-run-worker` mounts the volume read-write and is
   the only process permitted to write. Exactly one worker process per
   `runtime_id` may run at a time.
3. **Read-only reader.** `dry-run-status` mounts the same volume `read_only:
   true` at the Docker level, and uses only `ExecutionStateReader` methods.
   Enforcement is at the mount, not merely by convention.
4. **`dashboard` does not mount it at all.** The dashboard's only access to
   execution state is the status service's HTTP response.
5. **Atomicity requirements** (`SPRINT_062.md` Integration risks):
   - Writes stay temp-file + atomic rename on the *same* filesystem, so a
     concurrent reader always observes a whole previous or whole next
     document, never a partial one. The volume must therefore be a single
     mount point — no bind-mounting a subdirectory across filesystems.
   - The writer flushes and fsyncs the temp file before rename, so a VPS
     power loss cannot leave a renamed-but-empty document.
   - No lock file, no coordination protocol, no reader/writer handshake.
     Rename atomicity is the whole mechanism; anything more is out of scope.
6. **Fail closed on unreadable state.** Invalid JSON, an unsupported
   `version`, a missing required field, or a value that fails domain
   validation is an **error**, never a silently substituted empty/default
   state. The reader returns an explicit unavailable/error result upstream;
   the writer refuses to start (see §4.4). Leftover `*.tmp` files are ignored
   by readers.
7. **Bounded by construction.** The document keeps only bounded recent
   events/orders/fills/bars (existing `recent_*_limit` behavior). This is a
   read model, not history or an audit log; no session archive is
   introduced.

### 3. Public status schema

The status service returns one **versioned, sanitized snapshot**. It is a
public contract even though it is served privately, because its content is
rendered on a public page.

1. **Envelope.** Every 200 response carries `schema_version`
   (`execution.status.v1`), `generated_at` (UTC ISO-8601) and
   `simulated: true`.
2. **Allowlist, deny by default.** Only explicitly named fields are emitted.
   A new field appearing in the persisted document is **omitted**, not passed
   through. The v1 field set, chosen to remain compatible with the existing
   dashboard consumers listed in Context:

   | Group | Fields |
   |---|---|
   | Envelope | `schema_version`, `generated_at`, `simulated` |
   | Identity | `runtime_id`, `mode`, `provider`, `symbol` |
   | Health | `status` (`RUNNING`/`DEGRADED`/`STALE`/`STOPPED`/`FAILED`), `last_heartbeat_at`, `last_market_event_at`, `feed_connection_state`, `feed_reconnect_count`, `feed_last_error_code`, `stale` |
   | Market | `last_price`, bounded `recent_bars` |
   | Paper account | `paper_equity`, `realized_pnl`, `unrealized_pnl` |
   | Paper position | `current_position` (symbol, side, quantity, average entry, mark, unrealized PnL, `simulated`), `current_signal` |
   | Bounded activity | `recent_orders`, `recent_fills`, `recent_events` |

3. **Categorically forbidden, with no allowlist entry permitted:** any
   filesystem path (including the state path, event-log path, volume or mount
   name), container/service/host names, IP addresses, ports, image tags, env
   variable names or values, cloud identifiers (region, table, ARN, account),
   credentials or tokens of any kind, stack traces, and raw exception text.
4. **`feed_last_error` is not passed through.** The raw string can embed a
   stream URL or host. v1 exposes `feed_last_error_code`: a bounded, closed
   vocabulary of classified reasons (e.g. `connection_closed`,
   `connect_timeout`, `protocol_error`, `unknown`). This is a deliberate,
   documented narrowing of the current AWS payload.
5. **Freshness is computed and stated, never implied.** The response carries
   `generated_at` and the persisted `last_heartbeat_at`; the service marks
   `stale: true` when the heartbeat is older than a configured threshold. A
   stale snapshot is still returned — labelled — and the dashboard must never
   present it as current.
6. **Explicit non-2xx semantics**, each with a JSON body carrying
   `schema_version` and `simulated: true`:
   - `404` — no state for the configured runtime (never started, or wiped).
   - `405` with `Allow: GET` — any method other than GET or HEAD.
   - `503` — state present but unreadable/corrupt/incompatible (§2.6), or the
     volume is unavailable. Never a fabricated empty snapshot.
7. **Headers.** `Content-Type: application/json`, `Cache-Control: no-store`.
   No CORS wildcard is needed or set: the only caller is server-side on the
   private network.
8. **Compatibility.** Additive within `v1` (new optional fields, new
   bounded-list entries); consumers ignore unknown fields and treat an absent
   optional field as absent, never as zero. Removing/renaming a field,
   changing units or meaning, or widening the allowlist to a previously
   forbidden category is a major bump plus a new ADR.

### 4. Lifecycle and recovery (D062-04)

1. **Service lifetime.** The VPS worker runs as a continuous service. The
   bounded-duration behavior inherited from the AWS task
   (`duration_seconds=3600`) must not be the VPS default; unbounded operation
   is the normal mode and a bounded duration remains available for smoke
   runs.
2. **Graceful stop.** `SIGTERM`/`SIGINT` (Compose `stop`, `restart`,
   redeploy) stops the loop, persists a final `STOPPED` runtime status, and
   exits `0`. Compose `stop_grace_period` must exceed the worst-case flush so
   the final write is not `SIGKILL`ed mid-shutdown.
3. **Unrecoverable error.** A non-transient failure persists `FAILED` on a
   best-effort basis and exits non-zero. Transient feed problems are
   `DEGRADED`/`STALE`, not `FAILED` — the existing distinction is preserved.
4. **Restart: restore or refuse — never silently reset.** On start the worker
   reads the persisted state for its `runtime_id` and either:
   - finds no state → starts fresh (normal first run), or
   - finds **compatible** state → restores the paper account and open
     position and continues, or
   - finds **incompatible or unreadable** state → **refuses to start** with a
     single actionable error message naming the mismatch (no path, no dump)
     and exits non-zero.

   "Compatible" means: state document `version` is supported, and the
   persisted `mode`, `provider`, `symbol`, `account_id` and `currency` match
   the configured ones. A changed `starting_equity` with an open position is
   also incompatible.

   The existing `_restore_broker_state` returns `None` (i.e. starts fresh)
   whenever the persisted view is incomplete. That silent-reset path must be
   closed by T002: incomplete-but-present state with an open position is a
   refuse-to-start condition, not a fresh start. Deliberately discarding
   paper state is an explicit operator action (remove/rename the runtime's
   state directory, documented in the runbook), never an automatic one.
5. **Health checks.**
   - `dry-run-status`: HTTP health endpoint, separate from `/status`,
     reporting only process liveness plus whether the state volume is
     readable. It must not report unhealthy merely because the worker is
     stopped — a correct `404`/stale answer is healthy behavior.
   - `dry-run-worker`: no HTTP listener, so liveness is heartbeat freshness
     of its own persisted state, checked in-container. Feed `DEGRADED` is not
     by itself unhealthy.
   - `dashboard`: unchanged (`/_stcore/health`).
   - `dashboard` does **not** `depends_on: service_healthy` the status
     service — the dashboard must stay up and show an explicit offline state
     when status is down (an acceptance criterion).
6. **Restart policy must not mask a deterministic failure.** `restart:
   unless-stopped` with no bound would hide a bad config as an invisible
   crash loop. Therefore: a bounded restart policy (`on-failure` with a
   maximum attempt count), a refuse-to-start condition exiting with a
   distinct non-zero code, and a `FAILED`/unavailable state that is visible
   on the public card rather than only in `docker logs`. Operator
   intervention after exhausted retries is documented in the runbook (T007).
7. **Bounded logs and resources.** Every new service sets an explicit
   logging driver with size and file-count caps, and explicit memory/CPU
   limits (the worker is a single small asyncio process; the status service
   is smaller). Log lines are structured JSON and must contain no credential,
   token, URL query string or absolute host path.

### 5. Threat model

**Assets.** (a) VPS integrity; (b) the credibility of the public claim
"simulated"; (c) the deploy path's SSH key. Notably absent: there is no
exchange account, no API key, no capital, and no order path — ADR-0021's
safety boundary is inherited unchanged, so the highest-value asset of a
normal trading system does not exist here.

| Surface | Exposure | Control |
|---|---|---|
| Public dashboard | Internet, via shared edge | Unchanged by this ADR; read-only Streamlit |
| `dry-run-status` | Compose-internal only | No published port; not routable from `caddy`; GET-only; allowlisted response |
| `dry-run-worker` | No inbound surface at all | Outbound TLS to one public Binance endpoint |
| State volume | Two containers | RW worker / RO status; not mounted into `dashboard` |

Reasoning:

- **Why GET-only.** ADR-0021 states "no public endpoint can mutate runtime
  state" as a binding rule. Any mutation route (start/stop/flatten/reset)
  would create a control channel into a process that touches live market data
  — the exact category of surface this project has decided not to build.
  `405` on non-GET is an explicit, tested behavior, not an accident of the
  framework.
- **Why no command surface even on the private network.** Compose-internal is
  not a trust boundary: a compromised dashboard container would inherit it.
  With no mutation endpoint, dashboard compromise yields read access to
  already-public simulated numbers.
- **Why credentials cannot reach this path.** The worker consumes only public
  market data; no configuration key for an API key/secret exists, and none
  may be added on this path. A future authenticated adapter requires a new
  ADR, not a new environment variable. Deploy secrets (SSH) live in GitHub
  Actions secrets and never enter these containers.
- **Blast radius — compromised status service:** read access to the state
  volume (simulated numbers already shown publicly) plus the ability to
  return false status to the dashboard, i.e. a *credibility* incident, not a
  financial one. It cannot write state, cannot reach the internet inbound,
  and cannot influence the worker.
- **Blast radius — compromised worker:** write access to its own state volume
  (it could fabricate simulated positions) and outbound network from the VPS.
  It has no credentials to steal and no order path to abuse. It cannot serve
  traffic.
- **Residual risks accepted:** shared-VPS blast radius (the edge and other
  apps are outside this repository); a supply-chain compromise of the base
  image or Python dependencies; and the reputational risk of the dashboard
  presenting simulated numbers ambiguously — mitigated by the mandatory
  three-part `LIVE MARKET DATA` / `SIMULATED EXECUTION` / `NO REAL ORDERS`
  labelling on both the card and the detail page.
- **Denial of service** is explicitly not defended against beyond bounded
  resources and no public exposure; this is a portfolio demo.

### 6. VPS prerequisites inventory (generic — no secrets recorded)

Recorded as requirements only. **No hostname, IP, domain, port number in
use, username, path or key material of the actual VPS appears in this
repository**; those stay in GitHub Actions secrets and operator-managed
non-committed env files (`apps/dashboard/docs/RUNBOOK.md`).

**Host**

- Linux x86-64 with a modern LTS kernel and systemd.
- Docker Engine 24+ with the Compose v2 plugin (`docker compose`), matching
  the version assumption already in the dashboard runbook.
- A filesystem supporting atomic `rename(2)` within the volume (any standard
  Linux fs; the requirement is that the volume is one mount point).
- Outbound HTTPS/WSS egress permitted to the Binance public market-data
  endpoint. No inbound rule is added for the worker or status service.
- Correct system time (NTP) — all persisted timestamps are UTC-aware
  (ADR-0003) and freshness/staleness decisions depend on host clock accuracy.
- Modest headroom beyond the existing dashboard stack: the worker is one
  small asyncio process, the status service smaller; both are capped
  explicitly (§4.7).

**Storage**

- One Docker named volume dedicated to execution state, persisting across
  container recreation and host reboot.
- Mounted RW in the worker, RO in the status service, absent from the
  dashboard.
- Not shared with `user_data` research storage; not on `/tmp` or any
  tmpfs-backed path.
- Backup is **not** required — the state is a regenerable demo read model;
  the runbook documents deliberate reset instead.

**Network**

- Existing published surface unchanged: one loopback-bound HTTP port for the
  dashboard's Caddy, fronted by the shared edge that terminates TLS.
- Two or more internal Compose networks per §1.4; the status service is
  `expose`-only.

**Configuration and secrets**

- Runtime configuration is provided via a non-committed env file or the
  deploy environment; the repository contains only documented variable names
  and safe defaults.
- No secret is required by the worker or the status service. The only secrets
  in the whole path are the existing deploy/SSH credentials, which stay in
  GitHub Actions secrets.
- The concrete variable names for the provider-neutral VPS config are a T002
  task-level decision; they must not require any AWS-specific value
  (`AWS_REGION`, `EXECUTION_STATE_TABLE`) to start.

## Alternatives Considered

### A — Reuse `AwsBtcFuturesRuntimeConfig` with `EXECUTION_STATE_BACKEND=local`

- Pros: zero new configuration code; already tested.
- Cons: forces meaningless `AWS_REGION`/`EXECUTION_STATE_TABLE` values on a
  non-AWS host, defaults state to `/tmp` and duration to one hour, and makes
  an AWS-named type the permanent VPS contract. D062-02 rules it out
  explicitly.
- Rejected. The provider-neutral config is a thin wrapper over the same
  runtime, not a rewrite.

### B — Dashboard reads `state.json` directly from a shared read-only mount

- Pros: no status service, no HTTP hop, fewer moving parts.
- Cons: violates ADR-0022 rule 2 (`apps/*` must not import
  `trading_framework` execution/infrastructure), so the dashboard would have
  to re-implement the state schema — a second, silently divergent parser; it
  also puts an internal on-disk shape directly behind a public page with no
  allowlist between them, and discards the existing
  `HttpLivePaperStatusDataSource` contract.
- Rejected.

### C — Publish the status service on a public port (as AWS does via API Gateway)

- Pros: matches the AWS deployment shape; independently checkable by an
  operator with `curl`.
- Cons: adds a public surface for no product benefit — the only consumer is
  the dashboard, already on the same host; it would need CORS, rate limiting
  and its own TLS story.
- Rejected. Operators can reach it from inside the Compose network
  (`docker compose exec`), which the runbook documents.

### D — Run the worker as a bounded scheduled task (systemd timer / cron)

- Pros: cheapest; mirrors the AWS EventBridge scheduled mode.
- Cons: a portfolio card that is fresh for 30 minutes a day is mostly a stale
  card; restart/recovery semantics — the interesting engineering claim — are
  never exercised. D062-04 asks for a continuous service lifetime.
- Rejected for the VPS; bounded runs remain available for smoke tests.

### E — Replace JSON files with SQLite on the volume

- Pros: real concurrency control; no whole-document rewrites.
- Cons: a storage-strategy change requiring its own ADR and a rewrite of the
  adapter Sprint 062 is explicitly required to reuse; a single-writer JSON
  document with atomic rename is sufficient for one runtime writing a bounded
  read model every few seconds.
- Rejected for now. Revisit if multiple runtimes, multiple writers or write
  volume make full-document rewrites the bottleneck.

## Consequences

### Positive

- The public surface does not grow: still one dashboard behind the shared
  edge. The status service and worker are unreachable from the internet.
- "No credential can reach this path" is structural (no configuration key
  exists, no inbound surface exists), not a policy someone must remember —
  consistent with ADR-0021's safety boundary.
- The allowlisted, versioned schema makes "no path/infrastructure leakage" a
  single testable property instead of a per-field review, and gives the
  dashboard a contract it can validate rather than duck-type.
- Single-writer/read-only-mount ownership makes the corrupt-partial-read risk
  from `SPRINT_062.md` a property of the mount configuration, not of
  discipline.
- Refuse-to-start-on-incompatible-state closes a real existing silent-reset
  path (`_restore_broker_state` returning `None`), so an open paper position
  can never quietly vanish across a redeploy.
- Bounded restarts plus a visible `FAILED`/unavailable state address the
  "Compose restart loop hides a deterministic config failure" risk directly.
- The AWS runtime, ECS/Lambda path and its runbook are untouched and remain
  valid.

### Negative / trade-offs

- Two runtime configurations and two status implementations (AWS Lambda +
  VPS service) now exist over the same read model, and can drift. Accepted
  for this increment; convergence, if any, is later work.
- The VPS status payload is deliberately *narrower* than the AWS one
  (`feed_last_error` → `feed_last_error_code`), so troubleshooting a feed
  error requires container logs rather than the public payload. That is the
  intended trade.
- Refusing to start on incompatible state converts a previously silent
  recovery into an operator task. This is intentional but is real
  operational friction after a config change.
- A continuously running worker consumes VPS resources 24/7 and produces a
  continuous log stream; caps are mandatory, not optional.
- The JSON read-modify-write remains O(document) per event. Fine at one
  runtime and bounded lists; it is not a general execution store.
- `apps/dashboard/pages/5_Live_Paper_Trading.py` reads `recent_trades`, which
  no producer emits. Under the allowlist it stays absent; the page must treat
  absent as absent, not as empty-because-nothing-happened.

### Explicitly out of scope (per `SPRINT_062.md`)

```text
PAPER or LIVE execution modes
authenticated Binance APIs, API keys, private endpoints
real orders, broker adapters, capital
any public command/mutation surface
new strategy logic or any claim of trading performance
multiple symbols, multiple accounts, public session history, control buttons
replacing the dashboard deployment stack or the shared edge TLS architecture
```

## Follow-up

- **T002** decides the concrete provider-neutral config type, module path and
  environment variable names, within §1.6, §4.1 and §4.4.
- **T003** decides the status service's HTTP framework, bind port and route
  paths, within §3. It consumes `ExecutionStateReader` — the sprint's
  `ExecutionStateReadRepository` name should be corrected.
- **T004** decides the Compose network names, volume name, health-check
  commands and concrete limit values, within §1, §4.5–4.7.
- **T007** documents deliberate paper-state reset, exhausted-restart
  intervention and rollback in a new provider-neutral runbook.
  `AWS_BTC_FUTURES_DRY_RUN.md` is not renamed or repurposed.
- Whether the AWS Lambda status payload should also adopt
  `schema_version`/`feed_last_error_code` is deferred; this ADR does not
  change it.

## References

- `docs/adr/ADR-0021-live-dry-run-execution-demo.md` — the `DRY_RUN` mode,
  safety boundary and status vocabulary inherited unchanged (D062-01).
- `docs/adr/ADR-0022-repository-top-level-layout.md` — rule 2, why the status
  service is framework-side and the dashboard stays HTTP-only.
- `docs/adr/ADR-0002-separate-src-and-user-data.md` — why execution state is
  a separate volume from research storage.
- `docs/adr/ADR-0003-utc-internal-time.md` — UTC timestamps and the host NTP
  prerequisite.
- `docs/planning/sprints/SPRINT_062.md` — D062-01..D062-04, scope, acceptance
  criteria and integration risks recorded here.
- `docs/planning/sprints/SPRINT_024.md`, `SPRINT_025.md` — prior execution
  state/read-model and operational hardening work.
- `docs/reference/workflows/STRATEGY_EXECUTION.md` — the execution workflow
  this deployment hosts without changing.
- `docs/reference/runbooks/LOCAL_BTC_FUTURES_DRY_RUN.md`,
  `docs/reference/runbooks/AWS_BTC_FUTURES_DRY_RUN.md`,
  `docs/reference/runbooks/LIVE_PAPER_PIPELINE_INSPECTION.md` — existing
  operator surfaces; the AWS one is consumed, not amended.
- `apps/dashboard/docs/RUNBOOK.md` — the existing VPS Compose/edge deployment
  this topology extends.
- `apps/dashboard/src/dashboard_app/datasources/live_paper_http.py` — the
  GET-only consumer the v1 schema stays compatible with.
- `src/trading_framework/infrastructure/storage/execution_state.py` —
  `JsonExecutionStateRepository`, the durable adapter and its atomicity
  behavior.
- `src/trading_framework/execution/repositories/protocols.py` —
  `ExecutionStateWriter` / `ExecutionStateReader` ports.
- `src/trading_framework/application/execution/aws_btc_futures_runtime.py` —
  the AWS-specific config that must not become the VPS API.
