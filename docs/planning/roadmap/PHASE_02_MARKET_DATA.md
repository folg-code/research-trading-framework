# Phase 2 Family — Market Data Capability

```text
Status: 2A COMPLETE / 2B, 2C.2, 2C.3, 2D PLANNED / 2E GATED
```

Full detail for `ROADMAP.md` §6 — this is the LIVE, canonically-updated location for this
phase; `ROADMAP.md` carries only a short pointer stub under the same section number.

**This file is expected to keep changing** as the phase progresses (Wave 0 decisions, sprint
openings, status flips). Unlike `docs/planning/ROADMAP_COMPLETED_PHASES.md` — which is
frozen history — edits to this phase's detail happen **HERE**, not by re-inflating the
`ROADMAP.md` stub.

Internal heading numbering is preserved exactly as it was in `ROADMAP.md`, so a citation of
the form `roadmap/PHASE_02_MARKET_DATA.md §6` resolves, matching the convention already used
in `ROADMAP_COMPLETED_PHASES.md`.

---

# 6. Market Data Capability — Phase 2 Family

## Historical label

Roadmap sections historically titled **Phase 2 — Market Data MVP** refer to **Phase 2A** below. Sprint 002 scope is unchanged. Completion of Phase 2A does **not** close the Data Capability Track.

---

## Phase 2A — OHLCV Market Data MVP (COMPLETE)

**Delivered:** Sprint 002 on `main`.

### Purpose

Deliver the first complete, reproducible **OHLCV-only** Market Data vertical slice.

### Primary Flow

```text
External OHLCV File
        ↓
Inspect
        ↓
Normalize to UTC
        ↓
Validate
        ↓
Persist in Parquet
        ↓
Register Dataset Version
        ↓
Finalize
        ↓
Publish
        ↓
Query Through Repository
```

## Expected Capabilities

- `Instrument`,
- `Timeframe`,
- `MarketBar`,
- `DatasetId`,
- `DatasetRef`,
- `DatasetMetadata`,
- dataset lifecycle,
- external file inspection,
- CSV or Parquet import,
- timestamp normalization,
- OHLCV validation,
- Parquet writer and repository,
- dataset registry,
- finalization,
- publication,
- historical query.

## Completion Criteria

- one OHLCV dataset can be imported end to end,
- provider-specific schema is normalized at the boundary,
- all timestamps are timezone-aware UTC,
- invalid OHLCV data produces explicit validation results,
- dataset identity is independent from file path,
- `WORKING → FINALIZED → PUBLISHED` is explicit,
- published versions are immutable,
- consumers query by `DatasetRef`,
- direct Parquet access from Research and Strategy is unnecessary,
- integration tests cover storage and publication.

## Dependencies

- repository foundation,
- core time models,
- configuration loading.

## Active Sprint

Sprint 002 implemented the MVP vertical slice:

```text
docs/planning/sprints/SPRINT_002.md
```

**Status:** COMPLETED on `main` (Sprint 002).

## Beyond Phase 2A

Phase 2A delivered the OHLCV import and publication pipeline only. Further source datasets and archive import are **Phase 2B–2E** and **§14 Research Data Strategy**. Sprint 002 history is not revised.

## Main Risks

- ambiguous dataset identity,
- mixing storage paths with domain identity,
- hidden mutation of published datasets,
- incorrect gap assumptions,
- excessive small files,
- premature support for every provider and data type.

## Out of Scope (Phase 2A / Sprint 002)

The following were out of scope for the OHLCV vertical slice. They are **not rejected**; see Phase 2B–2E and **§14**:

- live ingestion and provider synchronization,
- continuous futures construction,
- tick trades, quotes, DOM and options data,
- automatic missing-range fetching during Research.

---

## Phase 2B — Historical Archive Import Foundation (PLANNED)

**Initial adapter:** Databento DBN. **Architectural outcome:** provider-independent archive import workflow (not a one-off script).

### Target flow

```text
Vendor archive
    ↓
Import inspection
    ↓
Source decoding
    ↓
Provider-specific schema mapping
    ↓
Canonical market facts
    ↓
Validation
    ↓
Partitioned persistence
    ↓
Dataset lifecycle
    ↓
Published DatasetRef
```

### Capability scope

- archive inspection and import manifest,
- schema and instrument mapping, futures contract identity,
- timestamp normalization, validation summary,
- chunked decoding; resumable import where practical,
- partitioned Parquet, publication as `DatasetRef`,
- domain logic in `src/`; thin CLI under `scripts/databento/`.

### First vertical slice (recommended Sprint 011)

```text
Databento DBN OHLCV archive
    ↓
inspection → decoding → canonical MarketBar
    ↓
validation → partitioned Parquet → published DatasetRef
```

Do **not** combine in one sprint: trades, quotes, options, orderflow, continuous futures, full resumability, or live adapters.

### Dependencies

- Phase 2A lifecycle and repository contracts.

---

## Phase 2C — Trades and Quotes (PLANNED)

Do **not** use a single ambiguous `Tick` model. Canonical types:

```text
MarketTrade
MarketQuote
OrderBookUpdate   (only when justified)
```

Suggested increments:

```text
Phase 2C.1 — MarketTrade datasets
Phase 2C.2 — MarketQuote datasets
Phase 2C.3 — Order-book data (MBO/MBP only when justified)
Phase 2C.4 — Continuous futures materialization (Sprint 015)
```

Example `MarketTrade` fields: instrument, `event_at`, price, size, aggressor/side semantics, trade_id, sequence, flags, source metadata.

Default partitioning: by day (trades, quotes) for legacy single-contract import; **by `session_date` for contract-layer datasets** (Sprint 015).

### Phase 2C.4 — Continuous Futures Materialization (COMPLETE — Sprint 015)

Materialize versioned continuous datasets from normalized contract trades:

```text
Raw DBN → contract datasets → roll schedule → continuous trades → derived continuous OHLCV
```

Consumers (`run_strategy_research`, `run_signal_research`) read published continuous `DatasetRef`
values only — no runtime roll construction.

ADR: ADR-0018 (ACCEPTED). See `SPRINT_015.md`, `S015_WAVE0_DECISIONS.md`. Delivered on `main` (PR #123).

MBO/MBP are **not** in the first trades sprint scope.

### Dependencies

- Phase 2B archive import patterns (recommended).

---

## Phase 2D — Options Snapshot Data (PLANNED)

Store vendor-provided option facts; do not assume every provider supplies Greeks, OI, volume, or quotes in every dataset.

Example models:

```text
OptionContractMetadata
OptionContractQuote
OptionsSnapshot
```

Fields may include: underlying, option symbol, expiration, strike, option type, snapshot time, bid/ask/last, volume, open interest, IV, Greeks (when available), source fields, quality flags.

Preferred source: chain snapshots (~1m), not raw option tick streams (**§14**).

Initial provider direction: Intrinio (**§14**).

---

## Phase 2E — Live Market Data (GATED)

Concrete paid live CME adapters are deferred until **§15.2 Live Market Data Entry Gate** conditions are met.

Until then: historical research via archives; replay via published datasets; live **contracts** may exist without expensive adapter implementation.
