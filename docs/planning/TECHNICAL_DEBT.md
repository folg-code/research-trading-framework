# Trading Research Framework

# TECHNICAL_DEBT.md

## 1. Purpose

This register records known implementation debt that has been consciously accepted.

Technical debt is different from:

- an unresolved architectural problem,
- an unvalidated idea,
- a bug that violates expected behaviour,
- intentionally deferred future functionality.

An item belongs here only when:

1. a simpler or incomplete implementation is consciously accepted,
2. the limitation is understood,
3. the current system may still operate correctly within documented boundaries,
4. future remediation cost or risk is known.

Because the project is currently pre-implementation, this register initially contains mostly planned debt boundaries and no large body of accumulated code debt.

---

## 2. Statuses

```text
ACCEPTED
PLANNED_REPAYMENT
IN_PROGRESS
REPAID
OBSOLETE
```

---

## 3. Priority

```text
CRITICAL
HIGH
MEDIUM
LOW
```

Priority reflects repayment importance.

---

## 4. Debt Entry Template

```markdown
## TD-XXX — Title

Status:
Priority:
Domain:
Introduced:
Target Review:
Owner:

### Accepted Shortcut

...

### Reason

...

### Consequences

...

### Safe Operating Boundary

...

### Repayment Trigger

...

### Repayment Direction

...

### Related Problems

- ...

### Related Tasks

- ...
```

---

# 5. Accepted Technical Debt

## TD-001 — Architecture Decisions Are Consolidated Before Individual ADR Files Exist

```text
Status: ACCEPTED
Priority: MEDIUM
Domain: Governance / Architecture
Introduced: 2026-06-19
Target Review: Phase 0 completion
Owner: Unassigned
```

### Accepted Shortcut

Architectural decisions are currently documented in consolidated architecture files instead of individual numbered ADRs.

### Reason

The architecture was evolving rapidly and consolidating decisions first reduced fragmentation.

### Consequences

- historical alternatives are less visible,
- individual decisions are harder to supersede cleanly,
- contributors must inspect large documents.

### Safe Operating Boundary

No material architectural change should be implemented without checking the consolidated documents.

### Repayment Trigger

Before implementation moves beyond repository foundation.

### Repayment Direction

Create the initial ADR set and cross-reference it from architecture documents.

### Related Problems

- PRB-016.

---

## TD-002 — Planning State Is Maintained in Markdown Before GitHub Project Setup

```text
Status: ACCEPTED
Priority: LOW
Domain: Governance
Introduced: 2026-06-19
Target Review: Phase 0 completion
Owner: Unassigned
```

### Accepted Shortcut

Current status, problems and ideas are stored in Markdown before GitHub Issues and Projects become the operational source of truth.

### Reason

The repository governance structure is still being created.

### Consequences

- manual updates,
- possible status drift,
- no automated issue linking.

### Safe Operating Boundary

Do not duplicate detailed task state in multiple Markdown files.

### Repayment Trigger

Repository and GitHub Project are initialized.

### Repayment Direction

Move operational task state to GitHub and retain Markdown for stable rules and summaries.

---

## TD-003 — Initial Market Analysis Module Uses a Minimal Directory Structure

```text
Status: ACCEPTED
Priority: LOW
Domain: Market Analysis
Introduced: Planned for Phase 3
Target Review: After first 5–10 stable components
Owner: Unassigned
```

### Accepted Shortcut

Begin with:

```text
market_analysis/
├── components/
├── engine/
├── models/
└── protocols.py
```

instead of immediately creating separate permanent directories for every semantic category and engine capability.

### Reason

The conceptual taxonomy is known, but the practical component volume is not.

### Consequences

- temporary mixed component directory,
- later file moves may be required.

### Safe Operating Boundary

Every component must still declare whether its output is a Feature, Structure or State.

### Sprint 029 note

Whole-repo layout work (Sprint 029) **defers** deep `market_analysis/` reshuffles.
Repay this debt when Phase 4B/4C starts or navigation pain is demonstrated
(see `S029_WAVE0_DECISIONS.md` D-S029-04).


### Repayment Trigger

The module becomes difficult to navigate or stable clusters emerge.

### Repayment Direction

Split into justified directories without changing domain semantics.

---

## TD-004 — Version 1 Keeps Position Sizing Inside the Risk Model

```text
Status: ACCEPTED
Priority: LOW
Domain: Strategy
Introduced: Architecture baseline
Target Review: Phase 6A or later
Owner: Unassigned
```

### Accepted Shortcut

Do not create a separate Position Sizing Model in Version 1.

### Reason

Independent composition and versioning are not yet demonstrated requirements.

### Consequences

Some Risk Models may contain both capital constraints and sizing logic.

