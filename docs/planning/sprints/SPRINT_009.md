# Sprint 009 — Market Model and Combined Research Scopes

## Metadata

```text
Sprint: 009
Phase: Phase 5 — Signal Research MVP (second increment)
Status: COMPLETE — sprint branch ready for merge to main (2026-07-12)
Planned Start: TBD
Planned End: TBD
Sprint Goal Owner: Project Maintainer
Depends On: SPRINT_008 (required, merged to main)
Sprint Branch: sprint/combined-research-scopes
Task branch convention: sprint/combined-research-scopes--<task-slug>
Direction: docs/planning/sprints/PHASE_4_5_SPRINT_DIRECTION.md
Wave 0 decisions: docs/planning/sprints/S009_WAVE0_DECISIONS.md
Prerequisite: Sprint 007 skipped — existing components sufficient (same gate as 008)
Architecture Sources:
  - docs/vision/WORKFLOWS_AI_ADR_UPDATED.md (§3.3 Research Scope)
  - docs/adr/ADR-0011-signal-research-outcomes-and-persistence.md
  - docs/planning/sprints/S008_WAVE0_DECISIONS.md (outcome semantics carry forward)
```

---

## 1. Sprint Goal

Sprint 009 extends Signal Research by two missing scopes:

```text
MARKET_MODEL_ONLY
MARKET_AND_SIGNAL
```

After completion, all three Signal Research scopes work **explicitly**:

```text
SIGNAL_MODEL_ONLY     — Sprint 008 (unchanged semantics)
MARKET_MODEL_ONLY     — new
MARKET_AND_SIGNAL     — new
```

Scope must **not** be inferred from missing or present fields. Every new run declares scope
explicitly.

Sprint includes:

```text
computation
fact materialization
persistence
explicit alignment rules
envelope versioning
integration tests
```

Sprint does **not** include:

```text
aggregations, rankings, statistics
cross-run analytics
experiment grids
dashboard
execution simulation
```

Analytics on stored runs → **Sprint 010**.

---

## 2. Main Flows

### MARKET_MODEL_ONLY

```text
Published Market Dataset
        ↓
Market Analysis
        ↓
Market Model evaluation
        ↓
Market Model state (dense)
        ↓
MarketModelObservation (TRUE_EDGE)
        ↓
Forward outcomes
        ↓
Persistent Research Dataset (envelope v2)
```

### MARKET_AND_SIGNAL

```text
Published Market Dataset
        ↓
Market Analysis
        ↓
Market Model + Signal Model evaluation
        ↓
SignalOccurrence
        ↓
Market context evaluated at signal.available_at
        ↓
ContextFact
        ↓
Forward outcomes
        ↓
Persistent Research Dataset (envelope v2)
```

---

## 3. Domain Boundaries

### Strategy Domain

Owns:

```text
SignalOccurrence
Market Model Definition
Signal Model Definition
```

Research must not redefine `SignalOccurrence` semantics.

### Research Domain

Owns:

```text
MarketModelObservation
ContextFact
forward outcomes
research dataset envelope
```

### Application Layer

Owns:

```text
scope-aware orchestration
model evaluation
materialization
outcome calculation
persistence
```

---

## 4. Reuse from Sprint 008

Do not rebuild the existing vertical:

```text
evaluate_models
run_analysis
SignalModelEvaluator
ForwardOutcomeDefinition
compute_forward_outcomes
reference_price policy
SignalResearchDatasetRepository
run_signal_research
canonical model examples
```

ADR-0011 outcome semantics remain unchanged.

---

## 5. Binding Decisions (Wave 0 — locked)

Full rationale: `S009_WAVE0_DECISIONS.md`.

| ID | Decision |
|----|----------|
| **D-S009-01** | Explicit `ResearchScope` on every run; invalid scope/model combos rejected |
| **D-S009-02** | MARKET_AND_SIGNAL: context at `SignalOccurrence.available_at` (backward as-of) |
| **D-S009-03** | Market Model has no `SignalFiringPolicy` — generates state only |
| **D-S009-04** | `MarketModelObservationPolicy.TRUE_EDGE` (`false → true`) |
| **D-S009-05** | Segment materialization deferred; dense state from `evaluate_models` |
| **D-S009-06** | One Market Model + one Signal Model per run; no implicit composition |
| **D-S009-07** | Envelope v2: separate fact tables (Option A) |
| **D-S009-08** | v1 read-only; v2 read/write; no physical migrator |
| **D-S009-09** | Keep `run_signal_research`; add `SignalResearchRequest` with required scope |
| **D-S009-10** | Canonical E2E pair: `high_volatility × higher_low_long` |
| **D-S009-11** | Deterministic temporal fixture for alignment / no-look-ahead contract test |

