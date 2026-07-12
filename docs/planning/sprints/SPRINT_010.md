# Sprint 010 — Signal Research Analytics MVP

## Metadata

```text
Sprint: 010
Phase: Phase 5 — Signal Research MVP (analytics increment — Phase 5 closure)
Status: COMPLETE (2026-07-12, on sprint branch — pending merge to main)
Planned Start: TBD
Planned End: TBD
Sprint Goal Owner: Project Maintainer
Depends On: SPRINT_009 (required, merged to main)
Sprint Branch: sprint/signal-research-analytics
Task branch convention: sprint/signal-research-analytics--<task-slug>
Direction: docs/planning/sprints/PHASE_4_5_SPRINT_DIRECTION.md
Wave 0 decisions: docs/planning/sprints/S010_WAVE0_DECISIONS.md
Architecture Sources:
  - docs/vision/WORKFLOWS_AI_ADR_UPDATED.md (§3.14 Signal Research Analytics)
  - docs/adr/ADR-0011-signal-research-outcomes-and-persistence.md
  - docs/adr/ADR-0012-combined-research-scopes-and-context-alignment.md
  - docs/planning/sprints/S008_WAVE0_DECISIONS.md (outcome semantics)
  - docs/planning/sprints/S009_WAVE0_DECISIONS.md (context facts, scope)
Prerequisite: Sprint 007 skipped — CmeEsRthSessionResolver sufficient for RTH membership MVP
```

---

## 1. Sprint Goal

Sprint 010 **closes Phase 5 — Signal Research MVP**.

Sprints 008–009:

```text
compute → materialize → persist
```

Sprint 010:

```text
read → join → filter → group → aggregate → interpret
```

Main flow:

```text
SignalResearchRunEnvelope
        ↓
scope-aware analysis frame
        ↓
filters and grouping dimensions
        ↓
aggregate metrics
        ↓
conditional comparison
        ↓
optional HTML report
```

**Hard boundary:** analytics must not re-run:

```text
evaluate_models
occurrence / observation materialization
context alignment
outcome calculator
```

Immutable persisted Signal Research runs remain the source of truth.

---

## 2. MVP Scope

### Metrics

```text
sample size (total / complete / incomplete / completion_rate)
mean forward return
median forward return
hit rate
mean / median MFE
mean / median MAE
```

### Filters

Default:

```text
outcome_status == COMPLETE   — for mean / median / hit rate aggregates
```

Incomplete rows:

```text
included in sample diagnostics
excluded from mean / median / hit rate
never coerced to zero
```

### Grouping dimensions (MVP)

```text
HORIZON
RTH_MEMBERSHIP
TIME_OF_DAY
CALENDAR_MONTH          — optional; first to cut if scope pressure
CONTEXT_MET             — grouped summaries only
```

Not a dynamic dimension framework — fixed enum only.

### Conditional analytics

For `MARKET_AND_SIGNAL`:

```text
context_met_at_available_at == true  vs  false
```

False rows must not be dropped.

### Scopes

```text
SIGNAL_MODEL_ONLY
MARKET_MODEL_ONLY
MARKET_AND_SIGNAL
```

v1 and v2 envelope read compatibility required.

### Persistence

Analytics results are **ephemeral** in MVP. No new persisted analytics schema.

### Report (optional)

Local HTML (Plotly): forward_return / MFE / MAE distributions and conditional split.
Report is presentation-only — no joins or aggregates inside the report layer.

---

## 3. Out of Scope

```text
DuckDB / SQL
multi-run ranking
cross-run experiment comparison
FastAPI / React / production dashboard
recompute
Monte Carlo / parameter grids / clustering
persistent analytics datasets
physical migration v1 → v2
statistical significance (p-values, CIs) in MVP
```

---

## 4. Domain Boundary

```text
Sprint 008–009  → compute, materialize, persist
Sprint 010      → read, join, filter, group, aggregate
Inspection      → single-fact chart (S008/S009 spikes)
Analytics       → population metrics
Reporting       → optional HTML from AnalyzeSignalResearchResult
```

Analytics imports:

```text
SignalResearchDatasetRepository.read
research/analytics/*
application/signal_research/analyze_signal_research.py
```

Must **not** import `evaluate_models`, materializers, context alignment or outcome calculator
(except test fixtures that *produce* runs).

### Reuse

```text
SignalResearchDatasetRepository
ResearchScope / manifest.effective_scope()
CmeEsRthSessionResolver          — RTH membership classification
run_inspect_combined_research.py — single-fact only; not population analytics
Polars                           — aggregation engine
```

