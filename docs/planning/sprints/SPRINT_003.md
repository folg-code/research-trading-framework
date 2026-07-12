# Sprint 003 — Market Analysis Engine MVP

## Metadata

```text
Sprint: 003
Phase: Phase 3 — Market Analysis Engine MVP
Status: IN_PROGRESS (Waves 0–4 COMPLETE; Wave 5 next)
Planned Start: 2026-06-23
Planned End: TBD
Sprint Goal Owner: Project Maintainer
Depends On: SPRINT_002 (COMPLETED)
Sprint Branch: sprint/market-analysis-mvp
Architecture Sources:
  - docs/vision/MARKET_ANALYSIS_WITH_DECISIONS.md (engine, identity, DAG, cache)
  - docs/vision/ANALYSIS_WORKSPACE_AND_DERIVED_DATA.md (workspace, result store, frames)
Precedence: where documents conflict on workspace or derived-data topics, the workspace
document is authoritative (newer).
```

---

## Sprint Goal

```text
Design and implement a minimal deterministic Market Analysis Engine that
registers components, resolves dependencies, builds a DAG, deduplicates shared
computations, executes batch analysis sequentially, manages execution-scoped
result storage and workspace, applies in-memory execution cache, and returns
results with full identity and lineage — without using a shared mutable DataFrame
as the primary domain model.
```

Success means the framework runs a complete flow from a published `DatasetRef`:

```text
MarketDataset (via DatasetRef)
    ↓
AnalysisDataView (read-only canonical OHLCV)
    ↓
Component DAG execution
    ↓
AnalysisResultStore (per-output identity)
    ↓
AnalysisWorkspace (execution-scoped, executor-owned)
    ↓
AnalysisFrameAssembler → ConsumerView / AnalysisFrame
```

Vertical slice components:

```text
True Range → ATR → Volatility State
+ EMA(20) (additional reusable feature)
+ at least one diagnostic output
```

The sprint validates architecture through an external-library adapter (NumPy default; TA-Lib optional extra), not through building an indicator catalog.

---

## Phase Alignment

This sprint implements **Phase 3 — Market Analysis Engine MVP** from `ROADMAP.md`.

Primary flow (four-layer model):

```text
MarketDataset
    ↓
AnalysisResultStore
    ↓
AnalysisWorkspace
    ↓
ConsumerView / AnalysisFrame
```

Execution path:

```text
Published DatasetRef → ComponentRequest → DAG → Sequential Execution
    → AnalysisResult (per node) → ResultStore → Workspace → optional AnalysisFrame
```

Phase 3 completion criteria deferred to later sprints remain explicitly out of scope (see below).

---

## Architectural Decisions (Binding)

Decisions **D-001 through D-036** in `MARKET_ANALYSIS_WITH_DECISIONS.md` and architectural
invariants §32 in `ANALYSIS_WORKSPACE_AND_DERIVED_DATA.md` are binding unless superseded by
an accepted ADR before implementation.

Key constraints for planning:

| Area | Decision |
|------|----------|
| Domain | Features, Structures, States only — not Market Model / Strategy |
| Data layers | `MarketDataset` → `AnalysisResultStore` → `AnalysisWorkspace` → `ConsumerView` |
| Semantics vs implementation | `ComponentId` ≠ `ImplementationId` |
| Data access | Components receive read-only market input view; no Parquet/repository in components |
| Output model | Components **return** `AnalysisResult`; executor registers outputs — no `df["col"] = ...` |
| Public vs internal | Only declared outputs enter store/workspace; temporaries stay local |
| Dependencies | Explicit data + component deps via `ComponentOutputRef`; no hidden calls in `compute()` |
| Aliases | Presentation aliases ≠ computation identity; collisions fail explicitly |
| Execution | Batch, sequential, single-timeframe, in-memory materialization |
| DAG node | Resolved computation (`ATR(14)` ≠ `ATR(50)`) |
| Cache | Exact-match execution cache, in-memory, single plan only |
| Frames | `AnalysisFrame` is workflow-specific materialization, not canonical Market Data |
| Vertical slice | `True Range → ATR → Volatility State` + reusable feature + diagnostic output |
| Persistence | No `DerivedAnalysisDataset` storage in Sprint 003 |
| Spike gate | Data view and internal representation frozen only after technical benchmark |

---

## Scope

In scope:

- architecture closure and technical spike (Wave 0),
- identity and core contracts: request, parameters, result, lineage, warm-up, causality, availability,
- component and implementation protocols,
- registry with multi-implementation resolution,
- dependency planner: expansion, cycle detection, topological sort,
- sequential batch executor, `AnalysisResultStore`, `AnalysisWorkspace`,
- execution cache integrated with result store,
- `AnalysisDataView` and Data Module bridge (`DatasetRef` → bars → view),
- `AnalysisFrameAssembler`, `AnalysisFrameRequest`, deterministic aliases,
- vertical slice components: True Range, ATR, EMA, Volatility State (+ diagnostic output),
- NumPy adapter (default MVP backend); TA-Lib as optional extra,
- contract, integration and identity tests,
- ADR materialization for Market Analysis (see task T036),
- partial MVP resolution of PRB-002 (computation fingerprint) and PRB-005 (result shape).

