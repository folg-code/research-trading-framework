# Sprint 003 — Wave 0 Architecture Closure

```text
Date: 2026-06-23
Sprint: 003
Wave: 0
Task: S003-T001
Status: ACCEPTED FOR IMPLEMENTATION
```

## Purpose

Confirm that architecture decisions for Market Analysis MVP are complete enough to begin
Wave 1 contract implementation after the technical spike (S003-T002/T003).

Sources:

- `docs/vision/MARKET_ANALYSIS_WITH_DECISIONS.md` (D-001–D-036)
- `docs/vision/ANALYSIS_WORKSPACE_AND_DERIVED_DATA.md` (§29–§33, invariants §32)

Where the documents conflict on workspace or derived-data topics, the workspace document
takes precedence.

---

## Decision Groups

### Domain boundary — ACCEPTED

| Ref | Decision | Status |
|-----|----------|--------|
| D-001 | Market Analysis owns Feature, Structure, State only | ACCEPTED |
| D-002 | MVP categories: Feature, Structure, State | ACCEPTED |
| D-003 | Public component granularity by analytical/reuse value | ACCEPTED |
| Workspace §7 | Public vs internal temporaries | ACCEPTED |

No blocking open questions.

### Identity and requests — ACCEPTED

| Ref | Decision | Status |
|-----|----------|--------|
| D-004 | `ComponentId` ≠ `ImplementationId` | ACCEPTED |
| D-006 | `ComponentRequest` ≠ `ComputationIdentity` | ACCEPTED |
| D-007 | Typed parameter schemas; dict only at API boundary | ACCEPTED |
| D-019 | Dataset identity from published `DatasetRef` | ACCEPTED |
| Workspace §10 | Aliases ≠ computation identity | ACCEPTED |

PRB-002 (parameter fingerprint) — MVP slice resolved in Wave 1; full cross-domain policy deferred.

### Dependencies and DAG — ACCEPTED

| Ref | Decision | Status |
|-----|----------|--------|
| D-008 | Explicit data + component dependencies | ACCEPTED |
| D-009 | Dynamic deps deterministic from parameters | ACCEPTED |
| D-016 | DAG node = resolved computation | ACCEPTED |
| D-017 | Lazy execution of requested outputs only | ACCEPTED |
| Workspace §11 | `ComponentOutputRef` for multi-output deps | ACCEPTED |

### Data access and workspace — ACCEPTED

| Ref | Decision | Status |
|-----|----------|--------|
| D-011 | Components receive read-only market input view | ACCEPTED |
| D-012 | Domain contract technology-neutral | ACCEPTED |
| D-013 | Read-only input; stateless batch components | ACCEPTED |
| Workspace §3–§9 | Four-layer model; executor-only workspace mutation | ACCEPTED |
| Workspace §12 | `AnalysisResultStore` not a single required DataFrame | ACCEPTED |
| Workspace §23 | No persistent derived storage in Sprint 003 | ACCEPTED |

Physical representation details frozen after spike (S003-T003).

### Results, outputs, lineage — ACCEPTED

| Ref | Decision | Status |
|-----|----------|--------|
| D-014 | Multi-output `AnalysisResult` | ACCEPTED |
| D-015 | Stable `OutputId`; aliases are presentation | ACCEPTED |
| D-026 | Lineage mandatory | ACCEPTED |
| D-025 | Executor validates adapter outputs | ACCEPTED |
| Workspace §6 | Internal temporaries not published | ACCEPTED |

PRB-005 (result storage shape) — MVP in-memory map-of-outputs; persistent shape deferred.

### Warm-up, causality, availability — ACCEPTED

| Ref | Decision | Status |
|-----|----------|--------|
| D-020 | `HistoryRequirement`; engine extends range | ACCEPTED |
| D-021 | Causality categories | ACCEPTED |
| D-022 | `available_at` in contract | ACCEPTED |
| D-029 | Single-timeframe MVP | ACCEPTED |

### Cache and execution — ACCEPTED

| Ref | Decision | Status |
|-----|----------|--------|
| D-018 | Exact-match in-memory execution cache, single plan | ACCEPTED |
| D-023 | `BatchAnalysisComponent` only | ACCEPTED |
| D-024 | Deterministic batch default | ACCEPTED |
| D-028 | Sequential in-memory executor | ACCEPTED |
| D-027 | `float64` research default | ACCEPTED |

### Registry and external libraries — ACCEPTED

| Ref | Decision | Status |
|-----|----------|--------|
| D-005 | TA-Lib optional extra; not domain contract | ACCEPTED |
| D-010 | Multi-implementation registry with explicit default | ACCEPTED |
| D-033 | Shared adapter contract tests | ACCEPTED |
| D-034 | Semantic contract + numeric tolerance | ACCEPTED |

### Vertical slice and consumer views — ACCEPTED

| Ref | Decision | Status |
|-----|----------|--------|
| D-035 | `True Range → ATR → Volatility State` + component dep | ACCEPTED |
| Workspace §29 | + reusable feature (EMA) + diagnostic output in integration test | ACCEPTED |
| Workspace §13–§14 | `AnalysisFrame` as explicit consumer materialization | ACCEPTED |
| D-032 | Public API: request, schema, protocols, registry, facade | ACCEPTED |

### User components and models — ACCEPTED

| Ref | Decision | Status |
|-----|----------|--------|
| D-031 | User components same contract as core | ACCEPTED |
| Workspace §24–§25 | Models declare outputs; do not own DataFrames | ACCEPTED |

---

## Entry Criteria Check (MARKET_ANALYSIS §18)

| Criterion | Status |
|-----------|--------|
| D-001–D-036 accepted or explicitly open | PASS — all accepted |
| Required ADRs for Wave 1 drafted in Wave 0 PR (T034 draft) | PASS — planned in same sprint branch |
| `AnalysisDataView` checked in spike | PENDING — S003-T003 |
| Benchmark dataset defined | PASS — synthetic 1y 1m equivalent (~98k bars) |
| Reference outputs for vertical slice defined | PASS — True Range, ATR, EMA, Volatility State + diagnostic |
| Dataset identity from `DatasetRef` | PASS — uses Sprint 002 `DatasetRef` contract |
| Sprint scope decomposed to PRs | PASS — `SPRINT_003.md` |
| `CURRENT_STATUS.md` updated | PASS — Wave 0 PR |

---

## Explicitly Deferred Beyond Sprint 003

Unchanged from architecture documents:

- persistent / cross-process cache,
- `DerivedAnalysisDataset` storage,
- column pruning implementation,
- parallel and distributed execution,
- multitimeframe alignment and resampling nodes,
- incremental / live execution,
- Market Model and Signal Model execution,
- full indicator library,
- GPU backends,
- automatic backend optimizer.

---

## Blocking Open Questions

```text
None for Wave 1 start after spike sign-off (S003-T004).
```

---

## Sign-off

Architecture closure for Sprint 003 Wave 0 is **complete** pending spike report approval
in S003-T003/T004.
