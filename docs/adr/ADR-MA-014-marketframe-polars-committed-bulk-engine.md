# ADR-MA-014 — MarketFrame and Polars as the Committed Bulk Engine

## Status

ACCEPTED

Sprint 036 (D-REP-01). Authorizes Stage 4 implementation; this record does not ship `MarketFrame` code.

## Context

`AnalysisDataView` carries `tuple[float, ...]` columns and a custom `column()` API (ADR-MA-004).
Every tabular operation the engine needs (resample, as-of align, join, aggregate) leaves that
contract, goes to Polars, and comes back. ADR-MA-010 treated Polars as an optional adapter.
ADR-MA-012 already uses Polars for resample/align, then converts back to the view.

TD-015 and TD-011 registered a `MarketFrame(pl.LazyFrame, metadata)` bulk path. The Sprint 036
data representation audit accepted that direction as D-REP-01, with `AnalysisDataView` kept for
the live runtime (N=1, object semantics). Stage 4 must not start without this superseding ADR.

## Decision

1. **Polars is a committed engine** for bulk market-analysis and research pipelines, not an
   optional backend. Bulk public contracts may name `pl.LazyFrame` / `pl.DataFrame`.
2. **Canonical bulk representation** is `MarketFrame(pl.LazyFrame, metadata)`. Stage 4 introduces
   the type and an adapter from `AnalysisDataView`. Components migrate incrementally behind that
   adapter. No big-bang rewrite.
3. **`AnalysisDataView` remains** the live-runtime adapter (object semantics, N=1). Live dry-run
   and paper paths do not have to consume `MarketFrame`.
4. **NumPy kernels stay adapters.** ADR-MA-010 still applies to NumPy and TA-Lib: they are not
   domain contracts; shared contract tests still bind implementations. Domain protocols may import
   Polars types for bulk work; they still must not import NumPy/TA-Lib.
5. **This ADR is authorization, not implementation.** Existing `run_analysis` / `evaluate_models`
   contracts stay unchanged until a Stage 4 PR lands tests proving identical `AnalysisResult`
   values on fixtures.

## What this ADR does not decide

- D-REP-04b (`price_nanos` storage) — separate sprint; ADR-0018 and D-S027-08 remain binding.
- D-REP-05 / D-REP-10 — amended on ADR-MA-009 and ADR-MA-005; Stage 3 implements them.
- Which component migrates first — Stage 4 PRs choose incrementally (`ema` / `true_range` first
  in the audit plan).

## Consequences

### Positive

- one structural repayment for TD-011 / TD-015 instead of four local conversions (H2–H4, H6),
- Polars lazy plans can stay lazy across resample, align, and research joins,
- live runtime keeps a small object adapter instead of forcing LazyFrame at N=1.

### Negative

- Polars becomes part of the bulk domain contract (the “boundary creep” risk in
  `CURRENT_STATUS.md` §10 is accepted, not ignored),
- every bulk component and its tests must eventually move behind `MarketFrame`,
- until Stage 4 ships, code still uses `AnalysisDataView` as the executed contract.

## Supersession

Supersedes:

- ADR-MA-004 — the claim that the backend-neutral view is the **bulk** representation contract,
- ADR-MA-010 — the claim that Polars is only an optional implementation backend.

Does **not** supersede:

- ADR-MA-004 ownership rules (`DataFieldDependency`, no `DatasetRef` into components, immutable
  input),
- ADR-MA-010 NumPy/TA-Lib adapter rules and shared contract tests,
- ADR-MA-012 resample/align semantics (UTC buckets, `LAST_CLOSED_BAR`) until a later ADR changes
  them.

## References

- `docs/reference/DATA_REPRESENTATION_AUDIT.md` — D-REP-01, Stage 0 / Stage 4
- `docs/planning/TECHNICAL_DEBT.md` — TD-011, TD-015
- `docs/adr/ADR-MA-004-analysis-data-view-and-data-ownership.md`
- `docs/adr/ADR-MA-010-external-analytical-libraries.md`
- `docs/adr/ADR-MA-012-batch-multitimeframe-computation-with-polars.md`
- `src/trading_framework/market_analysis/data/view.py`
