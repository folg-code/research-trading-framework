# Sprint 006 — Declarative Model Expression MVP

## Metadata

```text
Sprint: 006
Phase: Phase 4 / Phase 5 bridge
Status: PLANNED
Depends On: SPRINT_005 (PLANNED)
Sprint Branch: sprint/declarative-models (TBD)
Direction: docs/planning/sprints/PHASE_4_5_SPRINT_DIRECTION.md
```

---

## Sprint Goal

Enable declarative composition of Market Analysis outputs into **Market Model** and **Signal Model** — without Strategy, Exit Model, or Risk Model.

```text
one-condition Market Model   e.g. VolatilityState == HIGH
one-condition Signal Model   e.g. pivot == HL  OR  last_confirmed_HL is not null
combined example             VolatilityState == HIGH AND pivot == HL
```

Outputs: **Polars DataFrame** tables, not per-event Python object lists.

---

## Scope

### In scope

- `ComponentOutputReference`
- Minimal `MarketFieldReference` (canonical field, timeframe, shift, comparison — no arbitrary Polars/lambda/repository access)
- Expression operators: `REFERENCE`, `COMPARE`, `AND`, `OR`, `NOT`
- `MarketModel` and `SignalModel` definitions + validation
- Temporal availability propagation (`available_at` respected)
- In-memory model result materialization
- Visual inspection extension: model state overlay, signal markers, model id filter
- One ADR + tests + documentation

### Out of scope

- Full expression DSL
- Strategy / Exit / Risk models
- Persistent research datasets (Sprint 008)
- Production dashboard

---

## Task Overview (draft)

| ID | Task | Status |
|----|------|--------|
| S006-T001 | ComponentOutputReference contract | TODO |
| S006-T002 | Minimal MarketFieldReference | TODO |
| S006-T003 | Comparison expression | TODO |
| S006-T004 | AND / OR / NOT composition | TODO |
| S006-T005 | MarketModel definition and evaluator | TODO |
| S006-T006 | SignalModel definition and evaluator | TODO |
| S006-T007 | Expression validation | TODO |
| S006-T008 | Temporal availability propagation | TODO |
| S006-T009 | One-condition Market Model example | TODO |
| S006-T010 | One-condition Signal Model example | TODO |
| S006-T011 | Combined model example | TODO |
| S006-T012 | In-memory model result (Polars) | TODO |
| S006-T013 | Visual inspection extension | TODO |
| S006-T014 | End-to-end tests | TODO |
| S006-T015 | ADR and sprint closure | TODO |

---

## Model output shapes (target)

**Market Model:**

```text
timestamp, available_at, model_id, model_result
```

**Signal Model:**

```text
detected_at, available_at, signal_model_id, direction, metadata
```

---

## PR Guidance (draft)

~4–5 outcome PRs: references → expressions → evaluators → viz + tests → ADR.

---

## Revision History

| Date | Change |
|------|--------|
| 2026-07-12 | Initial outline from PHASE_4_5_SPRINT_DIRECTION |
