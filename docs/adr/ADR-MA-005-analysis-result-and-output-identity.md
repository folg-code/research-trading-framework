# ADR-MA-005 — AnalysisResult and Output Identity

## Status

ACCEPTED

Amended 2026-08-25 for D-REP-10 (lineage sidecar after evaluation-frame assembly).

## Context

PRB-005 asked how Features, Structures and States should be stored. Sprint 003 needed a shape that
supports multi-output components, warm-up metadata and lineage without forcing a universal scalar schema.

## Decision

Components **return** `AnalysisResult` objects; the executor registers them in `AnalysisResultStore`.

Each result includes:

- `ComputationIdentity`,
- `OutputSchema` and typed `OutputSeries` map,
- `Lineage` (dataset, component, implementation, parameters, dependency keys, engine version),
- `ValidityMetadata` and `WarmUpMetadata`,
- `AvailabilityMetadata`,
- optional diagnostics map.

Semantic `OutputId` values are stable; presentation aliases are applied only at frame assembly.

Output groups distinguish core vs diagnostic outputs (`OutputGroup.CORE`, `OutputGroup.DIAGNOSTIC`).

Persistent derived-dataset storage is **out of Sprint 003 scope**.

## Amendment 2026-08-25 — lineage sidecar (D-REP-10)

`AnalysisResult.Lineage` remains the per-computation record. `AnalysisFrame.column_lineage` must
stay addressable after `build_evaluation_dataframe`. Stage 3 binds evaluation columns to their
producing `OutputRef` through a **sidecar keyed by assembled column name**, not extra lineage
columns on the evaluation frame.

Name uniqueness is already enforced by `AliasCollisionError` in `AnalysisFrameAssembler`. Reject
lineage-as-columns unless a later research-reproducibility requirement demands it.

## Consequences

### Positive

- multi-output state components (core + diagnostic) without schema hacks,
- PRB-005 MVP resolution via typed in-memory results and explicit lineage.

### Negative

- no long-term persistence format yet,
- Structures with event semantics may need additional payload types later.

## References

- `docs/vision/MARKET_ANALYSIS_WITH_DECISIONS.md` — D-014, D-015, D-025
- `docs/planning/PROBLEM_REGISTRY.md` — PRB-005 (MVP resolution note)
- `src/trading_framework/market_analysis/models/result.py`
- `docs/reference/system/DATA_REPRESENTATION_AUDIT.md` — D-REP-10