### Market Model State vs Observation vs Segment

```text
Market Model State       — dense result on evaluation axis (evaluate_models)
MarketModelObservation   — research sampling point for forward outcomes
Market Model Segment     — continuous true interval (deferred)
```

### Envelope v2 layout (Option A)

```text
SIGNAL_MODEL_ONLY:
    manifest.json, occurrences.parquet, outcomes.parquet

MARKET_MODEL_ONLY:
    manifest.json, observations.parquet, outcomes.parquet

MARKET_AND_SIGNAL:
    manifest.json, occurrences.parquet, context.parquet, outcomes.parquet
```

### ContextFact (MARKET_AND_SIGNAL)

Unique key: `occurrence_id + market_model_id`

```text
occurrence_id
market_model_id
context_met_at_available_at
context_evaluated_at
```

Occurrences are **not** dropped when context is false — Sprint 010 needs conditional filtering.

### SignalResearchRequest (API shape)

```python
@dataclass(frozen=True, slots=True)
class SignalResearchRequest:
    scope: ResearchScope
    dataset_ref: DatasetRef
    market_models: tuple[MarketModelDefinition, ...]
    signal_models: tuple[SignalModelDefinition, ...]
    outcome_definition: ForwardOutcomeDefinition
```

Convenience factories: `.signal_only(...)`, `.market_only(...)`, `.market_and_signal(...)`.

---

## 6. Three Outcomes

| Outcome | Deliverable |
|---------|-------------|
| **A — Explicit research scope** | `ResearchScope`, `SignalResearchRequest`, validation |
| **B — MARKET_MODEL_ONLY** | `MarketModelObservation` + outcomes + envelope v2 |
| **C — MARKET_AND_SIGNAL** | `ContextFact` at `available_at` + outcomes + envelope v2 |

---

## 7. Mandatory Core Scope

Must ship:

```text
ResearchScope
MarketModelObservation
ContextFact
MARKET_MODEL_ONLY workflow
MARKET_AND_SIGNAL workflow
context at available_at
envelope v2
repository read/write
v1 read compatibility
integration tests (canonical E2E + deterministic contract)
ADR-0012
documentation closure
```

---

## 8. Deferred / Optional

| Item | Status |
|------|--------|
| Segment materialization | Deferred |
| Multiple market models per run | Deferred |
| Configurable observation policies | Deferred (TRUE_EDGE only) |
| Experiment grids | Deferred |
| Physical v1 → v2 migration | Out of scope |
| Inspection increment | Optional — does not block closure |

### Scope reduction priority (if needed)

```text
1. inspection increment
2. physical migration
3. multiple model support
4. segment materialization
5. configurable observation policies
```

Never cut: `available_at` alignment, explicit scope, `context_met` facts, schema versioning,
v1 read compatibility, deterministic run identity.

---

## 9. Task Table

| ID | Task | Status | Depends On |
|----|------|--------|------------|
| S009-T001 | Wave 0 spike + binding decisions doc | DONE | — |
| S009-T002 | `ResearchScope`, `SignalResearchRequest`, validation | DONE | S009-T001 |
| S009-T003 | `MarketModelObservation`, `ContextFact` | DONE | S009-T001 |
| S009-T004 | MARKET_MODEL_ONLY workflow + persistence | DONE | S009-T002, S009-T003 |
| S009-T005 | Context alignment at `available_at` | DONE | S009-T001 |
| S009-T006 | MARKET_AND_SIGNAL workflow + context facts | DONE | S009-T004, S009-T005 |
| S009-T007 | Envelope schema v2 + repository read/write + v1 read | DONE | S009-T004 |
| S009-T008 | Integration tests (three scopes + deterministic fixture) | DONE | S009-T006, S009-T007 |
| S009-T009 | Inspection spike increment (optional) | DONE | S009-T008 |
| S009-T010 | ADR-0012 — scope and context alignment | ACCEPTED | S009-T001 |
| S009-T011 | MODULE_MAP, CURRENT_STATUS, sprint closure | DONE | S009-T010 |