### Safe Operating Boundary

Risk responsibilities must remain strategy-level and separate from operational execution risk controls.

### Repayment Trigger

Sizing variants require independent research, composition or execution reuse.

### Repayment Direction

Introduce a separate contract through an ADR and migration plan.

---

## TD-005 — Version 1 Uses an In-Memory Event Bus

```text
Status: ACCEPTED
Priority: LOW
Domain: Events / Execution
Introduced: Planned for Phase 8
Target Review: Before Live Execution
Owner: Unassigned
```

### Accepted Shortcut

Use an in-process EventBus rather than Redis, Kafka or another durable broker.

### Reason

The initial system is a modular monolith and does not require distributed messaging.

### Consequences

- no process-independent durability,
- no horizontal consumer scaling,
- restart loses non-persisted in-flight events.

### Safe Operating Boundary

Critical Execution state must be persisted independently.

The EventBus must not be treated as the system of record.

### Repayment Trigger

Multiple processes, durable replay or independent services become required.

### Repayment Direction

Evaluate a distributed broker through an ADR.

---

## TD-006 — Historical Storage Uses Local Parquet Before a Dedicated Data Platform

```text
Status: ACCEPTED
Priority: LOW
Domain: Market Data / Infrastructure
Introduced: Architecture baseline
Target Review: After measured storage bottlenecks
Owner: Unassigned
```

### Accepted Shortcut

Use local Parquet, optional DuckDB and metadata storage rather than a distributed data platform.

### Reason

This maximizes value with minimum operational complexity.

### Consequences

- limited multi-user concurrency,
- local-machine storage constraints,
- manual distribution across machines.

### Safe Operating Boundary

Dataset identity and lineage remain independent from physical paths.

### Repayment Trigger

One-machine storage, query or coordination limits are repeatedly exceeded.

### Repayment Direction

Assess object storage, shared catalogues or distributed query engines using measured requirements.

---

## TD-007 — Initial Trading Calendar May Wrap an External Library

```text
Status: ACCEPTED
Priority: MEDIUM
Domain: Time / Market
Introduced: Planned for Phase 2 or 4
Target Review: After CME vertical slice
Owner: Unassigned
```

### Accepted Shortcut

Use an adapter around an existing calendar library rather than implementing full exchange calendars internally.

### Reason

Exchange holiday and shortened-session logic is complex and not a core differentiator.

### Consequences

- external library behaviour and updates become dependencies,
- unsupported markets may need overrides,
- reproducibility requires calendar-version metadata.

### Safe Operating Boundary

Domain and application layers depend only on framework calendar contracts.

### Repayment Trigger

Required markets are unsupported or external behaviour cannot be versioned reliably.

### Repayment Direction

Add framework-owned overrides or selected internal calendar definitions.

---

## TD-008 — Initial Research Planner Uses Conservative Static Limits

```text
Status: ACCEPTED
Priority: MEDIUM
Domain: Research
Introduced: Planned for Phase 5
Target Review: After measured research workloads
Owner: Unassigned
```

### Accepted Shortcut

Use static candidate-count and model-complexity limits before dynamic cost estimation is available.

### Reason

A simple hard boundary protects against accidental explosion.

### Consequences

- limits may be too strict or too permissive,
- no accurate runtime estimate.

### Safe Operating Boundary

Overrides must be explicit and visible.

The planner must never silently prune requested experiments.

### Repayment Trigger

Measured workloads provide enough data for cost estimation.

### Repayment Direction

Implement preflight resource estimates and configurable policy tiers.

---

## TD-009 — Initial Strategy Backtest Supports a Limited Fill Model

```text
Status: ACCEPTED
Priority: HIGH
Domain: Research
Introduced: Planned for Phase 6A
Target Review: Before robustness claims
Owner: Unassigned
```

### Accepted Shortcut

The first batch/vectorized backtest should support a deliberately limited, explicit fill model rather than full broker realism.

### Reason

Full execution simulation would significantly expand Phase 6A scope and blur the Research/Execution boundary.

### Consequences

- some strategy types cannot be evaluated accurately,
- results depend strongly on documented assumptions,
- no claim of live parity is allowed.

### Safe Operating Boundary

Unsupported orders, partial fills and intrabar ambiguity must fail or be explicitly excluded.

### Repayment Trigger

A selected strategy requires more realistic order semantics.

### Repayment Direction

Add simulation capabilities incrementally while preserving assumptions in run identity.

---

## TD-010 — Documentation Consistency Is Reviewed Manually Before Automation

```text
Status: ACCEPTED
Priority: MEDIUM
Domain: Documentation / Governance
Introduced: 2026-06-19
Target Review: Phase 1
Owner: Unassigned
```

