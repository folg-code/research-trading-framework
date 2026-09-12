# Sprint 009 — T001 Combined Research Spike and Architecture Decisions

## Metadata

```text
Task: S009-T001
Sprint: 009 — Market Model and Combined Research Scopes
Status: DONE (2026-07-12)
Branch: sprint/combined-research-scopes--wave0-decisions
Spike script: tests/spike/run_combined_research_spike.py
Direction: docs/planning/sprints/SPRINT_009.md
Depends on: SPRINT_008 merged to main (2026-07-12)
Scope: MARKET_MODEL_ONLY, MARKET_AND_SIGNAL (second Phase 5 increment)
```

---

## 1. Spike objective

Validate scope-aware Signal Research before Wave 1 contracts:

```text
MARKET_MODEL_ONLY
    evaluate_models → dense market model state
        ↓
    MarketModelObservation (TRUE_EDGE policy)
        ↓
    forward outcomes → envelope v2 (observations.parquet + outcomes.parquet)

MARKET_AND_SIGNAL
    evaluate_models → signal occurrences + dense market model state
        ↓
    context facts at SignalOccurrence.available_at (backward as-of)
        ↓
    forward outcomes → envelope v2 (occurrences.parquet + context.parquet + outcomes.parquet)
```

Run (planned):

```bash
uv run python tests/spike/run_combined_research_spike.py
uv run python tests/spike/run_combined_research_spike.py --json
```

Spike uses canonical Sprint 006 models and committed market-data fixtures — no new components.

---

## 2. Domain boundary (binding)

### Strategy Domain owns

```text
SignalOccurrence
Market Model Definition
Signal Model Definition
```

Research must not redefine `SignalOccurrence` semantics (ADR-0011 / D-S008-02 carry forward).

### Research Domain owns

```text
MarketModelObservation
ContextFact
forward outcomes
research dataset envelope
```

### Application Layer owns

```text
scope-aware orchestration
model evaluation
materialization
outcome calculation
persistence
```

---

## 3. Market Model State vs Observation vs Segment

Market Model describes **context**, not a signal. Three concepts must remain separate:

| Concept | Definition | Sprint 009 |
|---------|------------|------------|
| **Market Model State** | Model result on the evaluation axis (dense true/false) | Output of `evaluate_models` |
| **MarketModelObservation** | Point selected for forward outcome study | Materialized by research |
| **Market Model Segment** | Continuous interval where model was true | **Deferred** |

**Decision D-S009-03:** Market Model does **not** receive `SignalFiringPolicy`. It generates state only.

**Decision D-S009-04:** Research materializes observations via a separate policy:

```text
MarketModelObservationPolicy.TRUE_EDGE
```

Observation created on transition `false → true`.

**Decision D-S009-05:** Segment materialization (enter/exit, duration, segment statistics) is
**deferred**. Dense state remains available from `evaluate_models`.

---

## 4. Explicit research scope

**Decision D-S009-01:** Every new run requires explicit `ResearchScope`:

```text
SIGNAL_MODEL_ONLY
MARKET_MODEL_ONLY
MARKET_AND_SIGNAL
```

Scope must **not** be inferred from missing or present model fields. Invalid scope/model
combinations are rejected before computation.

Validation rules (binding):

```text
SIGNAL_MODEL_ONLY:
    requires signal model
    rejects market model

MARKET_MODEL_ONLY:
    requires market model
    rejects signal model

MARKET_AND_SIGNAL:
    requires market model
    requires signal model
```

---

## 5. Context timing (MARKET_AND_SIGNAL)

**Decision D-S009-02:** Market Model context for a `SignalOccurrence` is evaluated at:

```text
SignalOccurrence.available_at
```

Not at `detected_at`.

Rule:

```text
use latest market context legally available at signal.available_at
```

Alignment must use backward as-of semantics or an equivalent mechanism. Spike must prove no
look-ahead when `available_at > detected_at`.

---

## 6. One model combination per run

**Decision D-S009-06:** MVP contract for one experiment:

```text
one run
one scope
one Market Model
one Signal Model
```

Multiple combinations require separate runs with distinct `experiment_id` (future planner). No
implicit Cartesian product, OR, or AND composition from a model list.

---

## 7. Envelope v2 layout

**Decision D-S009-07:** Option A — separate fact tables (not unified `kind` column).

Per scope:

```text
SIGNAL_MODEL_ONLY:
    manifest.json
    occurrences.parquet
    outcomes.parquet

MARKET_MODEL_ONLY:
    manifest.json
    observations.parquet
    outcomes.parquet

MARKET_AND_SIGNAL:
    manifest.json
    occurrences.parquet
    context.parquet
    outcomes.parquet
```

Not every file appears in every scope.

