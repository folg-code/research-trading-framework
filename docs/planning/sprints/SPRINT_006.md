# Sprint 006 — Declarative Market Model and Signal Model MVP

## Metadata

```text
Sprint: 006
Phase: Phase 4 / Phase 5 bridge
Status: IN_PROGRESS (Wave 0 complete)
Planned Start: 2026-07-12
Planned End: TBD
Sprint Goal Owner: Project Maintainer
Depends On: SPRINT_005 (COMPLETED, merged to main)
Sprint Branch: sprint/declarative-models
Task branch convention: sprint/declarative-models--<task-slug>  (Git ref collision workaround)
Direction: docs/planning/sprints/PHASE_4_5_SPRINT_DIRECTION.md
Architecture Sources:
  - docs/vision/ARCHITECTURE_FOUNDATIONS_UPDATED.md
  - docs/vision/MULTITIMEFRAME_MARKET_MODEL_ARCHITECTURE_UPDATED.md
  - docs/adr/ADR-MA-013-cme-es-rth-session-and-swing-structure-mtf-projection.md
Prerequisite review: docs/planning/retrospectives/ARCHITECTURE_SIMPLIFICATION_REVIEW_S002_S003.md §5
```

**Directory note:** Vision docs provisionally place `market_models/` and `signal_models/` under
`strategy/`. Sprint 006 implements them as **separate domains** (`market_model/`, `signal_model/`,
shared `model_expression/`). Strategy remains a later composition layer. Reconcile in ADR
(S006-T025).

---

## Sprint Goal

Bridge **Market Analysis** and **Signal Research** by enabling declarative composition of
Market Analysis outputs into **Market Model** and **Signal Model** — without Strategy, Exit
Model, Risk Model, persistent research datasets, or forward outcomes.

```text
Model definitions
    ↓
dependency extraction
    ↓
run_analysis (once, shared)
    ↓
temporally valid AnalysisFrame
    ↓
ModelEvaluator
    ↓
MarketModelResult
SignalModelConditionResult
SignalEmissionResult
    ↓
inspection overlay
```

Deliver **declarative models**, not a strategy system.

---

## Three Outcomes

| Outcome | Deliverable |
|---------|-------------|
| **A — Reference and expression layer** | `ComponentOutputReference`, `MarketFieldReference`, expression AST, validation, dependency extraction |
| **B — Model evaluation** | `MarketModelDefinition`, `SignalModelDefinition`, evaluators, `SignalFiringPolicy`, null and temporal semantics |
| **C — Application integration and inspection** | `evaluate_models` use case, canonical examples, chart overlays, temporal regression tests |

---

## Domain Boundary

### Market Model and Signal Model are not Strategy

```text
Market Model ≠ Strategy
Signal Model ≠ Strategy
```

Do **not** place new model types under `strategy/`.

| Domain | Role |
|--------|------|
| **Market Analysis** | Computes reusable Features, Structures, States |
| **Market Model** | Declarative composition of market context conditions |
| **Signal Model** | Declarative composition of signal conditions + explicit firing |
| **Strategy** (later) | May consume Signal Model, Exit Model, Risk Model, execution rules |

Market Model composes: Market Features + Structures + States.  
Signal Model composes: signal-relevant Features, States, and Market Analysis outputs.

### Recommended package layout

```text
src/trading_framework/
├── model_expression/
│   ├── expressions.py
│   ├── references.py
│   ├── validation.py
│   ├── dependencies.py
│   └── evaluation.py      # shared expression evaluation helpers
├── market_model/
│   ├── definitions.py
│   ├── evaluation.py
│   └── results.py
├── signal_model/
│   ├── definitions.py
│   ├── evaluation.py
│   ├── firing.py
│   └── results.py
└── application/model_evaluation/
    └── evaluate_models.py
```

**Application** orchestrates dependency extraction and `run_analysis`.  
**Domain evaluators** consume a resolved `AnalysisFrame` only — they do not fetch data,
resample, align, or call `run_analysis`.

