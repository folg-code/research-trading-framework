# ADR-0013 — Signal Research Analytics Boundary

## Status

ACCEPTED

## Context

Sprints 008–009 deliver Signal Research **computation and persistence** (ADR-0011, ADR-0012).
Phase 5 closes with Sprint 010 **analytics on stored runs** without recompute.

Wave 0 spike (`tests/spike/run_signal_research_analytics_spike.py`) validates binding
decisions in `docs/planning/sprints/S010_WAVE0_DECISIONS.md`.

Key boundary: analytics interprets immutable Parquet fact tables; it must not invoke model
evaluation, materialization or outcome calculation.

## Decision

### Read-only analytics

Analytics loads runs exclusively via `SignalResearchDatasetRepository.read`.

Analytics must not:

```text
write or mutate run storage
call evaluate_models
materialize occurrences or observations
align context facts
recompute forward outcomes
```

Fixture run production in spikes/tests may use `run_signal_research`; production analytics
modules must not.

### Primary grain

One **ForwardOutcome row**:

```text
entity_id × horizon_bars
```

Normalized analysis frame columns include `entity_id`, `entity_kind`, outcome metrics and
optional `context_met_at_available_at`.

### Default aggregate filter

```text
outcome_status == COMPLETE   — for mean / median / hit rate / MFE / MAE aggregates
all statuses               — sample diagnostics only
```

Summaries expose `sample_size_total`, `sample_size_complete`, `sample_size_incomplete`,
`completion_rate`, `minimum_required`, `metrics_eligible`.

When `sample_size_complete < min_sample_size`: group row remains; metrics are null;
`metrics_eligible = false`.

### Hit rate

```text
hit_rate = count(forward_return > 0) / sample_size_complete
```

Flat returns (`forward_return == 0`) are not hits. Returns are direction-normalized (ADR-0011).

### Timestamp basis

Explicit `AnalyticsTimestampBasis`:

```text
AVAILABLE_AT   — MVP default
DETECTED_AT
```

Grouping dimensions derive from the selected basis. Result metadata records the basis used.

### Grouping dimensions (MVP)

Fixed enum — not a dynamic dimension framework:

```text
HORIZON
RTH_MEMBERSHIP     — RTH | OUTSIDE_RTH via CmeEsRthSessionResolver
TIME_OF_DAY        — 60-minute buckets in exchange-local time
CALENDAR_MONTH     — optional; first to cut under scope pressure
CONTEXT_MET        — grouped summaries only
```

### Conditional comparison

For `MARKET_AND_SIGNAL` only — split on `context_met_at_available_at`.

Both true and false populations are counted. False rows are never dropped from the frame.

MVP includes descriptive deltas (`true - false`). No p-values or significance tests.

### Application API

Single-run MVP:

```python
AnalyzeSignalResearchRequest(run_ref: RunDatasetRef, ...)
AnalyzeSignalResearchResult(run_summaries, grouped_summaries, conditional_comparison, metadata)
```

Entry point: `analyze_signal_research_run(...)`.

Multi-run comparison deferred.

### Output format

Validated `pl.DataFrame` schemas in `research/analytics/schemas.py` (Wave 1).

Analytics results are **ephemeral** in MVP — no persisted analytics envelope.

### Reporting layer

Optional Plotly HTML report consumes `AnalyzeSignalResearchResult` only.

Report layer must not read Parquet, join facts or compute aggregates.

Plotly is an optional reporting dependency — not required for core analytics.

### Engine

Polars-only MVP. No DuckDB or SQL query layer (carry-forward from S008 Wave 0 boundary).

## Consequences

### Positive

- Clear separation of computation (008–009) and interpretation (010),
- reuses persisted v1/v2 envelopes without schema migration,
- conditional analytics enabled by Sprint 009 context facts,
- small fixed API surface suitable for Sprint 010 closure.

### Negative

- single-run request only in MVP,
- no statistical testing,
- no cross-run ranking,
- grouping limited to fixed dimensions.

## References

- `docs/planning/sprints/S010_WAVE0_DECISIONS.md`
- `docs/planning/sprints/SPRINT_010.md`
- `docs/adr/ADR-0011-signal-research-outcomes-and-persistence.md`
- `docs/adr/ADR-0012-combined-research-scopes-and-context-alignment.md`
- `tests/spike/run_signal_research_analytics_spike.py`
