# Execution — implementation map

This page records the existing packages and entry points for execution. Start with the [module map](../system/MODULE_MAP.md) for system-wide placement and follow the links below for contracts and workflows.

## Packages and entry points

### Responsibilities

The delivered mode is the BTC futures simulated-order dry-run. The broader
replay, paper, real-broker and multi-account modes remain in
[future runtime direction](../../vision/EXECUTION_RUNTIME_FUTURE.md); the
package map below must not be read as support for all modes.

| Responsibility | Package |
|---|---|
| Execution modes and safety contracts | `execution/` |
| Orders, fills, positions and account models | `execution/models/` |
| Broker simulation | `execution/broker_sim/` |
| Runtime state ports | `execution/repositories/` |
| Runtime logic | `execution/runtime/` |
| Workflow orchestration | `application/execution/` |
| Live provider adapters | `infrastructure/providers/` |
| Runtime-state persistence | `infrastructure/storage/` |
| Status and monitoring delivery | application and infrastructure adapters |

### Workflow mapping

```text
Live Provider Adapter
  → normalized market facts
  → application/execution
  → execution/runtime
  → broker abstraction
  → runtime-state repository
  → monitoring or dashboard
```

### Dependency direction

```text
execution
    does not depend on research

application/execution
    orchestrates execution domain and adapters

infrastructure
    implements provider and persistence boundaries
```

### Tests

```text
tests/unit/execution/
tests/unit/application/execution/
tests/unit/infrastructure/
tests/integration/live_data/
```

### Deep references

- [System Overview](../system/SYSTEM_OVERVIEW.md)
- [Strategy Execution workflow](../workflows/STRATEGY_EXECUTION.md)
- [Runbooks](../runbooks/README.md)
- [ADR-0021 dry-run execution](../../adr/ADR-0021-live-dry-run-execution-demo.md)

---