### Accepted Shortcut

Use manual review and simple text searches before implementing documentation linting or architecture checks.

### Reason

Document conventions are still stabilizing.

### Consequences

- stale terminology may remain,
- heading numbering and references may drift.

### Safe Operating Boundary

Architecture-changing work must update all affected documents.

### Repayment Trigger

The documentation set stabilizes and repository CI exists.

### Repayment Direction

Add lightweight checks for deprecated terms, required files and broken internal references.

---

## TD-011 — Historical Query Returns List of MarketBar Objects

```text
Status: ACCEPTED
Priority: HIGH
Domain: Market Data
Introduced: Sprint 002 (2026-06)
Target Review: Before large-scale batch analysis or Sprint 004 MTF spike completion
Owner: Unassigned
```

### Accepted Shortcut

`query_historical` materializes results as `list[MarketBar]` — one Python object per bar.

### Reason

Sprint 002 prioritized semantic clarity and testability over columnar throughput for MVP fixtures.

### Consequences

- high memory and construction cost for multi-year 1m data,
- mandatory conversion before Polars/NumPy vectorized analysis,
- Sprint 003 `AnalysisDataView.from_bars()` adds another conversion step.

### Safe Operating Boundary

Use committed fixtures and modest bar counts in CI. Do not assume million-row in-memory lists are production-viable.

### Repayment Trigger

Sprint 004 Polars resample path or first production-scale dataset import.

### Repayment Direction

Add columnar batch return type (`MarketDataBatch` / `pl.LazyFrame` with metadata) alongside or instead of list materialization for analytical paths.

### Related Problems

- PRB-004 (user_data discovery — separate concern).

### Related Tasks

- Sprint 004 T001 spike
- `docs/planning/retrospectives/ARCHITECTURE_SIMPLIFICATION_REVIEW_S002_S003.md` §5.1
- `docs/reference/DATA_REPRESENTATION_AUDIT.md` — D-REP-01 and D-REP-03 (accepted 2026-08-25)
  define the repayment shape; H4 in §6.2 tracks the remaining object-materialization sites

### Post-Sprint 025 Review Notes

Return to this after Sprint 025. Keep `MarketBar` as a boundary/live-event object, but move bulk
historical/research paths toward Arrow/Polars/`OhlcvColumnBatch`.

Files to review:

- `src/trading_framework/infrastructure/storage/parquet/writer.py` — legacy
  `market_bars_to_table`, `market_bars_from_table`, `ParquetBarWriter.write/read`.
- `src/trading_framework/infrastructure/storage/parquet/repository.py` — legacy `write_bars`
  and `query_bars`; prefer `write_session_table` / `query_ohlcv_table` for bulk paths.
- `src/trading_framework/application/market_data/import_external_dataset.py` — CSV import
  materializes `NormalizedBarRow` and `MarketBar` lists before validation/write.
- `src/trading_framework/application/market_data/derive_ohlcv_from_trades.py` — trade and bar
  derivation materializes full Python lists.
- `src/trading_framework/application/market_data/derive_continuous_ohlcv.py` — aggregation/write
  is table-based, but validation still converts session tables to `MarketBar`.
- `src/trading_framework/application/strategy_research/dashboard.py` and
  `src/trading_framework/research/analytics/strategy_dashboard.py` — dashboard source candles
  flow through `query_historical` and `list[MarketBar]`.
- `src/trading_framework/market_analysis/data/view.py` and
  `src/trading_framework/market_analysis/data/resample.py` — `AnalysisDataView.from_bars` and
  resampling still round-trip through `MarketBar`.

Likely repayment direction:

- make columnar/table APIs the default for historical query, import, derivation and dashboards,
- keep object APIs as explicit compatibility adapters or small live-runtime boundaries,
- add validator paths that operate on Arrow/Polars/column batches without constructing one Python
  object per bar,
- migrate strategy research/dashboard reads to `query_historical_columnar` or direct table queries.

---

## TD-012 — Decimal OHLCV in Market Data with float64 Analysis Conversion

```text
Status: ACCEPTED
Priority: MEDIUM
Domain: Market Data / Market Analysis
Introduced: Sprint 002 (MarketBar) + Sprint 003 (AnalysisDataView float64)
Target Review: When analytical backend standardizes on Polars-native types
Owner: Unassigned
```

### Accepted Shortcut

Market Data stores prices as `Decimal`; Market Analysis adapters consume `float64`.

### Reason

Domain-safe storage vs research-default computation dtype (D-027).

### Consequences

- conversion on every analysis run,
- impedance with Polars/TA-Lib native types,
- two precision semantics to document.

### Safe Operating Boundary