Manifest must include:

```text
schema_version          — signal_research.v2
research_scope
market_model_ids
signal_model_ids
fact table descriptors
row counts
checksums
```

---

## 8. Schema versioning and compatibility

**Decision D-S009-08:**

```text
v1: read-only
v2: read/write
```

No physical `v1 → v2` migrator in Sprint 009. Reader recognizes both versions. Immutable v1 runs
are not rewritten.

---

## 9. Workflow API

**Decision D-S009-09:** Keep `run_signal_research(...)`. Do **not** introduce generic
`run_research(...)` (name too broad; collides with future research workflows).

Introduce scope-aware request:

```python
@dataclass(frozen=True, slots=True)
class SignalResearchRequest:
    scope: ResearchScope
    dataset_ref: DatasetRef
    market_models: tuple[MarketModelDefinition, ...]
    signal_models: tuple[SignalModelDefinition, ...]
    outcome_definition: ForwardOutcomeDefinition
```

Optional convenience factories:

```python
SignalResearchRequest.signal_only(...)
SignalResearchRequest.market_only(...)
SignalResearchRequest.market_and_signal(...)
```

---

## 10. ContextFact (MARKET_AND_SIGNAL)

Introduce in Wave 1 so envelope v2 is designed for both new scopes.

MVP unique key:

```text
occurrence_id + market_model_id
```

Fields:

```text
occurrence_id
market_model_id
context_met_at_available_at   — bool
context_evaluated_at          — signal.available_at (audit)
```

**Invariant:** Do not drop occurrences when context is false. Preserve `context_met = false` so
Sprint 010 can compare conditional outcomes.

---

## 11. MarketModelObservation invariants

```text
observation_id              — deterministic within run
market_model_id             — preserved
detected_at                 — preserved
available_at                — preserved
reference_price             — descriptive (Sprint 008 policy: close at detected_at)
source dataset lineage      — preserved
```

Forward outcomes attach to `observation_id` using Sprint 008 calculator and sign conventions
(ADR-0011 unchanged).

---

## 12. Run identity

Hash inputs must include:

```text
research_scope
dataset ref
market model identity
signal model identity
outcome definition
evaluation timeframe
requested range
framework version
```

Changing scope must change `run_id` even when models and dataset are identical. Repository
immutability unchanged from Sprint 008.

---

## 13. Test strategy

### Canonical E2E (real framework stack)

```text
Market Model:  high_volatility
Signal Model:  higher_low_long
```

Exercises State + Structure, MTF, event semantics, real `available_at` meaning.

### Deterministic contract test (alignment correctness)

Separate test with controlled models:

```text
Market Model:  close > threshold
Signal:        controlled emission at known timestamp
```

Must prove:

```text
available_at join
no look-ahead
context true
context false
run identity
```

**Decision D-S009-10:** Canonical integration pair = `high_volatility × higher_low_long`.

**Decision D-S009-11:** Deterministic temporal fixture required in addition to canonical E2E.

---

## 14. Reuse from Sprint 008 (do not rebuild)

```text
evaluate_models
run_analysis
SignalModelEvaluator
ForwardOutcomeDefinition
compute_forward_outcomes
reference_price policy
SignalResearchDatasetRepository (extend for v2)
run_signal_research (scope-aware evolution)
canonical model examples
```

Outcome semantics from ADR-0011 remain unchanged.

---

## 15. Explicitly out of scope

```text
aggregations, rankings, statistics
cross-run analytics
experiment grids
dashboard
execution simulation
segment materialization
configurable observation policies (beyond TRUE_EDGE)
physical v1 → v2 migration
multiple market models per run
```

Inspection increment is **optional** — must not block sprint closure.

---

## 16. Scope reduction priority (if sprint grows)

Cut in this order:

```text
1. inspection increment
2. physical migration v1 → v2
3. multiple model support
4. segment materialization
5. configurable observation policies
```

Do **not** cut:

```text
available_at alignment
explicit ResearchScope
context_met facts
schema versioning
v1 read compatibility
deterministic run identity
```

---

## 17. Spike checklist (must pass before Wave 1)

```text
high_volatility → TRUE_EDGE observation rows
higher_low_long + high_volatility context at available_at
no look-ahead when available_at > detected_at
scope recorded in manifest
run_id changes when scope changes
v1 SIGNAL_MODEL_ONLY envelope still readable
deterministic contract scenario documented (Wave 3 implements full test)
```

---

## 18. Revision history

| Date | Change |
|------|--------|
| 2026-07-12 | Binding decisions D-S009-01 … D-S009-11 locked; spike script pending |
| 2026-07-12 | Spike implemented (`run_combined_research_spike.py`); ADR-0012 draft |
