# Sprint 007 — Research-Enabling Analytical Set

## Metadata

```text
Sprint: 007
Phase: Phase 4 continuation
Status: SKIPPED (scope gate 2026-07-12 — proceed to Sprint 008)
Depends On: SPRINT_005 (minimum); SPRINT_006 recommended
Sprint Branch: TBD
Direction: docs/planning/sprints/PHASE_4_5_SPRINT_DIRECTION.md
```

---

## Sprint Goal

Extend the component catalog **only** with pieces needed for the first real research experiments — not a full TA library.

**Note:** Sprint 007 may be **partially skipped or trimmed** if Sprints 005–006 already suffice for the first Signal Research experiment (see direction doc §3).

**Scope gate (2026-07-12):** SKIPPED — minimum set satisfied; Sprint 008 started.

---

## Recommended components

### Features (new)

```text
slope
wick ratio
distance to level
```

### Structures (new)

```text
Session Range  — consumes Sprint 005 session metadata
```

### States (new)

```text
basic Trend State
```

### Already available (do not rebuild)

```text
ATR, EMA, Volatility State, Pivot Structure (+ HH/HL/LH/LL outputs)
```

---

## Session Range semantics

Outputs (examples): `session_open`, `session_high`, `session_low`, `session_close`, `session_range`, `session_completed`.

Distinguish **live/incomplete** session values from **final** session values — final high/low unavailable before session end.

---

## Explicitly deferred

```text
Liquidity Sweep — until Pivot, Session Range, levels, reclaim semantics exist
Separate HH/HL component — only if Pivot outputs insufficient
```

---

## Task Overview (draft)

| ID | Task | Status |
|----|------|--------|
| S007-T001 | Scope gate: confirm components required before Sprint 008 | DONE (skip) |
| S007-T002 | slope feature | TODO |
| S007-T003 | wick ratio feature | TODO |
| S007-T004 | distance to level feature | TODO |
| S007-T005 | Session Range structure | TODO |
| S007-T006 | Trend State component | TODO |
| S007-T007 | Visualization increment (session lines, structure labels) | TODO |
| S007-T008 | Tests and integration | TODO |
| S007-T009 | Documentation and closure | TODO |

Task list finalized after Sprint 006 retrospective and first research question definition.

---

## Revision History

| Date | Change |
|------|--------|
| 2026-07-12 | Initial outline — scope conditional on Sprint 008 readiness |