Research/backtest paths only; not used for order accounting without separate money types.

### Repayment Trigger

Polars-first batch pipeline adopted for query + analysis boundary.

### Repayment Direction

Analytical OHLCV as float64 or scaled integer at storage boundary; reserve Decimal for execution/accounting.

### Related Tasks

- Architecture Simplification Review §2.2, §3.2
- `docs/reference/DATA_REPRESENTATION_AUDIT.md` — D-REP-04a accepted 2026-08-25 (simulation PnL as
  `int64` minor units); D-REP-04b (unified Parquet `price_nanos`) deferred to a dedicated sprint,
  D-S027-08 remains binding until then

---

## TD-013 — Multi-Implementation Registry Before Second Backend

```text
Status: ACCEPTED
Priority: MEDIUM
Domain: Market Analysis
Introduced: Sprint 003
Target Review: When second backend (Polars-native or TA-Lib) is committed
Owner: Unassigned
```

### Accepted Shortcut

`ComponentRegistry` resolves multiple implementations per component with explicit/default policy; only NumPy adapter is production-ready.

### Reason

Vision doc D-004/D-005 anticipated interchangeable backends before MVP delivery.

### Consequences

- resolver and dual identity axis maintained without interchange benefit,
- higher mental load for contributors,
- tests cover resolution paths rarely used.

### Safe Operating Boundary

Register only NumPy implementations in CI. Do not add resolver features until a second backend ships.

### Repayment Trigger

TA-Lib extra (S003-T027) or Polars-native component path lands with real interchange need.

### Repayment Direction

Simplify to `ComponentId → ComponentDefinition` if second backend never materializes; otherwise keep registry but document interchange contract.

---

## TD-014 — Separate ResultStore, Workspace and In-Plan ExecutionCache

```text
Status: ACCEPTED
Priority: MEDIUM
Domain: Market Analysis
Introduced: Sprint 003
Target Review: Sprint 004 executor changes or persistent cache work
Owner: Unassigned
```

### Accepted Shortcut

Three execution-scoped structures: `AnalysisResultStore`, `AnalysisWorkspace`, `ExecutionCache`.

### Reason

Four-layer model from workspace vision doc; cache ADR-MA-008 for exact-match deduplication.

### Consequences

- overlapping responsibilities for single-plan batch MVP,
- duplicate lookup paths,
- more surface area for MTF extensions.

### Safe Operating Boundary

Single sequential plan per run; no cross-run cache; no persistent workspace.

### Repayment Trigger

Cross-run cache, partial reruns, or persistent derived results require distinct lifecycles.

### Repayment Direction

Evaluate consolidation into `ExecutionState: dict[NodeKey, ComponentResult]` when touching executor without breaking ADR semantics.

---

## TD-015 — AnalysisDataView Map-of-Arrays Instead of Columnar Frame

```text
Status: ACCEPTED
Priority: HIGH
Domain: Market Analysis
Introduced: Sprint 003 (post Wave 0 spike)
Target Review: Sprint 004 T001; before expanding view API
Owner: Unassigned
```

### Accepted Shortcut

`AnalysisDataView` exposes tuple columns and custom `column()` API instead of Polars LazyFrame payload.

### Reason

Backend-neutral contract (D-011); avoid locking domain to pandas/Polars in Sprint 003.

### Consequences

- custom mini-API that may grow toward DataFrame emulation,
- friction for resampling, join_asof, LazyFrame,
- Sprint 004 needs conversion boundary for Polars MTF path.

### Safe Operating Boundary

Do not extend `AnalysisDataView` with select/join/resample methods. New batch paths should use thin `MarketFrame` wrapper (future) per simplification review.

### Repayment Trigger

Sprint 004 spike confirms Polars resample/align; or second analytical backend requires shared columnar contract.

### Repayment Direction

Introduce `MarketFrame(pl.LazyFrame, metadata)` for batch paths; migrate components incrementally; deprecate view API growth not conversions at boundary.

### Related Tasks

- Sprint 004 Design Principles
- ADR-MA-012 (planned)
- `docs/reference/DATA_REPRESENTATION_AUDIT.md` — D-REP-01 accepted 2026-08-25; `MarketFrame`
  becomes the canonical bulk contract, `AnalysisDataView` is retained as a live-runtime adapter.
  Blocked on a superseding ADR for ADR-MA-004 / ADR-MA-010.

---

## TD-016 — ComponentId and ImplementationId Dual Identity Axis

```text
Status: ACCEPTED
Priority: LOW
Domain: Market Analysis
Introduced: Sprint 003
Target Review: With TD-013 (second backend)
Owner: Unassigned
```

### Accepted Shortcut