Out of scope:

- complete indicator library,
- persistent derived-data storage (`DerivedAnalysisDataset`),
- column pruning implementation,
- persistent or cross-process cache,
- parallel, distributed or GPU execution,
- incremental or live execution,
- multitimeframe, resampling, backward as-of alignment,
- Market Model, Signal Model, Strategy composition,
- Research dataset consumption workflows,
- user-facing component authoring tooling beyond shared contract,
- final backend standardization (pandas vs Polars vs TA-Lib as sole backend).

---

## Dependencies

```text
Sprint 002 — published DatasetRef, query_historical, MarketBar (complete)
docs/vision/MARKET_ANALYSIS_WITH_DECISIONS.md
docs/vision/ANALYSIS_WORKSPACE_AND_DERIVED_DATA.md
docs/vision/MULTITIMEFRAME_MARKET_MODEL_ARCHITECTURE_UPDATED.md (directional)
docs/agents/AGENTS_MULTITIMEFRAME_MARKET_MODEL_UPDATED (1).md
```

New runtime dependencies expected:

- `numpy` — default analytical adapter backend (demonstrated need after spike),
- `pandas` — spike comparison and optional adapter only unless spike mandates,
- `TA-Lib` — optional extra (`framework[talib]`), never required for core install.

Prefer the smallest dependency set confirmed by the Wave 0 spike.

---

## Risks

| Risk | Mitigation |
|------|------------|
| Overengineering before real use cases | Minimal vertical slice; spike before contract freeze |
| Premature pandas/TA-Lib lock-in | Neutral domain contracts; adapters behind implementation protocol |
| Shared mutable DataFrame anti-pattern | Components return outputs; executor-only workspace mutation |
| Hidden dataset copies | Read-only view; spike measures memory, map-of-arrays vs wide DataFrame |
| Wide workspace complexity | Explicit output identity, aliases, deferred flat-frame assembly |
| Incorrect cache identity | Separate `ComponentRequest` and `ComputationIdentity` |
| Look-ahead bias | Causality + availability metadata from day one |
| Excessive DAG granularity | D-003: public components only when analytically meaningful |
| Sprint too large | Strict batch/single-timeframe; defer MTF and persistent cache |
| Spike blocks progress | Time-box Wave 0; default to NumPy if TA-Lib unavailable on CI |

---

## Task Summary

| ID | Task | Status | Depends On |
|----|------|--------|------------|
| S003-T001 | Architecture closure checklist (both architecture docs) | DONE | — |
| S003-T002 | Technical spike: backend and workspace benchmark | DONE | S003-T001 |
| S003-T003 | Spike report: AnalysisDataView and internal representation | DONE | S003-T002 |
| S003-T004 | Wave 0 gate: Definition of Ready sign-off | DONE | S003-T003 |
| S003-T005 | Component and implementation identity models | DONE | S003-T004 |
| S003-T006 | ComponentKind, Causality, HistoryRequirement | DONE | S003-T004 |
| S003-T007 | Parameter schema and canonicalization (PRB-002 MVP) | DONE | S003-T005 |
| S003-T008 | ComponentRequest contract | DONE | S003-T007 |
| S003-T009 | ComputationIdentity contract | DONE | S003-T005, S003-T008 |
| S003-T010 | AnalysisContext contract | DONE | S003-T008 |
| S003-T011 | AnalysisResult, OutputId, OutputRef, OutputSchema (PRB-005 MVP) | DONE | S003-T009 |
| S003-T012 | Lineage and availability metadata models | DONE | S003-T011 |
| S003-T013 | Component and implementation protocols | DONE | S003-T006, S003-T011 |
| S003-T014 | Component registry and resolution policy | DONE | S003-T013 |
| S003-T015 | Data and component dependency declarations | DONE | S003-T013 |
| S003-T016 | Request normalization and dependency expansion | DONE | S003-T014, S003-T015 |
| S003-T017 | Cycle detection | DONE | S003-T016 |
| S003-T018 | Topological sort and execution plan | DONE | S003-T017 |
| S003-T019 | AnalysisDataView contract | DONE | S003-T003, S003-T004 |
| S003-T020 | Data Module bridge: DatasetRef to AnalysisDataView | DONE | S003-T019 |
| S003-T037 | AnalysisResultStore | DONE | S003-T011, S003-T018 |
| S003-T038 | AnalysisWorkspace (executor-controlled registration) | DONE | S003-T037 |
| S003-T021 | Sequential batch executor | DONE | S003-T018, S003-T020, S003-T038 |
| S003-T022 | Execution cache (exact-match, in-plan) | DONE | S003-T021, S003-T037 |
| S003-T023 | Warm-up range extension and output validation | DONE | S003-T021 |
| S003-T024 | Analysis error hierarchy | DONE | S003-T021 |
| S003-T025 | True Range Feature component | DONE | S003-T014, S003-T020 |
| S003-T026 | ATR Feature and NumPy adapter | DONE | S003-T025 |
| S003-T027 | Optional TA-Lib adapter extra | TODO | S003-T026 |
| S003-T040 | EMA reusable Feature component | DONE | S003-T014, S003-T020 |
| S003-T028 | Volatility State + diagnostic output | DONE | S003-T026 |
| S003-T039 | AnalysisFrameAssembler and alias policy | DONE | S003-T038, S003-T028 |
| S003-T029 | Engine facade and run_analysis use case | DONE | S003-T022, S003-T039 |
| S003-T030 | Adapter contract test suite | TODO | S003-T026 |
| S003-T031 | Integration test: wide AnalysisFrame from DatasetRef | TODO | S003-T029 |
| S003-T041 | Workspace and frame assembly tests | TODO | S003-T039 |
| S003-T032 | Cache dedup and cycle detection tests | TODO | S003-T022, S003-T017 |
| S003-T033 | Input immutability and identity tests | TODO | S003-T021 |
| S003-T034 | Market Analysis ADRs (ADR-0005 + MA decisions) | TODO | S003-T004 |
| S003-T035 | Update architecture docs and problem registry notes | TODO | S003-T034 |
| S003-T036 | Sprint review and CURRENT_STATUS update | TODO | All preceding tasks |

