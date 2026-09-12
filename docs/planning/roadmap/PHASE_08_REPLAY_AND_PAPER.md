# Phase 08 Replay And Paper

This is the detailed planning record extracted from the accepted roadmap. Use [Roadmap](../ROADMAP.md) for phase status and navigation; use [Reference](../../reference/README.md) for current behavior.

# 12. Phase 8 — Replay and Paper Execution

## Purpose

Run selected Strategy Models with runtime-style semantics without real-money execution.

## Expected Capabilities

- Replay Clock,
- Replay Execution,
- Paper Execution,
- runtime Market Analysis updates,
- SignalOccurrence processing,
- strategy decisions,
- order lifecycle,
- partial fills,
- positions,
- operational risk controls,
- persistence,
- reconciliation,
- recovery,
- monitoring.

## Completion Criteria

- replay consumes published historical data,
- paper mode consumes live normalized market data,
- Strategy Model is execution-mode independent,
- order transitions are explicit,
- duplicate events are handled safely,
- runtime state survives restart where required,
- broker-like state can be reconciled,
- Research workflow state is not required.

## Dependencies

- stable Strategy Model contracts,
- Market Analysis runtime semantics,
- Event System where justified,
- replay data access,
- execution persistence.

## Main Risks

- divergence between research and runtime behaviour,
- hidden event ordering assumptions,
- insufficient idempotency,
- in-memory-only state,
- operational risk logic leaking into Strategy Risk Models.

## Out of Scope

- real broker orders,
- multi-account orchestration,
- prop-firm-specific controls.

---
