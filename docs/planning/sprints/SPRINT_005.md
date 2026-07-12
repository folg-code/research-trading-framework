# Sprint 005 — Trading Calendar, Pivot Structure and Visual Inspection MVP

## Metadata

```text
Sprint: 005
Phase: Phase 4 — Market Analysis Components and Multitimeframe (second increment)
Status: PLANNED (Wave 0 complete)
Planned Start: TBD
Planned End: TBD
Sprint Goal Owner: Project Maintainer
Depends On: SPRINT_004 (COMPLETED, merged to main)
Sprint Branch: sprint/market-analysis-components
Direction: docs/planning/sprints/PHASE_4_5_SPRINT_DIRECTION.md
Architecture Sources:
  - docs/vision/ARCHITECTURE_FOUNDATIONS_UPDATED.md
  - docs/vision/MULTITIMEFRAME_MARKET_MODEL_ARCHITECTURE_UPDATED.md
  - docs/adr/ADR-MA-012-batch-multitimeframe-computation-with-polars.md
Prerequisite review: docs/planning/retrospectives/ARCHITECTURE_SIMPLIFICATION_REVIEW_S002_S003.md §5
```

---

## Sprint Goal

Deliver **three independently testable outcomes** without rewriting Sprint 004 MTF:

```text
Outcome A: CME ES RTH session resolution (batch)
Outcome B: Pivot Structure (point events + stateful HH/HL/LH/LL)
Outcome C: Local visual inspection of analysis results
```

End-to-end vertical slice:

```text
Published DatasetRef (1m)
    ↓
batch session metadata enrichment
    ↓
existing ResampleNode (1m → 5m) — unchanged from S004
    ↓
Pivot Structure on 5m
    ↓
lookahead-free detection on confirmation bar
    ↓
stateful structure outputs aligned to 1m (LAST_CLOSED_BAR)
    ↓
point-event outputs with explicit projection policy
    ↓
AnalysisFrame + pivot event columns
    ↓
local interactive chart (user_data/development)
```

Reuse from Sprint 004 (do not reimplement):

```text
ResampleNode, available_at, LAST_CLOSED_BAR, join_asof, AnalysisFrameAssembler
```

---

## Design Principles

Binding for implementation and review. See also `PHASE_4_5_SPRINT_DIRECTION.md`.

### Keep

```text
Batch calendar mapping (Polars Series in → DataFrame out) — no per-bar Python loops
Pivot emitted on detection bar; never back-written to pivot_at row
Explicit pivot_at / detected_at / available_at on outputs
HH/HL/LH/LL as integral Pivot Structure outputs (not separate component in S005)
Separate projection policy for point events vs stateful structure levels
Visualization consumes results only — no compute in chart layer
Sprint 004 MTF path unchanged
Behavior tests on timestamps/outputs, not internal class names
Outcome-scoped PRs (~100–400 lines)
```

### Reduce

```text
Session-boundary resampling
Full ETH / is_market_open calendar semantics
Holiday administration UI
MarketFieldReference / model evaluator
Signal Research / SignalOccurrence
Persistent derived datasets
Production dashboard / web app / chart DSL
Liquidity Sweep
Separate HH/HL component (unless classification needs independent lifecycle)
TA-Lib adapter (carry-forward)
Full TD-011 / TD-015 migration
```

### Calendar semantics (CME ES RTH)

MVP resolver scope:

```text
timestamp → trading_day
timestamp → session_id
timestamp → is_rth
```

**Not in MVP:** full `is_trading_minute` for 24h ES availability, missing-range integration, global calendar registry.

Distinguish explicitly:

```text
is_rth          — regular trading hours session membership
is_market_open  — deferred (ES trades outside RTH)
```

Recommended contract (batch-oriented):

```python
class TradingSessionResolver(Protocol):
    def resolve(self, timestamps: pl.Series) -> pl.DataFrame:
        ...
```

Output columns at minimum: `timestamp`, `trading_day`, `session_id`, `is_rth`.

---

## Pivot Structure semantics

Port or adapt **PivotDetectorBatched** semantics to framework conventions.

For row index `t` and `pivot_range = pr`:

```text
pivot_at = t - pr                    # historical pivot bar
detection at t uses bars [t-pr .. t] # all available at t
no reference to t+1, t+2, ...
```

Temporal fields:

| Field | Meaning |
|-------|---------|
| `pivot_at` | timestamp of historical pivot bar |
| `detected_at` | timestamp of confirmation bar (output index) |
| `available_at` | close of detection bar |

```text
pivotprice at t references high/low from bar at t - pivot_range
framework MUST NOT shift pivot result back to pivot_at and treat as earlier availability
```

Component id: `structure.pivot` (or domain-equivalent `Pivot Structure`).

Component description must state: *Pivot is emitted on the detection bar; refers to historical source bar `pivot_range` bars earlier; does not write back to historical pivot row.*

### HH / HL / LH / LL classification

Lookahead-free: compare new confirmed pivot to **previous confirmed pivot of same type** at detection row.

```text
new pivot high > previous confirmed pivot high → HH
new pivot high < previous confirmed pivot high → LH
(analogous for lows → LL / HL)
```

Classification at detection row only; no future pivots.

**Equal highs/lows (MVP policy):** local pivot may use `<=` / `>=`; HH/HL/LH/LL classification uses strict `>` / `<` — equal levels are valid pivots but **not** classified as HH/LH/HL/LL unless explicitly changed in spike.

**Simultaneous high+low at one row:** must be defined in contract (spike picks: precedence or emit-both — not implementation order dependent).

**`pivot_body`:** document precisely (rolling body extreme in pivot window); consider rename to `pivot_body_extreme` if clearer.

### Output kinds