---

## Tasks

### S003-T001 — Architecture closure checklist (D-001–D-036)

**Status:** DONE  
**Category:** Architecture  
**Domain:** Market Analysis  
**Wave:** 0

#### Scope

Confirm all decisions in both architecture documents are accepted for implementation or explicitly listed as open with an owner:

- `MARKET_ANALYSIS_WITH_DECISIONS.md` — D-001 through D-036,
- `ANALYSIS_WORKSPACE_AND_DERIVED_DATA.md` — four-layer model, invariants §32, Sprint 003 requirements §29.

Produce a short closure note referencing: domain, identity, dependencies, data view, result store, workspace, cache, warm-up, vertical slice, frame assembly.

#### Acceptance Criteria

- [x] No blocking open questions remain undocumented
- [x] Deferred decisions (beyond Sprint 003) are listed and unchanged
- [x] Entry criteria from architecture doc §18 are checked

Artifact: `docs/planning/sprints/S003_WAVE0_ARCHITECTURE_CLOSURE.md`

---

### S003-T002 — Technical spike: backend and workspace benchmark

**Status:** DONE  
**Category:** Spike  
**Domain:** Market Analysis / Infrastructure  
**Wave:** 0  
**Depends On:** S003-T001

#### Scope

Benchmark outside production module (e.g. `user_data/development/` or `tests/spike/`, not committed as framework API):

- backends: NumPy, pandas, optional TA-Lib, optional Polars,
- operations: ATR, EMA, rolling max, shared dependency reuse,
- dataset: representative OHLCV bars (≥ 1 year 1m; prefer published fixture or synthetic equivalent for CI).

Measure wall-clock, peak memory, conversion cost, copy cost, adapter overhead, and:

- cost of adding many outputs,
- map-of-arrays vs wide DataFrame memory,
- repeated DataFrame concatenation vs deferred assembly,
- conversion cost for TA-Lib and pandas adapters.

#### Acceptance Criteria

- [x] Spike script runs locally without external APIs
- [x] Results recorded in spike report artifact (markdown under `docs/planning/` or sprint notes)
- [x] No new mandatory runtime dependency without demonstrated need (NumPy deferred to Wave 1 PR)

Artifact: `tests/spike/run_market_analysis_backend_benchmark.py`

---

### S003-T003 — Spike report: AnalysisDataView and internal representation

**Status:** DONE  
**Category:** Architecture  
**Domain:** Market Analysis  
**Wave:** 0  
**Depends On:** S003-T002

#### Scope

Document spike outcomes and freeze MVP designs:

- `AnalysisDataView` — read-only canonical market columns (D-011),
- internal workspace representation — must not require a single pandas DataFrame (§19 workspace doc),
- `AnalysisResultStore` lookup model — map of arrays or equivalent,
- float64 default (D-027),
- relationship to `MarketBar` / `query_historical`.

#### Acceptance Criteria

- [x] Design decision references spike metrics
- [x] D-036 satisfied: data contract not approved on aesthetics alone
- [x] Open questions for Wave 1 contracts are empty or deferred with reason

Artifact: `docs/planning/sprints/S003_WAVE0_SPIKE_REPORT.md`

---

### S003-T004 — Wave 0 gate: Definition of Ready sign-off

**Status:** DONE  
**Category:** Planning  
**Domain:** Core  
**Wave:** 0  
**Depends On:** S003-T003

#### Scope

Confirm sprint implementation may start (architecture doc §16, §20).

Update this file: Wave 0 tasks marked DONE; implementation waves unblocked.

#### Acceptance Criteria

- [x] Definition of Ready checklist complete
- [x] Sprint branch `sprint/market-analysis-mvp` created from `main`
- [x] First implementation work may start (outcome-scoped PRs; see PR guidance below)

#### Definition of Ready — signed 2026-06-23

```text
[x] Sprint goal is unambiguous
[x] Architecture decisions documented (D-001–D-036 + workspace invariants)
[x] No blocking open contract questions
[x] Spike confirms data/workspace representation viability
[x] Vertical slice defined (True Range → ATR → Volatility State + EMA + diagnostic)
[x] In/out scope frozen in SPRINT_003.md
[x] PR pipeline defined
```

**Wave 1 implementation is UNBLOCKED.**

---

