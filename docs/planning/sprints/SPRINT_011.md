# Sprint 011 — Historical Archive Import Foundation

## Metadata

```text
Sprint: 011
Phase: Phase 2B + Phase 2C.1 (archive import + MarketTrade)
Status: COMPLETE
Planned Start: 2026-07-13
Planned End: 2026-07-14
Sprint Goal Owner: Project Maintainer
Depends On: SPRINT_002 (Phase 2A OHLCV MVP, COMPLETE on main)
Sprint Branch: sprint/historical-archive-import
Task branch convention: sprint/historical-archive-import/<task-slug>
Wave 0 decisions: docs/planning/sprints/S011_WAVE0_DECISIONS.md
Architecture Sources:
  - docs/planning/ROADMAP.md (§6 Phase 2B–2C, §14, §15)
  - docs/reference/modules/DATA_MODULE_UPDATED.md
  - docs/agents/AGENTS_UPDATED.md
  - docs/adr/ADR-0007-dataset-lifecycle.md
  - docs/adr/ADR-0008-parquet-historical-storage.md
Initial adapter: Databento DBN (trades schema)
```

---

## 0. Slice choice

`ROADMAP.md` §15.4 suggested OHLCV DBN first to reuse `MarketBar` without new models.

**This sprint targets trades** because the available Databento archives are **trade (tick) data**, which also matches §14 (tick trades as primary expansion).

```text
Phase 2B  — archive import workflow (inspect, manifest, checksum, chunked decode, lifecycle)
Phase 2C.1 — canonical MarketTrade + trade dataset persistence/query
```

**Deferred:** Databento DBN `ohlcv-1m` → `MarketBar` (follow-up increment 2B.2). Bar-based Signal Research continues on Phase 2A CSV OHLCV.

---

## 1. Sprint Goal

```text
Databento DBN trades archive
    ↓
import inspection
    ↓
chunked decode
    ↓
schema mapping → canonical MarketTrade
    ↓
trade validation
    ↓
day-partitioned Parquet persistence
    ↓
import manifest + dataset lifecycle
    ↓
finalize → publish → published DatasetRef
    ↓
query_trades
```

Success: import a local trades DBN, obtain a **PUBLISHED** `DatasetRef` (`data_type=trades`, `timeframe=tick`), query `MarketTrade` records through framework contracts.

---

## 2. Three Outcomes

| Outcome | Deliverable |
|---------|-------------|
| **A — Archive adapter** | DBN inspect + chunked trades decode in infrastructure |
| **B — MarketTrade persistence** | Domain model, day partitions, `ParquetTradeDatasetRepository` |
| **C — Import workflow** | `import_databento_trades_archive` + `query_trades` + CLI + CI-safe tests |

---

## 3. Domain Boundary

```text
market/models/             MarketTrade
market/validation/         trade validation contract
market/importers/          archive protocols, ImportManifest
market/repositories/       trade query protocol
infrastructure/.../databento/   SDK adapter only
infrastructure/storage/parquet/ trades writer + repository
application/market_data/   import + query workflows
scripts/databento/         thin CLI
```

Rules:

- no generic `Tick` type,
- no `databento` imports outside infrastructure,
- CSV OHLCV `import_external_dataset` / `query_historical` unchanged.

---

## 4. Reuse

```text
DatasetId, DatasetRef, DatasetMetadata, lifecycle (ADR-0007)
FileDatasetRegistry, finalize_dataset, publish_dataset
ValidationResult pattern
Parquet / pyarrow conventions from ADR-0008 (new trade column schema)
```

---

## 5. In Scope

- `MarketTrade` domain model,
- `Timeframe("tick")` for trade dataset identity,
- `databento` runtime dependency,
- `DatabentoDBNInspector`, `DatabentoDBNTradeReader`,
- trades → `MarketTrade` mapper (side / sequence / trade_id when present),
- `TradeValidator` MVP,
- day-partitioned `trades.parquet` per partition,
- `ParquetTradeDatasetRepository` + `query_trades`,
- `import_databento_trades_archive`,
- `import_manifest.json` + SHA-256 checksum,
- Tier 1 mocked tests; `@pytest.mark.tier2_databento` for local DBN,
- spike `tests/spike/run_databento_dbn_trades_spike.py`,
- CLI: `inspect_dbn.py`, `import_trades.py`,
- ADR-0014.

---

## 6. Out of Scope

| Item | Target |
|------|--------|
| `MarketQuote`, order book | Phase 2C.2+ |
| Databento DBN OHLCV → `MarketBar` | Phase 2B.2 / Sprint 012 |
| Options snapshots | Phase 2D |
| Orderflow features / footprint | Phase 4B |
| Continuous futures | Derived datasets later |
| Bar resampling from trades | Phase 4B or explicit derived dataset sprint |
| Full resume-after-failure | Deferred |
| Live adapters | Phase 2E (gated) |
| Strategy Research | Phase 6A |

---

## 7. Risks

| Risk | Mitigation |
|------|------------|
| Larger scope (2B + 2C.1) | Strict trades-only schema; no quotes/OHLCV in sprint |
| Trade volume / partition count | Day partitions; chunked decode; Tier 2 sample sized to days/weeks first |
| `Timeframe` extension | Single `tick` value; ADR-0014 documents identity rule |
| Side semantics vary by venue | Nullable side; document mapping; spike on real DBN |
| SDK leakage | Architecture boundary test |

---

## 8. Task Summary