---

## Design Principles

### Keep

```text
Small immutable expression AST (REFERENCE, COMPARE, AND, OR, NOT)
Explicit ComponentOutputReference and MarketFieldReference
Three-valued null semantics (true / false / null)
Signal condition result separate from SignalEmissionResult
Explicit SignalFiringPolicy (ON_TRUE_EDGE, ON_EVENT)
Explicit static SignalDirection on SignalModelDefinition
ModelEvaluator consumes already aligned AnalysisFrame
Shared run_analysis for deduplicated component dependencies
Polars DataFrame materialization for model results
Inspection consumes finished results only
Outcome-scoped PRs (~100–400 lines)
```

### Reduce

```text
Full expression DSL (shift, rolling, arbitrary Polars)
Strategy / Exit / Risk / position sizing
SignalOccurrence final schema (Sprint 008)
Persistent research dataset, forward returns, MFE / MAE
Combined MARKET_AND_SIGNAL research workflow (Sprint 009)
Dynamic signal direction
EACH_TRUE_BAR firing policy (defer unless needed)
New Market Analysis catalog components
```

### Reuse from Sprint 004–005

```text
ComponentOutputRef (market_analysis DAG — compare before duplicating)
AnalysisFrame, AnalysisFrameColumnSpec, AnalysisFrameAssembler
run_analysis, ComponentRequest, computation_timeframe / evaluation_timeframe
structure.swing, volatility.state, trend.ema, volatility.atr
tests/spike/run_inspect_mtf_swing.py (extend, do not fork compute path)
```

---

## Signal Model: Condition vs Firing

Signal Model evaluation is **two-stage**:

```text
1. SignalModelEvaluator  → dense SignalModelConditionResult (condition_met)
2. SignalFiringPolicy    → sparse SignalEmissionResult
```

Example dense condition:

```text
10:00  condition_met=false
10:01  condition_met=true
10:02  condition_met=true
10:03  condition_met=true
10:04  condition_met=false
```

Firing policies (MVP):

| Policy | Semantics | Example use |
|--------|-----------|-------------|
| `ON_TRUE_EDGE` | Emit on `false → true` transition | `volatility.state == 1` |
| `ON_EVENT` | Emit where sparse event output is true | `higher_low_event == true` |

Deferred: `EACH_TRUE_BAR` (every bar where condition is true).

Do not encode one universal firing semantics for all models.

---

## Signal Direction

Direction is **explicit** on `SignalModelDefinition`:

```python
SignalModelDefinition(
    signal_model_id="bullish_higher_low",
    expression=Equals(...),
    direction=SignalDirection.LONG,
    firing_policy=SignalFiringPolicy.ON_EVENT,
)
```

MVP values: `LONG`, `SHORT`, `NEUTRAL`.

Do **not** infer direction from component semantics (e.g. `higher_low_event → LONG`).
Same event may appear in mean-reversion or neutral research models.

---

## MarketFieldReference (MVP)

Required in Sprint 006 so simple conditions like `close > open` do not require a new
Market Analysis component.

Allowed:

```text
canonical OHLCV: OPEN, HIGH, LOW, CLOSE, VOLUME
evaluation timeframe (from run context)
comparison and temporal availability via AnalysisFrame
```

Forbidden in MVP:

```text
shift, rolling, resampling
arbitrary column names
Polars expressions, lambda, callbacks
repository or dynamic DataFrame access
```

Mitigates PRB-011 with fixed field enum and negative tests.

---

## ComponentOutputReference

Existing `ComponentOutputRef` (`market_analysis/models/outputs.py`) links components in the
MA DAG. Before introducing a parallel type, compare semantics.

Model-layer reference may need:

```text
component identity, parameters, computation_timeframe, output_id
presentation-independent identity for dependency extraction
```

If `ComponentOutputRef` + `ComponentRequest.computation_timeframe` suffice, reuse or wrap —
do not duplicate meaning under a second name.

