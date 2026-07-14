# Sprint 011 — T001 Archive Import Spike and Architecture Decisions

## Metadata

```text
Task: S011-T001
Sprint: 011 — Historical Archive Import Foundation
Status: COMPLETE
Planned Start: 2026-07-13
Branch: sprint/historical-archive-import--wave0-decisions
Spike script: tests/spike/run_databento_dbn_trades_spike.py (to be created in T001)
Direction: docs/planning/sprints/SPRINT_011.md
Depends on: SPRINT_002 merged to main; ROADMAP.md §6 Phase 2B, §6 Phase 2C
Scope: Databento DBN trades archive → canonical MarketTrade
```

---

## 0. Slice revision rationale

`ROADMAP.md` §15.4 recommended an **OHLCV DBN** first slice to validate archive workflow with the existing `MarketBar` model only.

**Revised decision:** the first vertical slice targets **Databento DBN trades** because:

- the project owner holds **trade (tick) archives**, not OHLCV DBN files,
- `ROADMAP.md` §14 already identifies **tick trades** as the primary futures expansion dataset,
- importing real data early surfaces partition volume, timestamp and symbology issues sooner.

Sprint 011 therefore delivers **Phase 2B** (archive import foundation) together with **Phase 2C.1** (`MarketTrade` datasets).

**Deferred to a follow-up increment (2B.2 / Sprint 012):** Databento DBN `ohlcv-1m` → `MarketBar`. Phase 2A CSV OHLCV remains the bar research path until then.

Terminology: Databento **trades** map to canonical **`MarketTrade`** — not a generic `Tick` type (`ROADMAP.md` §6 Phase 2C).

---

## 1. Spike objective

Validate the adapter boundary on a **local trades DBN** before Wave 1 contracts:

```text
local .dbn / .dbn.zst (trades schema)
    ↓
DatabentoDBNInspector (metadata, schema, symbols, time range, row estimate)
    ↓
chunked DatabentoDBNTradeReader
    ↓
MarketTrade (UTC event_at, price, size, side semantics, trade_id, sequence)
    ↓
TradeValidator
    ↓
partitioned Parquet write (day buckets)
    ↓
FileDatasetRegistry WORKING metadata + import manifest
```

Spike uses a **Tier 2** DBN file under `user_data/` — not committed to the repository.

Planned commands:

```bash
uv run python tests/spike/run_databento_dbn_trades_spike.py --path user_data/samples/nq_trades.dbn.zst
uv run python tests/spike/run_databento_dbn_trades_spike.py --path ... --json
```

CI must not require the spike file.

---

## 2. Dependency — Databento Python client

**Decision D-S011-01:** Add the official **`databento`** package as a **runtime** dependency in `pyproject.toml`.

Rules:

- no `databento` imports outside `infrastructure/importers/databento/`,
- domain and application layers depend on protocols and `MarketTrade` only,
- document version pin and licensing note in ADR-0014.

---

## 3. First DBN schema slice

**Decision D-S011-02:** Sprint 011 supports **one** Databento schema:

```text
trades   (primary — matches available Databento archives)
```

Out of scope for this sprint:

```text
ohlcv-1m, ohlcv-1s, mbp-*, definition, statistics, status
```

Inspector rejects unsupported DBN schemas with an explicit error.

---

## 4. Canonical MarketTrade (Phase 2C.1 MVP)

**Decision D-S011-03:** Introduce `MarketTrade` in `market/models/` with minimum fields:

```text
instrument_id      — framework Identifier (from explicit import mapping)
event_at           — UTC trade time (from DBN ts_event; spike confirms semantics)
received_at        — optional; populate when DBN provides ts_recv
price
size
side               — aggressor / taker side when available; nullable when vendor omits
trade_id           — provider trade id when available
sequence           — provider sequence when available
source_metadata    — small string map for vendor fields not promoted to columns
```

Do **not** introduce a generic `Tick` model.

---

## 5. Trade dataset identity

`DatasetId` currently requires a bar `Timeframe`. Trade datasets are event streams, not bars.

**Decision D-S011-04:** Extend `Timeframe` with canonical value:

```text
tick   — event-level trade datasets (non-bar)
```

Trade archive imports use:

```text
data_type  = trades
timeframe  = tick
provider   = databento
source_id  = operator-chosen stable slug (e.g. nq_cme_trades_2024)
```

OHLCV CSV datasets remain unchanged (`data_type=ohlcv`, `timeframe=1m`, etc.).

---

## 6. Partitioned Parquet layout (trade archives)

**Decision D-S011-05:** Partition key = **calendar day (UTC)** of `event_at`.

```text
normalized/<instrument>/trades/tick/<provider>/<source_id>/v<version>/
├── partitions/
│   ├── day=2019-01-02/trades.parquet
│   └── day=2019-01-03/trades.parquet
└── import_manifest.json
```

