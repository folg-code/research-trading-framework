# Sprint 004 — Multitimeframe Foundation MVP

## Metadata

```text
Sprint: 004
Phase: Phase 4 — Market Analysis Components and Multitimeframe (first increment)
Status: COMPLETED (2026-07-12)
Planned Start: 2026-07-12
Planned End: TBD
Sprint Goal Owner: Project Maintainer
Depends On: SPRINT_003 (COMPLETED, merged to main)
Sprint Branch: sprint/market-analysis-mtf
Architecture Sources:
  - docs/vision/MULTITIMEFRAME_MARKET_MODEL_ARCHITECTURE_UPDATED.md (§6–§9, §19)
  - docs/vision/MARKET_ANALYSIS_WITH_DECISIONS.md (identity, DAG, cache)
  - docs/planning/sprints/SPRINT_004.md — Design Principles (this file, § Anti-Overengineering)
Precedence: MTF vision doc defines semantics; this sprint applies a minimal implementation slice.
Sprint 003 engine ADRs remain binding unless superseded by the single Sprint 004 ADR.
Prerequisite review: docs/planning/retrospectives/ARCHITECTURE_SIMPLIFICATION_REVIEW_S002_S003.md
```

---

## Sprint Goal

```text
Deliver one working batch multitimeframe vertical slice with correct temporal semantics:
explicit resampling, explicit computation timeframe, deduplicated DAG execution,
layered cache identity, LAST_CLOSED_BAR protection, and backward as-of alignment —
without building a general workflow engine or premature calendar/policy subsystems.
```

Success pipeline:

```text
DatasetRef (1m)
    ↓
Polars source frame
    ↓
ResampleNode (1m → 5m, shared, deduplicated)
    ↓
ATR(14) on 5m (existing component path)
    ↓
available_at on HTF result
    ↓
Polars join_asof → 1m evaluation grid
    ↓
AnalysisFrame (1m index + aligned 5m ATR + 1m EMA)
```

Vertical slice:

```text
Source:      published 1m OHLCV (fixture or synthetic)
Computation: ATR(14) on 5m via explicit ResampleNode
Evaluation:  1m grid
Alignment:   LAST_CLOSED_BAR (default)
Also:        EMA(20) on 1m (reuse Sprint 003 components unchanged)
```

---

## Design Principles (Anti-Overengineering)

These principles are **binding** for Sprint 004 implementation and review.

### Keep (non-negotiable semantics)

```text
explicit computation timeframe
explicit resampling as deduplicated DAG node
available_at / observed_at where MTF applies
LAST_CLOSED_BAR default
backward as-of alignment (join_asof semantics)
layered material cache identity
look-ahead regression tests
one full end-to-end vertical slice
request resolution separated from DAG planning
```

### Reduce (avoid in this sprint)

```text
propagating all three timeframe roles into every public object
single mega cache key mixing computation and alignment dimensions
ResamplingPolicy / BoundaryPolicy enums with one implementation
ResampledAnalysisDataView or view-type hierarchy
resampling registered as ordinary Market Analysis Feature/Structure/State
planner magic that auto-selects data source or resampling policy
Trading Calendar subsystem for fixed-duration UTC windows
multiple Wave 0 spikes and formal gates before first working path
task-per-abstraction PR fragmentation
structure tests that freeze internal node class names
multiple related ADRs for one vertical slice
custom read-only wrapper duplicating Polars API
```

### Timeframe roles — single source of truth

| Role | Where it lives | Notes |
|------|----------------|-------|
| `source_timeframe` | `DatasetRef` | Derived, not repeated on `ComponentRequest` |
| `computation_timeframe` | `ComponentRequest` | User-selected per component |
| `evaluation_timeframe` | `AnalysisRunRequest` / `AnalysisContext` | Run-level consumption grid |

Full triple appears only on **resolved** execution artifacts (`ResolvedComponentRequest`, `ExecutionNode`), not duplicated on every public request type.

### Layered identity — stage-appropriate keys

```text
ResampleIdentity
  = dataset identity + source TF + target TF + boundary semantics + aggregation version

ComponentComputationIdentity
  = component + parameters + input identity + computation timeframe

AlignmentIdentity
  = component result identity + evaluation grid identity + alignment policy
```

