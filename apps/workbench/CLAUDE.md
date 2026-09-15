# apps/workbench (`trading-workbench`)

Responsibility: the private, local operator control surface for the Research
Workbench (Sprint 064, Phase 17 — Research Application). Invokes Market Data
and Signal Research workflows through a loopback-only JSON API
(`workbench.api.v1`). See `docs/adr/ADR-0037-research-workbench-application-boundary.md`
for the full decision, `docs/adr/ADR-0041-workbench-local-job-runner.md` for
the job runner (spawn/state/cancel/restart-reconciliation, T006/T007),
`docs/adr/ADR-0044-workbench-ui-frontend-framework.md` for the frontend
(T008), and `docs/planning/roadmap/PHASE_17_RESEARCH_APPLICATION.md` for
phase context.

`workbench_core`'s job runner (`job_runner.py`, `job_store.py`,
`windows_process.py`) spawns **one `trading-cli` subprocess per job**
(ADR-0041 §2) — never calls `run_signal_research` or any research workflow
in-process for a job. `windows_process.py` is pure `ctypes` against
`kernel32` (no new dependency, D-S064-03) for the Windows-only process-tree
kill and pid/start-time restart reconciliation; it has a real effect only on
Windows (CI runs `ubuntu-latest`) — see `tests/test_job_cancellation.py`'s
own docstring for how that's handled.

## Conventions specific to this module

- **Two packages, two different import boundaries — not one blanket rule** (ADR-0037 §2), enforced by `tests/unit/test_apps_boundaries.py`:
  - `workbench_core` **MAY** import `trading_framework.application.*` and the ADR-0026 Amendment 1 allow-list (the same module list `apps/cli` uses — see `apps/cli/CLAUDE.md`). It **MUST NOT** import `trading_framework.research.*`, `.market_analysis.*`, `.strategy.*`, `.execution.*`, or an infrastructure adapter outside that allow-list, and must never reimplement research/analysis/execution logic.
  - `workbench_ui` **MUST NOT** import `trading_framework` at all — the dashboard's total ban, not the CLI's allow-list. It talks to `workbench_core` only over `workbench.api.v1`.
- **Widening either boundary is a fresh ADR amendment with maintainer approval, never a test-file edit** — same rule as `apps/cli`'s allow-list (ADR-0026 Amendment 1, D-S047-08 precedent).
- **`workbench-api` binds to loopback only** (`127.0.0.1`/`localhost`/`::1`). `WorkbenchApiConfig.__post_init__` refuses any other host at construction time — this is not a runtime firewall rule, it is a structural refusal. No authentication, no authorization roles, no TLS; exposing this port publicly is unsupported (ADR-0037 §4).
- **The API returns no filesystem path the operator did not supply.** `PublishedDatasetSummary` (`trading_framework.application.market_data.list_published_datasets`) deliberately excludes `checksum`, `lineage`, and any storage path — only fields an operator already knows about a dataset (identity, instrument, timeframe, range, row count).
- **Transport-independent handler, separate from the aiohttp wiring** — same pattern as `trading_framework.application.execution.vps_status_api` / `scripts/execution/run_vps_status_service.py`: `datasets_endpoint.py` builds a plain dict; `app.py` is the only file that imports `aiohttp`.
- **`workbench_ui` is React + Next.js (App Router), static export only — ADR-0044.** No Next.js server process ever runs; there are no API routes, no SSR, no middleware. `next.config` sets `output: 'export'`, and `workbench-api` serves the built `out/` directory itself at `/`, alongside `/api/v1/*`, on the same loopback origin/port. This is deliberate, not incidental: it makes "`workbench_ui` MUST NOT import `trading_framework`" (ADR-0037 §2) true at the language level — there is no Node server at runtime that could ever be handed a Python import. Do not add `next start`/a live Next.js server, API routes, or SSR data-fetching without a fresh ADR amendment to ADR-0044; that would reopen exactly the failure mode this decision closed. `workbench_ui` lives at `apps/workbench/ui/` (its own `package.json`/toolchain, not a uv workspace member) — not `apps/workbench/src/workbench_ui/`, which was T004's Python placeholder, retired by ADR-0044.
- **Template listing goes through `trading_framework.application.signal_research`, never the research-layer catalog directly.** `list_signal_research_templates`/`apply_signal_research_template` live at `trading_framework.research.signal_research.template_catalog` (ADR-0038 §4) — off-limits to `workbench_core` per the boundary above. `apps/workbench/src/workbench_core/templates_endpoint.py` calls the application-layer wrapper (`trading_framework.application.signal_research.list_signal_research_templates`, Sprint 064 T008) instead, the same pattern T004 already used for `PublishedDatasetSummary`. If a future workbench feature needs another research-layer capability, add another thin application-layer wrapper — do not widen `workbench_core`'s allow-list to reach into `trading_framework.research.*` directly.

## Never

- Reimplement research, simulation, analytics, or execution logic in either package — call the application layer.
- Have `workbench_core` invoke a Signal Research or Market Data workflow in-process for a *job* (ADR-0041 §2: one job = one `trading-cli` subprocess, once the job runner lands). Direct application calls for a synchronous read (like the datasets listing here) are fine; spawning research work is not.
- Let `workbench_ui` import `trading_framework` for any reason, including "just this one value object" — that is exactly the erosion `apps/cli`'s allow-list history (ADR-0026 Amendment 1) warns against, and `workbench_ui` does not get the CLI's allow-list at all.
- Embed, iframe, or reverse-proxy the existing dashboard or a generated report (ADR-0037 §5) — link out only.

## Tests

- `apps/workbench/tests/` is this package's own suite (own CI job, matching `apps/cli`/`apps/dashboard`). `test_config.py` covers the loopback-bind refusal and environment loading; `test_datasets_endpoint.py` covers the response body directly (no server) and the full HTTP contract via `aiohttp.test_utils` (no `pytest-asyncio` dependency — a synchronous test function wraps `asyncio.run()`).
- The import-boundary tests themselves live in the shared `tests/unit/test_apps_boundaries.py`, not here — this package has no boundary-test file of its own, by the same convention `apps/cli` and `apps/dashboard` follow.