---

## 5. Primary Analytics Grain

One **ForwardOutcome row**:

```text
entity_id × horizon_bars
```

Scope mapping (before normalization):

| Scope | entity_id source |
|-------|------------------|
| `SIGNAL_MODEL_ONLY` | `occurrence_id` |
| `MARKET_MODEL_ONLY` | `observation_id` |
| `MARKET_AND_SIGNAL` | `occurrence_id` |

Normalized analysis frame uses generic columns:

```text
entity_id
entity_kind    — SIGNAL_OCCURRENCE | MARKET_MODEL_OBSERVATION
```

Do not mix occurrence and observation semantics without `entity_kind`.

---

## 6. Scope-Aware Analysis Frame

`build_analysis_frame(envelope)` unifies v1/v2 runs to one schema.

Proposed columns:

```text
run_id
research_scope
entity_id
entity_kind
horizon_bars
outcome_status
forward_return
mfe
mae
detected_at
available_at
reference_price
instrument
context_met_at_available_at
```

`context_met_at_available_at`:

```text
SIGNAL_MODEL_ONLY / MARKET_MODEL_ONLY  → null
MARKET_AND_SIGNAL                      → true | false
```

Frame builder responsibilities only:

```text
load (via repository)
scope-aware joins
column normalization
schema validation
```

No metric computation in frame builder.

---

## 7. Filter Semantics

Default aggregate filter: **COMPLETE only**.

Every summary retains:

```text
sample_size_total
sample_size_complete
sample_size_incomplete
completion_rate = sample_size_complete / sample_size_total
minimum_required          — from min_sample_size request
metrics_eligible          — false when complete count < min_sample_size
```

When `metrics_eligible == false`: aggregate columns may be **null**; row remains in output.

---

## 8. Hit Rate

```text
hit           = forward_return > 0
flat          = forward_return == 0   — not a hit
negative      = forward_return < 0

hit_rate      = positive_count / sample_size_complete
```

Returns are direction-normalized per ADR-0011.

---

## 9. Timestamp Basis

Explicit enum — not hardcoded forever:

```python
class AnalyticsTimestampBasis(StrEnum):
    AVAILABLE_AT = "available_at"
    DETECTED_AT = "detected_at"
```

MVP default: **`AVAILABLE_AT`** (legal information availability; aligns with Sprint 009).

`AnalyticsResultMetadata` records the chosen basis.

---

## 10. RTH Membership Grouping

Dimension name: **`RTH_MEMBERSHIP`** (not generic "session").

Values:

```text
RTH
OUTSIDE_RTH
```

This is **not** session instance, session date or trading-day identity.

Classifier: `CmeEsRthSessionResolver` on the selected timestamp basis.

---

## 11. Time-of-Day Grouping

Wave 0 locks:

```text
timestamp basis:     available_at (default)
timezone:            exchange/session local (CME ES)
bucket size:         60 minutes
boundary:            left-closed, right-open  [09:00, 10:00)
```

UTC remains canonical storage; buckets are analytical derivatives in market-local time.

---

## 12. Calendar Period Grouping

MVP supports:

```text
CALENDAR_DATE
CALENDAR_MONTH
```

If scope pressure: keep **`CALENDAR_MONTH` only**. Non-critical for core correctness.

---

## 13. Output Schemas

### RunSummary

Grain: `run_id × horizon_bars`

```text
run_id
research_scope
horizon_bars
sample_size_total
sample_size_complete
sample_size_incomplete
completion_rate
minimum_required
metrics_eligible
forward_return_mean
forward_return_median
hit_rate
mfe_mean
mfe_median
mae_mean
mae_median
```

### GroupedSummary

```text
run_id
research_scope
horizon_bars
group_dimension
group_value
sample_size_total
sample_size_complete
sample_size_incomplete
metrics_eligible
forward_return_mean
forward_return_median
hit_rate
mfe_mean
mfe_median
mae_mean
mae_median
```

Allowed `group_dimension` values: see §2.

### ConditionalComparison

For `MARKET_AND_SIGNAL` only:

```text
run_id
horizon_bars
context_true_sample_size
context_false_sample_size
forward_return_mean_true / _false / _delta
hit_rate_true / _false / _delta
mfe_mean_true / _false / _delta
mae_mean_true / _false / _delta
```

Delta convention: **`true - false`**.

No p-values, confidence intervals or significance labels in MVP.

All outputs: validated `pl.DataFrame` schemas (`schemas.py`).

---

## 14. Application API

Single-run MVP only:

