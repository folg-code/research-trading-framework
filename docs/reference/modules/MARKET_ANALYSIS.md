# Market Analysis — implementation map

This page records the existing packages and entry points for market analysis. Start with the [module map](../system/MODULE_MAP.md) for system-wide placement and follow the links below for contracts and workflows.

## Packages and entry points

### Responsibilities

| Responsibility | Package |
|---|---|
| Component contracts | `market_analysis/protocols/` |
| Component identity | `market_analysis/identity/` |
| Component requests and outputs | `market_analysis/models/` |
| Component registry | `market_analysis/registry/` |
| Dependency planning | `market_analysis/planning/` |
| Batch execution | `market_analysis/execution/` |
| Analysis input data | `market_analysis/data/` |
| Results and workspace | `market_analysis/storage/` |
| Built-in components | `market_analysis/components/` — for the full catalog of built-in components (per-component semantics, warm-up, output fields, zero-denominator conventions), see [`../modules/ANALYSIS_COMPONENT_CATALOG.md`](../modules/ANALYSIS_COMPONENT_CATALOG.md) |
| Frame assembly and alignment | `market_analysis/assembly/` |
| Workflow orchestration | `application/market_analysis/` |

### Workflow mapping

```text
Published Dataset
  → application/market_analysis
  → market_analysis/data
  → market_analysis/planning
  → market_analysis/execution
  → market_analysis/storage
  → features and states
```

### Public workflow surface

The Market Analysis application layer is responsible for:

- loading published market data,
- resolving component requests,
- building an execution plan,
- executing shared computations,
- assembling model-facing analytical outputs.

### Tests

```text
tests/unit/market_analysis/
tests/unit/application/market_analysis/
tests/integration/market_analysis/
```

### Deep references

- [System Overview](../system/SYSTEM_OVERVIEW.md)
- [Market Analysis implementation](MARKET_ANALYSIS_MODULE.md) and [architecture](../system/MARKET_ANALYSIS_ARCHITECTURE.md)
- [Component catalog](ANALYSIS_COMPONENT_CATALOG.md) and [Market Analysis ADRs](../../adr/README.md)

---
