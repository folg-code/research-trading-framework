# S010 Wave 0 — Binding Decisions (Signal Research Analytics)

> **Status:** LOCKED for Wave 0 spike validation (2026-07-12)  
> **Sprint:** SPRINT_010  
> **Spike:** `tests/spike/run_signal_research_analytics_spike.py`  
> **ADR:** ADR-0013 (draft → ACCEPTED in Wave 4)

Wave 0 spike must confirm these decisions on fixture runs before Wave 1 production code.

---

## D-S010-01 — Primary grain

Primary analytics grain = one **ForwardOutcome row**:

```text
entity_id × horizon_bars
```

---

## D-S010-02 — Default aggregate filter

Default aggregate filter = **`COMPLETE` only**.

Incomplete statuses contribute to sample diagnostics only.

---

## D-S010-03 — Hit rate

```text
hit_rate = count(forward_return > 0) / sample_size_complete
```

Returns are direction-normalized (ADR-0011).

---

## D-S010-04 — Flat return

`forward_return == 0` is **not** a hit.

---

## D-S010-05 — Timestamp basis is explicit

Grouping and time-derived dimensions use an explicit `AnalyticsTimestampBasis` — not an implicit column choice.

---

## D-S010-06 — Default timestamp basis

MVP default: **`AVAILABLE_AT`**.

---

## D-S010-07 — Normalized entity columns

Scope-aware analysis frame uses:

```text
entity_id
entity_kind   — SIGNAL_OCCURRENCE | MARKET_MODEL_OBSERVATION
```

not raw `occurrence_id` for all scopes.

---

## D-S010-08 — RTH grouping semantics

Grouping dimension **`RTH_MEMBERSHIP`** classifies:

```text
RTH | OUTSIDE_RTH
```

via `CmeEsRthSessionResolver` on the selected timestamp basis.

Not session instance, session date or trading-day identity.

---

## D-S010-09 — Time-of-day timezone

TIME_OF_DAY buckets use **exchange/session local timezone** (CME ES MVP).

UTC remains canonical in stored facts.

---

## D-S010-10 — Time-of-day bucket

MVP default bucket: **60 minutes**, left-closed right-open `[start, end)`.

---

## D-S010-11 — Minimum sample size visibility

Groups with `sample_size_complete < min_sample_size` **remain in output**.

---

## D-S010-12 — Metrics eligibility

When below minimum:

```text
metrics_eligible = false
aggregate metrics = null
```

---

## D-S010-13 — Conditional split column

Conditional comparison splits on:

```text
context_met_at_available_at
```

Both true and false populations preserved.

---

## D-S010-14 — Conditional deltas

Descriptive deltas included: **`true - false`**.

---

## D-S010-15 — No significance tests

No p-values, confidence intervals or significance labels in MVP.

---

## D-S010-16 — No DuckDB / SQL

Analytics MVP is Polars-only. No DuckDB or SQL query layer.

---

## D-S010-17 — Ephemeral analytics results

No new persisted analytics envelope or schema in MVP.

---

## D-S010-18 — Single-run application request

`AnalyzeSignalResearchRequest` accepts one `RunDatasetRef` only.

Multi-run deferred.

---

## D-S010-19 — Polars output format

Analytics outputs are validated **`pl.DataFrame`** schemas.

---

## D-S010-20 — Report layer boundary

Plotly HTML report is optional and **presentation-only**.

Report consumes `AnalyzeSignalResearchResult` — no Parquet reads, joins or metric computation in report layer.

---

## Spike validation checklist

```text
[ ] v1 SIGNAL_MODEL_ONLY — frame + RunSummary
[ ] v2 MARKET_MODEL_ONLY — entity_kind = MARKET_MODEL_OBSERVATION
[ ] v2 MARKET_AND_SIGNAL — conditional split partitions complete rows; false rows kept
[ ] COMPLETE filter + completion_rate diagnostics
[ ] RTH_MEMBERSHIP + TIME_OF_DAY non-trivial on ohlcv_sample_1m
[ ] analytics module imports exclude evaluate_models / outcome calculator
[ ] metrics_eligible false path visible in spike output
```

Spike command validates all items when `all_checks_pass=true`.

---

## Revision History

| Date | Change |
|------|--------|
| 2026-07-12 | Initial binding decisions D-S010-01 … D-S010-20 |
