# Sprint 012 — Wave 0 Architecture Decisions (Phase 2B.2)

## Metadata

```text
Task: S012-T001
Sprint: 012 — Databento DBN OHLCV Archive Import
Status: PLANNED
Planned Start: 2026-07-14
Branch: sprint/databento-ohlcv-archive-import
Direction: docs/planning/sprints/SPRINT_012.md
Depends on: SPRINT_011 merged to main (ADR-0014)
Scope: Databento DBN ohlcv-1m → canonical MarketBar
```

---

## 0. Rationale

Sprint 011 established archive import patterns on **trades** because that was the available vendor data.

Sprint 012 completes the deferred **Phase 2B.2** slice:

```text
Databento DBN ohlcv-1m → MarketBar → bars.parquet → query_historical
```

This reuses Phase 2A bar persistence (ADR-0008) rather than introducing new storage layout.

---

## 1. DBN schema slice

**Decision D-S012-01:** Sprint 012 supports **one** Databento OHLCV schema:

```text
ohlcv-1m
```

Out of scope: `ohlcv-1s`, `ohlcv-1h`, `ohlcv-1d`, `mbp-*`, `trades` (already Sprint 011).

---

## 2. Persistence layout

**Decision D-S012-02:** OHLCV DBN imports use **single-file** `bars.parquet` per dataset version (ADR-0008).

Do **not** use day partitions for bar datasets. Trade day partitions remain trades-only (ADR-0014).

---

## 3. Timestamp semantics

**Decision D-S012-03:** Map Databento OHLCV `ts_event` to:

```text
observed_at   — bar interval start (UTC)
available_at  — observed_at + bar duration (1m for ohlcv-1m)
```

Spike script `tests/spike/run_databento_dbn_ohlcv_spike.py` validates on Tier 2 local DBN when available.

Bar timestamp semantics align with Phase 2A CSV import (`BarTimestampSemantics.INTERVAL_START`).

---

## 4. Dataset identity

**Decision D-S012-04:** OHLCV archive imports use:

```text
data_type  = ohlcv
timeframe  = 1m          (from schema / import config; must match DatasetId)
provider   = databento
source_id  = operator-chosen stable slug
```

---

## 5. Inspector boundary

**Decision D-S012-05:** Refactor `DatabentoDBNInspector` to support **multiple** vendor schemas for inspect-only:

```text
trades     — existing Sprint 011 behaviour
ohlcv-1m   — new Sprint 012 behaviour
```

Decode remains schema-specific (`DatabentoDBNTradeReader`, `DatabentoDBNOhlcvReader`).

`inspect_dbn.py` reports `vendor_schema` without failing on unsupported schemas at CLI level (decode/import workflows reject unsupported schemas explicitly).

---

## 6. Application workflow

**Decision D-S012-06:** Dedicated workflow:

```text
import_databento_ohlcv_archive(...)
```

Reuse: `query_historical`, `finalize_dataset` (bar path), `publish_dataset`, manifest store.

Do **not** overload `import_databento_trades_archive` or CSV `import_external_dataset`.

---

## 7. Manifest and checksum

**Decision D-S012-07:** Reuse `ImportManifest` from Sprint 011. Same source SHA-256 rules (ADR-0014 D-S011-07/08).

---

## 8. Test tiers

**Decision D-S012-08:** Tier 1 CI uses `MockDBNStore` with synthetic OHLCV rows (extend `tests/fixtures/databento/`).

Tier 2: `@pytest.mark.tier2_databento` with local OHLCV DBN under `user_data/` when contributor has one.

---

## 9. Sprint branch and ADR

**Decision D-S012-09:**

```text
Sprint branch:  sprint/databento-ohlcv-archive-import
Task branches:  feat/ | fix/ | docs/
ADR-0015:       Databento DBN OHLCV archive import
```

---

## 10. Wave 0 exit criteria (T001)

- [x] spike script stub added (`run_databento_dbn_ohlcv_spike.py`)
- [x] timestamp mapping documented (D-S012-03)
- [ ] Tier 2 run pending local OHLCV DBN (optional; not blocking Wave 1 contracts)
- [x] no blockers for S012-T002

---

## Revision History

| Date | Change |
|------|--------|
| 2026-07-14 | Initial Wave 0 decisions for Phase 2B.2 OHLCV DBN slice |
