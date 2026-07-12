# Sprint 008 — Signal Research Computation MVP

## Metadata

```text
Sprint: 008
Phase: Phase 5 — Signal Research MVP (first increment)
Status: PLANNED
Depends On: SPRINT_006 (required); SPRINT_005 (required); SPRINT_007 (optional subset)
Sprint Branch: TBD
Direction: docs/planning/sprints/PHASE_4_5_SPRINT_DIRECTION.md
```

---

## Sprint Goal

Run the first real **Signal Research** workflow end-to-end:

```text
Published Market Dataset
    ↓
Market Analysis
    ↓
Signal Model evaluation
    ↓
SignalOccurrence (Polars event table)
    ↓
Forward outcomes (return, MFE, MAE)
    ↓
Persistent Signal Research Dataset (immutable Parquet)
```

Start with scope: **`SIGNAL_MODEL_ONLY`**.

---

## SignalOccurrence payload (Polars)

```text
detected_at
available_at
signal_model_id
direction
reference_price
instrument
timeframe
source_dataset_ref
```

---

## Forward outcome contract (MVP — must be precise)

```text
reference_price: close at signal available_at
horizon:         N evaluation bars
forward_return:  close[t+N] / reference_price - 1
MFE:             best favorable excursion over horizon
MAE:             worst adverse excursion over horizon
```

Spike must resolve: next-bar inclusion, missing horizon, direction normalization, session crossing, overlapping signals.

---

## Persistent research dataset (MVP)

Single immutable Parquet dataset schema (examples):

```text
run_id, experiment_id, dataset_ref, signal_model_id,
detected_at, available_at, direction, reference_price,
horizon, forward_return, mfe, mae
```

Not a full research warehouse.

---

## Visualization increment

```text
signal markers on chart
forward outcome path for single signal
basic distribution / event frequency preview
```

---

## Task Overview (draft)

| ID | Task | Status |
|----|------|--------|
| S008-T001 | Signal research scope and outcome semantics spike | TODO |
| S008-T002 | SignalOccurrence materialization | TODO |
| S008-T003 | Forward outcome calculator | TODO |
| S008-T004 | Parquet research dataset writer | TODO |
| S008-T005 | Application workflow (signal_model_only) | TODO |
| S008-T006 | End-to-end integration test | TODO |
| S008-T007 | Visual inspection extension | TODO |
| S008-T008 | ADR and sprint closure | TODO |

---

## Revision History

| Date | Change |
|------|--------|
| 2026-07-12 | Initial outline |