**Decision D-S011-06:** Phase 2A CSV OHLCV datasets **keep** single-file `bars.parquet` (ADR-0008). Trade archive imports use day partitions only. Repositories are **separate**:

```text
ParquetDatasetRepository        — bars (unchanged)
ParquetTradeDatasetRepository   — trades (new)
```

Avoid overloading bar read/write paths with trade schema branching in Sprint 011.

---

## 7. Import manifest and checksum

**Decision D-S011-07:** Every archive import persists `import_manifest.json`.

Minimum fields:

```text
manifest_version
source_path
source_format          — databento_dbn
source_checksum_sha256
databento_schema       — trades
symbol_mapping         — provider symbol → instrument_id
decode_row_count
rejected_row_count
imported_at_utc
normalization_version
```

**Decision D-S011-08:** Source checksum = **SHA-256** of raw archive bytes. Copy digest to `DatasetMetadata.checksum` on successful import.

---

## 8. Instrument and contract identity (MVP)

**Decision D-S011-09:** No symbology resolver or continuous futures in Sprint 011.

Import config supplies explicit mapping:

```text
provider_symbol  — e.g. NQH9 from DBN
instrument_id    — framework Identifier
```

Contract symbol preserved in manifest and `DatasetMetadata.lineage`.

---

## 9. Timestamp semantics

**Decision D-S011-10:** Spike confirms Databento `trades` schema semantics (Databento docs + `databento==0.81.0`):

```text
event_at     — ts_event (matching-engine receive time, UTC via to_df pretty_ts)
received_at  — ts_recv when present
price        — float via DBNStore.to_df(price_type=float); vendor fixed-point in raw DBN
size         — uint32 quantity
side         — Bid = buy aggressor, Ask = sell aggressor (map in S011-T011; nullable)
sequence     — venue message sequence when present
```

Spike script: `tests/spike/run_databento_dbn_trades_spike.py`. Helpers: `tests/spike/_databento_trades_spike.py`.

**Decision D-S011-16 (side mapping MVP):** Framework `side` stores normalized strings `buy` / `sell` / `unknown`.

Databento `trades` schema uses single-character codes (confirmed on `glbx-mdp3-20250713.trades.dbn.zst`):

```text
B  → buy   (buy aggressor)
A  → sell  (sell aggressor)
N  → unknown / not specified
```

---

## 10. Application workflow boundary

**Decision D-S011-11:** Dedicated workflow:

```text
import_databento_trades_archive(...)
query_trades(...)          — historical trade query by DatasetRef + time range
```

Do **not** overload `import_external_dataset` (CSV OHLCV) or `query_historical` (bars).

Shared reuse:

```text
FileDatasetRegistry / DatasetMetadata / DatasetRef
finalize_dataset
publish_dataset
ValidationResult pattern
```

---

## 11. Chunked decode vs resumability

**Decision D-S011-12:** Chunked iteration only. Full resume-after-failure deferred.

On failure: no `PUBLISHED` version; operator may delete `WORKING` version and re-import.

---

## 12. Test data tiers

**Decision D-S011-13:** CI uses mocked / synthetic decode (Tier 1).

```text
@pytest.mark.tier2_databento
```

Tier 2: contributor's local NQ (or ES) trades DBN under `user_data/`. Closes part of PRB-017 for trades; OHLCV Tier 2 remains separate.

---

## 13. CLI surface

**Decision D-S011-14:**

```text
scripts/databento/inspect_dbn.py    — schema-agnostic inspect
scripts/databento/import_trades.py  — primary import entrypoint this sprint
```

`import_bars.py` deferred until OHLCV DBN slice (2B.2).

---

## 14. Sprint branch and ADR

**Decision D-S011-15:**

```text
Sprint branch:  sprint/historical-archive-import
Task branches:  sprint/historical-archive-import/<task-slug>
ADR-0014:       Historical archive import + MarketTrade partitioned storage
```

---

## 15. Spike exit criteria (T001)

Implementation landed on branch `sprint/historical-archive-import--wave0-decisions`:

- [x] spike scripts added (`run_databento_dbn_trades_spike.py`, `_databento_trades_spike.py`)
- [x] `databento` runtime dependency added (`uv add databento`)
- [x] timestamp and side mapping documented (D-S011-10, D-S011-16)
- [x] **Tier 2 run** on contributor's local trades DBN (`glbx-mdp3-20250713.trades.dbn.zst` — 9/9 checks)
- [x] day partition signal verified (1 UTC day in 2000-row sample)
- [x] no blockers for S011-T002

Tier 2 command:

```bash
uv run python tests/spike/run_databento_dbn_trades_spike.py --path <your_trades.dbn.zst>
```

---

## Revision History

| Date | Change |
|------|--------|
| 2026-07-13 | Initial Wave 0 decisions (OHLCV slice) |
| 2026-07-13 | **Revised** first slice to Databento DBN `trades` → `MarketTrade` (available data) |
| 2026-07-13 | T001 spike scripts + `databento` dependency; Tier 2 run pending local DBN |
