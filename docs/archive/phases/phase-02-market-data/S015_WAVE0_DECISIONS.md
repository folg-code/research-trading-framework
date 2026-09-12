# Sprint 015 — Wave 0 Architecture Decisions (Continuous Futures Materialization)

## Metadata

```text
Task: S015-T001
Sprint: 015 — Continuous Futures Materialization
Status: ACCEPTED
Planned Start: 2026-07-14
Branch: sprint/continuous-futures-materialization
Direction: docs/planning/sprints/SPRINT_015.md
Depends on: SPRINT_011–012 merged to main (ADR-0014, ADR-0015)
Scope: four-layer preprocessing pipeline — contract → roll schedule → continuous → consumer read
```

---

## 0. Rationale

Sprint 011 imports one `provider_symbol` into one `instrument_id` (e.g. `NQU5` → `NQ.c.0`).
That pattern is correct for a vertical slice but unsuitable for long backtests:

```text
every strategy run  →  decode DBN  →  filter contract  →  roll  →  stitch  →  simulate
```

Continuous futures must be **materialized once** as a versioned research artifact. Raw DBN remains
immutable source of truth; contract datasets remain available for expiry and roll validation work.

Initial product scope: **NQ** trades from Databento DBN. ES and other products follow the same
contracts in later increments.

---

## 1. Four-layer data model

**Decision D-S015-01:** Adopt four explicit layers:

```text
Layer 1  Raw DBN              — immutable vendor archives (user_data/market_data)
Layer 2  Contract Dataset      — normalized per actual_contract (e.g. NQ.NQM5)
Layer 3  Roll Schedule         — versioned policy artifact
Layer 4  Continuous Dataset    — materialized trades / derived OHLCV for NQ.c.0
```

Consumers (Signal Research, Strategy Research) read **Layer 4 only**. They must not build Layer 4.

---

## 2. Raw DBN retention

**Decision D-S015-02:** Raw `.dbn` / `.dbn.zst` files are never deleted or overwritten after
contract normalization. They remain the source of truth for rebuilds after normalizer or roll-policy
changes.

Recommended layout (operator-managed under `user_data/`):

```text
user_data/market_data/NQ/databento/<dataset_id>/*.dbn.zst
```

---

## 3. Contract instrument identity

**Decision D-S015-03:** Each CME outright contract maps to a distinct framework instrument:

```text
NQ.NQM5   — June 2025 NQ outright
NQ.NQU5   — September 2025 NQ outright
ES.Z5     — (future) December ES outright
```

Pattern: `{PRODUCT}.{CONTRACT_CODE}` where `CONTRACT_CODE` is the Databento/CME symbol suffix
(`NQM5`, `NQU5`, …).

Continuous instrument remains:

```text
NQ.c.0    — continuous NQ (materialized output target)
```

Spread symbols (e.g. `NQU5-NQZ5`) are **excluded** from contract import in MVP.

---

## 4. Contract dataset partitioning

**Decision D-S015-04:** Contract trade datasets partition by **`session_date`** (CME RTH session
date), not UTC calendar day.

```text
normalized/NQ.NQM5/trades/tick/databento/<source_id>/v<N>/
  partitions/session_date=2025-03-14/trades.parquet
```

`session_date` is derived via `CmeEsRthSessionResolver` from `event_at`. Overnight Globex trades
belong to the session date defined by the resolver (same rules as Strategy Research session
breakdowns).

Existing Sprint 011 UTC `day=` partitions remain valid for legacy single-contract imports; new
contract workflow uses `session_date=` exclusively.

---

## 5. Contract Parquet schema extension

**Decision D-S015-05:** Contract-layer Parquet uses schema version `market-trade-contract-v1`:

```text
price, size, event_at, side, received_at?, trade_id?, sequence?   — canonical MarketTrade fields
actual_contract    — CME symbol (e.g. NQM5)
product            — root product (NQ)
session_date       — RTH session date (date)
source_file        — originating DBN filename
publisher_id?      — optional vendor field when present in DBN
```

Domain `MarketTrade` dataclass stays unchanged. Extra columns are a **storage projection** mapped
at read/write in infrastructure. Consumers that need contract lineage read from continuous dataset
columns or manifest.

---

## 6. Roll policy (MVP)

**Decision D-S015-06:** First supported roll policy slug: `volume-rth-close`.

```text
evaluation_session     = CME RTH close
metric                 = session volume on outright contracts
confirmation_sessions  = 1
switch_at              = next_session_open
price_adjustment       = none
```

Roll decisions use completed RTH sessions only — no intraday roll switches in MVP.

Open-interest roll, calendar roll and back-adjusted series are deferred.

---

## 7. Roll schedule artifact

**Decision D-S015-07:** Roll schedule is a **separate versioned artifact**, not embedded only in
continuous Parquet:

```text
continuous/schedules/NQ/volume-rth-close/v<N>/
  schedule.parquet
  manifest.json
```

Schedule rows include at minimum:

```text
product, valid_from_session, valid_to_session, active_contract, rule, evidence_volume, roll_id
```

The same schedule version is referenced by:

```text
continuous trades materialization
continuous OHLCV derivation
(future) orderflow bars
```

---

## 8. Continuous trades dataset

**Decision D-S015-08:** Materialized continuous trades use:

```text
DatasetId:
  instrument_id = NQ.c.0
  data_type     = trades
  timeframe     = tick
  provider      = continuous
  source_id     = volume-rth-close
```

Partition key: `session_date=`.