### S003-T005 — Component and implementation identity models

**Status:** TODO  
**Category:** Architecture  
**Domain:** Market Analysis  
**Wave:** 1  
**Depends On:** S003-T004

#### Scope

Implement in `src/trading_framework/market_analysis/`:

- `ComponentId`, `ComponentVersion`,
- `ImplementationId`, `ImplementationVersion`,
- validation and canonical string forms.

#### Acceptance Criteria

- [ ] Identity types are immutable value objects
- [ ] Semantic and implementation identity are separate types
- [ ] Unit tests cover validation and equality

---

### S003-T006 — ComponentKind, Causality, HistoryRequirement

**Status:** TODO  
**Category:** Architecture  
**Domain:** Market Analysis  
**Wave:** 1  
**Depends On:** S003-T004

#### Scope

Define enums/value objects:

- `ComponentKind`: Feature, Structure, State,
- `Causality`: Causal, Delayed, Retrospective,
- `HistoryRequirement` for warm-up declaration.

#### Acceptance Criteria

- [ ] Types exported from market_analysis public API
- [ ] Documented in module docstring
- [ ] Unit tests for enum parsing and validation

---

### S003-T007 — Parameter schema and canonicalization (PRB-002 MVP)

**Status:** TODO  
**Category:** Architecture  
**Domain:** Market Analysis  
**Wave:** 1  
**Depends On:** S003-T005

#### Scope

Typed parameter schemas per component with:

- validation,
- default completion,
- canonical serialization for fingerprinting.

Resolve MVP slice of PRB-002 for computation parameters (not full cross-domain fingerprint policy).

#### Acceptance Criteria

- [ ] Raw `dict[str, Any]` only at API boundary
- [ ] Canonical form is deterministic and JSON-serializable
- [ ] Unit tests for defaults, validation and canonicalization

---

### S003-T008 — ComponentRequest contract

**Status:** TODO  
**Category:** Architecture  
**Domain:** Market Analysis  
**Wave:** 1  
**Depends On:** S003-T007

#### Scope

Define `ComponentRequest` per D-006: component id + validated parameters only.

No dataset path, DataFrame, cache key or lineage in request.

#### Acceptance Criteria

- [ ] Request is immutable
- [ ] Protocol or dataclass documented as public contract
- [ ] Unit tests reject invalid requests

---

### S003-T009 — ComputationIdentity contract

**Status:** TODO  
**Category:** Architecture  
**Domain:** Market Analysis  
**Wave:** 1  
**Depends On:** S003-T005, S003-T008

#### Scope

Define resolved `ComputationIdentity` including component, implementation, parameters, dataset identity, timeframe, range, dependency identities.

Distinct from `ComponentRequest`.

#### Acceptance Criteria

- [ ] Identity is hashable or provides stable canonical key
- [ ] Unit tests prove request ≠ computation identity
- [ ] Suitable for execution cache keying

---

### S003-T010 — AnalysisContext contract

**Status:** TODO  
**Category:** Architecture  
**Domain:** Market Analysis  
**Wave:** 1  
**Depends On:** S003-T008

#### Scope

Runtime context for one analysis run:

- published `DatasetRef`,
- instrument/timeframe (single-timeframe MVP),
- requested time range,
- computation range (after warm-up extension),
- engine version metadata.

#### Acceptance Criteria

- [ ] Context is immutable for duration of plan execution
- [ ] Rejects multitimeframe mismatch in MVP (D-029)
- [ ] Unit tests cover range validation

---

### S003-T011 — AnalysisResult, OutputId, OutputRef, OutputSchema (PRB-005 MVP)

**Status:** TODO  
**Category:** Architecture  
**Domain:** Market Analysis  
**Wave:** 1  
**Depends On:** S003-T009

#### Scope

Multi-output result contract:

- `OutputId`, `OutputRef`, `ComponentOutputRef`,
- `OutputSchema` with core and optional diagnostic output groups,
- `AnalysisResult` with outputs map, valid range, diagnostics,
- serialization helpers for tests.

Dependencies reference specific outputs via `ComponentOutputRef`, not column order.

#### Acceptance Criteria

- [ ] Result supports one or many outputs (D-014, D-015)
- [ ] MVP result shape documented; PRB-005 note updated
- [ ] Unit tests for schema validation

---

### S003-T012 — Lineage and availability metadata models

**Status:** TODO  
**Category:** Architecture  
**Domain:** Market Analysis  
**Wave:** 1  
**Depends On:** S003-T011

#### Scope

`Lineage` (D-026): dataset, component, implementation, parameters, dependencies, engine version, execution timestamp.

`AvailabilityMetadata` (D-022): observation vs availability timestamps.

#### Acceptance Criteria

- [ ] Lineage attached to every `AnalysisResult`
- [ ] Serializable to JSON-compatible dict
- [ ] Unit tests for required fields

---

### S003-T013 — Component and implementation protocols

**Status:** TODO  
**Category:** Architecture  
**Domain:** Market Analysis  
**Wave:** 2  
**Depends On:** S003-T006, S003-T011

#### Scope

Define protocols in `market_analysis/protocols/`:

- `BatchAnalysisComponent` — declares kind, causality, history, deps, parameters schema, outputs,
- `ComponentImplementation` — executes against read-only view + dependency results.

