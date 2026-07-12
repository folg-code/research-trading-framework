# Sprint 005 — T001 Calendar Spike and Architecture Decisions

## Metadata

```text
Task: S005-T001
Sprint: 005 — Trading Calendar, Pivot Structure and Visual Inspection MVP
Status: DONE (2026-07-12)
Branch: feat/calendar-spike
Spike script: tests/spike/run_calendar_spike.py
Direction: docs/planning/sprints/PHASE_4_5_SPRINT_DIRECTION.md
```

---

## 1. Spike objective

Validate batch CME ES **RTH** session resolution before Wave 1 contracts:

```text
pl.Series[timestamp UTC]
    → batch Polars resolver
    → trading_day, session_id, is_rth
```

Run:

```bash
uv run python tests/spike/run_calendar_spike.py
uv run python tests/spike/run_calendar_spike.py --json --scale-bars 98280
```

---

## 2. Spike results

Environment: Polars **1.42.1**, exchange_calendars **4.13.2** (dev only).

| Check | Result |
|-------|--------|
| RTH open 09:30 ET (EDT fixture) | PASS |
| Before open / at close boundaries | PASS |
| DST winter (EST) and spring (EDT) open | PASS |
| Saturday outside RTH | PASS |
| Batch vs loop equivalence (10_000 timestamps) | PASS |
| Batch faster than per-bar loop (~0.001s vs ~0.027s at 10k) | PASS |

### CMES Globex vs ES RTH

```text
exchange_calendars CMES session_minutes(2024-06-03) = 1440 minutes
```

CMES models **Globex** nearly-24h availability, **not** ES RTH. Using `CMES.is_open_on_minute` as `is_rth` would be incorrect for Sprint 005 semantics.

### ES RTH MVP definition (spike)

```text
Window:     09:30–16:00 America/New_York
Weekdays:   Monday–Friday
session_id: ES_RTH | OUTSIDE_RTH
is_rth:     bool — RTH membership only (not full market open / ETH)
```

`trading_day` = calendar date in `America/New_York` at the timestamp.

**Not in spike MVP:** CME holiday calendar on ES, early closes, ETH/Globex, `is_market_open`.

### Holiday mask (spike helper, optional Wave 1)

Spike includes `xnys_holiday_dates()` using **XNYS** sessions to derive US equity closed weekdays. Suitable as optional mask on `is_rth`; not required for boundary PASS set above.

### Batch vs loop

Production path must use **batch Polars** resolver. Per-bar loop retained in spike only for equivalence check.

At **98_280** timestamps (scale run optional): batch remains orders of magnitude faster than loop (same pattern as S004 conversion spike).

---

## 3. Binding decisions for Wave 1+

| # | Decision |
|---|----------|
| D-S005-01 | **`TradingSessionResolver`** protocol: `resolve(timestamps: pl.Series) -> pl.DataFrame` with columns `timestamp`, `trading_day`, `session_id`, `is_rth`. |
| D-S005-02 | **ES RTH MVP** = owned **09:30–16:00 America/New_York** window; **not** raw CMES Globex calendar. |
| D-S005-03 | **`is_rth` ≠ `is_market_open`**; ETH/Globex deferred. |
| D-S005-04 | **Batch-only** hot path; no `for bar in bars` session resolution in production. |
| D-S005-05 | **exchange_calendars** stays **dev dependency** for spike/holiday evaluation; promote to runtime only if Wave 1 PR adopts XNYS holiday mask. |
| D-S005-06 | Calendar enrichment is **not** a `ComponentRegistry` entry; adapter at infrastructure/application boundary. |
| D-S005-07 | **UTC `observed_at` on `MarketBar` unchanged**; calendar adds interpretation columns only. |
| D-S005-08 | **Architecture Simplification Checklist §5** — PASS (see spike JSON `checklist`). |

---

## 4. Architecture Simplification Checklist (§5)

| Item | Spike assessment |
|------|------------------|
| 5.1 Polars-first batch mapping | PASS — resolver is Polars-native |
| 5.2 MarketBar role limited | PASS — no change to bar storage |
| 5.3 No AnalysisDataView growth | PASS — session columns at enrichment/frame layer |
| 5.4 ExecutionState unchanged | PASS |
| 5.5 Registry unchanged | PASS |
| 5.6 Minimal protocol surface | PASS — one resolver protocol |
| 5.7 Outcome-based Wave 1 PR | PASS — calendar PR bundles T002–T004 |
| 5.8 One ADR in Wave 5 | Planned |
| 5.9 Heuristic applied | PASS — no calendar class hierarchy |

---

## 5. Wave 1 handoff

Next tasks:

```text
S005-T002  TradingSessionResolver protocol (time/)
S005-T003  CmeEsRthSessionResolver adapter (implements spike semantics)
S005-T004  Session metadata enrichment on analysis/frame path
```

Optional in T003: `use_equity_holidays: bool` backed by XNYS-derived closed dates.

---

## Revision History

| Date | Change |
|------|--------|
| 2026-07-12 | Initial spike complete; Wave 0 gate cleared |
