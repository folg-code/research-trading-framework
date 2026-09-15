# apps/workbench (`trading-workbench`)

Private local operator control surface for the trading research framework
(Sprint 064, Phase 17 — Research Application / Local Workbench). Invokes
Market Data and Signal Research workflows through a loopback-only JSON API.
Never exposed publicly; see `docs/adr/ADR-0037-research-workbench-application-boundary.md`.

## Packages

- `workbench_core` — control core. MAY import `trading_framework.application.*`
  plus the ADR-0026 Amendment 1 allow-list. MUST NOT import
  `trading_framework.research.*`, `.market_analysis.*`, `.strategy.*`,
  `.execution.*`, or an infrastructure adapter outside that allow-list.
- `workbench_ui` — presentation. MUST NOT import `trading_framework` at all;
  talks to `workbench_core` only over the loopback `workbench.api.v1` API.

Both boundaries are enforced by `tests/unit/test_apps_boundaries.py`.

## Running

```bash
TRADING_WORKBENCH_STORAGE_ROOT=user_data uv run --package trading-workbench workbench-api
```

Binds to `127.0.0.1` only (`TRADING_WORKBENCH_HOST` must be a loopback
address; a non-loopback value is refused at startup).