No data fetching inside implementation.

#### Acceptance Criteria

- [ ] Protocols documented with explicit dependency declaration methods
- [ ] Stub implementations pass mypy protocol checks
- [ ] Architecture boundary test: no market_analysis import of infrastructure storage

---

### S003-T014 — Component registry and resolution policy

**Status:** TODO  
**Category:** Feature  
**Domain:** Market Analysis  
**Wave:** 2  
**Depends On:** S003-T013

#### Scope

Registry supporting:

- multiple implementations per `ComponentId`,
- default implementation policy (D-010),
- explicit implementation selection,
- registration conflict errors.

#### Acceptance Criteria

- [ ] Register and resolve components
- [ ] Duplicate default implementation raises explicit error
- [ ] Unit tests for resolution policies

---

### S003-T015 — Data and component dependency declarations

**Status:** TODO  
**Category:** Architecture  
**Domain:** Market Analysis  
**Wave:** 2  
**Depends On:** S003-T013

#### Scope

Models for:

- `DataDependency` (e.g. OHLCV fields),
- `ComponentDependency` with `ComponentOutputRef` for specific outputs,
- dynamic deps deterministic from parameters (D-009).

#### Acceptance Criteria

- [ ] Dependencies exposed separately from compute
- [ ] Unit tests for parameter-dependent dependency lists

---

### S003-T016 — Request normalization and dependency expansion

**Status:** TODO  
**Category:** Feature  
**Domain:** Market Analysis  
**Wave:** 2  
**Depends On:** S003-T014, S003-T015

#### Scope

Planner phase 1:

- validate and normalize requests,
- expand component dependencies recursively,
- assign implementation ids,
- build preliminary node list keyed by `ComputationIdentity`.

#### Acceptance Criteria

- [ ] Expansion is deterministic
- [ ] Unit tests with nested component dependencies

---

### S003-T017 — Cycle detection

**Status:** TODO  
**Category:** Feature  
**Domain:** Market Analysis  
**Wave:** 2  
**Depends On:** S003-T016

#### Scope

Detect cycles in component dependency graph; return explicit error with cycle path.

#### Acceptance Criteria

- [ ] Cyclic dependency raises structured error
- [ ] Unit tests for simple and multi-node cycles

---

### S003-T018 — Topological sort and execution plan

**Status:** TODO  
**Category:** Feature  
**Domain:** Market Analysis  
**Wave:** 2  
**Depends On:** S003-T017

#### Scope

Produce deterministic `ExecutionPlan`:

- topologically sorted nodes,
- deduplicated `ComputationIdentity` nodes,
- lazy inclusion of requested components only (D-017).

#### Acceptance Criteria

- [ ] Plan order is stable across runs
- [ ] Shared dependency appears once (ATR(14) reuse)
- [ ] Unit tests for deduplication and ordering

---

### S003-T019 — AnalysisDataView contract

**Status:** TODO  
**Category:** Architecture  
**Domain:** Market Analysis  
**Wave:** 3  
**Depends On:** S003-T003, S003-T004

#### Scope

Implement read-only data view per spike decision (D-011, D-012):

- column access,
- UTC time index,
- no mutation API,
- no pandas leakage in public types.

#### Acceptance Criteria

- [ ] View is read-only by contract and tests
- [ ] float64 research default documented
- [ ] Unit tests with small in-memory fixture

---

### S003-T020 — Data Module bridge: DatasetRef to AnalysisDataView

**Status:** TODO  
**Category:** Feature  
**Domain:** Application / Market Analysis  
**Wave:** 3  
**Depends On:** S003-T019

#### Scope

Application-layer bridge in `application/market_analysis/` or market_analysis service:

- accept published `DatasetRef` + range,
- call `query_historical`,
- materialize one `AnalysisDataView` per plan (no per-component fetch).

#### Acceptance Criteria

- [ ] Rejects non-published datasets
- [ ] Components never receive repository or paths
- [ ] Unit test with in-memory or tmp storage fixture

---

- [ ] Unit tests for parameter-dependent dependency lists
- [ ] Dependent component can target a named output (e.g. `SessionRange.low`)

---

### S003-T037 — AnalysisResultStore

**Status:** TODO  
**Category:** Architecture  
**Domain:** Market Analysis  
**Wave:** 3  
**Depends On:** S003-T011, S003-T018

#### Scope

Execution-scoped store mapping `ComputationIdentity` → `AnalysisResult` → `OutputId` → array.

Provides lookup, output selection, dependency injection, deduplication integration, and lineage traversal.

Internal representation may be map-of-arrays; contract must not require one physical DataFrame (workspace doc §12).

#### Acceptance Criteria

- [ ] Lookup by resolved computation identity
- [ ] Output selection by `OutputRef`
- [ ] Unit tests for store and deduplicated identity keys

---

### S003-T038 — AnalysisWorkspace (executor-controlled registration)

**Status:** TODO  
**Category:** Architecture  
**Domain:** Market Analysis  
**Wave:** 3  
**Depends On:** S003-T037

#### Scope

Execution-scoped container combining canonical market columns and registered analysis outputs.

Only the executor may add or remove results. Components return outputs; they do not mutate shared state (workspace doc §9).

