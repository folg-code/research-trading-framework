# Architecture Simplification Review — Sprints 002 and 003

## 1. Purpose

Retrospective assessment of Sprints 002 and 003 regarding:

- excessive abstractions,
- premature contract freeze,
- unnecessary layers,
- departure from a columnar data model,
- process cost from task and PR granularity,
- impact on Sprint 004 and later work.

Both sprints delivered working capabilities. This document does **not** recommend rewriting completed work solely because it is heavier than necessary.

It records where decisions were taken before real use cases required them, and defines a **forward direction** for new implementation.

**Orientation:**

```text
Sprint 002: ~1.3–1.5× larger than necessary (good vertical slice, heavy batch choices)
Sprint 003: ~1.8–2.5× larger than necessary (good domain direction, platform overbuild)
```

**Status:** ACCEPTED AS REVIEW (2026-07-12)  
**Binding for:** Sprint 004 planning and implementation; future Phase 4+ increments  
**Does not supersede:** accepted ADRs on `main` without explicit follow-up ADR

---

## 2. Sprint 002 — Market Data MVP

### 2.1 What worked (keep)

```text
DatasetRef
explicit lifecycle (WORKING → FINALIZED → PUBLISHED)
PUBLISHED immutability
Parquet storage
UTC normalization
OHLCV validation
storage path independent of identity
end-to-end integration test
```

Vertical slice was well scoped:

```text
CSV → inspect → normalize → validate → Parquet → register → finalize → publish → query
```

### 2.2 Overengineering areas

#### MarketBar as primary batch payload

`query_historical` returns `list[MarketBar]`. For multi-year 1m data this implies:

- high per-row Python object overhead,
- loss of Arrow/Polars columnar benefits,
- mandatory re-conversion before vectorized analysis.

**Forward direction:** batch query should support columnar payload (`MarketDataBatch`, `pl.LazyFrame`, or Arrow table) in a thin metadata wrapper. `MarketBar` remains valid for single events, runtime, replay, tests, and API boundaries.

#### Decimal for historical OHLCV

Prices use `Decimal`; Sprint 003 analysis uses `float64` via NumPy — an extra conversion layer exists between modules.

**Forward direction:**

```text
Historical analytical OHLCV: float64 or scaled integer
Orders, fills, accounting: Decimal or minor units
```

#### FileInspector subsystem

`FileInspector`, column mapping candidates, encoding detection — valuable for ad hoc multi-vendor import, not required for known-schema CSV MVP.

**Forward direction:** treat inspector as optional UX layer; explicit `ImportConfig` sufficient for first path.

#### Lifecycle ceremony in public API

Internal lifecycle separation is correct. Public API could offer `import_and_publish_dataset(...)` for static files while preserving internal state transitions.

#### Semantic DatasetId

Identity encodes instrument, timeframe, provider, source semantics. Risk: hard to evolve for continuous futures, derived bars, roll policies.

**Forward direction:** opaque stable `DatasetId` + rich `DatasetMetadata`.

#### Process granularity

26 tasks, practice close to one PR per task. Natural outcomes were larger than single contracts.

**Recommended sprint shape (reference):** 10–14 tasks, 4–5 outcome PRs.

Example PR grouping:

```text
PR 1 — Dataset identity and lifecycle
PR 2 — CSV normalization and validation
PR 3 — Parquet repository and metadata registry
PR 4 — Import, finalize, publish, query vertical slice
PR 5 — Integration tests and ADR
```

### 2.3 Sprint 002 summary

```text
Good vertical slice, moderate overengineering
Too object-oriented batch pipeline
Too much process fragmentation
```

---

## 3. Sprint 003 — Market Analysis Engine MVP

### 3.1 Real vertical slice vs platform built

**Needed for slice:**

```text
True Range → ATR → Volatility State
EMA, frame assembly, run_analysis, integration test
```

**Also built (platform scope):**

```text
ComponentId / ComponentVersion / ImplementationId / ImplementationVersion
multi-implementation registry and resolution policy
ComponentRequest, ComputationIdentity, OutputId, OutputRef, OutputSchema
Lineage, AvailabilityMetadata, Causality, HistoryRequirement
AnalysisResultStore, AnalysisWorkspace, AnalysisWorkspaceView
ExecutionCache (separate from result store)
AnalysisDataView (custom column API)
AnalysisFrameAssembler, ConsumerView
11 ADRs, 41 tasks, 7 waves, stacked PR workflow
```