---

## Null Semantics

Three-valued logic:

```text
Compare with unavailable operand → null

false AND null → false
true  AND null → null

true  OR null  → true
false OR null  → null

NOT null → null
```

Null sources: warm-up, missing prior state, inactive data, unavailable component output.

```text
null does not fire
```

Do not coerce all nulls to `false` — that hides warm-up and missing data.

---

## Temporal Availability

**ModelEvaluator does not perform MTF alignment.** It consumes operands that are already
temporally legal on the evaluation grid.

Forbidden in ModelEvaluator:

```text
resampling, join_asof, LAST_CLOSED_BAR, data fetch
```

Semantic rule:

```text
model available_at = latest available_at of required operands
```

If `AnalysisFrame` guarantees row-level operand legality, simplify to:

```text
model available_at = evaluation row available_at
```

Do not duplicate Sprint 004–005 alignment logic in the model layer.

Temporal tests must confirm:

```text
model result never precedes operand availability
HTF swing events not available early
warm-up remains null
firing does not occur on null
```

---

## Result Shapes (Polars)

### MarketModelResult (dense)

```text
timestamp, available_at, market_model_id, model_result
```

`model_result`: bool in MVP (categorical / score later).

### SignalModelConditionResult (dense)

```text
timestamp, available_at, signal_model_id, condition_met
```

### SignalEmissionResult (sparse)

```text
detected_at, available_at, signal_model_id, direction, firing_policy
```

Do **not** name this `SignalOccurrence` in Sprint 006. Final `SignalOccurrence` (with
`reference_price`, research lineage, horizon, MFE / MAE) belongs to Signal Research
(Sprint 008).

---

## Dependency Extraction and Orchestration

```text
Model definitions
    ↓
ExpressionDependencyExtractor
    ↓
ComponentRequest set + required MarketFields
    ↓
run_analysis once (deduplicated)
    ↓
AnalysisFrame
    ↓
MarketModelEvaluator / SignalModelEvaluator (+ firing)
```

Multiple models sharing `volatility.state`, `structure.swing`, `trend.ema` must trigger
**one** `run_analysis`, then evaluate all models on the same frame.

---

## Canonical Examples

| Example | Expression | Config |
|---------|------------|--------|
| Market Model | `volatility.state == 1` | dense result |
| Signal — event | `structure.swing.higher_low_event == true` | `direction=LONG`, `ON_EVENT` |
| Signal — state edge | `volatility.state == 1` | `direction=LONG` or `NEUTRAL`, `ON_TRUE_EDGE` |
| Combined expression | `volatility.state == 1 AND higher_low_event == true` | composition test only — no `CombinedModel` type |

Full `MARKET_AND_SIGNAL` research scope remains Sprint 009.

---

## Visualization Increment

Extend `tests/spike/run_inspect_mtf_swing.py` (or sibling under `tests/spike/`):

```text
Market Model state overlay
Signal Model condition overlay
Signal emission markers
model_id filtering
available_at in hover
```

Chart layer must **not** evaluate models, compute components, apply firing, or resample.

---

## Task Overview

