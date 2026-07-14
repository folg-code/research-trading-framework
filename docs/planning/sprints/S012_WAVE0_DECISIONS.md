# Sprint 012 — Wave 0 Architecture Decisions (Derived OHLCV from Trades)

## Metadata

```text
Task: S012-T001
Sprint: 012 — Derived OHLCV from Trades
Status: PLANNED
Planned Start: 2026-07-14
Branch: sprint/trades-to-ohlcv-derived
Direction: docs/planning/sprints/SPRINT_012.md
Depends on: SPRINT_011 merged to main (ADR-0014)
Scope: published trades (tick) → canonical MarketBar (1m)
Pivot: PR #100 closed — Databento OHLCV DBN import (2B.2) not needed for current vendor path
```

---

## 0. Rationale

Sprint 011 established Databento **trades** archive import because that is the available vendor data.

The project owner will fetch **tick trades only** from Databento and derive OHLCV internally. Direct Databento DBN `ohlcv-1m` import (roadmap increment 2B.2) is **deferred** until a concrete need for vendor-native bar archives exists.

Sprint 012 delivers the operational bar path:

```text
Published trades → aggregate → MarketBar → bars.parquet → query_historical
```

This aligns with `ROADMAP.md` §14 (Tick Trades as primary source) and `DATA_MODULE_UPDATED.md` (bars may be aggregated from trades).

---

## 1. Source dataset

**Decision D-S012-01:** Input is a **PUBLISHED** trades `DatasetRef`:

```text
data_type  = trades
timeframe  = tick
provider   = databento   (or other trade provider)
```

The derivation workflow reads trades through existing `query_trades` / `ParquetTradeDatasetRepository` contracts. It does **not** re-decode vendor archives.

---

## 2. Target dataset identity

**Decision D-S012-02:** Output is a new logical dataset:

```text
data_type  = ohlcv
timeframe  = 1m
provider   = derived
source_id  = operator-chosen stable slug (e.g. nq_1m_from_trades_2025)
```

First slice supports **`1m` only**. Other bar timeframes are follow-up increments.

---

## 3. Bucket semantics

**Decision D-S012-03:** Use **UTC left-labeled, closed-left** 1-minute buckets — aligned with Sprint 004 `ResampleSpec` and Phase 2A bar semantics:

```text
observed_at   — bucket start (interval start, UTC)
available_at  — observed_at + 1m
```

Trade `event_at` determines bucket membership. Empty buckets produce **no bar** (no zero-volume filler bars in MVP).

Spike: `tests/spike/run_trades_to_bars_spike.py`.

---

## 4. Aggregation rules

**Decision D-S012-04:** Within each bucket, aggregate trades as:

```text
open    = price of first trade  (by event_at, then sequence when present)
high    = max(price)
low     = min(price)
close   = price of last trade   (by event_at, then sequence when present)
volume  = sum(size)
```

Side is **not** used for OHLCV construction in this sprint.

Normalization version string: `trades-to-bars-v1`.

---

## 5. Persistence layout

**Decision D-S012-05:** Derived OHLCV uses **single-file** `bars.parquet` per dataset version (ADR-0008).

Do **not** use day partitions for derived bar datasets. Trade day partitions remain trades-only (ADR-0014).

Logical storage layer: **derived** (see `DATA_MODULE_UPDATED.md` §18.2).

---

## 6. Lineage

**Decision D-S012-06:** Persist lineage on derived `DatasetMetadata.lineage`:

```text
source_dataset_ref     — canonical string of source trades DatasetRef
source_data_type       — trades
derivation_method      — trades_to_bars
derivation_version     — trades-to-bars-v1
target_timeframe       — 1m
```

Lineage is required on every derived bar dataset version.

---

## 7. Application workflow

**Decision D-S012-07:** Dedicated workflow:

```text
derive_ohlcv_from_trades(...)
```

Reuse: `finalize_dataset` (bar path), `publish_dataset`, `query_historical`.

Do **not** overload `import_databento_trades_archive`, CSV `import_external_dataset`, or Market Analysis resample nodes.

---

## 8. Domain vs analysis boundary

**Decision D-S012-08:** Trades→bars aggregation is a **market data derivation** in `market/`, not a Market Analysis component.

`market_analysis.data.resample` remains OHLCV→OHLCV for on-the-fly analysis (Sprint 004). Persisted derived bars are a separate dataset lifecycle concern.

---

## 9. Test tiers

**Decision D-S012-09:** Tier 1 CI uses synthetic `MarketTrade` sequences (no DBN, no `user_data/`).

Optional Tier 2: derive from a locally imported trades dataset under `user_data/` when available — not required for CI.

---

## 10. Sprint branch and ADR

**Decision D-S012-10:**

```text
Sprint branch:  sprint/trades-to-ohlcv-derived
Task branches:  feat/ | fix/ | docs/
ADR-0015:       Derived OHLCV from trades
Deferred:       Databento DBN OHLCV direct import (2B.2)
```

---

## 11. Wave 0 exit criteria (T001)

- [x] pivot documented (SPRINT_012, PR #100 closed)
- [x] aggregation semantics documented (D-S012-03, D-S012-04)
- [x] spike script added (`run_trades_to_bars_spike.py`)
- [x] no blockers for S012-T002

---

## Revision History

| Date | Change |
|------|--------|
| 2026-07-14 | Initial Wave 0 — derived OHLCV from trades (pivot from 2B.2 OHLCV DBN) |
