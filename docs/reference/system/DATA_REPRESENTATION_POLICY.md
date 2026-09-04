# Data Representation Policy

> Extracted from the original `docs/reference/system/DATA_REPRESENTATION_AUDIT.md`
> (former §4 "Target Representation Policy", §5.2 "Target primitives", §5.3
> "Null semantics") by Sprint 055 T007, per
> [`docs/planning/sprints/SPRINT_055_T004_DECISIONS.md`](../../planning/sprints/SPRINT_055_T004_DECISIONS.md)
> §1. This is the durable, binding half of that document — the canonical
> carrier per kind of work, the directional rules and the target primitive
> table constrain every module and do not decay with a code baseline.
>
> The point-in-time measurement record (representation map, transformation
> map, hot-path benchmarks pinned to commit `f0a82c5`) and the decision
> register / refactoring-plan PR board (D-REP-01..10, Stage 0-6) are a
> Sprint 036 planning artifact, not as-implemented reference — they now live
> at
> [`docs/planning/sprints/SPRINT_036_DATA_REPRESENTATION_AUDIT.md`](../../planning/sprints/SPRINT_036_DATA_REPRESENTATION_AUDIT.md),
> which this file cites as its evidence record. Where a rule below references
> a `D-REP-##` decision, its status/history is recorded there.

```text
Status: ACCEPTED (policy) — D-REP-06, D-REP-08, D-REP-09 remain PROPOSED
        (see SPRINT_036_DATA_REPRESENTATION_AUDIT.md §7 for per-decision status)
```

This document answers one question: **which type is the canonical carrier
for a given kind of work, and what rules keep representations from
oscillating between kinds?**

---

## 1. Canonical carrier per kind of work

| Kind of work | Canonical type | Rationale |
|---|---|---|
| Persistence and storage boundary | `pa.Table` + explicit `pa.schema` → Parquet | already established; keeps schema versioning explicit |
| Bulk historical read | `MarketFrame(pl.LazyFrame, metadata)` | pushdown, no object-per-row cost; TD-011/TD-015 repayment direction |
| Tabular transforms (resample, align, join, group, aggregate) | Polars **lazy**, `collect()` only at the materialization point | one engine, one optimizer |
| Numeric kernels (indicators, simulation) | `np.ndarray` with explicit dtype | Numba and vectorized math require contiguous typed buffers |
| Columnar ingest buffers | `np.ndarray` structure-of-arrays | already the case after TD-019 |
| Single domain facts at live/event boundaries | frozen dataclass (`MarketBar`, `MarketTrade`) | semantics and invariants matter more than throughput at N=1 |
| Money in accounting and execution | `Decimal` via `Price` | exactness is a correctness requirement |
| Money in storage | `int64` fixed-point (minor units / nanos) | exact, sortable, aggregable, compact |
| Numbers in analysis and research | `float64` | D-027; matches Polars and NumPy natively |
| Identity and cache keys | canonical sorted-key JSON `str` | already consistent inside `market_analysis` |
| Configuration | frozen dataclass + explicit parsers | one mechanism for TOML and env |
| Metadata and manifests | frozen dataclass ⇄ JSON via `to_dict`/`from_dict` | already consistent; `Decimal` as `str` |
| Presentation DTOs | frozen dataclass with `float`/`str` | deliberate decoupling, already the case in `apps/` |

## 2. Directional rules

1. **Representations may narrow, never oscillate.** A value moves
   `storage → frame → array → result` in one direction per pipeline. Any path that returns to an
   earlier representation is a defect unless it crosses a process boundary.
2. **One conversion per boundary.** `Decimal → float64` happens exactly once, at the storage-to-analysis
   boundary. `float64 → Decimal` happens exactly once, at the kernel-to-facts boundary.
3. **`Decimal(str(x))` where `x` is already a float is forbidden.** It restores the type but not the
   precision and is therefore misleading. Use `float64` explicitly or carry `int64` fixed-point.
4. **Validation follows the representation.** Validators must exist for the representation being
   validated. Decoding a table into dataclasses purely to validate it is not acceptable on bulk paths.
5. **Metadata travels with data or with a stable key, never by position.** `available_at` and lineage
   must be addressable, not reconstructed by convention.
6. **Lazy by default at I/O.** `scan_parquet` over `read_parquet`; `collect()` at the point where a
   materialized result is genuinely required.

## 3. Explicit non-goals

- No migration to pandas anywhere.
- No `pl.Decimal` adoption while it remains marked unstable in Polars.
- No removal of `MarketBar` / `MarketTrade`; they stay as boundary and live-runtime objects (TD-011
  post-S025 note).
- No new DSL surface (owned by Sprint 037).
- No distributed storage or query engine (TD-006 boundary unchanged).
- No change to research **methodology** or fact semantics — only to their carriers.

## 4. Target primitives

| Concept | Canonical primitive | Permitted encodings | Forbidden |
|---|---|---|---|
| Price — accounting | `Price(Decimal)` | — | `float` in order/fill/position paths |
| Price — storage | `int64` fixed-point, scale documented in the schema | — | `pa.string()` in new schemas |
| Price — analysis | `float64` | — | `Decimal` inside kernels or Polars expressions |
| Volume / size | `int64` | `float64` only inside a numeric kernel | silent truncation without `ROUND_FLOOR` |
| Money / PnL — persisted | `int64` minor units | `str` in JSON | `pl.Float64` for money columns |
| Timestamp — domain | UTC-aware `datetime` | — | naive datetimes anywhere in domain code |
| Timestamp — storage | `pa.timestamp("us", tz="UTC")` | `int64` ns for tick-scale contract data | naive `timestamp("us")` + `.replace(tzinfo=UTC)` |
| Timestamp — kernel | `int64` epoch ns | — | — |
| Session date | `datetime.date` / `pa.date32()` | — | string dates |
| Identity | `Identifier` or canonical sorted-key JSON `str` | SHA-256 hex where a fixed-width id is needed | pipe-joined ad-hoc strings |
| Missing value | Polars null / `None` | `NaN` only inside a float kernel, documented | dropping rows to signal absence |

## 5. Null semantics

`OutputSeries` has no null representation and uses `NaN`; Polars uses real nulls. The reconciliation
currently lives in `align.py:118-123`. Under D-REP-01 this disappears, because the carrier gains
native null support. Until then, the NaN sentinel must be documented at every boundary that
produces or consumes `OutputSeries`.

---

For the measurement evidence behind these rules (representation map,
transformation map, hot-path benchmarks) and the decision register that
accepted them, see
[`docs/planning/sprints/SPRINT_036_DATA_REPRESENTATION_AUDIT.md`](../../planning/sprints/SPRINT_036_DATA_REPRESENTATION_AUDIT.md).