| ID | Task | Wave | Status | Depends On |
|----|------|------|--------|------------|
| S011-T001 | Wave 0 spike on local trades DBN | 0 | DONE | — |
| S011-T002 | Archive import domain contracts + `ImportManifest` | 1 | DONE | S011-T001 |
| S011-T003 | Source checksum helper | 1 | DONE | S011-T002 |
| S011-T004 | `MarketTrade` domain model | 1 | DONE | S011-T001 |
| S011-T005 | `Timeframe` `tick` extension | 1 | DONE | S011-T004 |
| S011-T006 | Trade validation contract + validator | 1 | DONE | S011-T004 |
| S011-T007 | `DatabentoTradesArchiveImportConfig` | 1 | DONE | S011-T002, S011-T005 |
| S011-T008 | Add `databento` dependency | 2 | DONE | S011-T001 |
| S011-T009 | `DatabentoDBNInspector` | 2 | DONE | S011-T008, S011-T002 |
| S011-T010 | `DatabentoDBNTradeReader` (chunked) | 2 | DONE | S011-T008, S011-T007 |
| S011-T011 | DBN trades → `MarketTrade` mapper | 2 | DONE | S011-T010 |
| S011-T012 | Day partition path helpers | 3 | DONE | S011-T001 |
| S011-T013 | `ParquetTradeWriter` (stable schema) | 3 | DONE | S011-T004 |
| S011-T014 | `ParquetTradeDatasetRepository` | 3 | DONE | S011-T012, S011-T013 |
| S011-T015 | `HistoricalTradeQuery` + `query_trades` | 3 | DONE | S011-T014 |
| S011-T016 | `import_databento_trades_archive` workflow | 4 | DONE | S011-T011, S011-T006, S011-T014, S011-T003 |
| S011-T017 | Import manifest persistence | 4 | DONE | S011-T016 |
| S011-T018 | E2E: import → finalize → publish → query | 4 | DONE | S011-T016, S011-T015 |
| S011-T019 | Tier 1 mocks + synthetic trade rows | 5 | DONE | S011-T011 |
| S011-T020 | Unit tests (model, mapper, validator, manifest) | 5 | DONE | S011-T009–T017 |
| S011-T021 | CI integration test (mocked DBN decode) | 5 | DONE | S011-T018, S011-T019 |
| S011-T022 | `tier2_databento` marker + Tier 2 docs | 5 | DONE | S011-T021 |
| S011-T023 | `scripts/databento/inspect_dbn.py` | 5 | DONE | S011-T009 |
| S011-T024 | `scripts/databento/import_trades.py` | 5 | DONE | S011-T016 |
| S011-T025 | ADR-0014 | 6 | DONE | S011-T014, S011-T016 |
| S011-T026 | Update MODULE_MAP, DATA_WORKFLOWS, CURRENT_STATUS | 6 | DONE | S011-T021 |
| S011-T027 | Sprint review and closure | 6 | DONE | All preceding |

**Progress:** 27 / 27 tasks

---

## 9. Waves (summary)

| Wave | Focus |
|------|--------|
| 0 | Trades DBN spike; confirm timestamps and side fields |
| 1 | `MarketTrade`, `tick` timeframe, validation, archive contracts |
| 2 | Databento adapter (inspect, read, map) |
| 3 | Day-partitioned trade Parquet + repository + query |
| 4 | Import workflow + manifest + lifecycle e2e |
| 5 | Tests, Tier 2 docs, CLI |
| 6 | ADR-0014, reference docs, closure |

---

## 10. Completion Criteria

- [x] Local trades DBN inspectable via API and `inspect_dbn.py`,
- [x] Trades decode to `MarketTrade` with validation results,
- [x] Day-partitioned Parquet + `query_trades` on published `DatasetRef`,
- [x] Manifest + checksum on every import,
- [x] CSV OHLCV regression tests still pass,
- [x] CI green without Tier 2 DBN file,
- [x] ADR-0014 accepted,
- [x] No `databento` imports outside infrastructure.

---

## 11. Post-Sprint Decision

```text
Option A — Phase 2B.2: Databento DBN OHLCV → MarketBar (if OHLCV archives acquired)
Option B — Phase 4B prep: orderflow features on published trade datasets
Option C — Phase 6A: OHLCV Strategy Research (still on CSV / future bar archives)
```

---

## 12. References

- Wave 0: `S011_WAVE0_DECISIONS.md`
- Roadmap: `ROADMAP.md` §6 (2B, 2C), §14, §15.1
- IDEA-005 (Databento importer)

---

## 13. Sprint Closure (2026-07-14)

### Delivered outcomes

```text
A — Archive adapter     DatabentoDBNInspector, DatabentoDBNTradeReader, side mapper
B — MarketTrade storage day partitions, ParquetTradeWriter, ParquetTradeDatasetRepository
C — Import workflow       import_databento_trades_archive, query_trades, CLI, Tier 1/2 tests
```

### PRs (working → sprint branch)

| PR | Outcome |
|----|---------|
| #95 | Wave 3 — trade Parquet persistence + query_trades |
| #96 | Wave 4 — import workflow + manifest |
| #97 | Wave 5 — Tier 1 tests, CLI, tier2 docs |
| pending | Wave 6 — ADR-0014, reference docs, closure |

### Quality at closure

```text
458 tests passed
ruff / mypy / pre-commit green
CI excludes tier2_databento in integration job
```

### Deferred (explicit)

```text
Databento DBN OHLCV → MarketBar     Phase 2B.2
MarketQuote / order book              Phase 2C.2+
Resume-after-failure on import        later increment
Streaming validate-then-write         large-archive follow-up
```

### Post-sprint decision

See §11 — choose Phase 2B.2, 4B prep, or 6A before next sprint kickoff.

---

## 14. Revision History

| Date | Change |
|------|--------|
| 2026-07-13 | Initial sprint plan; Wave 0 trades slice |
| 2026-07-14 | Waves 0–6 complete; ADR-0014; sprint closure |