Real goal was running a few analyses; delivery was a full component computation framework.

### 3.2 Overengineering areas

#### Component vs implementation identity (before second backend)

Only NumPy adapter shipped; TA-Lib deferred. Dual versioning axis and resolver exist without interchangeable backends.

**Rule:** abstraction after second real use case, not before.

#### Multi-implementation registry

Plugin-style resolution before proven need for dynamic backend selection.

**Minimal alternative:** `dict[ComponentId, ComponentDefinition]` until second backend exists.

#### Identity and reference proliferation

Simple ATR flows through many value objects. A single immutable `NodeKey` or one `ComputationIdentity` may suffice until complexity proves otherwise.

#### ResultStore + Workspace + Cache

All execution-scoped, executor-owned, holding overlapping roles. For single-plan batch MVP, one `ExecutionState: dict[NodeKey, ComponentResult]` could cover store, workspace, and in-plan cache.

Separate cache justified for cross-run reuse, persistence, partial reruns — not yet required.

#### Rejection of DataFrame as computational payload

Correctly rejected shared mutable `df["col"] = ...`. Also rejected columnar frame as primary payload.

Polars functional pipeline (`input → expression → new frame`) is not the same anti-pattern.

**Forward direction:** distinguish shared mutable DataFrame from immutable-style Polars pipeline.

#### AnalysisDataView as custom data API

Map-of-arrays with `column()`, `timestamps()` — tends toward a parallel DataFrame API requiring per-backend adapters and blocking LazyFrame/resampling integration.

**Forward direction:**

```python
@dataclass(frozen=True)
class MarketFrame:
    frame: pl.LazyFrame
    metadata: FrameMetadata  # lineage, timeframe, dataset identity
```

Thin metadata wrapper; do not emulate Polars API.

#### Over-granular DAG (True Range as public node)

Separate node justified when reusable, independently meaningful, cache-worthy. Not every formula step needs a public component.

#### Multi-output schema before real need

`OutputSchema`, diagnostic outputs in first slice tested framework generality more than a user problem.

**Progression:** one Series → real multi-output component → typed multi-output contract.

#### Metadata contracts (Causality, AvailabilityMetadata)

`HistoryRequirement`: practical from start.  
`AvailabilityMetadata`: important for MTF; derivable from bar metadata in single-TF MVP.  
`Causality`: valuable but could start as simple metadata field with default.

#### Execution cache duplication

If each node runs once per plan, results map already deduplicates. Separate `ExecutionCache` duplicates ResultStore for in-plan scope.

#### Error hierarchy breadth

Typed errors are fine; not every category needs a public type in MVP. Minimal: planning, execution, validation.

#### Process cost

41 tasks, 7 waves, many ADRs, stacked PRs, landing PRs, branch drift. Strong signal that process structure became its own complexity source.

**Recommended shape:** 14–16 tasks, 4–6 outcome PRs.

Example grouping:

```text
PR 1 — Request, identity, registry
PR 2 — DAG and sequential executor
PR 3 — Frame integration and warm-up
PR 4 — ATR, EMA, Volatility State vertical slice
PR 5 — Integration tests and one ADR
```

### 3.3 What to keep from Sprint 003

```text
ComponentRequest with explicit parameters
explicit dependencies
DAG, cycle detection, topological sort, deduplication
sequential batch execution
warm-up
computation fingerprint (parameters)
frame assembly
vertical slice and integration test
look-ahead-safe metadata direction (availability)
```

### 3.4 Lighter Sprint 003 reference scope

Had the sprint been scoped minimally:

```text
1. Polars MarketFrame input contract
2. ComponentDefinition
3. ComponentRequest + parameter normalization
4. Dependency declaration
5. NodeKey / computation fingerprint
6. DAG builder, cycle detection, topological sort
7. Sequential executor + ExecutionState result map
8. Warm-up
9. ATR, EMA, Volatility State
10. Frame assembly
11. End-to-end integration test
12. One ADR and documentation
```