Expose read-only `AnalysisWorkspaceView` to implementations.

#### Acceptance Criteria

- [ ] Components cannot append columns to workspace directly
- [ ] Workspace scoped to one execution plan
- [ ] Unit tests prove executor-only mutation

---

### S003-T021 — Sequential batch executor

**Status:** TODO  
**Category:** Feature  
**Domain:** Market Analysis  
**Wave:** 3  
**Depends On:** S003-T018, S003-T020, S003-T038

#### Scope

Execute plan sequentially:

- inject dependency results from `AnalysisResultStore`,
- call implementations with read-only market view + workspace view,
- register returned `AnalysisResult` in store and workspace,
- enforce input immutability (D-013, workspace invariant §32).

#### Acceptance Criteria

- [ ] Executor does not mutate shared view
- [ ] Failed node aborts plan with structured error
- [ ] Unit tests with stub components

---

### S003-T022 — Execution cache (exact-match, in-plan)

**Status:** TODO  
**Category:** Feature  
**Domain:** Market Analysis  
**Wave:** 3  
**Depends On:** S003-T021, S003-T037

#### Scope

In-memory cache keyed by `ComputationIdentity` integrated with `AnalysisResultStore` (D-018).

No persistent or cross-plan reuse.

#### Acceptance Criteria

- [ ] Cache hit skips re-execution
- [ ] Cache miss computes and stores
- [ ] Unit tests prove reuse for identical identity

---

### S003-T023 — Warm-up range extension and output validation

**Status:** TODO  
**Category:** Feature  
**Domain:** Market Analysis  
**Wave:** 3  
**Depends On:** S003-T021

#### Scope

Engine extends input range per `HistoryRequirement`, then trims outputs to requested range (D-020).

Executor validates output length, index alignment, schema (D-025).

#### Acceptance Criteria

- [ ] Warm-up bars excluded from returned valid range metadata
- [ ] Invalid adapter output rejected
- [ ] Unit tests for warm-up trimming

---

### S003-T024 — Analysis error hierarchy

**Status:** TODO  
**Category:** Architecture  
**Domain:** Market Analysis  
**Wave:** 3  
**Depends On:** S003-T021

#### Scope

Typed errors: planning, cycle, validation, implementation, cache.

Extend `TradingFrameworkError` hierarchy without god-object exception type.

#### Acceptance Criteria

- [ ] Errors carry enough context for debugging (node identity, component id)
- [ ] Unit tests instantiate and message each category

---

### S003-T025 — True Range Feature component

**Status:** TODO  
**Category:** Feature  
**Domain:** Market Analysis  
**Wave:** 4  
**Depends On:** S003-T014, S003-T020

#### Scope

Semantic component `volatility.true_range` (or equivalent canonical id):

- raw OHLC data dependencies,
- causal,
- NumPy implementation.

#### Acceptance Criteria

- [ ] Registered in registry
- [ ] Contract tests pass
- [ ] Declares history requirement explicitly

---

### S003-T026 — ATR Feature and NumPy adapter

**Status:** TODO  
**Category:** Feature  
**Domain:** Market Analysis  
**Wave:** 4  
**Depends On:** S003-T025

#### Scope

Semantic component `volatility.atr`:

- depends on True Range component (not hidden internal calc),
- parameterized period,
- NumPy `implementation_id` e.g. `numpy.atr`.

#### Acceptance Criteria

- [ ] Component dependency on True Range explicit
- [ ] Adapter contract tests pass
- [ ] Reference tolerance documented

---

### S003-T027 — Optional TA-Lib adapter extra

**Status:** TODO  
**Category:** Feature  
**Domain:** Market Analysis / Infrastructure  
**Wave:** 4  
**Depends On:** S003-T026

#### Scope

Optional `talib.atr` implementation:

- extra dependency group in `pyproject.toml`,
- skipped in CI if unavailable,
- same contract tests as NumPy adapter (D-034).

#### Acceptance Criteria

- [ ] Core install works without TA-Lib
- [ ] Contract tests run when extra installed
- [ ] Documented in README or extras table

---

### S003-T028 — Volatility State + diagnostic output

**Status:** TODO  
**Category:** Feature  
**Domain:** Market Analysis  
**Wave:** 4  
**Depends On:** S003-T026

#### Scope

State component e.g. `volatility.high_volatility`:

- depends on ATR via `ComponentOutputRef`,
- parameterized threshold,
- core output: state series with availability metadata,
- at least one diagnostic output (e.g. distance-to-threshold) in optional output group.

#### Acceptance Criteria

- [ ] Completes D-035 vertical slice chain
- [ ] Diagnostic output declared in schema but optional in planner
- [ ] State kind and causality declared
- [ ] Contract tests pass

---

### S003-T040 — EMA reusable Feature component

**Status:** TODO  
**Category:** Feature  
**Domain:** Market Analysis  
**Wave:** 4  
**Depends On:** S003-T014, S003-T020

#### Scope

Semantic component e.g. `trend.ema`:

- raw close data dependency,
- parameterized period (default 20),
- causal, independently reusable (workspace doc §29 integration test requirement).

#### Acceptance Criteria