Separate semantic component identity and implementation identity in public types and cache keys.

### Reason

Supports multiple backends and versioned implementations per vision architecture.

### Consequences

- two versioning dimensions for single NumPy implementation,
- longer identity keys and resolver tests.

### Safe Operating Boundary

One implementation per component in CI registry.

### Repayment Trigger

Second implementation of same component shipped.

### Repayment Direction

Collapse to single identity axis if interchange never needed; else keep and document in ADR.

---

## TD-017 — Signal / Market Research Occurrence and Outcome Materialization Is Row-Wise Python

Status: REPAID  
Priority: CRITICAL  
Domain: Signal Research / Market Model Research  
Introduced: Sprint 008–010 (accepted for MVP correctness)  
Target Review: Sprint 026  
Owner: Project Maintainer
Repaid: Sprint 026 Wave A (`feat/signal-reference-price-index`,
`feat/signal-forward-outcomes-numpy`, `feat/signal-occurrence-batch-reference-prices`)

### Accepted Shortcut

Occurrence and observation materialization call `resolve_reference_price` per row, rebuilding a
full timestamp→index map each time. Forward outcomes iterate occurrences in Python and build
per-window high/low lists; multi-horizon evaluation repeats that work per horizon.

### Reason

MVP prioritized correct occurrence / outcome contracts and Polars persistence over vectorized
post-evaluation paths. Strategy Research later received columnar + Numba investment; Signal
Research post-process did not.

### Consequences

On NQ half-year scale (~177k bars, thousands of observations), Signal / Market Research wall-clock
is dominated by O(occurrences × bars) work and is not comparable to the ~6 s Strategy Research
baseline despite sharing `evaluate_models`.

### Safe Operating Boundary

Fixture-scale and small samples remain usable. Half-year / multi-horizon demos and family runs are
operator-painful until repaid.

### Repayment Trigger

Sprint 026 Wave A — amortize timestamp index; vectorize reference prices and forward outcomes
without changing methodology or outcome schema.

### Repayment Direction

See `docs/planning/sprints/SPRINT_026.md` and `S026_WAVE0_DECISIONS.md` (D-S026-02, D-S026-07).

### Repayment Notes

- Timestamp→index + close series built once per materialization (`ReferencePriceLookup`).
- Occurrences / observations join reference prices via Polars (`to_frame()`).
- Forward outcomes use shared NumPy float64 OHLCV arrays across horizons.
- Residual: occurrence/observation ID hashing remains Python; family-run analysis cache deferred.

---

## TD-018 — Robustness Child Runs Re-Execute Full Strategy Research Without Shared Evaluation

Status: REPAID  
Priority: HIGH  
Domain: Robustness Research  
Introduced: Sprint 016 (accepted for MVP orchestration)  
Target Review: Sprint 026  
Owner: Project Maintainer
Repaid: Sprint 026 Wave B (`feat/robustness-shared-evaluation-context`)

### Accepted Shortcut

Parameter sweep, walk-forward and non-post-process stress scenarios each call
`run_strategy_research` independently. Only exact fingerprint resume skips work. OHLCV load,
Market Analysis and model evaluation are not reused when only exit / risk / assumptions change.

### Reason

MVP delivered correct experiment manifests, resume registry and verdict analytics by composing the
existing Strategy Research entry point without introducing a shared research session abstraction.

### Consequences

Experiment cost scales roughly as `N_variants × strategy_research_cost`. Small demos are tolerable;
serious grids and walk-forward folds become slow relative to a single backtest.

### Safe Operating Boundary

Resume of identical completed experiments works. Post-process stress and Monte Carlo on persisted
trades remain cheap. Fresh multi-cell experiments pay full N× cost.

### Repayment Trigger

Sprint 026 Wave B — optional shared evaluation context for child runs that share market/signal
models; resimulate only variant-specific simulation inputs.

### Repayment Direction

See `docs/planning/sprints/SPRINT_026.md` and `S026_WAVE0_DECISIONS.md` (D-S026-03, D-S026-07).
Methodology remains repeated Strategy Research runs.

### Repayment Notes

- `SharedStrategyEvaluationCache` reuses columnar OHLCV + `evaluate_models` when market/signal
  definitions and range match (e.g. `exit_after_bars` sweeps).
- Wired into parameter sweep, walk-forward and stress runners.
- Residual: Monte Carlo path summarization still uses Decimal lists; parallel child runs deferred.

---

## TD-019 — Databento Contract Import Chunk Buffers Use Python Lists