**Do not** put evaluation timeframe or alignment policy into raw component computation cache keys when they do not affect the computation result.

Example: ATR 5m from 1m source is identical whether later aligned to 1m or 30s evaluation grids.

### Resampling — `ResampleSpec`, not policy enum

MVP uses one explicit implementation:

```python
@dataclass(frozen=True, slots=True)
class ResampleSpec:
    target_timeframe: Timeframe
    timezone: Literal["UTC"] = "UTC"
    label: Literal["left"] = "left"
    closed: Literal["left"] = "left"
    partial_bucket_policy: ...  # fixed in spike; document in ADR
```

OHLCV rules (fixed, not pluggable enum):

```text
open = first, high = max, low = min, close = last, volume = sum
```

`AlignmentPolicy` is kept (enum) because `LAST_CLOSED_BAR` vs future `INTRABAR` is a real contrast.

`ResamplingPolicy` deferred until a second real resampling semantics exists.

### DAG node types — not all are registry components

```text
SourceNode
ResampleNode      ← explicit, deduplicated; NOT in ComponentRegistry
ComponentNode     ← from ComponentRegistry (ATR, EMA, …)
AlignmentNode     ← optional explicit stage; may be executor-internal for MVP
```

Resampling is input transformation, not market semantics.

### Request resolution before planning

```text
User requests
    ↓
Request Resolution  ← chooses DatasetRef input, ResampleSpec, resolved inputs
    ↓
Resolved Input Plan
    ↓
DAG Planner         ← dedupe, cycle detect, topological order only
    ↓
Execution Plan
```

Planner **must not** silently decide: published 5m dataset vs resampled 1m, calendar choice, or boundary anchor.

For MVP, resolution is explicit and narrow (always resample stated source to stated target with fixed UTC semantics).

### Polars scope

Polars is used for **resampling and alignment** (`group_by_dynamic`, `join_asof`).

Existing Sprint 003 components continue on the established adapter path (`AnalysisDataView` → NumPy).

Conversion happens at **one boundary** per stage — no Polars wrapper hierarchy, no duplicate mini-API.

### Overengineering heuristic (from S002/S003 review)

```text
If a simple Polars operation requires several new public contracts,
first check whether the problem was over-abstracted upstream (S003 AnalysisDataView, MarketBar list, etc.).
Do not add new wrapper types without passing §5 Architecture Simplification Checklist in the review doc.
```

---

Fixed UTC duration windows are part of `ResampleSpec` / resampler implementation.

Full `TradingCalendar` (CME sessions, holidays, DST) → Sprint 005+ when first real use case requires it.

PRB-007: note deferral; do not block MTF MVP on calendar subsystem.

### Tests — behavior over structure

Required behavioral coverage:

1. Resampling OHLCV correctness
2. No look-ahead on evaluation grid
3. Shared resample executed once (cache / plan dedupe)
4. Material input change changes appropriate identity layer
5. End-to-end MTF frame correctness
6. Partial bucket edge behaviour
7. Warm-up / missing HTF history behaviour

Avoid tests that assert internal class names, registry entries for ResampleNode, or adapter type hierarchy.

---

## Phase Alignment

First increment of **Phase 4** from `ROADMAP.md`.

**In Sprint 004:**

```text
timeframe role semantics (derived vs explicit fields)
ResampleSpec + fixed UTC boundaries
ResampleNode in execution DAG
layered cache identity
available_at on HTF outputs
LAST_CLOSED_BAR + join_asof alignment
look-ahead regressions
one ADR for batch MTF with Polars resample/align path
```

**Deferred (Sprint 005+):**

```text
TradingCalendar / exchange sessions / PRB-007 full resolution
ResamplingPolicy enum
Market Model / Signal Model / MarketFieldReference
intrabar contract
persistent derived datasets in user_data
component catalog expansion (Pivot, structures)
auto-resolution of published HTF dataset vs on-the-fly resample
optional TA-Lib (S003-T027 carry-forward)
```

---

## Scope

### In scope

