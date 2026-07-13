# Sprint 011 — Historical Archive Import Foundation (Phase 2B)

## Metadata

```text
Sprint: 011
Phase: Phase 2B — Historical Archive Import Foundation
Status: PLANNED (Roadmap Revision / Phase Entry Review)
Planned Start: TBD
Planned End: TBD
Sprint Goal Owner: Project Maintainer
Depends On: SPRINT_002 (Phase 2A OHLCV MVP, COMPLETE on main)
Sprint Branch: TBD — expected sprint/historical-archive-import or similar
Task branch convention: sprint/<sprint-slug>/<task-slug>
Architecture Sources:
  - docs/planning/ROADMAP.md (§6 Phase 2B, §15)
  - docs/reference/modules/DATA_MODULE_UPDATED.md
  - docs/agents/AGENTS_UPDATED.md
Initial adapter: Databento DBN
```

---

## 1. Sprint Goal

Deliver the first **archive import vertical slice** on Databento DBN OHLCV:

```text
Databento DBN OHLCV archive
    ↓
import inspection
    ↓
source decoding
    ↓
schema mapping → canonical MarketBar
    ↓
validation
    ↓
partitioned Parquet persistence
    ↓
dataset lifecycle (register → finalize → publish)
    ↓
published DatasetRef
    ↓
query through repository
```

Success means a contributor can import a DBN OHLCV archive locally, obtain a `PUBLISHED` `DatasetRef`, and query `MarketBar` records through existing Market Data contracts — without bypassing lifecycle or validation.

The sprint validates **provider-independent archive import architecture**. Databento is the first adapter, not the only intended outcome.

---

## 2. Phase Alignment

This sprint implements the recommended first slice of **Phase 2B** from `ROADMAP.md` §6 and §15.4.

It reuses Phase 2A lifecycle, `MarketBar`, validation and publication contracts where possible.

Completing Sprint 011 does **not** complete the Data Capability Track. Trades, quotes, options and live data remain Phase 2C–2E.

---

## 3. In Scope (MVP slice)

Domain logic in `src/`; thin CLI under `scripts/databento/`:

- `DatabentoDBNInspector` — archive metadata, schema summary, record counts,
- `DatabentoDBNReader` — chunked DBN OHLCV decoding,
- import manifest and source checksum,
- provider-specific schema mapping to canonical `MarketBar`,
- instrument mapping and futures contract identity (minimum needed for OHLCV bars),
- timestamp normalization to UTC,
- validation summary integrated with existing OHLCV validation,
- partitioned Parquet writer aligned with repository layout,
- wiring through existing dataset lifecycle to `DatasetRef` publication,
- unit tests with **Tier 1** deterministic fixtures,
- integration test path (may use **Tier 2** opt-in marker when sample DBN available locally).

Example CLI surface (interfaces only in sprint plan; exact names subject to Wave 0):

```text
scripts/databento/inspect_dbn.py
scripts/databento/import_bars.py
```

---

## 4. Out of Scope

Do **not** combine in Sprint 011:

- `MarketTrade` / `MarketQuote` import (Phase 2C),
- options snapshots (Phase 2D),
- orderflow or derived indicators (Phase 4B),
- continuous futures construction,
- full resumable import across all failure modes (chunked decode yes; full resume policy deferred),
- live Databento or CME adapters (Phase 2E — gated),
- Strategy Research or backtest engine (Phase 6A),
- replacing Sprint 002 CSV import workflow.

Future CLI placeholders (not this sprint):

```text
scripts/databento/import_trades.py
scripts/databento/import_options_snapshots.py
```

---

## 5. Dependencies

```text
Phase 2A — MarketBar, DatasetRef, lifecycle, Parquet repository (Sprint 002)
ROADMAP.md §15.1 — Tier 1 fixtures required; Tier 2 optional for integration
PRB-017 — representative datasets (document approach; full Tier 2 may follow implementation)
```

Runtime dependency: Databento Python client / DBN decoding library — to be confirmed in Wave 0 with ADR if new dependency.

---

## 6. Completion Criteria

- [ ] DBN OHLCV archive inspectable without manual binary inspection,
- [ ] decoded bars map to canonical `MarketBar` with explicit validation results,
- [ ] partitioned Parquet persisted and registered through lifecycle,
- [ ] published version immutable and queryable by `DatasetRef`,
- [ ] domain logic testable without CLI,
- [ ] CI passes with Tier 1 fixtures only,
- [ ] sprint ADR or amendment if archive import contract differs materially from CSV import.

---

## 7. Main Risks

- treating Databento as a one-off script instead of an adapter pattern,
- duplicating lifecycle logic outside existing application workflows,
- instrument / contract identity ambiguity for futures bars,
- scope creep into trades, quotes or continuous futures,
- committing large DBN samples to the repository (use Tier 2/3 locally).

---

## 8. Wave 0 Decisions (TBD)

Before task breakdown, resolve:

1. Databento dependency version and licensing constraints,
2. minimum DBN OHLCV schema variant for first slice,
3. partition key strategy (align with existing Parquet layout),
4. import manifest schema and checksum policy,
5. instrument mapping source (DBN symbology vs external definitions),
6. Tier 2 sample location and opt-in test marker name,
7. sprint integration branch name and ADR need.

Document in `docs/planning/sprints/S011_WAVE0_DECISIONS.md` when Wave 0 runs.

---

## 9. Task Breakdown

**Not yet defined.** Tasks will be added after Wave 0 decisions and phase entry approval.

Expected task themes:

```text
Wave 0 — decisions and adapter boundaries
Wave 1 — DBN inspect + decode + MarketBar mapping
Wave 2 — validation, partitioned persistence, lifecycle wiring
Wave 3 — CLI, integration tests, documentation
```

---

## 10. Post-Sprint Decision

After Sprint 011 closure, choose next increment:

```text
Option A — Phase 2C.1: Databento MarketTrade archive import
Option B — Phase 6A: OHLCV Strategy Research MVP
```

Decision criteria: research priority, adapter reuse maturity, and whether Strategy contracts need immediate validation on existing OHLCV only.

See `ROADMAP.md` §15.4.