Status: REPAID  
Priority: CRITICAL  
Domain: Market Data / Historical Archive Import  
Introduced: Sprint 011 (accepted for MVP columnar bridge)  
Target Review: Sprint 027  
Owner: Project Maintainer
Repaid: Sprint 027 Wave A (`feat/import-column-buffers-numpy`, #217)

### Accepted Shortcut

`ContractChunkColumns` stores trade fields as Python `list`s. Chunk mapping converts NumPy
masked selections via `.tolist()` on every column every chunk; session `take` and Parquet table
build copy those lists again into Arrow.

### Reason

MVP prioritized correct outright-contract decode, session partitions and merge-existing writes
over zero-copy columnar buffers after Databento `to_df` chunks.

### Consequences

On NQ half-year batch import (~297 archives), `decode.map_chunk_batch` alone is ~61 s and parquet
build/write adds ~100 s of related copy/I/O work. Operator rebuilds are dominated by ingest even
when research is fast.

### Safe Operating Boundary

Small archive sets and fixtures remain fine. Half-year / multi-contract re-imports are slow but
correct.

### Repayment Trigger

Sprint 027 Wave A — NumPy/Arrow buffers through map → partition → `pa.Table` without changing
ADR-0014 schemas or merge semantics.

### Repayment Direction

See `docs/planning/sprints/SPRINT_027.md` and `S027_WAVE0_DECISIONS.md` (D-S027-03, D-S027-05).

### Repayment Notes

- Column buffers are NumPy chunk parts with lazy concat; `extend_masked` / `take` avoid `.tolist()`.
- Contract Parquet tables build from arrays (`contract_trade_columns_to_table`).
- Synthetic microbench (`scripts/ops/bench_contract_chunk_columns.py`): ~2M rows extend+take+table
  in ~0.32 s locally (2026-07-17).
- Residual: vendor `DBNStore.to_df` still dominates full import wall (~200 s self in baseline
  profile); parallel archive import deferred.

---

## TD-020 — Continuous Trades Materialize Pays Per-Session Write + String Price Schema

Status: REPAID  
Priority: HIGH  
Domain: Market Data / Continuous Futures  
Introduced: Sprint 015 (accepted for Decimal-preserving continuous Parquet)  
Target Review: Sprint 027  
Owner: Project Maintainer
Repaid: Sprint 027 Wave B (`feat/continuous-materialize-write-path`, #218) — orchestration /
write-path; string `price` schema kept (D-S027-08)

### Accepted Shortcut

Continuous materialization writes one Parquet file per `session_date` sequentially. Continuous
schema stores `price` as string while contract-layer storage already uses `price_nanos` int64.
Polars transform converts nanos → string every session before write.

### Reason

MVP matched continuous domain `MarketTrade` / Decimal presentation and kept Layer-4 continuous
artifacts separate from contract storage without a second schema migration.

### Consequences

NQ half-year materialize spends ~62 s in `materialize.write` across ~345 sessions (~0.18 s/write
avg), more than transform (~14 s). Full rebuilds remain expensive after import.

### Safe Operating Boundary

Fingerprint reuse (`--skip-build` / unchanged source fingerprint) avoids rematerialize. Fresh
rebuilds and policy changes pay full sequential write cost.

### Repayment Trigger

Sprint 027 Wave B — reduce avoidable write-path cost; decide keep string `price` vs ADR-amended
`price_nanos` continuous schema.

### Repayment Direction

See `docs/planning/sprints/SPRINT_027.md` and `S027_WAVE0_DECISIONS.md` (D-S027-04, D-S027-05,
D-S027-08). Do not silently change continuous Parquet schema.

### Repayment Notes

- Cheaper Polars timestamp (ns→us integer divide) and price-string formatting; skip redundant casts.
- Continuous writer: zstd, `use_dictionary=False`, cast only when schema differs.
- `session_workers` (default 4 via `build_continuous`) parallelizes per-session load/transform/write.
- Residual: continuous `price` remains string until an explicit ADR/`price_nanos` migration.

---

## TD-021 — Predictive Research Has No Model Registry

```text
Status: ACCEPTED
Priority: MEDIUM
Domain: Predictive Research
Introduced: Sprint 040 (2026-08-26)
Target Review: Sprint 044 / IDEA-014 promotion gate
Owner: Unassigned
```

### Accepted Shortcut

Predictive runs are addressed by content fingerprint under
`research/predictive_research/runs/{run_id}/`. There is no registry, no promotion
workflow, and no model lifecycle state.

### Reason

A registry is a product, not a storage layout. S040 needs reproducible runs, not
an addressable model store. IDEA-014 promotion (S044 / ADR-0024) is the first
consumer that might need one.

### Consequences

- runs are found by `run_id` / fingerprint, not by a catalog,
- there is no promotion or retirement workflow,
- S044 must decide whether a content-addressed store suffices.

### Safe Operating Boundary

Do not invent a registry in S041–S043. Analyze and report from persisted
predictions and metrics. Do not treat `run_id` directories as a promotion API.

### Repayment Trigger

Promoting a trained model to a Market Analysis component (IDEA-014), which
requires an addressable, durable artifact store. Sprint 044 ADR-0024 decides
whether a content-addressed store suffices or a registry is genuinely required.

### Repayment Direction

Decide in ADR-0024. Do not add a registry as a side effect of trees or networks.

### Related Problems

- IDEA-014 (promotion gate).

---

## TD-022 — Fitted Predictive Artifacts Are Opaque and Not Portable

```text
Status: ACCEPTED
Priority: LOW
Domain: Predictive Research
Introduced: Sprint 040 (2026-08-26)
Target Review: When a library upgrade blocks inspection, or at IDEA-014
Owner: Unassigned
```

### Accepted Shortcut

The durable facts of a run are `predictions.parquet` and `metrics.json`. Fitted
estimators are stored as opaque `models/fold_{n}.bin` blobs (joblib), tagged with
library name and version. The framework makes no promise that a blob can be
loaded after a library upgrade. Reproduction re-fits from the manifest.

### Reason

Predictions and metrics stay readable in ten years. A model registry or a
stability-guaranteed serializer would expand S040 into infrastructure that Phase
10 explicitly deferred.

### Consequences

- a run whose library version is no longer installable can be read and analyzed
  but not re-fitted identically,
- `analyze_predictive_run` must not call `joblib.load`,
- inspection after a bump requires a re-fit.

### Safe Operating Boundary

No workflow may depend on reloading a fitted blob. Fingerprints record library
name + version so a bump is a different experiment, not a silent drift.

### Repayment Trigger

Model promotion (same as TD-021), or a demonstrated need to inspect old artifacts
after a library upgrade.

### Repayment Direction

Choose a serialization format with a stability guarantee. That is not the same
as adding a registry.

### Related Tasks

- `TECHNICAL_DEBT.md` §6 Phase 10 planned boundaries (now live)
- `SPRINT_040.md` §8
- ADR-0023 §7

---

## TD-023 — Binance Historical Import Only Works for 1m

```text
Status: ACCEPTED
Priority: LOW
Domain: Market Data / Binance Provider
Introduced: Sprint 045 (2026-08-31)
Target Review: When a non-1m Binance interval is genuinely needed
Owner: Unassigned
```

### Accepted Shortcut

`infrastructure/providers/binance/futures_mapper.py::map_kline_payload` hard-rejects
any kline payload whose `interval != "1m"`. Sprint 045's historical reader
(`futures_klines_history.py`) deliberately reuses this mapper unchanged, so
`import_binance_futures_ohlcv` only actually works for `interval="1m"` today.

### Reason

D-S045-04 forbids Wave 1/2 from editing shared Binance helpers, because
`map_kline_payload` is also used by the live dry-run reconnect path
(`fetch_closed_klines`) — widening it mid-sprint would have put that path at
risk for a capability (non-1m historical import) nothing in Sprint 045
actually needed. `S045_WAVE0_DECISIONS.md` D-S045-05 originally listed `1m`,
`5m`, `15m`, `1h`, `4h`, `1d` as v1-supported intervals before this
limitation was found; it was corrected to `1m` only rather than expanding
this sprint's scope.

### Consequences

- `import_binance_futures_ohlcv` with any non-`1m` interval fails at the
  mapper, not at the workflow's own validation — the error is real but one
  layer down from where an operator would first look,
- Sprint 046's CLI (`data fetch binance`) inherits this limitation until
  repaid.

### Safe Operating Boundary

No workflow may assume a non-`1m` Binance interval works. Callers must
either hardcode `1m` or fail clearly before reaching the mapper.

### Repayment Trigger

A genuine need for a non-1m Binance interval.

### Repayment Direction

Widen `map_kline_payload` to accept the full interval set — verifying this
cannot regress `fetch_closed_klines`'s existing behavior — or build an
interval-aware variant used only by the historical import path.

### Related Tasks

- `docs/planning/sprints/S045_WAVE0_DECISIONS.md` D-S045-05
- `docs/adr/ADR-0025-binance-usdm-historical-klines-import.md`
- `src/trading_framework/infrastructure/providers/binance/CLAUDE.md`

---

## TD-024 — CLI Import Boundary Is Module-Level, Not Symbol-Level

```text
Status: ACCEPTED
Priority: LOW
Domain: apps/cli / Architecture Boundary Tests
Introduced: Sprint 046 (2026-08-31)
Target Review: When a new apps/cli command needs a heavier symbol from an
  already-allowed module, or at the next apps/cli boundary audit
Owner: Unassigned
```

### Accepted Shortcut

`tests/unit/test_apps_boundaries.py::test_cli_only_imports_application_layer`
enforces ADR-0026 Amendment 1's named module allow-list by checking which
*modules* `apps/cli` imports from, not which *symbols* it imports. A module
on the allow-list (e.g. `trading_framework.research.datasets.predictive`) may
contain both the narrow value objects/identifiers a command uses today and
heavier symbols (e.g. a full repository class) nothing currently imports.

### Reason

Symbol-level enforcement (parsing which names are pulled from each
`ImportFrom` node, not just which module) is meaningfully more test logic
for a boundary that, as of Sprint 046 Wave 2, has exactly one violation
category worth catching: an accidental future import of something heavier
than what today's five command bodies actually use. Module-level enforcement
with an explicit, reviewed allow-list (Amendment 1) already prevents the
open-ended violation this test exists to catch; symbol-level tightening is a
refinement, not a missing guardrail.

### Consequences

- A future `apps/cli` command could import, say,
  `PredictiveDatasetRepository` (file I/O) from
  `trading_framework.research.datasets.predictive` without the boundary
  test noticing, since that module is already allow-listed for its
  `PredictiveDatasetRef` value object.
- Code review remains the actual backstop for this specific gap until
  repaid.

### Safe Operating Boundary

No `apps/cli` command may assume the boundary test would catch a heavier
symbol from an already-allowed module. Reviewers checking a Wave 3+ CLI PR
should read *which symbols* are imported from Amendment 1's modules, not
just confirm the module itself is on the list.

### Repayment Trigger

A new `apps/cli` command needs a symbol from an allow-listed module that
goes meaningfully beyond a value object/identifier/loader (e.g. a repository
class, a service object) — that is the moment to either tighten the test to
symbol-level checks or add a fresh, specifically-justified amendment entry
rather than relying on the existing module-level entry to cover it.

### Repayment Direction

Extend `test_cli_only_imports_application_layer` to record, per allow-listed
module, the specific symbol names Wave 2 actually used, and fail if a new
import pulls a different symbol from that module without an explicit
allow-list update.

### Related Tasks

- `docs/adr/ADR-0026-operator-cli-framework-and-placement.md` Amendment 1
- `tests/unit/test_apps_boundaries.py`

---

# 6. Planned Debt Boundaries

The following shortcuts may be accepted later but are not yet introduced:

```text
- limited provider set,
- limited asset-class coverage,
- bar-only OHLCV market facts (Phase 2A; trades/quotes/options are Phase 2C–2D),
- local-only research execution,
- no UI,
- no distributed task scheduler,
- no live multi-account support,
- no automatic ML model registry (accepted as TD-021 in Sprint 040),
- no portability guarantee for fitted model artifacts (accepted as TD-022 in Sprint 040).
```

They should become technical-debt entries only when implementation consciously relies on them and repayment conditions are known.

## Phase 10 — Predictive Research (accepted in Sprint 040)

The two shortcuts below were planned before S039 and became live when S040 persisted
run envelopes. Numbered entries: **TD-021** (no model registry, MEDIUM) and
**TD-022** (opaque fitted blobs, LOW). Restated here so S041–S044 do not treat
them as oversights.

### No model registry (TD-021)

Predictive runs are addressed by content fingerprint under
`research/predictive_research/runs/{run_id}/`. There is no registry, no promotion workflow and no
model lifecycle state.

**Repayment trigger:** promoting a trained model to a Market Analysis component (IDEA-014), which
requires an addressable, durable artifact store. Sprint 044 ADR-0024 decides whether a
content-addressed store suffices or a registry is genuinely required.

### Fitted artifacts are not portable (TD-022)

The durable facts of a run are `predictions.parquet` and `metrics.json`. The fitted model is stored
as an opaque blob tagged with library name and version, and the framework promises nothing about
loading it after a library upgrade. Reproduction re-fits from the manifest instead.

**Consequence accepted:** a run whose library version is no longer installable can be read and
analyzed but not re-fitted identically. Fingerprints make this visible rather than silent.

**Repayment trigger:** the same as above — model promotion, or a demonstrated need to inspect old
artifacts. Repayment means choosing a serialization format with a stability guarantee, not adding a
registry.

---

# 7. Debt Review Rules

Review technical debt:

- at sprint retrospectives,
- before phase completion,
- before introducing related abstractions,
- when a repayment trigger occurs,
- when a debt item becomes a correctness risk.

A debt item must move to `PROBLEM_REGISTRY.md` or a bug when it begins violating expected behaviour or safety.

Do not use technical debt as a label for every unfinished feature.
