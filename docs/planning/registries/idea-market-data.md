# Market Data — idea entries

Return to the [Idea Inbox index](../IDEA_INBOX.md).

# 5. Market Data

<a id="idea-005"></a>
## IDEA-005 — Databento DBN Importer

```text
Status: IMPLEMENTED
Category: Market Data
Added: 2026-06-19
Last reviewed: 2026-07-12
```

### Review (2026-09-12)

The DBN archive importer is implemented for the Databento `trades` schema via `import_databento_trades_archive`; derived OHLCV is a separate downstream workflow. The earlier "DBN OHLCV first" sequence below was superseded by the accepted trades-first slice. See the [Market Data workflow](../../reference/workflows/MARKET_DATA.md) and [Sprint 011 record](../../archive/phases/phase-02-market-data/SPRINT_011.md). Direct DBN OHLCV decoding is not implied by this disposition.

### Summary

Import Databento DBN archives through provider-independent archive import
contracts. The delivered slice reads DBN `trades` into canonical trades;
derived OHLCV is built by a separate workflow. The original direct DBN OHLCV
first-slice proposal was superseded.

### Potential Value

High-quality futures data and efficient archive ingestion; validates archive workflow before new fact models.

### Dependencies

- Phase 2A lifecycle and repository (COMPLETE),
- import inspection and manifest,
- schema mapping to canonical models,
- partitioned Parquet persistence.

### Delivery evidence

[Sprint 011](../../archive/phases/phase-02-market-data/SPRINT_011.md)
delivered the DBN trades archive path. The [current Market Data workflow](../../reference/workflows/MARKET_DATA.md)
states its supported schema and separate derived-OHLCV path.

---

<a id="idea-006"></a>
## IDEA-006 — Historical Provider Synchronization

```text
Status: INBOX
Category: Market Data
Added: 2026-06-19
```

### Review (2026-09-12)

The Binance historical importer implements explicit paginated import, but there is no local-coverage resolver that fetches only missing ranges under a declared policy. This idea remains open; see [Market Data Future](../../vision/MARKET_DATA_FUTURE.md).

### Summary

Resolve local coverage and fetch only missing historical ranges.

### Potential Value

Automates dataset preparation while preserving explicit policies.

### Dependencies

- dataset registry,
- missing-range calculator,
- Trading Calendar,
- provider adapter.

### Promotion Criteria

Phase 2A (OHLCV MVP) completed; archive import foundation (2B) or provider sync may follow per `ROADMAP.md` §6.

---

<a id="idea-007"></a>
## IDEA-007 — Continuous Futures Builder

```text
Status: IMPLEMENTED
Category: Market Data
Added: 2026-06-19
Promoted: 2026-07-14
```

### Review (2026-09-12)

The continuous-futures builder is delivered: contract trades, roll schedule, continuous trades and derived OHLCV have explicit lineage. See the [Market Data workflow](../../reference/workflows/MARKET_DATA.md), [ADR-0018](../../adr/ADR-0018-continuous-futures-materialization.md) and [Sprint 015](../../archive/phases/phase-02-market-data/SPRINT_015.md). Other roll/adjustment policies remain future work, not a reason to leave this original idea in the inbox.

### Summary

Build continuous futures datasets from explicit contract datasets.

Sprint 015 (`SPRINT_015.md`, ADR-0018 ACCEPTED) delivers four-layer materialization:
raw DBN → contract datasets → roll schedule → continuous trades + derived OHLCV.

### Potential Value

Supports long-term NQ, ES and other futures research.

### Main Questions

- calendar, volume or open-interest roll — **MVP: volume @ RTH close**
- adjusted or unadjusted series — **MVP: unadjusted trades; back-adjust deferred**
- Research use by purpose — **continuous for long backtests; contract datasets for roll validation**

### Dependencies

- contract metadata,
- contract dataset identity,
- roll policies,
- derived dataset lineage.

### Delivery evidence

Sprint 011 supplied contract trades; [Sprint 015](../../archive/phases/phase-02-market-data/SPRINT_015.md)
delivered multi-contract materialization. [ADR-0018](../../adr/ADR-0018-continuous-futures-materialization.md)
records the accepted roll and lineage semantics.

---

<a id="idea-008"></a>
## IDEA-008 — Data Quality Dashboard

```text
Status: INBOX
Category: Market Data / Observability
Added: 2026-06-19
```

### Review (2026-09-12)

The existing public research dashboard can show selected dataset identity and coverage, but it is not a Market Data quality dashboard for gaps, duplicates, partition health and validation state. This idea remains open.

### Summary

Visualize:

- coverage,
- gaps,
- duplicate counts,
- validation status,
- partition health,
- dataset versions.

### Promotion Criteria

Dataset registry and validation reports produce stable metadata.

---

<a id="idea-009"></a>
## IDEA-009 — Automated Partition Compaction Policy

```text
Status: INBOX
Category: Storage
Added: 2026-06-19
```

### Summary

Select and execute compaction based on small-file count, size and partition age.

### Promotion Criteria

Live or incremental ingestion produces a demonstrated small-file problem.

---