- one MTF implementation spike producing working prototype + decision note,
- `computation_timeframe` on `ComponentRequest`,
- `evaluation_timeframe` on run request / context,
- resolved request model for execution,
- layered identities,
- `ResampleSpec` and Polars resampling,
- `ResampleNode` planner/executor integration with deduplication,
- request resolution layer (explicit, narrow MVP),
- `available_at` on analytical outputs,
- `AlignmentPolicy` + Polars `join_asof`,
- `AnalysisFrame` MTF assembly,
- behavior-focused test suite + end-to-end vertical slice,
- single ADR + reference doc updates.

### Out of scope

- everything listed under Deferred above,
- `ComponentRegistry` entry for resampling,
- `ResamplingPolicy`, `BoundaryPolicy` enums,
- `ResampledAnalysisDataView` or view subclasses,
- exchange-aware calendar,
- planner auto-magic for data acquisition policy,
- more than ~5 outcome-scoped PRs for core delivery.

---

## Dependencies

```text
Sprint 003 — engine, registry, planner, executor, cache, workspace, NumPy adapter (main)
Sprint 002 — DatasetRef, MarketBar temporal fields (main)
```

New runtime dependency (expected after spike):

- `polars` — resampling and alignment only; justified in T001 spike note.

No new dependency for Trading Calendar in this sprint.

---

## Risks

| Risk | Mitigation |
|------|------------|
| Look-ahead bias | `available_at` + join_asof + dedicated regression tests (T012) |
| Overengineering relapse | Binding Design Principles; PR review against § Anti-Overengineering |
| Polars vs NumPy boundary creep | Polars only in resample/align modules; single conversion to `AnalysisDataView` |
| Identity fragmentation | Layered keys; alignment separate from computation cache |
| Hidden planner magic | Explicit resolution layer (T007); planner tests check dedupe only |
| Scope creep | 15 tasks, 5 PRs; no calendar subsystem |

---

## Task Summary

| ID | Task | Status | Depends On |
|----|------|--------|------------|
| S004-T001 | MTF implementation spike and architecture decision note | DONE | — |
| S004-T002 | `computation_timeframe` on request; `evaluation_timeframe` on run context | DONE | S004-T001 |
| S004-T003 | Resolved request / execution input model | DONE | S004-T002 |
| S004-T004 | Layered identities (Resample, ComponentComputation, Alignment) | DONE | S004-T003 |
| S004-T005 | `ResampleSpec` and fixed UTC boundary semantics | DONE | S004-T001 |
| S004-T006 | Polars OHLCV resampling + `ResampleNode` | DONE | S004-T004, S004-T005 |
| S004-T007 | Request resolution layer (explicit input plan) | DONE | S004-T003, S004-T005 |
| S004-T008 | Planner and executor: `ResampleNode` deduplication and integration | DONE | S004-T006, S004-T007 |
| S004-T009 | `available_at` derivation on component outputs | DONE | S004-T008 |
| S004-T010 | `AlignmentPolicy` + Polars `join_asof` alignment | DONE | S004-T009 |
| S004-T011 | `AnalysisFrame` MTF assembly on evaluation grid | DONE | S004-T010 |
| S004-T012 | Behavior-focused MTF test suite | DONE | S004-T010 |
| S004-T013 | End-to-end vertical slice and `run_analysis` MTF path | DONE | S004-T011, S004-T012 |
| S004-T014 | ADR — Batch Multitimeframe Computation with Polars | DONE | S004-T001 |
| S004-T015 | Module docs, MODULE_MAP, PRB-007 deferral note, sprint closure | DONE | S004-T013, S004-T014 |
| S004-T016 | Optional TA-Lib adapter (S003-T027 carry-forward) | DEFERRED | — |

**Total:** 16 tasks (15 planned + 1 deferred)

---

## Tasks

### S004-T001 — MTF implementation spike and architecture decision note

**Status:** DONE (2026-07-12)  
**Category:** Spike  
**Domain:** Market Analysis  
**Wave:** 0

#### Scope

Single spike task (replaces separate architecture closure, calendar spike, resampling spike, formal DoR gate).

Prototype outside production API (`tests/spike/` or `user_data/development/`):

