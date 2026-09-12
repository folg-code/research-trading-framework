# Market Data — idea entries

Return to the [Idea Inbox index](../IDEA_INBOX.md).

# 5. Market Data

<a id="idea-005"></a>
## IDEA-005 — Databento DBN Importer

```text
Status: INBOX → candidate for Sprint 011 (Phase 2B)
Category: Market Data
Added: 2026-06-19
Last reviewed: 2026-07-12
```

### Summary

Import Databento DBN archives through provider-independent archive import contracts. First slice: **DBN OHLCV → canonical MarketBar** (Phase 2B). Later: trades (**Phase 2C.1**).

### Potential Value

High-quality futures data and efficient archive ingestion; validates archive workflow before new fact models.

### Dependencies

- Phase 2A lifecycle and repository (COMPLETE),
- import inspection and manifest,
- schema mapping to canonical models,
- partitioned Parquet persistence.

### Promotion Criteria

Promote as Sprint 011 when Roadmap Revision / Phase Entry Review is complete. See `ROADMAP.md` §6, §15.4 and `SPRINT_011.md`.

---

<a id="idea-006"></a>
## IDEA-006 — Historical Provider Synchronization

```text
Status: INBOX
Category: Market Data
Added: 2026-06-19
```

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
Status: PROMOTED → Sprint 015
Category: Market Data
Added: 2026-06-19
Promoted: 2026-07-14
```

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

### Promotion Criteria

Contract-level futures datasets are stable. — **Sprint 011 trades import on main satisfies input path; Sprint 015 extends to multi-contract materialization.**

---

<a id="idea-008"></a>
## IDEA-008 — Data Quality Dashboard

```text
Status: INBOX
Category: Market Data / Observability
Added: 2026-06-19
```

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