**Total:** 11 tasks (~4 outcome PRs)

---

## 10. Tasks by Wave

### Wave 0 — T001, T010 (draft)

Spike + `S009_WAVE0_DECISIONS.md` (decisions locked) + ADR-0012 draft.

Deliverables:

- `tests/spike/run_combined_research_spike.py`
- spike validates TRUE_EDGE observations, context at `available_at`, envelope v2 layout, v1 read

### Wave 1 — T002–T003

```text
ResearchScope
SignalResearchRequest + validation rules
MarketModelObservation
ContextFact
```

### Wave 2 — T004, T007

```text
envelope v2 (manifest + fact tables)
repository read/write
v1 read compatibility
MARKET_MODEL_ONLY end-to-end
```

### Wave 3 — T005–T006, T008

```text
available_at alignment (backward as-of)
MARKET_AND_SIGNAL workflow
no-look-ahead tests
three-scope integration tests
deterministic temporal contract test
```

### Wave 4 — T009, T011

```text
ADR-0012 finalization
MODULE_MAP, CURRENT_STATUS
optional inspection
sprint closure
```

---

## 11. Acceptance Criteria

### Scope configuration

- [x] `ResearchScope` required on new runs; recorded in manifest
- [x] `SIGNAL_MODEL_ONLY` backward compatible with Sprint 008
- [x] Invalid scope/model combinations fail fast with clear errors

### MARKET_MODEL_ONLY

- [x] `high_volatility` produces TRUE_EDGE observation facts
- [x] Forward outcomes use Sprint 008 calculator and sign conventions
- [x] Envelope v2 persists and round-trips via repository

### MARKET_AND_SIGNAL

- [x] Context evaluated at signal `available_at` (not `detected_at`)
- [x] `context_met_at_available_at` preserved including `false` rows
- [x] Outcomes unchanged in schema; join via `occurrence_id`

### Persistence

- [x] `signal_research.v2` documented; v1 runs readable (read-only)
- [x] Deterministic `run_id` includes scope in hash

### Tests

- [x] Canonical E2E: `high_volatility × higher_low_long`
- [x] Deterministic contract: controlled emission + threshold market model
- [x] Sprint 008 integration tests pass for `SIGNAL_MODEL_ONLY`
- [x] ADR-0011 outcome semantics unchanged

---

## 12. PR Guidance

| PR | Outcome | Tasks |
|----|---------|-------|
| 1 | Wave 0 spike + binding decisions + ADR draft | T001, T010 (draft) |
| 2 | Domain and request contracts | T002–T003 |
| 3 | MARKET_MODEL_ONLY + envelope v2 | T004, T007 |
| 4 | Combined scope + tests + closure | T005–T006, T008–T009, T011 |

Branch model:

```text
sprint/combined-research-scopes
  sprint/combined-research-scopes--wave0-decisions
  sprint/combined-research-scopes--domain-contracts
  sprint/combined-research-scopes--market-model-only
  sprint/combined-research-scopes--market-and-signal
```

---

## 13. Wave 0 Spike Checklist

```bash
uv run python tests/spike/run_combined_research_spike.py
uv run python tests/spike/run_combined_research_spike.py --json
```

Must validate:

```text
high_volatility → TRUE_EDGE observation rows
higher_low_long + high_volatility context at available_at
no look-ahead when available_at > detected_at
scope recorded in manifest
run_id changes when scope changes
v1 SIGNAL_MODEL_ONLY envelope still readable
```

---

## 14. Deferred to Sprint 010

```text
mean/median return, hit rate, sample size filters
session / time-of-day grouping
forward return distributions
conditional outcome comparisons (uses context_met from 009)
```

---

## 15. Revision History

| Date | Change |
|------|--------|
| 2026-07-12 | Initial outline |
| 2026-07-12 | Full sprint plan: tasks, waves, binding decisions, acceptance criteria |
| 2026-07-12 | Wave 4 closure: inspection spike, ADR-0012 ACCEPTED, docs updated |