- Polars `group_by_dynamic` for 1m → 5m OHLCV on fixture data,
- Polars `join_asof` for HTF → LTF alignment with `available_at` semantics,
- timestamp / partial bucket behaviour,
- conversion boundary to existing `AnalysisDataView` for ATR path (document cost; see TD-011, TD-015),
- **Architecture Simplification Checklist** (review doc §5): confirm Polars-first direction for new batch paths without rewriting S002/S003 on main.

Decision note must record:

- fixed UTC boundary semantics (defer exchange calendar),
- layered identity approach,
- `ResampleNode` vs registry component,
- resolution vs planner split,
- Polars dependency justification,
- partial bucket policy.

#### Acceptance Criteria

- [x] Prototype runs locally without credentials
- [x] Decision note artifact: `docs/planning/sprints/S004_MTF_SPIKE_AND_DECISIONS.md`
- [x] Sprint branch `sprint/market-analysis-mtf` created from `main`
- [x] Wave 1 unblocked

Artifacts: `tests/spike/run_mtf_polars_spike.py`

**Wave 1 implementation is UNBLOCKED.**

---

### S004-T002 — Timeframe fields on public request types

**Status:** DONE  
**Category:** Architecture  
**Domain:** Market Analysis  
**Wave:** 1  
**Depends On:** S004-T001

#### Scope

- Add `computation_timeframe` to `ComponentRequest` (optional; default = dataset source TF for backward compatibility).
- Add `evaluation_timeframe` to run-level request / `AnalysisContext`.
- **Do not** add `source_timeframe` or `evaluation_timeframe` to `ComponentRequest`.
- Relax `AnalysisContext` validation: source TF comes from `DatasetRef`; evaluation TF may differ.

#### Acceptance Criteria

- [ ] Single-TF Sprint 003 call paths unchanged
- [ ] Invalid TF combinations fail with `ValidationError`
- [ ] Unit tests for defaults and backward compatibility

---

### S004-T003 — Resolved request / execution input model

**Status:** DONE  
**Category:** Architecture  
**Domain:** Market Analysis  
**Wave:** 1  
**Depends On:** S004-T002

#### Scope

Introduce resolved artifacts used by planner/executor only:

- `ResolvedComponentRequest` or equivalent with full material timeframe context,
- explicit resolved input reference (source dataset view or resample output identity).

Public API stays minimal; resolved model is internal to engine.

#### Acceptance Criteria

- [ ] Triple timeframe appears only on resolved/execution types
- [ ] No duplication of `source_timeframe` on public `ComponentRequest`
- [ ] Unit tests for resolution from run context + component requests

---

### S004-T004 — Layered computation identities

**Status:** DONE  
**Category:** Architecture  
**Domain:** Market Analysis  
**Wave:** 1  
**Depends On:** S004-T003

#### Scope

Implement three identity types with separate `canonical_key()`:

- `ResampleIdentity`
- `ComponentComputationIdentity` (extend existing `ComputationIdentity` or split cleanly)
- `AlignmentIdentity`

Update execution cache to key by appropriate layer per node type.

#### Acceptance Criteria

- [ ] Same ATR 5m computation key regardless of evaluation TF
- [ ] Different alignment policy → different alignment cache key only
- [ ] Sprint 003 single-TF identity tests still pass

---

### S004-T005 — ResampleSpec and fixed UTC boundary semantics

**Status:** DONE  
**Category:** Architecture  
**Domain:** Market Analysis  
**Wave:** 1  
**Depends On:** S004-T001

#### Scope

- `ResampleSpec` frozen dataclass (see Design Principles).
- Document OHLCV aggregation rules inline or in module docstring.
- Explicit statement: exchange `TradingCalendar` deferred; UTC fixed-duration only.

#### Acceptance Criteria

- [ ] No `ResamplingPolicy` or `BoundaryPolicy` public enums
- [ ] Canonical serialization for `ResampleIdentity`
- [ ] Unit tests for spec validation

---

### S004-T006 — Polars OHLCV resampling and ResampleNode

**Status:** DONE  
**Category:** Implementation  
**Domain:** Market Analysis  
**Wave:** 2  
**Depends On:** S004-T004, S004-T005

#### Scope

- Polars resampler: 1m → higher TF per `ResampleSpec`.
- `ResampleNode` execution type — **not** registered in `ComponentRegistry`.
- Output: material usable at component boundary (convert to `AnalysisDataView` once).
- Deterministic on fixtures.