- [ ] Registered and independently requestable
- [ ] Contract tests pass
- [ ] Demonstrates shared computation with slice components in one plan

---

### S003-T039 — AnalysisFrameAssembler and alias policy

**Status:** TODO  
**Category:** Feature  
**Domain:** Market Analysis  
**Wave:** 4  
**Depends On:** S003-T038, S003-T028

#### Scope

Implement public contracts:

- `AnalysisFrameRequest`,
- `AnalysisFrameAssembler`,
- `AnalysisFrame` / `ConsumerView`,
- deterministic alias generation,
- explicit alias collision detection (workspace doc §10).

Assemble flat aligned matrix from selected market columns and analysis outputs only when consumer requests it.

#### Acceptance Criteria

- [ ] Flat frame is not the primary domain model
- [ ] Alias collisions raise explicit errors
- [ ] Lineage preserved despite short aliases
- [ ] Unit tests for assembly and collision detection

---

### S003-T029 — Engine facade and run_analysis use case

**Status:** TODO  
**Category:** Feature  
**Domain:** Application  
**Wave:** 4  
**Depends On:** S003-T022, S003-T039

#### Scope

Public facade:

```text
run_analysis(context, requests) -> AnalysisRunResult
```

Returns access to `AnalysisResultStore`, final outputs, and optional `AnalysisFrame` assembly — not a god-object replacing separate modules.

#### Acceptance Criteria

- [ ] Single entry point for MVP workflows
- [ ] Lazy execution of requested roots only
- [ ] Unit test with stub registry

---

### S003-T030 — Adapter contract test suite

**Status:** TODO  
**Category:** Maintenance  
**Domain:** Market Analysis  
**Wave:** 5  
**Depends On:** S003-T026

#### Scope

Shared contract tests (D-033) for all adapters:

- determinism,
- immutability,
- output schema,
- index alignment,
- warm-up metadata,
- lineage presence.

#### Acceptance Criteria

- [ ] True Range and ATR adapters pass shared suite
- [ ] TA-Lib adapter included when extra available

---

### S003-T031 — Integration test: wide AnalysisFrame from DatasetRef

**Status:** TODO  
**Category:** Maintenance  
**Domain:** Market Analysis  
**Wave:** 5  
**Depends On:** S003-T029

#### Scope

`tests/integration/test_market_analysis_vertical_slice.py`:

- import/publish fixture dataset (or use committed bars fixture),
- run slice + EMA + diagnostic output,
- assemble wide `AnalysisFrame` via `AnalysisFrameAssembler`.

Frame must contain at least (workspace doc §29):

```text
OHLCV
True Range
ATR
EMA
Volatility State
one diagnostic output
```

#### Acceptance Criteria

- [ ] Runs in CI without external services
- [ ] Source dataset not mutated
- [ ] Asserts lineage and alias mapping
- [ ] Documents fixture provenance

---

### S003-T041 — Workspace and frame assembly tests

**Status:** TODO  
**Category:** Maintenance  
**Domain:** Market Analysis  
**Wave:** 5  
**Depends On:** S003-T039

#### Scope

Focused tests per workspace doc §31:

- no source-data mutation,
- no alias collision undetected,
- shared-result reuse across requests,
- correct dependency injection by output ref,
- correct final-output and wide-frame selection.

#### Acceptance Criteria

- [ ] Regression tests in `tests/unit/market_analysis/`
- [ ] Tests fail if executor allows component-side column mutation

---

### S003-T032 — Cache dedup and cycle detection tests

**Status:** TODO  
**Category:** Maintenance  
**Domain:** Market Analysis  
**Wave:** 5  
**Depends On:** S003-T022, S003-T017

#### Scope

Focused unit tests:

- duplicate `ATR(14)` requests → one execution,
- cyclic registration → planner error before execution.

#### Acceptance Criteria

- [ ] Tests fail if dedup or cycle detection regresses

---

### S003-T033 — Input immutability and identity tests

**Status:** TODO  
**Category:** Maintenance  
**Domain:** Market Analysis  
**Wave:** 5  
**Depends On:** S003-T021

#### Scope

Verify:

- view unchanged after execution,
- identical requests → identical computation identity,
- different parameters → different identities.

#### Acceptance Criteria

- [ ] Regression tests in `tests/unit/market_analysis/`

---

### S003-T034 — Market Analysis ADRs (ADR-0005 + MA decisions)

**Status:** TODO  
**Category:** Documentation  
**Domain:** Architecture  
**Wave:** 6  
**Depends On:** S003-T004

#### Scope

Materialize architecture decisions as ADRs. Minimum:

- ADR-0005 — Market Analysis Domain and Taxonomy,
- ADR-MA-007 — Analysis Workspace and Derived Data (from workspace doc §33),
- consolidate remaining ADR-MA-001–011 from architecture docs into accepted ADRs under `docs/adr/`.

Update `docs/adr/README.md`.

#### Acceptance Criteria

- [ ] ADR-0005 ACCEPTED
- [ ] Core MA decisions (identity, data view, DAG, cache, warm-up) have ADR coverage
- [ ] Cross-reference `MARKET_ANALYSIS_WITH_DECISIONS.md`

---

### S003-T035 — Update architecture docs and problem registry notes

