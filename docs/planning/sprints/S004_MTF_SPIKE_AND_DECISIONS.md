# Sprint 004 — T001 MTF Spike and Architecture Decisions

## Metadata

```text
Task: S004-T001
Sprint: 004 — Multitimeframe Foundation MVP
Status: DONE (2026-07-12)
Branch: sprint/market-analysis-mtf
Spike script: tests/spike/run_mtf_polars_spike.py
Prerequisite review: docs/planning/retrospectives/ARCHITECTURE_SIMPLIFICATION_REVIEW_S002_S003.md
```

---

## 1. Spike objective

Validate the lean MTF vertical slice path before Wave 1 contracts:

```text
1m Polars frame
    → group_by_dynamic resample (5m)
    → HTF ATR (spike-only SMA)
    → available_at on HTF rows
    → join_asof backward to 1m evaluation grid
    → optional boundary: Polars → MarketBar → AnalysisDataView
```

Run:

```bash
uv run python tests/spike/run_mtf_polars_spike.py
uv run python tests/spike/run_mtf_polars_spike.py --json --scale-bars 98280
```

---

## 2. Spike results

Environment: Polars **1.42.1** (dev dependency for spike; runtime promotion in PR 2).

| Check | Result |
|-------|--------|
| OHLCV aggregation rules (manual 10:00-10:04 bucket) | PASS |
| Look-ahead at 10:37 uses HTF `available_at=10:35`, not incomplete 10:40 bar | PASS |
| Look-ahead at 10:35 / 10:40 boundaries | PASS |
| 45×1m → 9×5m lookahead fixture | PASS |
| 98_280×1m → 19_656×5m scale resample | PASS |

### Look-ahead evidence (MTF doc §8.1 scenario)

```text
Evaluation time:     2024-06-03 10:37 UTC
Current 5m interval: 10:35-10:40 (not closed at 10:37)
Joined HTF available_at: 10:35 (10:30-10:35 bar close)
```

Backward `join_asof` on `available_at` enforces **LAST_CLOSED_BAR** without forward-fill.

### OHLCV rules (fixed, not enum)

```text
open   = first
high   = max
low    = min
close  = last
volume = sum
```

Polars call:

```python
.group_by_dynamic("observed_at", every="5m", closed="left", label="left")
```

`available_at` on resampled rows: `observed_at + 5m` via existing `derive_bar_interval`.

### Partial bucket policy

```text
group_by_dynamic(closed=left, label=left) aligns buckets to UTC epoch boundaries
relative to the sorted frame. Trailing partial bucket at range end is emitted when
it contains at least one source row. Production ResampleSpec must document this
explicitly; no TradingCalendar required for fixed-duration MVP.
```

### Conversion boundary cost (TD-011, TD-015)

At **98_280** source 1m bars (~252 sessions × 390 bars):

| Step | Time | Notes |
|------|------|-------|
| Polars 1m → 5m resample | (in scale run, not isolated) | Columnar, acceptable |
| Polars 5m → `tuple[MarketBar]` | **~0.88 s** | Row iteration + Decimal construction |
| `MarketBar` → `AnalysisDataView` | **~0.11 s** | Map-of-arrays copy |
| Peak memory (conversion only) | **~20 MB** | 19_656 bars |

**Decision:** Sprint 004 keeps **boundary-only** conversion for existing NumPy ATR path. Do not extend `AnalysisDataView` API. Full `MarketFrame(pl.LazyFrame)` migration deferred to Sprint 005+ (see TD-015 repayment).

At production scale, query should eventually return columnar batch without materializing `list[MarketBar]` (TD-011).

---

## 3. Binding decisions for Wave 1+

| # | Decision |
|---|----------|
| D-S004-01 | **Polars** for resampling and alignment in production (`group_by_dynamic`, `join_asof`). Add to **runtime** `dependencies` in PR 2 (spike uses dev dep). |
| D-S004-02 | **`ResampleSpec`**: fixed UTC, `closed=left`, `label=left`; no `BoundaryPolicy` / `ResamplingPolicy` enums. |
| D-S004-03 | **`ResampleNode`**: explicit execution DAG node; **not** `ComponentRegistry` entry. |
| D-S004-04 | **Layered identity**: `ResampleIdentity`, `ComponentComputationIdentity`, `AlignmentIdentity` — alignment dimensions do not pollute computation cache keys. |
| D-S004-05 | **Request resolution** before planner: explicit `ResampleSpec` + input plan; planner dedupes and orders only. |
| D-S004-06 | **TradingCalendar deferred**; PRB-007 note in ADR-MA-012. Fixed UTC duration sufficient for 1m→5m/1h MVP. |
| D-S004-07 | **`AlignmentPolicy` enum** kept (`LAST_CLOSED_BAR` only in S004; reserve `INTRABAR`). |
| D-S004-08 | **Timeframe roles**: `source` from `DatasetRef`; `computation` on `ComponentRequest`; `evaluation` on run request — triple only on resolved execution types. |
| D-S004-09 | **No new view adapters** (`ResampledAnalysisDataView` rejected). |
| D-S004-10 | **One ADR** (ADR-MA-012) covers batch MTF; no separate calendar ADR in S004. |

---

## 4. Architecture Simplification Checklist (§5)

Completed against `ARCHITECTURE_SIMPLIFICATION_REVIEW_S002_S003.md`:

```text
[x] 5.1 Polars-first for new batch paths (resample/align)
[x] 5.2 MarketBar not required on Polars MTF path (only at component boundary)
[x] 5.3 No AnalysisDataView API extension
[x] 5.4 ExecutionState consolidation deferred
[x] 5.5 Registry unchanged until second backend
[x] 5.6 Layered identity, not wrapper proliferation
[x] 5.7 Remaining tasks outcome-based (see SPRINT_004.md)
[x] 5.8 One ADR planned (ADR-MA-012)
[x] 5.9 Heuristic applied: Polars ops not wrapped in multiple new public types
```

**Wave 1 is UNBLOCKED.**

---

## 5. Definition of Ready (Wave 0)

```text
[x] MTF spike prototype runs locally
[x] OHLCV rules and look-ahead validated
[x] Conversion boundary cost measured
[x] Architecture decisions recorded (this document)
[x] Simplification checklist complete
[x] Sprint branch sprint/market-analysis-mtf created from main
[x] Polars justified (dev for spike; runtime in PR 2)
```

---

## 6. Recommended PR sequence (unchanged)

```text
PR 1 — MTF request model and layered identity (T002-T005)
PR 2 — Polars resampling and ResampleNode DAG path (T006-T008) + polars runtime dep
PR 3 — Alignment, available_at, frame assembly (T009-T011)
PR 4 — Vertical slice and behavior tests (T012-T013)
PR 5 — ADR-MA-012 and documentation (T014-T015)
```

Spike artefacts may ship in PR 1 or a dedicated `sprint/market-analysis-mtf/mtf-spike-and-decisions` PR.

---

## 7. Open questions (none blocking Wave 1)

| Item | Disposition |
|------|-------------|
| Polars `group_by_dynamic` anchor vs session calendar | Deferred with TradingCalendar (Sprint 005+) |
| `MarketFrame` replaces `AnalysisDataView` | Sprint 005+; S004 uses single conversion boundary |
| ExecutionState merges Store/Workspace/Cache | Deferred (TD-014); no change in S004 unless touching executor |

---

## 8. Revision history

| Date | Change |
|------|--------|
| 2026-07-12 | Initial spike run and decisions; T001 complete |