(~14–16 outcome tasks)

---

## 4. Impact on Sprint 004

Sprint 004 inherits complexity from S002 and S003:

```text
S002: object batch payload (MarketBar list), Decimal → float64 conversion
S003: backend-neutral engine, AnalysisDataView, ResultStore/Workspace/Cache, multi-level identity
```

Adding MTF on top without simplification review risks:

```text
resampled view adapter
more identity wrappers
calendar subsystem
alignment policy enums
each Polars operation wrapped in new contracts
```

**Core architectural tension:**

```text
Instead of Polars as computational core,
the framework built a backend-neutral engine above any backend.
```

Every new feature pays adapter and identity tax.

**Sprint 004 mitigation (already in SPRINT_004.md):**

- Polars for resample/align only; single conversion boundary to existing component path,
- layered identity (not one mega key),
- ResampleNode not registry component,
- no Trading Calendar subsystem in MVP,
- 15 tasks, 5 PRs,
- behavior tests not structure tests.

**Additional gate:** complete §5 checklist before Wave 1 implementation.

---

## 5. Architecture Simplification Checklist (forward direction)

Use before expanding Sprint 004 or starting Sprint 005. Does **not** require rewriting S002/S003 on `main`.

### 5.1 Polars-first batch payload

Establish Polars DataFrame/LazyFrame as primary representation for:

```text
historical query (new paths)
normalization output (incremental)
Market Analysis batch pipeline
resampling and alignment
frame assembly
```

Existing `MarketBar` paths remain until migrated behind an ADR.

### 5.2 Limit MarketBar role

Keep for: single events, live runtime, replay, tests, API boundaries.  
Do not require for: million-row historical batch default.

### 5.3 Thin MarketFrame instead of AnalysisDataView growth

Prefer `MarketFrame(frame, metadata)` over extending custom column API.

### 5.4 Consider ExecutionState consolidation (future)

When touching executor/workspace: evaluate merging ResultStore + Workspace + in-plan Cache into one execution-scoped map. Only when lifecycle/persistence do not differ.

### 5.5 Simplify registry when adding backends

Do not extend multi-implementation resolver until a **second** backend is committed (e.g. Polars-native ATR alongside NumPy).

### 5.6 Minimal identity surface

Prefer one clear `NodeKey` or stage-appropriate layered keys (Sprint 004 model). Avoid new value object per pipeline stage.

### 5.7 Outcome-based planning

Plan working capabilities, not one contract per task.

### 5.8 ADR discipline

One ADR per real architectural decision, not per class.

### 5.9 Overengineering heuristic

```text
If a simple Polars operation requires several new public contracts,
first check whether the problem was over-abstracted upstream.
```

---

## 6. Final assessment

| Sprint | Verdict | Primary risks |
|--------|---------|---------------|
| 002 | Good slice, moderate overengineering | MarketBar batch, Decimal OHLCV, inspector weight, semantic DatasetId, task-per-PR |
| 003 | Good domain direction, platform overbuild | dual identity, multi-backend registry, Store+Workspace+Cache, AnalysisDataView, 41 tasks, many ADRs |

**Main recommendation:**

```text
Do not rewrite completed sprints.
Stop adding layers.
Move new work toward Polars-first, columnar, thin metadata wrappers,
explicit DAG, minimal identity, outcome-based planning.
```

Architecture must protect correctness, lineage, reproducibility, look-ahead safety, and dependency reuse — not replace Polars with a custom tabular framework.

---

## 7. Related artifacts

| Artifact | Relationship |
|----------|--------------|
| `docs/planning/sprints/SPRINT_002.md` | Sprint record; § Retrospective cross-ref |
| `docs/planning/sprints/SPRINT_003.md` | Sprint record; § Retrospective cross-ref |
| `docs/planning/sprints/SPRINT_004.md` | Design Principles; reduced scope |
| `docs/planning/TECHNICAL_DEBT.md` | TD-011–TD-016 accepted debt from this review |
| `docs/planning/CURRENT_STATUS.md` | Active simplification direction |

---

## 8. Revision history

| Date | Change |
|------|--------|
| 2026-07-12 | Initial review documented from maintainer retrospective |
