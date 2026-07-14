# Sprint 012 — Databento DBN OHLCV Archive Import (Phase 2B.2)

## Metadata

```text
Sprint: 012
Phase: Phase 2B.2 (archive import — OHLCV DBN → MarketBar)
Status: PLANNED
Planned Start: 2026-07-14
Planned End: TBD
Sprint Goal Owner: Project Maintainer
Depends On: SPRINT_011 (Phase 2B + 2C.1, COMPLETE on main)
Sprint Branch: sprint/databento-ohlcv-archive-import
Task branch convention: feat/ | fix/ | docs/ (separate prefix, not nested under sprint ref)
Wave 0 decisions: docs/planning/sprints/S012_WAVE0_DECISIONS.md
Architecture Sources:
  - docs/planning/ROADMAP.md (§6 Phase 2B, §15.4)
  - docs/adr/ADR-0014-historical-archive-import-and-market-trade-storage.md
  - docs/adr/ADR-0007-dataset-lifecycle-and-publication.md
  - docs/adr/ADR-0008-parquet-historical-storage.md
Initial adapter: Databento DBN (ohlcv-1m schema)
```

---

## 0. Slice choice

Sprint 011 delivered **trades** first because local archives were trade DBN files. Sprint 011 also established the reusable archive import foundation (manifest, checksum, lifecycle, Tier 1/Tier 2 tests).

Sprint 012 completes the **original Phase 2B bar archive slice** deferred as 2B.2:

```text
Databento DBN ohlcv-1m archive → MarketBar → bars.parquet → query_historical
```

**Out of scope:** trades (done), quotes (2C.2), resampling trades→bars, continuous futures, live adapters.

---

## 1. Sprint Goal

```text
Databento DBN OHLCV archive (ohlcv-1m)
    ↓
schema-aware inspect
    ↓
chunked decode
    ↓
schema mapping → canonical MarketBar
    ↓
OHLCV validation
    ↓
single-file bars.parquet (ADR-0008)
    ↓
import manifest + dataset lifecycle
    ↓
finalize → publish → query_historical
```

Success: import a local OHLCV DBN (or mocked Tier 1 decode), obtain a **PUBLISHED** `DatasetRef` (`data_type=ohlcv`, bar timeframe e.g. `1m`), query `MarketBar` through existing contracts.

---

## 2. Three Outcomes

| Outcome | Deliverable |
|---------|-------------|
| **A — Schema-aware adapter** | Multi-schema inspect; OHLCV chunked decode + mapper |
| **B — Bar persistence reuse** | `ParquetDatasetRepository` / `ParquetBarWriter` (unchanged layout) |
| **C — Import workflow** | `import_databento_ohlcv_archive` + `import_bars.py` + CI-safe tests |

---

## 3. Domain Boundary

```text
market/models/                  MarketBar (existing)
market/importers/               DatabentoOhlcvArchiveImportConfig
infrastructure/.../databento/   OHLCV reader + mapper; schema-aware inspector
application/market_data/        import_databento_ohlcv_archive
scripts/databento/              import_bars.py (new); inspect_dbn.py (extend)
```

Rules:

- no changes to trade import paths or `query_trades`,
- CSV `import_external_dataset` unchanged,
- `databento` imports remain infrastructure-only.

---

## 4. Reuse

```text
MarketBar, OhlcvBarValidator, ParquetDatasetRepository, ParquetBarWriter
FileDatasetRegistry, finalize_dataset, publish_dataset, query_historical
ImportManifest, compute_source_checksum_sha256, write_import_manifest
Tier 1 MockDBNStore pattern from tests/fixtures/databento/
```

---

## 5. In Scope

- `ohlcv-1m` schema only (first slice),
- `DatabentoOhlcvArchiveImportConfig`,
- schema-aware `DatabentoDBNInspector`,
- `DatabentoDBNOhlcvReader` + OHLCV → `MarketBar` mapper,
- `import_databento_ohlcv_archive` workflow,
- `scripts/databento/import_bars.py`,
- Tier 1 mocked tests; `@pytest.mark.tier2_databento` for local OHLCV DBN,
- extend `inspect_dbn.py` for trades + ohlcv,
- ADR-0015 (OHLCV DBN import increment).

---

## 6. Out of Scope

| Item | Target |
|------|--------|
| `ohlcv-1s`, `ohlcv-1h`, other DBN schemas | follow-up 2B.3 |
| Trades / quotes / order book | Sprint 011 / Phase 2C.2+ |
| Day partitions for OHLCV bars | ADR-0008 single-file bars.parquet |
| Bar resampling from trades | Phase 4B or derived dataset |
| Strategy Research | Phase 6A |

---

## 7. Task Summary

| ID | Task | Wave | Status | Depends On |
|----|------|------|--------|------------|
| S012-T001 | Wave 0 decisions + OHLCV DBN spike script | 0 | DONE | — |
| S012-T002 | `DatabentoOhlcvArchiveImportConfig` | 1 | DONE | S012-T001 |
| S012-T003 | Schema-aware `DatabentoDBNInspector` | 1 | DONE | S012-T001 |
| S012-T004 | `DatabentoDBNOhlcvReader` + mapper | 2 | PLANNED | S012-T002, S012-T003 |
| S012-T005 | `import_databento_ohlcv_archive` workflow | 3 | PLANNED | S012-T004 |
| S012-T006 | E2E: import → finalize → publish → query_historical | 4 | PLANNED | S012-T005 |
| S012-T007 | Tier 1 mocks + integration test | 4 | PLANNED | S012-T005 |
| S012-T008 | `import_bars.py` CLI + tests | 5 | PLANNED | S012-T005 |
| S012-T009 | Extend `inspect_dbn.py` for OHLCV | 5 | PLANNED | S012-T003 |
| S012-T010 | ADR-0015 | 6 | PLANNED | S012-T006 |
| S012-T011 | Update MODULE_MAP, DATA_WORKFLOWS, CURRENT_STATUS | 6 | PLANNED | S012-T007 |
| S012-T012 | Sprint review and closure | 6 | PLANNED | All preceding |

**Progress:** 3 / 12 tasks

---

## 8. Waves (summary)

| Wave | Focus |
|------|--------|
| 0 | OHLCV DBN spike; timestamp semantics; Wave 0 decisions |
| 1 | Import config; schema-aware inspector |
| 2 | OHLCV reader + MarketBar mapper |
| 3 | Import workflow + manifest |
| 4 | E2E lifecycle + mocked integration tests |
| 5 | CLI + inspect extension |
| 6 | ADR-0015, reference docs, closure |

---

## 9. Completion Criteria

- [ ] Local OHLCV DBN inspectable via API and `inspect_dbn.py`,
- [ ] Bars decode to `MarketBar` with OHLCV validation,
- [ ] Single-file `bars.parquet` + `query_historical` on published `DatasetRef`,
- [ ] Manifest + source checksum on every import,
- [ ] Trades import regression tests still pass,
- [ ] CI green without Tier 2 OHLCV DBN file,
- [ ] ADR-0015 accepted,
- [ ] No `databento` imports outside infrastructure.

---

## 10. References

- Wave 0: `S012_WAVE0_DECISIONS.md`
- Prior sprint: `SPRINT_011.md`, `ADR-0014`
- Roadmap: `ROADMAP.md` §6 Phase 2B, §15.4