```python
@dataclass(frozen=True, slots=True)
class AnalyzeSignalResearchRequest:
    run_ref: RunDatasetRef
    horizons: tuple[int, ...] | None
    outcome_filter: OutcomeAnalyticsFilter
    group_by: tuple[GroupDimension, ...]
    conditional_context: bool
    timestamp_basis: AnalyticsTimestampBasis
    min_sample_size: int

@dataclass(frozen=True, slots=True)
class AnalyzeSignalResearchResult:
    source_run_id: str
    run_summaries: pl.DataFrame
    grouped_summaries: pl.DataFrame | None
    conditional_comparison: pl.DataFrame | None
    metadata: AnalyticsResultMetadata
```

Entry point: `analyze_signal_research_run(...)`.

Layering:

```text
build_analysis_frame()
        ↓
summarize_analysis_frame()    # RunSummary + optional grouping + conditional
        ↓
analyze_signal_research_run() # loads repository, returns result
```

Do **not** publish `run_ref | tuple[RunDatasetRef, ...]` in MVP — implies multi-run.

Optional reporting:

```python
render_signal_research_report(
    result: AnalyzeSignalResearchResult,
    output_path: Path,
) -> Path
```

Plotly is optional reporting dependency — not core analytics.

---

## 15. Package Layout

```text
src/trading_framework/research/analytics/
├── __init__.py
├── filters.py
├── dimensions.py
├── frame_builder.py
├── aggregates.py
├── conditional.py
├── schemas.py
└── reports.py              # optional presentation adapter

src/trading_framework/application/signal_research/
└── analyze_signal_research.py
```

---

## 16. Inspection vs Analytics vs Report

| Tool | Responsibility |
|------|----------------|
| `run_inspect_signal_research.py` | one `SignalOccurrence`, forward path chart |
| `run_inspect_combined_research.py` | one scope-aware fact, MFE/MAE lines |
| `run_signal_research_analytics_spike.py` | population, groups, conditional split |
| `render_signal_research_report` / HTML spike | distributions from finished result |

Report receives `AnalyzeSignalResearchResult` only — no Parquet, joins or recomputation.

---

## 17. Mandatory Core Scope

```text
read-only boundary (no recompute)
scope-aware analysis frame (entity_id + entity_kind)
RunSummary with sample diagnostics + metrics_eligible
RTH_MEMBERSHIP + TIME_OF_DAY grouping
conditional context_met comparison
single-run application API
integration tests (three scopes)
Wave 0 spike + S010_WAVE0_DECISIONS.md + ADR-0013
v1 and v2 envelope compatibility
```

---

## 18. Deferred / Scope Reduction

| Item | Status |
|------|--------|
| Multi-run request / ranking | Deferred |
| DuckDB / SQL | Deferred |
| Statistical testing | Deferred |
| Persistent analytics envelope | Deferred |
| HTML report | Optional — cut first under pressure |

Reduction priority:

```text
1. HTML report
2. calendar period grouping
3. median metrics
4. extra time-of-day bucket variants
```

Never cut:

```text
read-only boundary
COMPLETE filter semantics
scope-aware frame
RunSummary
context conditional split
schema validation
v1/v2 compatibility
metrics_eligible / visible small groups
```

---

## 19. Risks

| Risk | Mitigation |
|------|------------|
| Over-general GroupDimension framework | Fixed enum only in MVP |
| Implicit timezone conversion | Record basis, timezone, bucket in metadata |
| occurrence vs observation confusion | `entity_id` + `entity_kind` |
| Hidden small-group drop | `metrics_eligible=false`, null metrics, row kept |
| Analytics logic in report layer | Report consumes result only |
| Apparent multi-run support | Single `run_ref` in request type |

---

## 20. Task Table

| ID | Task | Status | Depends On |
|----|------|--------|------------|
| S010-T001 | Wave 0 spike + `S010_WAVE0_DECISIONS.md` | DONE | — |
| S010-T002 | Filters, `AnalyticsTimestampBasis`, schemas | DONE | S010-T001 |
| S010-T003 | Scope-aware `build_analysis_frame()` | DONE | S010-T001 |
| S010-T004 | `RunSummary` aggregates + `metrics_eligible` | DONE | S010-T002, S010-T003 |
| S010-T005 | Grouping: RTH, time-of-day, calendar period | DONE | S010-T004 |
| S010-T006 | Conditional comparison (`context_met`) | DONE | S010-T004 |
| S010-T007 | `analyze_signal_research_run` application API | DONE | S010-T004–T006 |
| S010-T008 | Integration tests (three scopes) | DONE | S010-T007 |
| S010-T009 | Optional HTML report spike | DONE | S010-T007 |
| S010-T010 | ADR-0013 — analytics boundary | DONE | S010-T001 |
| S010-T011 | MODULE_MAP, CURRENT_STATUS, sprint closure | DONE | S010-T010 |