| ID | Task | Status | Depends On |
|----|------|--------|------------|
| S006-T001 | Wave 0 decisions spike and note | DONE | — |
| S006-T002 | `ComponentOutputReference` (reuse/wrap `ComponentOutputRef`) | DONE | S006-T001 |
| S006-T003 | `MarketFieldReference` (canonical OHLCV) | DONE | S006-T001 |
| S006-T004 | Expression nodes (`Compare`, `And`, `Or`, `Not`) | DONE | S006-T002, S006-T003 |
| S006-T005 | Expression validation | DONE | S006-T004 |
| S006-T006 | `ExpressionDependencyExtractor` | DONE | S006-T004 |
| S006-T007 | `MarketModelDefinition` | DONE | S006-T004 |
| S006-T008 | `MarketModelEvaluator` | DONE | S006-T007 |
| S006-T009 | `SignalModelDefinition` + `SignalDirection` | DONE | S006-T004 |
| S006-T010 | `SignalModelEvaluator` (condition result) | DONE | S006-T009 |
| S006-T011 | `SignalFiringPolicy` + emission materialization | DONE | S006-T010 |
| S006-T012 | Null and temporal semantics in evaluators | DONE | S006-T008, S006-T010 |
| S006-T013 | `evaluate_models` application use case | TODO | S006-T006, S006-T012 |
| S006-T014 | Automatic `ComponentRequest` construction from models | TODO | S006-T013 |
| S006-T015 | Shared single `run_analysis` execution | TODO | S006-T014 |
| S006-T016 | Canonical Market Model example | TODO | S006-T015 |
| S006-T017 | Event-based Signal Model example (`ON_EVENT`) | TODO | S006-T015 |
| S006-T018 | State-edge Signal Model example (`ON_TRUE_EDGE`) | TODO | S006-T015 |
| S006-T019 | Combined expression example | TODO | S006-T015 |
| S006-T020 | Inspection chart overlay | TODO | S006-T016 |
| S006-T021 | End-to-end integration test | TODO | S006-T019 |
| S006-T022 | Temporal regression tests | TODO | S006-T012 |
| S006-T023 | Null and warm-up tests | TODO | S006-T012 |
| S006-T024 | Invalid reference / forbidden field tests | TODO | S006-T005 |
| S006-T025 | ADR — model expression, domain boundary, firing, null semantics | TODO | S006-T001 |
| S006-T026 | MODULE_MAP, reference docs, sprint closure | TODO | S006-T025 |

**Total:** 26 tasks (consolidated into ~5 outcome PRs)

---

## Tasks (by wave)

### Wave 0 — T001

Close package ownership, AST shape, `AnalysisFrame` adapter boundary, result schemas,
firing policies, null semantics, temporal rules, max expression depth, `MarketFieldReference`
scope.

**Done (2026-07-12):** `tests/spike/run_model_expression_spike.py`, `S006_WAVE0_DECISIONS.md`.
Binding decisions D-S006-01 … D-S006-12.

### Wave 1 — T002–T006

References, expression nodes, validation, dependency extraction.

**Done (2026-07-12):** `model_expression` package — references, AST, validation, `ExpressionDependencyExtractor`.

### Wave 2 — T007–T012

Model definitions, evaluators, firing, null and temporal semantics.

**Done (2026-07-12):** `model_expression/evaluation/`, `market_model/`, `signal_model/` with
`ExpressionEvaluator`, `MarketModelEvaluator`, `SignalModelEvaluator`, `SignalFiringPolicy`.

### Wave 3 — T013–T015

Application orchestration: `evaluate_models`, request construction, shared `run_analysis`.

### Wave 4 — T016–T021

Canonical examples, inspection overlay, end-to-end integration test.

### Wave 5 — T022–T026

Temporal / null / negative tests, ADR, documentation closure.

---

## PR Guidance

| PR | Outcome | Tasks |
|----|---------|-------|
| 1 | Decisions, references and expression contracts | T001–T004 |
| 2 | Validation and dependency extraction | T005–T006 |
| 3 | Market and Signal Model evaluation | T007–T012 |
| 4 | Application orchestration and canonical vertical slice | T013–T019, T021 |
| 5 | Inspection, temporal regression tests, ADR and docs | T020, T022–T026 |

Branch model:

```text
sprint/declarative-models
  → task branches sprint/declarative-models--<task-slug>
  → PR to sprint/declarative-models
  → squash merge
  → sprint PR to main (after sprint complete)
```

Git cannot nest `sprint/declarative-models/foo` when branch `sprint/declarative-models` exists;
use double-dash task names (see D-S006-11).

---

## Branching — Start Conditions

Planning may proceed now. **Implementation starts only after:**

```text
merge PR #66 (S005 Wave 5 ADR/docs)
merge sprint/market-analysis-components → main
```

Then:

```text
git switch main
git pull
git switch -c sprint/declarative-models
```

Do not start Sprint 006 from the Sprint 005 branch.

---

## Sprint 007 Relationship

Sprint 007 is **optional** and research-question-driven.

After Sprint 006, available building blocks:

```text
ATR, EMA, Volatility State, Swing Structure, HH/HL/LH/LL
Market Model, Signal Model
```

Decision gate after Sprint 006:

```text
Can a sensible first Signal Research experiment be formulated?
  yes → Sprint 006 → Sprint 008
  no  → Sprint 006 → narrow Sprint 007 → Sprint 008
```

Do not pre-commit the full Sprint 007 catalog (slope, wick ratio, Session Range, Trend State)
without a concrete research question.

---

## Out of Scope

```text
Strategy, Exit Model, Risk Model, position sizing
Signal Research persistence
SignalOccurrence final schema
forward returns, MFE, MAE, Research Dataset
full DSL, rolling/shift expressions, custom Polars, callbacks
dynamic direction
session-boundary resampling
new Market Analysis catalog
web dashboard
MARKET_AND_SIGNAL research workflow (Sprint 009)
```

---

## Definition of Done

- [ ] Market Model and Signal Model are separate from Strategy
- [ ] Definitions contain no DataFrame, Polars expressions, or callbacks
- [ ] Component outputs referenced explicitly via `ComponentOutputReference`
- [ ] Canonical OHLCV fields referenced via restricted `MarketFieldReference`
- [ ] `Compare`, `AND`, `OR`, `NOT` expressions work
- [ ] Three-valued null semantics tested
- [ ] Dependencies extracted deterministically; shared MA runs once
- [ ] Market Model produces dense evaluation-grid result
- [ ] Signal Model produces dense condition result
- [ ] `SignalFiringPolicy` produces sparse `SignalEmissionResult`
- [ ] `ON_TRUE_EDGE` works for state conditions; `ON_EVENT` for event conditions
- [ ] Signal direction is explicit on definition
- [ ] `available_at` never precedes operand availability
- [ ] Unknown outputs and forbidden fields fail before evaluation
- [ ] Canonical examples work end-to-end
- [ ] Inspection chart shows conditions and emissions
- [ ] Quality commands pass (`ruff`, `mypy`, `pytest`)
- [ ] One ADR accepted; `CURRENT_STATUS` and `MODULE_MAP` updated
- [ ] Sprint PR to `main` (agent stops before merge)

---

## Binding Decisions (accepted for planning)

| Topic | Decision |
|-------|----------|
| State firing | `ON_TRUE_EDGE` |
| Event firing | `ON_EVENT` |
| `MarketFieldReference` | canonical OHLCV only |
| Signal direction | explicit static field on `SignalModelDefinition` |
| Package ownership | `model_expression/`, `market_model/`, `signal_model/` — not `strategy/` |
| ModelEvaluator input | already aligned `AnalysisFrame` only |
| Orchestration | application extracts dependencies, runs MA once |
| Branch | create from `main` after Sprint 005 merge |
| Sprint 007 | optional, research-question-driven |

---

## Core Boundary (summary)

```text
Market Analysis     → computes reusable facts
Market / Signal Model → composes facts declaratively
Signal Research     → evaluates historical outcomes of model results (Sprint 008+)
Strategy            → later composition layer
```

---

## Sprint 008 Preview

`SignalOccurrence` materialization, forward outcomes, persistent Parquet research dataset —
see `SPRINT_008.md`.

---

## Revision History

| Date | Change |
|------|--------|
| 2026-07-12 | Initial outline from PHASE_4_5_SPRINT_DIRECTION |
| 2026-07-12 | **Full planning:** domain boundary (not Strategy), condition vs firing split, null semantics, package layout, 26 tasks, 5 PRs, branching gate on S005 merge |
| 2026-07-12 | **Wave 0 complete:** spike + S006_WAVE0_DECISIONS.md; sprint branch created from main |
