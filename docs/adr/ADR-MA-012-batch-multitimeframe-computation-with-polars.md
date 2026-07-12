# ADR-MA-012 — Batch Multitimeframe Computation with Polars

## Status

ACCEPTED

## Context

Sprint 003 delivered a single-timeframe batch analysis engine with `ComputationIdentity`,
dependency planning, execution cache and workspace storage. Phase 4 requires safe multitimeframe
(MTF) batch analysis: resample source OHLCV to a coarser computation timeframe, run existing
components on the resampled view, expose `available_at` on higher-timeframe outputs, and align
results onto a finer evaluation grid without look-ahead.

The MTF vision document describes broader roles (Market Model, Signal Model, published HTF
datasets). Sprint 004 applies a **lean MVP** slice: fixed UTC duration buckets, explicit
`ResampleNode` in the execution DAG, Polars for resample/align only, and layered cache identity.
Exchange/session calendars (PRB-007) are not required for this increment.

## Decision

### Timeframe roles (derived vs explicit)

Three roles exist; only two are set on public request types:

| Role | Source | Default when omitted |
|------|--------|----------------------|
| **Source** | `DatasetRef` / run `timeframe` | — |
| **Computation** | `ComponentRequest.computation_timeframe` | source timeframe |
| **Evaluation** | `RunAnalysisRequest.evaluation_timeframe` | source timeframe |

`RequestResolver` produces `RunTimeframeContext` and `ResolvedComponentRequest` with all three
roles materialized before planning. Resolved types carry explicit fields; public requests keep
optional overrides only.

### Resolved request model

`RequestResolver.resolve_input_plan()` runs **before** `DependencyPlanner`:

1. resolve run-level source and evaluation timeframes,
2. resolve per-component computation timeframes,
3. attach `ResolvedResampleRequirement` when computation timeframe is coarser than source,
4. emit `input_identity_key` (`ResampleIdentity.canonical_key()`) for downstream computation.

The planner consumes `ResolvedInputPlan`, deduplicates shared resample requirements, inserts
`ResampleNode` entries ahead of dependent component nodes, and does not infer resampling policy.

### ResampleSpec and OHLCV rules

`ResampleSpec` is a frozen dataclass with fixed Sprint 004 semantics:

- timezone: `UTC` only,
- bucket labeling: `closed=left`, `label=left`,
- aggregation version: `ohlcv_v1`.

OHLCV aggregation within each bucket:

```text
open   = first
high   = max
low    = min
close  = last
volume = sum
```

Implementation uses Polars `group_by_dynamic` with `every=target_timeframe.value`. Resampled bars
receive `available_at` via existing `derive_bar_interval(observed_at, target_timeframe)`.

**Partial bucket policy:** buckets align to UTC epoch boundaries relative to the sorted source
frame. A trailing partial bucket at the range end is emitted when it contains at least one source
row. Leading partial buckets occur when the first source timestamp falls inside an epoch-aligned
window (verified in behavior tests).

No `BoundaryPolicy` or `ResamplingPolicy` enums in Sprint 004.

### ResampleNode vs registry components

Resampling is an **execution DAG node type** (`ResampleNode`), not a `ComponentRegistry` entry.
Rationale:

- resampling is deterministic infrastructure, not an analytical component,
- shared resample outputs must dedupe by `ResampleIdentity`, not component parameters,
- NumPy component implementations remain unchanged on resampled `AnalysisDataView` inputs.

Flow:

```text
AnalysisDataView (source TF)
    → ResampleNode (Polars, cached by ResampleIdentity)
    → AnalysisDataView (target TF)
    → existing BatchAnalysisComponent / NumPy implementation
```

### Temporal availability and LAST_CLOSED_BAR

When computation timeframe is coarser than source, `OutputSeries.available_at` is populated on
component results (tuple parallel to values). Single-timeframe outputs omit `available_at` (`None`).