**Total:** 11 tasks (~4 outcome PRs)

---

## 21. Tasks by Wave

### Wave 0 — T001, T010 (draft)

```text
tests/spike/run_signal_research_analytics_spike.py
S010_WAVE0_DECISIONS.md (D-S010-01 … D-S010-20)
ADR-0013 draft
```

Spike validates:

```text
v1 SIGNAL_MODEL_ONLY read + RunSummary
v2 MARKET_MODEL_ONLY read + RunSummary
v2 MARKET_AND_SIGNAL conditional split
COMPLETE filter + sample diagnostics
RTH_MEMBERSHIP and TIME_OF_DAY grouping on fixture
no model evaluation imports in analytics path
```

### Wave 1 — T002–T003

```text
OutcomeAnalyticsFilter
GroupDimension
AnalyticsTimestampBasis
build_analysis_frame()
schema validation (schemas.py)
```

### Wave 2 — T004, T007

```text
RunSummary + summarize_analysis_frame()
analyze_signal_research_run()
```

### Wave 3 — T005–T006, T008

```text
RTH_MEMBERSHIP, TIME_OF_DAY, CALENDAR_MONTH
conditional comparison
integration tests (three scopes)
```

### Wave 4 — T009, T011

```text
optional HTML report (reports.py / spike)
ADR-0013 ACCEPTED
MODULE_MAP, CURRENT_STATUS, sprint closure
```

---

## 22. PR Guidance

| PR | Outcome | Tasks |
|----|---------|-------|
| 1 | Wave 0 spike + binding decisions + ADR draft | T001, T010 (draft) |
| 2 | Filters, frame builder, RunSummary | T002–T004 |
| 3 | Grouping, conditional, application API | T005–T007 |
| 4 | Integration tests, report spike, closure | T008–T009, T011 |

```text
sprint/signal-research-analytics
  sprint/signal-research-analytics--wave0-decisions
  sprint/signal-research-analytics--analytics-core
  sprint/signal-research-analytics--grouping-and-conditional
  sprint/signal-research-analytics--closure
```

---

## 23. Acceptance Criteria

### Read boundary

- [x] No writes to run storage; no `evaluate_models` or outcome recomputation
- [x] v1 and v2 loads via repository only

### Frame

- [x] Normalized frame uses `entity_id` + `entity_kind`
- [x] `context_met_at_available_at` null outside `MARKET_AND_SIGNAL`

### Metrics

- [x] COMPLETE-only aggregates; full sample diagnostics on every summary
- [x] Hit rate: `forward_return > 0`; flat not counted as hit
- [x] `metrics_eligible` and null aggregates for undersized groups

### Grouping

- [x] `RTH_MEMBERSHIP` via `CmeEsRthSessionResolver`
- [x] TIME_OF_DAY: 60m buckets, market-local, `[start, end)` boundaries
- [x] Metadata records timestamp basis and timezone

### Conditional

- [x] True and false context groups both present; false rows not dropped
- [x] Deltas = true − false; no significance tests

### API

- [x] Single `run_ref` per request
- [x] Ephemeral results; optional report from result object only

### Tests

- [x] Integration test per scope; Sprint 008/009 tests unchanged

---

## 24. Wave 0 Spike Checklist

```bash
uv run python tests/spike/run_signal_research_analytics_spike.py
uv run python tests/spike/run_signal_research_analytics_spike.py --json
```

---

## 25. Phase 5 Closure Context

```text
Sprint 008  → SignalOccurrence + outcomes
Sprint 009  → MarketModelObservation + context facts
Sprint 010  → analytics over persisted facts
```

Principles:

```text
no recompute
read-only
single-run MVP
Polars first
explicit timestamp basis
generic entity_id + entity_kind
context true vs false preserved
analytics separate from reporting
```

Post-010 (not this sprint): multi-run analytics, rankings, DuckDB, dashboard, statistical testing.

---

## 26. Revision History

| Date | Change |
|------|--------|
| 2026-07-12 | Initial outline |
| 2026-07-12 | Wave 4 closure: HTML report spike, ADR-0013 ACCEPTED, docs updated |
| 2026-07-12 | Binding spec: entity_id/entity_kind, RTH_MEMBERSHIP, metrics_eligible, single-run API, D-S010-01…20 |