Per-row columns (in addition to trade fields):

```text
actual_contract, continuous_symbol, roll_id, is_roll_boundary, session_date
```

`continuous_symbol` MVP value: `NQ_CONT` (logical label; `instrument_id` remains `NQ.c.0`).

No single monolithic `NQ_continuous.parquet` file — partitioned by session for range reads and
incremental updates.

---

## 9. Continuous derived OHLCV

**Decision D-S015-09:** OHLCV 1m from continuous trades reuses Sprint 012 aggregation rules
(UTC left-labeled 1m, no zero-volume bars) and **the same roll schedule version** as trades.

```text
DatasetId:
  instrument_id = NQ.c.0
  data_type     = ohlcv
  timeframe     = 1m
  provider      = derived
  source_id     = volume-rth-close
```

Lineage records `roll_schedule_ref`, `continuous_trades_dataset_ref`, `derivation_version`.

---

## 10. Manifest and fingerprint

**Decision D-S015-10:** Every continuous dataset version ships `continuous_manifest.json`:

```json
{
  "product": "NQ",
  "schema": "trades",
  "roll_policy": { "type": "volume", "evaluation_session": "CME_RTH", ... },
  "price_adjustment": "none",
  "normalizer_version": "...",
  "continuous_builder_version": "...",
  "roll_schedule_version": "...",
  "source_fingerprint": "sha256:...",
  "created_at": "..."
}
```

Fingerprint inputs:

```text
source DBN file list + checksums
roll policy config
normalizer_version + builder_version
schema_version
requested date range
```

Unchanged fingerprint → reuse published dataset. Changed inputs → rebuild affected partitions.

---

## 11. Incremental build

**Decision D-S015-11:** Incremental append rebuilds a trailing window:

```text
rebuild_window_sessions = 10   (default, configurable)
```

When new `session_date` data arrives:

```text
rebuild last N sessions + new sessions
recompute roll schedule tail if needed
rewrite affected continuous partitions only
```

Full-history rebuild remains available via explicit `--rebuild-all` flag.

---

## 12. No back-adjustment for execution paths

**Decision D-S015-12:** Trade and orderflow facts used for simulation, stops, fills and footprint
analytics are **never** back-adjusted across roll boundaries.

Roll boundaries are explicit:

```text
is_roll_boundary = true
actual_contract  = <new front month>
```

A separate back-adjusted analytical series may be added later as a different `source_id` / adjustment
policy — not in Sprint 015.

---

## 13. Preprocessing CLI boundary

**Decision D-S015-13:** Continuous build is a dedicated preprocessing command:

```bash
uv run python scripts/market_data/build_continuous.py \
  --product NQ \
  --schema trades \
  --roll-policy volume-rth-close \
  --start 2024-01-01 --end 2025-12-31 \
  --storage-root user_data/storage
```

`run_strategy_research`, `run_signal_research` and dashboard builders:

```text
MUST NOT invoke build_continuous or contract import
MUST fail with clear error if required continuous DatasetRef is missing
MAY verify manifest fingerprint matches expectations (future)
```

---

## 14. Coexistence with Sprint 011 import

**Decision D-S015-14:** `import_databento_trades_archive` (single symbol → single instrument) remains
unchanged for backward compatibility and quick single-contract slices.

New workflows:

```text
import_databento_contract_trades   — multi-contract split → contract datasets
build_roll_schedule
materialize_continuous_trades
derive_continuous_ohlcv
build_continuous                    — orchestrates the above
```

---

## 15. Consumer read API

**Decision D-S015-15:** Consumers use existing query contracts:

```python
query_trades(QueryTradesRequest(dataset_ref=continuous_ref, ...))
query_historical(QueryHistoricalRequest(dataset_ref=continuous_ohlcv_ref, ...))
```

Contract-level reads use contract `DatasetRef` values (e.g. `NQ.NQM5|trades|...`).

No new SQL/DuckDB layer in MVP.

---

## 16. Spike objective (T001)

Validate roll policy on available local NQ DBN before Wave 1 contracts:

```text
tests/spike/run_continuous_roll_policy_spike.py
  — load normalized or raw DBN contract symbols
  — compute per-session volume by contract
  — emit proposed roll schedule table for manual review
```

Tier 2 / local only — not required in standard CI.

---

## Decision summary

| ID | Summary |
|----|---------|
| D-S015-01 | Four-layer model: raw → contract → roll → continuous |
| D-S015-02 | Raw DBN immutable |
| D-S015-03 | Contract instrument `NQ.<CODE>`; continuous `NQ.c.0` |
| D-S015-04 | Contract partitions by `session_date` |
| D-S015-05 | `market-trade-contract-v1` storage schema |
| D-S015-06 | MVP roll policy `volume-rth-close` |
| D-S015-07 | Roll schedule as versioned artifact |
| D-S015-08 | Continuous trades `provider=continuous` |
| D-S015-09 | Continuous OHLCV shares roll schedule |
| D-S015-10 | Manifest + fingerprint |
| D-S015-11 | Incremental rebuild window (default 10 sessions) |
| D-S015-12 | No back-adjust on trade/orderflow paths |
| D-S015-13 | `build_continuous` preprocessing only |
| D-S015-14 | Legacy single-contract import unchanged |
| D-S015-15 | Reuse `query_trades` / `query_historical` |

---

## Revision History

| Date | Change |
|------|--------|
| 2026-07-14 | Initial binding decisions D-S015-01 … D-S015-15 |