**Status:** TODO  
**Category:** Documentation  
**Domain:** Architecture  
**Wave:** 6  
**Depends On:** S003-T034

#### Scope

Update PRB-002, PRB-005 with MVP resolution notes.

Align `docs/reference/` and `docs/vision/` if public contracts changed.

#### Acceptance Criteria

- [ ] Problem registry reflects MVP decisions
- [ ] No undocumented public contract drift

---

### S003-T036 — Sprint review and CURRENT_STATUS update

**Status:** TODO  
**Category:** Documentation  
**Domain:** Core  
**Wave:** 6  
**Depends On:** All preceding tasks

#### Scope

Complete Sprint Review and Retrospective in this file.

Update `docs/planning/CURRENT_STATUS.md` and Phase 3 progress in `ROADMAP.md`.

#### Acceptance Criteria

- [ ] Sprint 003 marked COMPLETED
- [ ] Phase 3 MVP criteria assessed against delivered capabilities
- [ ] Carry-forward items explicit

---

## Recommended Implementation Order

```text
Wave 0 — architecture closure and spike (GATE)
  T001, T002, T003, T004

Wave 1 — identity and core contracts
  T005, T006, T007, T008, T009, T010, T011, T012

Wave 2 — registry and dependency planner
  T013, T014, T015, T016, T017, T018

Wave 3 — data view, result store, workspace, executor, cache
  T019, T020, T037, T038, T021, T022, T023, T024

Wave 4 — vertical slice, frame assembly, facade
  T025, T026, T027, T040, T028, T039, T029

Wave 5 — verification
  T030, T031, T041, T032, T033

Wave 6 — ADRs and closure
  T034, T035, T036
```

**Do not start Wave 1 until T004 passes.**

---

## PR Guidance (Sprint 003)

Sprint tasks (T001–T041) track **what** must exist when the sprint is done.

**PR boundaries are chosen by outcome, size and reviewability** — see `.cursor/rules/sprint-git-workflow.mdc`.

### Sprint integration branch

```text
sprint/market-analysis-mvp
```

### Illustrative working branches

These are **outcome guides**, not a mandatory task-to-branch map:

| Branch | Review question |
|--------|-----------------|
| `docs/market-analysis-architecture` | Are architecture decisions and ADRs accepted? |
| `feat/market-analysis-identity` | Do component and implementation identity types exist? |
| `feat/market-analysis-parameters` | Are parameter schemas and `ComponentRequest` stable? |
| `feat/market-analysis-result-contract` | Do `AnalysisResult`, outputs and lineage contracts exist? |
| `feat/market-analysis-registry` | Can components be registered and resolved? |
| `feat/market-analysis-dag` | Can the planner build a DAG and detect cycles? |
| `feat/market-analysis-executor` | Does sequential execution with cache work? |
| `feat/market-analysis-workspace` | Do result store, workspace and frame assembly work? |
| `feat/market-analysis-vertical-slice` | Does True Range → ATR → Volatility State run end-to-end? |

Split further when a PR exceeds ~600–800 meaningful lines.

### PR flow

```text
feat/* or docs/*
    ↓ PR (squash)
sprint/market-analysis-mvp
    ↓ final sprint PR
main
```

### Known deviation

PR `sprint/market-analysis-mvp--identity-core-contracts` (~1 200 lines, T005–T012 bundled) predates this policy.

**Do not merge as-is.** Split into outcome-scoped `feat/market-analysis-*` PRs or close and replace.

Wave 0 branch `sprint/market-analysis-mvp--wave-0-closure-spike` is a historical exception (merged in PR #25).

---

## Sprint Review

_To be completed at sprint end._

### Completed

- ...

### Not Completed

- ...

### Demonstrated Capabilities

- ...

### Deviations From Plan

- ...

### Carry-Forward Items

- ...

---

## Retrospective

_To be completed at sprint end._

### What Worked

- ...

### What Did Not Work

- ...

### Process Improvements

- ...

### Next Recommended Sprint Goal

```text
Phase 4 increment: multitimeframe alignment, additional Features/Structures,
or Research consumption of AnalysisResult — based on Sprint 003 evidence.
```

---

## Definition of Done (Sprint Level)

The sprint is complete when:

```text
[ ] Sprint Goal is achieved
[ ] Four-layer model operational: MarketDataset → ResultStore → Workspace → AnalysisFrame
[ ] Vertical slice True Range → ATR → Volatility State runs from DatasetRef
[ ] Wide AnalysisFrame integration test includes OHLCV, slice, EMA, diagnostic output
[ ] Components return outputs; executor registers them — no shared mutable DataFrame model
[ ] Planner builds deterministic DAG with deduplication and cycle detection
[ ] Execution cache prevents duplicate work within a plan
[ ] AnalysisResult includes identity, lineage, warm-up and availability metadata
[ ] Alias collisions detected; aliases do not replace computation identity
[ ] Input dataset/view is not mutated by execution
[ ] Adapter contract tests pass (NumPy; TA-Lib when extra installed)
[ ] ADR-0005 and ADR-MA-007 (workspace) are ACCEPTED
[ ] CURRENT_STATUS.md is updated
[ ] Sprint Review and Retrospective sections are filled
[ ] No undocumented architectural deviation was introduced
```