#### Acceptance Criteria

- [x] OHLCV aggregation matches spike rules
- [x] Source frame immutability verified by test
- [x] Resample correctness tests (behavior, not class names)

---

### S004-T007 — Request resolution layer

**Status:** DONE  
**Category:** Implementation  
**Domain:** Market Analysis  
**Wave:** 2  
**Depends On:** S004-T003, S004-T005

#### Scope

Resolution step before planner:

```text
DatasetRef + ComponentRequests + ResampleSpec (when needed)
    → Resolved Input Plan
```

MVP resolution is explicit and narrow:

- when `computation_timeframe` > source TF → resolved plan includes `ResampleSpec` for that target,
- no auto-selection of alternate published datasets.

#### Acceptance Criteria

- [x] Planner receives resolved plan; does not infer resampling policy
- [x] Unit tests for resolution outcomes
- [x] Documented extension point for future “use published 5m dataset” resolution

---

### S004-T008 — Planner and executor ResampleNode integration

**Status:** DONE  
**Category:** Implementation  
**Domain:** Market Analysis  
**Wave:** 2  
**Depends On:** S004-T006, S004-T007

#### Scope

Single deliverable merging former “planner expansion”, “executor integration”, and “DAG dedupe”:

- planner inserts `ResampleNode` from resolved plan,
- two components on same target TF share one resample node,
- executor runs resample before dependents,
- cache hits on `ResampleIdentity`.

#### Acceptance Criteria

- [x] Plan deduplicates shared resample (behavior test: one execution)
- [x] Topological order preserved
- [x] No `ResampleNode` in `ComponentRegistry`

---

### S004-T009 — available_at derivation on component outputs

**Status:** DONE  
**Category:** Implementation  
**Domain:** Market Analysis  
**Wave:** 3  
**Depends On:** S004-T008

#### Scope

HTF component outputs carry per-index or per-bar `available_at` aligned with `LAST_CLOSED_BAR` semantics (bar close time on computation TF).

Single-TF outputs: preserve Sprint 003 behaviour.

#### Acceptance Criteria

- [x] HTF ATR series includes `available_at` metadata
- [x] Unit tests with hand-crafted timestamps (e.g. 10:37 vs 1h bar)

---

### S004-T010 — AlignmentPolicy and Polars join_asof

**Status:** DONE  
**Category:** Implementation  
**Domain:** Market Analysis  
**Wave:** 3  
**Depends On:** S004-T009

#### Scope

- `AlignmentPolicy` enum: MVP implements `LAST_CLOSED_BAR` only; reserve `INTRABAR` for future.
- Polars backward `join_asof` on evaluation grid using `available_at`.
- Alignment cached/keyed via `AlignmentIdentity`.

#### Acceptance Criteria

- [x] No future HTF value on earlier LTF timestamp (behavior test)
- [x] No unsafe forward-fill
- [x] Warm-up / missing history handled explicitly

---

### S004-T011 — AnalysisFrame MTF assembly

**Status:** DONE  
**Category:** Implementation  
**Domain:** Market Analysis  
**Wave:** 3  
**Depends On:** S004-T010

#### Scope

Extend `AnalysisFrameAssembler` to combine:

- native 1m columns (EMA),
- aligned HTF columns (ATR 5m on 1m index).

Regression: Sprint 003 single-TF frame assembly unchanged.

#### Acceptance Criteria

- [x] Frame index = evaluation timeframe
- [x] Mixed-TF columns correctly aligned
- [x] Alias policy unchanged for single-TF case

---

### S004-T012 — Behavior-focused MTF test suite

**Status:** DONE (2026-07-12)  
**Category:** Testing  
**Domain:** Market Analysis  
**Wave:** 4  
**Depends On:** S004-T010

#### Scope

One test module (or focused package) covering the seven required behaviors from Design Principles.

**Do not** add separate test tasks per internal subsystem.

#### Acceptance Criteria

- [x] All seven behavioral areas covered
- [x] Tests assert outputs and timestamps, not node class names
- [x] CI green with full suite

---

### S004-T013 — End-to-end vertical slice and run_analysis MTF path

