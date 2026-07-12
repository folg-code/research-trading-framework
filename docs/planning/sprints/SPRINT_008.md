# Sprint 008 — Signal Research Computation MVP

## Metadata

```text
Sprint: 008
Phase: Phase 5 — Signal Research MVP (first increment)
Status: IN_PROGRESS (Wave 0 complete)
Planned Start: 2026-07-12
Planned End: TBD
Sprint Goal Owner: Project Maintainer
Depends On: SPRINT_006 (required, merged); SPRINT_005 (required, merged); SPRINT_007 (skipped)
Sprint Branch: sprint/signal-research-mvp
Task branch convention: sprint/signal-research-mvp--<task-slug>
Direction: docs/planning/sprints/PHASE_4_5_SPRINT_DIRECTION.md
Wave 0: docs/planning/sprints/S008_WAVE0_DECISIONS.md
Architecture Sources:
  - docs/vision/WORKFLOWS_AI_ADR_UPDATED.md (SignalOccurrence, research datasets)
  - docs/vision/ARCHITECTURE_FOUNDATIONS_UPDATED.md
Prerequisite: Sprint 007 skipped — minimum component set satisfied on main
```

---

## Sprint Goal

Run the first real **Signal Research** workflow end-to-end with scope **`SIGNAL_MODEL_ONLY`**:

```text
Published Market Dataset
    ↓
run_analysis (via evaluate_models)
    ↓
Signal Model evaluation → emissions
    ↓
SignalOccurrence (sparse occurrence facts)
    ↓
ForwardOutcome (long-format outcome facts)
    ↓
Persistent Signal Research run envelope (immutable Parquet + manifest)
```

Deliver **research computation**, not analytics dashboards or combined Market×Signal scopes.

Sprint 008 studies **signal behaviour**, not strategy execution — no fill price, no entry price.

---

## Three Outcomes

| Outcome | Deliverable |
|---------|-------------|
| **A — Occurrence materialization** | `SignalOccurrence` with stable `occurrence_id`; reference-price policy (descriptive, not execution) |
| **B — Forward outcomes** | Explicit `ForwardOutcomeDefinition` + calculator; long-format outcome rows with status |
| **C — Application integration** | `run_signal_research`, dataset repository (write + read), e2e round-trip, inspection layer |

---

## Domain Boundary

### SignalOccurrence vs Research Dataset

```text
Strategy Domain  → SignalOccurrence (core event artifact — no research-only fields)
Research Domain  → ForwardOutcomeDefinition, outcome calculator, dataset persistence
Application      → orchestrates evaluate_models + materialization + write/read
Inspection       → consumes finished dataset only; no domain logic
```

Research must not redefine occurrence semantics. Market Model conditioning deferred to Sprint 009.

### Price semantics (binding)

```text
reference_price  — descriptive close at detected_at (Signal Research MVP)
fill_price       — NOT in Sprint 008
entry_price      — NOT in Sprint 008
```

### Reuse — do not rebuild

```text
evaluate_models       — shared run_analysis + model evaluation
SignalModelEvaluator  — emissions table (detected_at, available_at, direction)
canonical_examples    — first e2e signal models
Parquet patterns      — follow Sprint 002 infrastructure conventions
```

---

## Logical Dataset Schema

Two fact tables in **long format** (one row per occurrence × horizon):

### SignalOccurrence (occurrence facts)

```text
occurrence_id
signal_model_id
detected_at
available_at
direction
reference_price
instrument
evaluation_timeframe
source_dataset_ref
```

### ForwardOutcome (outcome facts)

```text
occurrence_id
horizon_bars
outcome_status          — COMPLETE | INCOMPLETE_HORIZON | INSUFFICIENT_DATA
terminal_price
forward_return          — signed, direction-normalized
mfe                     — non-negative
mae                     — non-positive
```

**Binding:** one occurrence may produce **multiple outcome rows** (one per horizon). Outcome rows
are **not** 1:1 with occurrences when multiple horizons are requested.

Forward price **paths** are not stored in MVP — summary outcomes only.

---

## Physical Run Envelope

```text
{storage_root}/{run_id}/
├── manifest.json           — run identity, schema version, framework/model fingerprints
├── occurrences.parquet
└── outcomes.parquet
```

Consumers load via repository adapter — **no direct path reads** outside infrastructure/tests.

Immutability: existing `run_id` directory must not be overwritten.

---

## Task Table

| ID | Task | Status | Depends On |
|----|------|--------|------------|
| S008-T001 | Wave 0 spike and binding decisions | DONE | — |
| S008-T002 | `SignalOccurrence` schema, stable `occurrence_id`, materialization | DONE | S008-T001 |
| S008-T003 | Reference-price policy and materialization (not fill price) | DONE | S008-T002 |
| S008-T004 | Forward outcome definition and calculator | TODO | S008-T001 |
| S008-T005 | Temporal and incomplete-horizon edge cases | TODO | S008-T004 |
| S008-T006 | Dataset schema, manifest, writer and reader | TODO | S008-T004 |
| S008-T007 | `run_signal_research` application workflow | TODO | S008-T003, S008-T006 |
| S008-T008 | End-to-end integration and round-trip determinism | TODO | S008-T007 |
| S008-T009 | Occurrence and forward-path inspector | TODO | S008-T008 |
| S008-T010 | ADR — full outcome and persistence semantics | TODO | S008-T001 |
| S008-T011 | Documentation and sprint closure | TODO | S008-T010 |

**Total:** 11 tasks (~4 outcome PRs)

