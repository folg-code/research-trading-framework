# ADR-0005 — Market Analysis Domain and Taxonomy

## Status

ACCEPTED

## Context

The framework separates reusable analytical computation from Market Models, Signal Models and execution.
Market Analysis must have a stable semantic taxonomy so components, dependencies and results remain
strategy-independent and composable.

Sprint 003 implemented the first engine slice over published `DatasetRef` inputs. Binding decisions
D-001–D-004 in `docs/vision/MARKET_ANALYSIS_WITH_DECISIONS.md` define domain boundaries and
component categories.

## Decision

Adopt **Market Analysis** as a dedicated domain that owns reusable calculations, detections and
classifications derived from market-related data.

Semantic taxonomy (MVP):

```text
Market Analysis Components
├── Features   — measurable time-aligned properties (ATR, EMA, True Range)
├── Structures — identified objects, levels, patterns or events (deferred beyond MVP catalog)
└── States     — classifications at a point in time (Volatility State)
```

Rules:

1. Market Analysis is **not** Market Model, Strategy or Signal Model semantics.
2. Components are **stateless** batch units; they declare dependencies and return typed outputs.
3. `ComponentId` names semantic capability; `ImplementationId` names a backend adapter.
4. Components do not access repositories, file paths or external APIs directly.
5. Sprint 003 validates the taxonomy through Features and States; Structures remain a planned category.

Primary flow:

```text
Published DatasetRef → AnalysisDataView → Component DAG → AnalysisResultStore
    → AnalysisWorkspace → optional AnalysisFrame
```

## Consequences

### Positive

- clear ownership boundary for analytical reuse,
- stable vocabulary for registry, planning and lineage,
- strategies consume outputs without embedding indicator logic.

### Negative

- Structures are not yet exemplified in the MVP vertical slice,
- taxonomy alone does not prescribe storage or UI presentation.

## References

- `docs/vision/ARCHITECTURE_FOUNDATIONS_UPDATED.md` §6.2
- `docs/vision/MARKET_ANALYSIS_WITH_DECISIONS.md` — D-001–D-004
- `docs/adr/ADR-MA-001-market-analysis-domain-boundaries.md`
- `src/trading_framework/market_analysis/`
