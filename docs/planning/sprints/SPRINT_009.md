# Sprint 009 — Market Model and Combined Research Scopes

## Metadata

```text
Sprint: 009
Phase: Phase 5 — Signal Research MVP (second increment)
Status: PLANNED
Depends On: SPRINT_008
Sprint Branch: TBD
Direction: docs/planning/sprints/PHASE_4_5_SPRINT_DIRECTION.md
```

---

## Sprint Goal

Add remaining research scopes:

```text
MARKET_MODEL_ONLY     → Future Market Behaviour
MARKET_AND_SIGNAL     → Conditional Signal Behaviour
```

---

## Key semantic decision (MVP default)

```text
Market Model context evaluated at Signal available_at
```

Market conditions must be legally available at signal time — no look-ahead from future market state.

---

## Flows

**Market Model only:**

```text
Market Model → Future Market Behaviour dataset
```

**Combined:**

```text
Market Model context + SignalOccurrence → conditional signal outcomes
```

---

## Task Overview (draft)

| ID | Task | Status |
|----|------|--------|
| S009-T001 | MARKET_MODEL_ONLY workflow | TODO |
| S009-T002 | MARKET_AND_SIGNAL workflow | TODO |
| S009-T003 | Context alignment at available_at | TODO |
| S009-T004 | Persistent dataset schema extension | TODO |
| S009-T005 | Tests and visual inspection | TODO |
| S009-T006 | ADR and sprint closure | TODO |

---

## Revision History

| Date | Change |
|------|--------|
| 2026-07-12 | Initial outline |