---

## Tasks (by wave)

### Wave 0 — T001, T010 (draft)

Scope gate, binding outcome semantics, dataset layout, ADR outline.

**Done (2026-07-12):** `tests/spike/run_signal_research_spike.py`, `S008_WAVE0_DECISIONS.md`.
Binding decisions D-S008-01 … D-S008-19 confirmed by spike (15/15 checks PASS).

Deliverables:

- ~~`tests/spike/run_signal_research_spike.py`~~
- ~~binding decisions confirmed by spike output~~
- ADR draft (T010) — next
- ADR draft covering occurrence/outcome boundary and long-format schema

### Wave 1 — T002–T003

Strategy-domain `SignalOccurrence` with stable identity and reference-price policy.

**Done (2026-07-12):** `reference_price.py`, `signal_occurrence.py`, unit tests; spike uses production strategy API.

### Wave 2 — T004–T005

`ForwardOutcomeDefinition` + calculator; incomplete horizon, nulls, temporal edge cases.

### Wave 3 — T006–T008

Dataset repository (write + read + schema validation), `run_signal_research`, e2e round-trip.

### Wave 4 — T009, T011

Occurrence/forward-path inspector (validation tooling only), ADR finalization, MODULE_MAP closure.

---

## Acceptance Criteria

### SignalOccurrence

- [ ] stable `occurrence_id` (deterministic from run context + occurrence key)
- [ ] model identity preserved (`signal_model_id`)
- [ ] `detected_at` and `available_at` preserved
- [ ] direction is typed (`LONG` | `SHORT`)
- [ ] `reference_price` semantics documented — descriptive, not execution
- [ ] no research-only fields in Strategy-domain occurrence object

### Outcomes

- [ ] explicit `ForwardOutcomeDefinition` before calculator implementation
- [ ] LONG and SHORT use one normalized sign convention
- [ ] `forward_return`: signed, direction-normalized (favourable > 0, adverse < 0)
- [ ] `mfe`: non-negative
- [ ] `mae`: non-positive (signed convention — do not mix with magnitude convention)
- [ ] horizon bar inclusion tested (`horizon=5` = 5 full bars after signal bar; terminal = close of 5th bar)
- [ ] MFE/MAE window excludes signal bar; includes bars `(t+1 … t+N]`
- [ ] incomplete horizon produces explicit `outcome_status` (not silent drop)
- [ ] null metrics are not silently replaced with zero
- [ ] no look-ahead beyond selected horizon

### Dataset

- [ ] write is immutable — existing `run_id` cannot be overwritten
- [ ] manifest includes framework version, schema version, model/dataset identity
- [ ] reader validates schema version
- [ ] load by `run_id` or research `DatasetRef` — paths hidden behind adapter
- [ ] round-trip test (write → read → assert equality)
- [ ] long-format outcomes; multiple horizons without schema change

### Determinism

Same inputs:

```text
dataset + model definition + horizon definition + framework version
```

must produce the same logical run identity, or detect duplicate run unambiguously.

### Inspection (T009)

Must include:

```text
occurrence selection
window before/after event
detected_at marker
available_at marker
reference_price level
horizon end marker
MFE / MAE levels
terminal outcome
```

Must **not** include:

```text
dashboard server
multi-model comparison
rankings
research filters
statistical tests
```

Optional adapter: finplot in spike/inspection only — not in domain or main workflow.

---

## PR Guidance

| PR | Outcome | Tasks |
|----|---------|-------|
| 1 | Wave 0 spike + binding decisions + ADR draft | T001, T010 (draft) |
| 2 | SignalOccurrence + reference-price policy | T002–T003 |
| 3 | Outcome definition, calculator, dataset repository | T004–T006 |
| 4 | Application workflow + e2e + inspector + closure | T007–T009, T011 |

Branch model:

```text
sprint/signal-research-mvp
  → task branches sprint/signal-research-mvp--<task-slug>
  → PR to sprint/signal-research-mvp
  → squash merge
  → sprint PR to main (after sprint complete)
```

---

## Branching — Start Conditions

**Met (2026-07-12):** Sprint 006 merged to `main` via PR #75.

```text
git switch main
git pull
git switch -c sprint/signal-research-mvp
git push -u origin sprint/signal-research-mvp
```

---

## Canonical E2E Scenario

```text
Signal model: higher_low_long (ON_EVENT)
Dataset:      committed integration fixture
Horizons:     e.g. (5,) or (5, 10) — long-format outcome rows
Assert:       ≥1 occurrence,
              COMPLETE outcomes where horizon fits,
              INCOMPLETE_HORIZON status where it does not,
              write → read round-trip,
              run_id immutability,
              deterministic run identity
```

---

## Explicit Non-Goals

```text
Sprint 007 component catalog expansion
MARKET_MODEL_ONLY / MARKET_AND_SIGNAL (Sprint 009)
Stored-dataset analytics without recompute (Sprint 010)
Experiment grids, rankings, statistical tests
Production dashboard
fill_price / entry_price / execution simulation
Stored forward price paths (summary outcomes only)
Direct file-path reads by analytics consumers
DuckDB / advanced query layer
```

---

## Revision History

| Date | Change |
|------|--------|
| 2026-07-12 | Initial outline |
| 2026-07-12 | Expanded task table, waves, Wave 0 kickoff; Sprint 007 skipped |
| 2026-07-12 | Corrections: reader in T006, outcome definition in T004, reference_price policy, long schema, run envelope, acceptance criteria |
