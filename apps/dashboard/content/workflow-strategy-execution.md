---
slug: workflow-strategy-execution
title: Strategy Execution Workflow
status: IN_DEVELOPMENT
updated: 2026-09-10
order: 21
links: docs/reference/workflows/STRATEGY_EXECUTION.md, docs/reference/runbooks/LIVE_PAPER_PIPELINE_INSPECTION.md, docs/adr/ADR-0021-live-dry-run-execution-demo.md, docs/reference/system/MODULE_MAP.md
---

Strategy Execution applies a selected Strategy Model to runtime market and
account state. The as-built mode is simulated `DRY_RUN`; real broker execution
is not presented as available.

## Shared definition, independent workflow

Execution can consume the same compositional definition used in research:
Market × Signal × Exit × Risk. It does not load research rankings, notebooks,
reports or verdicts. Selection and promotion are explicit human decisions, not
automatic edges between workflows.

## Runtime architecture

```text
live or replay normalized data
  → Market Analysis update
  → Market and Signal evaluation
  → Exit and Risk evaluation
  → strategy decision
  → operational safety controls
  → simulated order and fill state
  → read-only status API and dashboard
```

Runtime safety controls remain distinct from the Risk Model used to define the
strategy. The public dashboard only reads status; it cannot start workers,
change configuration or submit orders.

## Current evidence

The technical page exposes heartbeat, recent bars, simulated fills and runtime
state for the local status path. Missing or stale status remains visible.

## Limits

There is no real-broker adapter or live-order mode in the public capability
described here. Simulated fills do not establish production readiness, and
research evidence is never automatic permission to trade.
