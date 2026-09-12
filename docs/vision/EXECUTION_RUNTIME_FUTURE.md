# Execution Runtime — Future Direction

The implemented runtime is a simulated-order dry-run; see [Execution module](../reference/modules/EXECUTION.md) and [Strategy Execution workflow](../reference/workflows/STRATEGY_EXECUTION.md). The modes and contracts below are targets, not claims about current support. The [pre-review snapshot](../archive/snapshots/EXECUTION_RUNTIME_FUTURE_pre_review.md) preserves detailed earlier proposals and classification evidence.

## Modes and ownership

Replay Execution would consume published historical facts with a replay clock while preserving runtime order, fill and position semantics. Paper Execution would use live market data and simulated broker interaction. Live Execution would use a real broker. A selected Strategy Model should not have to know which mode is active.

Batch/vectorized backtesting remains Strategy Research: it optimizes experiment evaluation and produces research datasets. Replay belongs to Execution and can test research/runtime parity. The two should not collapse into an ambiguous engine.

## Order and fill lifecycle

A broker-capable runtime needs explicit, validated order transitions: created, submitted, accepted, partially filled, filled, cancelled, rejected and expired. Broker-specific statuses would be normalized at an adapter boundary. Fill processing would handle multiple and partial fills, fees, slippage, provider identifiers, duplicate detection and average price. Accepted fills are facts; corrections require explicit records.

## Broker boundary

A future broker contract may support connection lifecycle, order submit/cancel/replace, order and position queries, account state and execution-event streaming. Broker SDK types must remain inside infrastructure adapters. Research and domain code should depend only on framework contracts.

## Reconciliation and recovery

The runtime should compare internal order, fill, position and account state with broker state. Missing/unknown orders, quantity differences, duplicate fills and stale account information need explicit incidents or error states. Recovery after restart, disconnect or provider interruption requires persisted state plus reconciliation; in-memory state alone is insufficient.

## Operational controls and observability

Runtime configuration should declare mode, selected strategy, broker/account, instrument mapping, order policy, operational limits and reconnect policy. Secrets come from environment or external secret storage. Strategy Risk and operational controls remain separate.

Critical transitions, health, connection state, latency and order failures should be observable. Future event delivery may help where justified, but it must not hide risk checks, state transitions, failure policy or persistence. See [Event System Future](EVENT_SYSTEM_FUTURE.md) and [Phase 8/9 plans](../planning/ROADMAP.md).
