# apps/workbench (`trading-workbench`)

Responsibility: the private, local operator control surface for the Research
Workbench (Sprint 064, Phase 17 — Research Application). Invokes Market Data
and Signal Research workflows through a loopback-only JSON API
(`workbench.api.v1`). See `docs/adr/ADR-0037-research-workbench-application-boundary.md`
for the full decision and `docs/planning/roadmap/PHASE_17_RESEARCH_APPLICATION.md`
for phase context.

## Conventions specific to this module

- **Two packages, two different import boundaries — not one blanket rule** (ADR-0037 §2), enforced by `tests/unit/test_apps_boundaries.py`:
  - `workbench_core` **MAY** import `trading_framework.application.*` and the ADR-0026 Amendment 1 allow-list (the same module list `apps/cli` uses — see `apps/cli/CLAUDE.md`). It **MUST NOT** import `trading_framework.research.*`, `.market_analysis.*`, `.strategy.*`, `.execution.*`, or an infrastructure adapter outside that allow-list, and must never reimplement research/analysis/execution logic.
  - `workbench_ui` **MUST NOT** import `trading_framework` at all — the dashboard's total ban, not the CLI's allow-list. It talks to `workbench_core` only over `workbench.api.v1`.
- **Widening either boundary is a fresh ADR amendment with maintainer approval, never a test-file edit** — same rule as `apps/cli`'s allow-list (ADR-0026 Amendment 1, D-S047-08 precedent).
- **`workbench-api` binds to loopback only** (`127.0.0.1`/`localhost`/`::1`). `WorkbenchApiConfig.__post_init__` refuses any other host at construction time — this is not a runtime firewall rule, it is a structural refusal. No authentication, no authorization roles, no TLS; exposing this port publicly is unsupported (ADR-0037 §4).
- **The API returns no filesystem path the operator did not supply.** `PublishedDatasetSummary` (`trading_framework.application.market_data.list_published_datasets`) deliberately excludes `checksum`, `lineage`, and any storage path — only fields an operator already knows about a dataset (identity, instrument, timeframe, range, row count).
- **Transport-independent handler, separate from the aiohttp wiring** — same pattern as `trading_framework.application.execution.vps_status_api` / `scripts/execution/run_vps_status_service.py`: `datasets_endpoint.py` builds a plain dict; `app.py` is the only file that imports `aiohttp`.
- **`workbench_ui` is deliberately a near-empty stub in this sprint.** The frontend framework choice is out of scope (PRD non-goal; ADR-0037 Follow-up) — do not add a UI dependency or framework import here without a separate decision.

## Never

- Reimplement research, simulation, analytics, or execution logic in either package — call the application layer.
- Have `workbench_core` invoke a Signal Research or Market Data workflow in-process for a *job* (ADR-0041 §2: one job = one `trading-cli` subprocess, once the job runner lands). Direct application calls for a synchronous read (like the datasets listing here) are fine; spawning research work is not.
- Let `workbench_ui` import `trading_framework` for any reason, including "just this one value object" — that is exactly the erosion `apps/cli`'s allow-list history (ADR-0026 Amendment 1) warns against, and `workbench_ui` does not get the CLI's allow-list at all.
- Embed, iframe, or reverse-proxy the existing dashboard or a generated report (ADR-0037 §5) — link out only.

## Tests

- `apps/workbench/tests/` is this package's own suite (own CI job, matching `apps/cli`/`apps/dashboard`). `test_config.py` covers the loopback-bind refusal and environment loading; `test_datasets_endpoint.py` covers the response body directly (no server) and the full HTTP contract via `aiohttp.test_utils` (no `pytest-asyncio` dependency — a synchronous test function wraps `asyncio.run()`).
- The import-boundary tests themselves live in the shared `tests/unit/test_apps_boundaries.py`, not here — this package has no boundary-test file of its own, by the same convention `apps/cli` and `apps/dashboard` follow.