Frame assembly and alignment use `AlignmentPolicy.LAST_CLOSED_BAR` (default): Polars backward
`join_asof` on `available_at` onto the evaluation grid timestamps. Incomplete higher-timeframe
bars must not appear on earlier lower-timeframe evaluation timestamps.

`AlignmentPolicy.INTRABAR` is reserved; not used in Sprint 004 MVP.

### Layered identity boundaries

Three identity layers prevent cache and lineage pollution:

| Layer | Type | Scope |
|-------|------|-------|
| Resample | `ResampleIdentity` | shared resampled market view |
| Component computation | `ComputationIdentity` (+ optional `input_identity_key`) | one component execution |
| Alignment | `AlignmentIdentity` | presentation on evaluation grid |

`ResampleCache` keys resample-stage outputs. `ExecutionCache` keys component results by
`ComputationIdentity` (ADR-MA-008). `AlignmentCache` keys aligned column tuples by
`AlignmentIdentity`. Alignment dimensions do not appear in computation cache keys.

Material input changes (dataset version, target timeframe, resample spec, evaluation range,
alignment policy) change the appropriate layer's canonical key independently.

### Polars scope (resample/align only)

Polars is a **runtime dependency** used at two boundaries:

1. OHLCV resampling (`group_by_dynamic`) in `ResampleNode` execution,
2. backward as-of alignment (`join_asof`) in frame assembly.

Conversion to existing domain types remains at the boundary:

```text
AnalysisDataView → Polars → resample/align → MarketBar → AnalysisDataView
```

NumPy component kernels are unchanged. Full columnar `MarketFrame` migration (TD-015) and query-path
columnar batches (TD-011) remain deferred.

### Trading Calendar deferral

Sprint 004 uses **fixed UTC duration** buckets only. Exchange sessions, holidays, shortened
sessions and DST-aware boundaries are **not** implemented. PRB-007 remains OPEN; calendar-aware
resampling is deferred to Sprint 005+ when a CME/session use case requires it.

This ADR is the single MTF batch decision record for Sprint 004. No separate calendar MVP ADR is
introduced in this sprint.

## Consequences

### Positive

- End-to-end MTF vertical slice validated: 1m dataset → 5m ATR aligned to 1m + 1m EMA.
- Look-ahead protection enforced by `available_at` + backward `join_asof`.
- Shared resample executes once per plan (planner dedupe + `ResampleCache`).
- Sprint 003 single-timeframe path remains backward compatible when computation and evaluation
  timeframes equal source.
- One ADR consolidates MTF MVP decisions; avoids policy-enum proliferation.

### Negative

- Resample/align conversion cost at Polars ↔ `MarketBar` boundary (see spike note TD-011/TD-015).
- Fixed UTC buckets may misalign with exchange session boundaries until PRB-007 is resolved.
- Published HTF dataset reuse vs on-the-fly resample is not auto-resolved (noted in
  `ResolvedInputPlan` docstring for future work).
- `ResamplingPolicy`, exchange calendar and intrabar consumption remain future increments.

## References

- `docs/planning/sprints/S004_MTF_SPIKE_AND_DECISIONS.md` — spike evidence and binding decisions
- `docs/planning/sprints/SPRINT_004.md` — sprint scope and design principles
- `docs/planning/PROBLEM_REGISTRY.md` — PRB-007 (deferred)
- `docs/vision/MULTITIMEFRAME_MARKET_MODEL_ARCHITECTURE_UPDATED.md` — long-term MTF vision
- `docs/adr/ADR-MA-008-cache-identity-and-cache-scope.md` — computation cache baseline
- `docs/adr/ADR-MA-009-warmup-causality-and-availability.md` — availability semantics
- `src/trading_framework/market_analysis/planning/resolution.py`
- `src/trading_framework/market_analysis/data/resample.py`
- `src/trading_framework/market_analysis/data/align.py`
- `src/trading_framework/market_analysis/assembly/assembler.py`
- `tests/unit/market_analysis/test_mtf_behavior.py`
- `tests/integration/test_market_analysis_mtf_vertical_slice.py`
