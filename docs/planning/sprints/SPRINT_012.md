# Sprint 012 — Derived OHLCV from Trades (Phase 2B.3)

## Metadata

```text
Sprint: 012
Phase: Phase 2B.3 (derived dataset — published trades → MarketBar)
Status: PLANNED
Planned Start: 2026-07-14
Planned End: TBD
Sprint Goal Owner: Project Maintainer
Depends On: SPRINT_011 (Phase 2B + 2C.1, COMPLETE on main)
Sprint Branch: sprint/trades-to-ohlcv-derived
Task branch convention: feat/ | fix/ | docs/ (separate prefix, not nested under sprint ref)
Wave 0 decisions: docs/planning/sprints/S012_WAVE0_DECISIONS.md
Architecture Sources:
  - docs/planning/ROADMAP.md (§6 Phase 2B, §14 Research Data Strategy)
  - docs/adr/ADR-0014-historical-archive-import-and-market-trade-storage.md
  - docs/adr/ADR-0007-dataset-lifecycle-and-publication.md
  - docs/adr/ADR-0008-parquet-historical-storage.md
  - docs/reference/modules/DATA_MODULE_UPDATED.md (derived layer)
Pivot note: Databento DBN OHLCV direct import (2B.2) deferred — vendor path is trades-only.
```

---

## 0. Slice choice

Sprint 011 delivered **Databento trades** import. The project owner's Databento pipeline is **tick trades only**; OHLCV bars are produced internally by aggregation, not from vendor OHLCV DBN archives.

Sprint 012 delivers the first **derived bar dataset** increment:

```text
Published trades (tick) → aggregate → MarketBar → bars.parquet → query_historical
```

**Out of scope:** Databento OHLCV DBN import (2B.2, deferred), quotes (2C.2), orderflow analytics (4B), continuous futures, live adapters.

PR #100 (OHLCV DBN config/inspector) was **closed** without merge (2026-07-14) as part of this pivot.

---

## 1. Sprint Goal

```text
Published trades DatasetRef (tick, PUBLISHED)
    ↓
read trades (query_trades / trade repository)
    ↓
UTC left-labeled 1m bucket aggregation → MarketBar
    ↓
OHLCV validation (OhlcvBarValidator)
    ↓
single-file bars.parquet (ADR-0008)
    ↓
lineage metadata → source trades dataset
    ↓
finalize → publish → query_historical
```

Success: given a **PUBLISHED** trades dataset, produce a **PUBLISHED** derived `DatasetRef` (`data_type=ohlcv`, `timeframe=1m`, `provider=derived`) queryable through existing bar contracts.

---

## 2. Three Outcomes

| Outcome | Deliverable |
|---------|-------------|
| **A — Domain aggregation** | `TradesToBarsAggregator` + config contract |
| **B — Bar persistence reuse** | `ParquetDatasetRepository` / `ParquetBarWriter` (unchanged layout) |
| **C — Derivation workflow** | `derive_ohlcv_from_trades` + CLI + CI-safe tests |

---

## 3. Domain Boundary

```text
market/models/                  MarketTrade, MarketBar (existing)
market/derivation/              TradesToBarsAggregator, DerivedOhlcvFromTradesConfig
application/market_data/        derive_ohlcv_from_trades
infrastructure/storage/         ParquetDatasetRepository (bars), ParquetTradeDatasetRepository (read)
scripts/market_data/            derive_bars_from_trades.py (new)
```

Rules:

- no changes to Databento trade import paths,
- CSV `import_external_dataset` unchanged,
- aggregation logic lives in `market/` (domain), not in `market_analysis/` resample path,
- `market_analysis` OHLCV→OHLCV resample remains analysis-only (not dataset persistence).

---

## 4. Reuse

```text
MarketTrade, MarketBar, OhlcvBarValidator
ParquetDatasetRepository, ParquetBarWriter, ParquetTradeDatasetRepository
query_trades, HistoricalTradeQuery
FileDatasetRegistry, finalize_dataset, publish_dataset, query_historical
DatasetMetadata.lineage (existing field)
derive_bar_interval, BarTimestampSemantics.INTERVAL_START
```

---

## 5. In Scope

- `1m` target timeframe only (first slice),
- `DerivedOhlcvFromTradesConfig`,
- `TradesToBarsAggregator` (open=first, high=max, low=min, close=last, volume=sum),
- `derive_ohlcv_from_trades` workflow,
- lineage on derived dataset metadata,
- `scripts/market_data/derive_bars_from_trades.py`,
- Tier 1 tests with synthetic trades (extend or reuse `tests/fixtures/databento/` patterns),
- ADR-0015 (derived OHLCV from trades).

---

## 6. Out of Scope

| Item | Target |
|------|--------|
| Databento DBN OHLCV direct import | deferred 2B.2 (optional future) |
| `5m`, `1h`, other bar timeframes from trades | follow-up sprint |
| Quotes / order book | Phase 2C.2+ |
| Footprint, delta, CVD | Phase 4B |
| Persistent Market Analysis resample datasets | ADR-MA-007 follow-up |
| Strategy Research | Phase 6A |

---

## 7. Task Summary

| ID | Task | Wave | Status | Depends On |
|----|------|------|--------|------------|
| S012-T001 | Wave 0 decisions + trades→bars spike script | 0 | DONE | — |
| S012-T002 | `DerivedOhlcvFromTradesConfig` | 1 | DONE | S012-T001 |
| S012-T003 | `TradesToBarsAggregator` | 1 | DONE | S012-T001 |
| S012-T004 | `derive_ohlcv_from_trades` workflow | 2 | DONE | S012-T002, S012-T003 |
| S012-T005 | Lineage metadata on derived dataset | 2 | DONE | S012-T004 |
| S012-T006 | E2E: trades publish → derive → publish → query_historical | 3 | DONE | S012-T005 |
| S012-T007 | Unit tests (aggregator + workflow) | 3 | DONE | S012-T004 |
| S012-T008 | Integration test with synthetic trades dataset | 4 | DONE | S012-T006 |
| S012-T009 | `derive_bars_from_trades.py` CLI + tests | 4 | DONE | S012-T006 |
| S012-T010 | ADR-0015 | 5 | PLANNED | S012-T008 |
| S012-T011 | Update MODULE_MAP, DATA_WORKFLOWS, CURRENT_STATUS | 5 | PLANNED | S012-T008 |
| S012-T012 | Sprint review and closure | 5 | PLANNED | All preceding |

**Progress:** 9 / 12 tasks

---

## 8. Waves (summary)

| Wave | Focus |
|------|--------|
| 0 | Aggregation semantics; bucket rules; Wave 0 decisions; spike |
| 1 | Config + domain aggregator |
| 2 | Application workflow + lineage |
| 3 | E2E lifecycle + unit tests |
| 4 | Integration test + CLI |
| 5 | ADR-0015, reference docs, closure |

---

## 9. Completion Criteria

- [ ] Published trades dataset can be aggregated to `MarketBar` with OHLCV validation,
- [ ] Single-file `bars.parquet` + `query_historical` on published derived `DatasetRef`,
- [ ] Lineage points to source trades `DatasetRef` and derivation version,
- [ ] Trade import regression tests still pass,
- [ ] CI green without local DBN files,
- [ ] ADR-0015 accepted,
- [ ] No `databento` imports outside infrastructure.

---

## 10. References

- Wave 0: `S012_WAVE0_DECISIONS.md`
- Prior sprint: `SPRINT_011.md`, `ADR-0014`
- Roadmap: `ROADMAP.md` §6 Phase 2B, §14 Research Data Strategy
- Closed pivot PR: #100