**Status:** DONE (2026-07-12)  
**Category:** Integration  
**Domain:** Application / Market Analysis  
**Wave:** 4  
**Depends On:** S004-T011, S004-T012

#### Scope

- Extend `run_analysis` for MTF run request.
- Integration test: 1m dataset → 5m ATR aligned to 1m + 1m EMA in one frame.

#### Acceptance Criteria

- [x] Runs in CI without external APIs
- [x] Coexists with `test_market_analysis_vertical_slice.py`
- [x] Single-TF path unchanged

---

### S004-T014 — ADR — Batch Multitimeframe Computation with Polars

**Status:** DONE (2026-07-12)  
**Category:** Architecture  
**Domain:** Documentation  
**Wave:** 5  
**Depends On:** S004-T001

#### Scope

**One ADR** (not four). Suggested id: `ADR-MA-012`.

Sections:

- timeframe roles and derived vs explicit fields,
- resolved request model,
- `ResampleSpec` and OHLCV rules,
- `ResampleNode` vs registry components,
- temporal availability and `LAST_CLOSED_BAR`,
- layered identity boundaries,
- Polars scope (resample/align only),
- Trading Calendar deferral,
- partial bucket policy.

Accept ADR before sprint closure.

#### Acceptance Criteria

- [x] Indexed in `docs/adr/README.md`
- [x] Supersedes or clarifies MTF-related planning assumptions where needed
- [x] No separate ADRs for calendar MVP in this sprint

---

### S004-T015 — Documentation and sprint closure

**Status:** DONE (2026-07-12)  
**Category:** Documentation  
**Domain:** Core  
**Wave:** 5  
**Depends On:** S004-T013, S004-T014

#### Scope

- Update `docs/reference/modules/MARKET_ANALYSIS_MODULE.md`, `MODULE_MAP.md`.
- PRB-007: document deferral of exchange calendar; fixed UTC path for S004.
- Sprint review section in this file; `CURRENT_STATUS.md`.

#### Acceptance Criteria

- [x] Reference docs match public API
- [x] Sprint marked COMPLETED with date and quality command results

---

### S004-T016 — Optional TA-Lib adapter (carry-forward)

**Status:** DEFERRED  
**Notes:** S003-T027; out of Sprint 004 scope.

---

## Recommended Implementation Order

```text
Wave 0
  T001

Wave 1 — request model, identity, ResampleSpec
  T002 → T003 → T004
  T005 (parallel after T001)

Wave 2 — resampling path
  T006, T007 → T008

Wave 3 — alignment and frame
  T009 → T010 → T011

Wave 4 — verification
  T012, T013

Wave 5 — ADR and closure
  T014 → T015
```

---

## PR Guidance (Sprint 004)

Target **4–5 outcome-scoped PRs** (~100–400 lines each; split above ~600–800).

PRs represent **working outcomes**, not single abstractions.

### Sprint integration branch

```text
sprint/market-analysis-mtf
```

### Recommended PR sequence

| PR | Outcome | Tasks (typical) |
|----|---------|-----------------|
| 1 | MTF request model and layered identity | T002–T005 |
| 2 | Polars resampling and ResampleNode DAG path | T006–T008 |
| 3 | Alignment, available_at, frame assembly | T009–T011 |
| 4 | Vertical slice and behavior tests | T012–T013 |
| 5 | ADR and documentation | T014–T015 |

Wave 0 spike (T001) may land as first PR to sprint branch or as part of PR 1 if spike artifacts are included.

### Example task branches

```text
sprint/market-analysis-mtf/mtf-spike-and-decisions
sprint/market-analysis-mtf/mtf-request-and-identity
sprint/market-analysis-mtf/polars-resample-dag
sprint/market-analysis-mtf/alignment-and-frame
sprint/market-analysis-mtf/mtf-vertical-slice
```

### PR flow

```text
sprint/market-analysis-mtf/<task-slug>
    ↓ PR (squash)
sprint/market-analysis-mtf
    ↓ final sprint PR
main
```

Review checklist: verify PR does not violate **Design Principles (Anti-Overengineering)**.

---

## Definition of Done (Sprint Level)