**Point events (sparse):** e.g. `pivot`, `pivotprice`, `pivot_at`, `pivot_kind`, `detected_at` — tied to detection moment.

**Stateful levels (ffill after alignment):** `HH`, `LL`, `LH`, `HL`, optional `_idx` and `_shift_n` columns — last known structure level until next update.

### MTF projection

| Output kind | MVP policy |
|-------------|------------|
| Stateful HH/HL/LH/LL | `LAST_CLOSED_BAR` backward join_asof; forward propagation intentional |
| Point pivot event | Explicit policy required — recommend **`pivot_detected_now`** on first available 1m bar only (Variant A), or sparse event table (Variant C) documented in ADR |

Misalignment of point events on dense grid is a **representation** problem, not look-ahead — decide in T010 and test visually.

---

## Phase Alignment

Continues Phase 4 increment 2. Enables Phase 5 Signal Research path (Sprints 006–008).

**In Sprint 005:** calendar batch resolver, Pivot Structure, inspection chart, PRB-007 partial (CME ES RTH).

**Deferred:** sections in Design Principles § Reduce and `PHASE_4_5_SPRINT_DIRECTION.md` §7.

---

## Task Overview

| ID | Task | Status | Depends On |
|----|------|--------|------------|
| S005-T001 | Calendar adapter spike and decision note | DONE | — |
| S005-T002 | Batch `TradingSessionResolver` protocol | TODO | S005-T001 |
| S005-T003 | CME ES RTH resolver implementation | TODO | S005-T002 |
| S005-T004 | Session metadata enrichment on analysis path | TODO | S005-T003 |
| S005-T005 | Pivot Structure contract and output schema | TODO | — |
| S005-T006 | Port/adapt Pivot detector + implementation choice (Polars/NumPy) | TODO | S005-T005 |
| S005-T007 | Registry integration | TODO | S005-T006 |
| S005-T008 | Pivot timing metadata (`pivot_at`, `detected_at`, `available_at`) | TODO | S005-T006 |
| S005-T009 | Stateful HH/HL/LH/LL outputs and classification | TODO | S005-T008 |
| S005-T010 | MTF alignment: state vs point-event projection policy | TODO | S005-T009, S004-T011 |
| S005-T011 | Calendar behavior tests | TODO | S005-T004 |
| S005-T012 | Pivot temporal and classification tests | TODO | S005-T009 |
| S005-T013 | End-to-end `run_analysis` integration test | TODO | S005-T010 |
| S005-T014 | Local visual inspection prototype | TODO | S005-T013 |
| S005-T015 | ADR — Calendar + Pivot Structure semantics | TODO | S005-T001 |
| S005-T016 | Documentation and sprint closure | TODO | S005-T014, S005-T015 |
| S005-T017 | Optional TA-Lib adapter (carry-forward) | DEFERRED | — |
| S005-T018 | Columnar boundary spike (TD-011 / TD-015) | DEFERRED | — |

**Total:** 18 tasks (16 planned + 2 deferred)

---

## Tasks (summary)

### Wave 0 — T001

Calendar spike: adapter choice, CME ES RTH + DST fixture, batch mapping cost, decision note under `docs/planning/sprints/`.

**Done (2026-07-12):** `tests/spike/run_calendar_spike.py`, `S005_CALENDAR_SPIKE_AND_DECISIONS.md`.

### Wave 1 — T002–T004

Batch resolver protocol, CME ES adapter, session columns on analysis/frame path without mutating bars.

### Wave 2 — T005–T009

Pivot contract, detector port, registry, timing metadata, HH/HL/LH/LL state outputs, edge-case policies documented.

### Wave 3 — T010

MTF 5m → 1m: stateful outputs via existing alignment; point events per chosen projection policy; no S004 regression.

### Wave 4 — T011–T014

Calendar tests, pivot tests, e2e integration, `user_data/development/inspect_mtf_pivot.py` (or notebook) — OHLCV, optional EMA/ATR, RTH shading, pivot markers at `pivot_at` and `detected_at`, stateful levels.

### Wave 5 — T015–T016

One ADR (calendar MVP + pivot temporal semantics + event/state projection). Update MODULE_MAP, MARKET_ANALYSIS_MODULE, CURRENT_STATUS, PRB-007 note.

---

## PR Guidance

| PR | Outcome | Tasks |
|----|---------|-------|
| 1 | Calendar resolver | T001–T004 |
| 2 | Pivot Structure and classification | T005–T009 |
| 3 | MTF state alignment and event projection | T010 |
| 4 | Behavior tests and visual inspection | T011–T014 |
| 5 | ADR and documentation | T015–T016 |

Branch: `sprint/market-analysis-components` → squash PRs → sprint PR to `main`.

---

## Definition of Done

- [ ] T001–T016 DONE (T017–T018 deferred)
- [ ] Quality commands pass (`ruff`, `mypy`, `pytest`)
- [ ] Batch session resolver — no per-bar calendar loop in hot path
- [ ] Pivot detection lookahead-free; no back-write to `pivot_at`
- [ ] Stateful HH/HL/LH/LL align to 1m without look-ahead
- [ ] Point-event projection policy documented and tested
- [ ] Visual inspection script runs locally against fixture run
- [ ] Sprint 004 MTF tests still green
- [ ] ADR accepted; sprint PR to `main` (agent stops before merge)

---

## Sprint 006 Preview

Declarative Market Model and Signal Model — see `SPRINT_006.md`.

---

## Revision History

| Date | Change |
|------|--------|
| 2026-07-12 | Initial lean calendar + Pivot plan |
| 2026-07-12 | **Corrected direction:** visual inspection, batch calendar, full Pivot event/state semantics, HH/HL/LH/LL integral outputs (`PHASE_4_5_SPRINT_DIRECTION.md`) |