- [x] T001–T015 DONE (T016 remains deferred unless explicitly pulled in)
- [x] `uv run ruff check .` passes
- [x] `uv run ruff format --check .` passes
- [x] `uv run mypy` passes
- [x] `uv run pytest` passes
- [x] Seven behavioral test areas (T012) green
- [x] End-to-end MTF integration (T013) green
- [x] ADR-MA-012 accepted
- [x] `CURRENT_STATUS.md` updated
- [ ] Sprint PR to `main` opened; agent stops before merge

---

## Sprint Review

Completed 2026-07-12.

### Completed

- Lean MTF foundation: timeframe roles, `RequestResolver`, layered identities, `ResampleSpec`.
- Polars resample path: `ResampleNode` in execution DAG with planner deduplication and `ResampleCache`.
- Temporal safety: `available_at` on HTF outputs, `LAST_CLOSED_BAR` alignment via Polars `join_asof`.
- MTF frame assembly on evaluation grid; single-TF path backward compatible.
- Behavior regression suite (seven areas) and end-to-end MTF vertical slice through `run_analysis`.
- ADR-MA-012 accepted; reference docs and MODULE_MAP updated; PRB-007 deferral documented.

### Not Completed

- S004-T016 optional TA-Lib adapter (deferred from Sprint 003).
- Exchange/session Trading Calendar (PRB-007 — deferred to Sprint 005+).
- Published HTF dataset vs on-the-fly resample auto-resolution.
- `ResamplingPolicy` / `BoundaryPolicy` enums.

### Demonstrated Capabilities

- Vertical slice: 1m dataset → 5m ATR aligned to 1m + 1m EMA in one `AnalysisFrame`.
- Shared 1m→5m resample executes once when multiple components share target timeframe.
- Look-ahead regression at hand-crafted timestamps (10:37 evaluation grid case).
- Partial bucket edge behaviour on non-aligned range starts.
- 240 automated tests on sprint integration branch at closure.

### Deviations From Plan

- Task branches used flat `feat/*` names when Git could not namespace under sprint branch slug.
- Scope reduced from original 33-task plan per overengineering review (calendar MVP, policy enums, registry resample rejected).

### Carry-Forward Items

- Merge `sprint/market-analysis-mtf` to `main`.
- TradingCalendar when CME/session use case appears (PRB-007).
- Structure components, MarketFieldReference, persistent derived datasets (Sprint 005 preview).
- Columnar query/resample boundary (TD-011, TD-015).
- Optional TA-Lib adapter (S004-T016).

---

## Retrospective

### What Worked

- Lean MVP scope held: one ADR, five outcome-scoped PRs, Polars at boundary only.
- Behavior-focused tests caught look-ahead and partial-bucket semantics early.
- Layered identity kept resample, computation and alignment caches independent.
- Reusing Sprint 003 NumPy components on resampled views avoided adapter proliferation.

### What Did Not Work

- Git branch namespace collision required flat feature branch names.
- Documentation status in MODULE_MAP lagged until Wave 5 closure.

### Process Improvements

- Update reference docs in the same PR as sprint closure (Wave 5).
- Keep MTF tests asserting outputs/timestamps, not internal node type names.
- Run full quality suite before opening sprint integration PR to `main`.

### Next Recommended Sprint Goal

```text
Sprint 005 — TradingCalendar when session use case appears; structure catalog;
published HTF dataset resolution; optional columnar boundary improvements (TD-011/TD-015).
See Sprint 005 Preview below.
```

---

## Sprint 005 Preview (not committed)

```text
TradingCalendar when CME/session use case appears
Structure components (Pivot, swing labels)
Resolution: published HTF dataset vs on-the-fly resample
ResamplingPolicy when second semantics exists
MarketFieldReference
persistent derived datasets
```

Ordering depends on Sprint 004 retrospective.

---

## Revision History

| Date | Change |
|------|--------|
| 2026-07-12 | Initial plan (33 tasks, calendar MVP, policy enums, registry resample) |
| 2026-07-12 | **Reduced scope** per overengineering review: 15 tasks, layered identity, ResampleNode, Polars resample/align only, calendar deferred, one ADR, 5 PRs |
| 2026-07-12 | Sprint closure: ADR-MA-012, reference docs, Wave 5 complete |
