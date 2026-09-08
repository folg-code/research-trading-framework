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
- `docs/planning/sprints/SPRINT_036_DATA_REPRESENTATION_AUDIT.md` (formerly
  `docs/reference/system/DATA_REPRESENTATION_AUDIT.md`, split by Sprint 055
  T007) — D-REP-01 and D-REP-03 (accepted 2026-08-25)
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
- `docs/planning/sprints/SPRINT_036_DATA_REPRESENTATION_AUDIT.md` (formerly
  `docs/reference/system/DATA_REPRESENTATION_AUDIT.md`, split by Sprint 055
  T007) — D-REP-04a accepted 2026-08-25 (simulation PnL as
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
- `docs/planning/sprints/SPRINT_036_DATA_REPRESENTATION_AUDIT.md` (formerly
  `docs/reference/system/DATA_REPRESENTATION_AUDIT.md`, split by Sprint 055
  T007) — D-REP-01 accepted 2026-08-25; `MarketFrame`
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

### Sprint 049 disposition (2026-09-02)

**Restated as deferred, not repaid.** ADR-0024 decided: a content-addressed
directory (`research/predictive_research/promoted/{artifact_fingerprint}/`,
ADR-0029 §2) suffices — no index, no `latest` pointer, no lifecycle/status
field. This is a **negative constraint** (ADR-0024 condition 5), not a gap
still to fill: a future plan that starts adding an index file has misread
the decision, not found unfinished work. TD-021 stays open at its original
status because "no registry" is the accepted design, not a shortcut awaiting
repayment on its original terms.

### Related Problems

- IDEA-014 (promotion gate).

### Planned repayment route (2026-09-04)

ROADMAP §13H increment **16C — Signal Quality Scoring** (phase APPROVED,
increment not planned, no sprint open) is the first genuine consumer that
must reference a fitted predictive model from a *Strategy Research* config.
That is the "demonstrated need" this entry's repayment trigger names. 16C's
completion criteria therefore include an explicit answer to "how is the
scorer this strategy uses identified, and is a content-addressed
promoted-artifact directory (ADR-0024 condition 5, ADR-0029 §2) still
sufficient once a *strategy config* — not a human — has to name one?"

The expected answer is **yes, still sufficient**: ADR-0024's negative
constraint stands, and 16C is expected to reference an artifact
fingerprint, not introduce an index, a `latest` pointer or a lifecycle
field. TD-021 is repaid by that being *confirmed against a real consumer
and written down*, not by a registry appearing. If 16C's design work shows
a fingerprint reference is genuinely unusable from a config, that is an
ADR-0024 revisit and a maintainer decision — not something 16C may do
inline.

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

### Sprint 049 disposition (2026-09-02)

**Partially addressed, not resolved.** ADR-0029's promoted-artifact
parameter format (`research/datasets/promoted_artifact.py`,
`research/predictive/promotion/parameters.py`) gives **promoted** artifacts a
stability guarantee this entry originally asked for: they are plain-number
JSON, portable across scikit-learn upgrades, human-readable, and inspectable
without installing anything. That resolves the repayment trigger's *first*
branch ("model promotion") but not its second: **research-run blobs
(`models/fold_{n}.bin`) are completely unchanged** — still opaque joblib,
still version-tagged, still non-reloadable by any workflow except the one
narrow promotion-time read ADR-0023 §7 was amended for (ADR-0029 §7). A run
that is never promoted is exactly as opaque as it was before this sprint.
Do not describe TD-022 as repaid; the durable-portability guarantee exists
only for artifacts that have gone through `promote_predictive_run`.

### Related Tasks

- `TECHNICAL_DEBT.md` §6 Phase 10 planned boundaries (now live)
- `SPRINT_040.md` §8
- ADR-0023 §7
- `docs/adr/ADR-0029-promoted-predictive-artifact.md` — the partial
  repayment mechanism (Sprint 049)
- `docs/reference/modules/PREDICTIVE_PROMOTION.md`

### Planned repayment route (2026-09-04)

ROADMAP §13H increment **16C — Signal Quality Scoring** (phase APPROVED,
increment not planned, no sprint open) is the demonstrated need behind this
entry's second repayment branch. 16C makes a fitted scorer something a
Strategy Research config refers to and a simulation depends on, which is
exactly the situation in which "the framework makes no promise that a blob
can be loaded" stops being a harmless research-time property.

16C's completion criteria therefore require that the score path 16C
defines depends **only** on artifacts with a stated durability guarantee —
either the ADR-0029 portable parameter format, or a materialized score
column persisted with its own provenance. No part of 16C may depend on
reloading `models/fold_{n}.bin`; the Sprint 049 disposition's boundary
("research-run blobs are completely unchanged") is preserved, not widened.
TD-022's residual — opacity of *never-promoted* research-run blobs —
remains open after 16C and is not claimed as repaid.

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

## TD-025 — Boundary Test Is Structurally Blind to Dynamically Loaded Strategy Files

```text
Status: ACCEPTED
Priority: LOW
Domain: apps/cli / Architecture Boundary Tests
Introduced: Sprint 047 (2026-09-01)
Target Review: If the loader is ever extended to run untrusted or
  third-party strategies (see Repayment Trigger)
Owner: Unassigned
```

### Accepted Shortcut

`tests/unit/test_apps_boundaries.py` is a static AST scan of `apps/cli/src`.
`trading_cli/strategy_loader.py` (S047-T002, ADR-0027) loads a
`research.strategy.strategy_file` path at runtime via
`importlib.util.spec_from_file_location`; that file is not part of
`apps/cli/src`, is never scanned, and can import anything the operator's
own Python environment can import. A green boundary test is not, and never
was intended to be, proof that nothing outside the allow-list was imported
by a loaded strategy at runtime.

### Reason

ADR-0027 Sec6 decided this deliberately, not by oversight: the boundary
governs what this repository ships and CI can enforce, a typical strategy
file lives in gitignored `user_data/` and CI never sees it, the file is the
operator's own trusted code running with their own privileges (no security
benefit from restricting it), and enforcing it would require import hooks or
AST rewriting at load time -- real machinery, protecting nothing.

### Consequences

- A loaded strategy file can import anything, including
  `trading_framework.research.*`/`trading_framework.execution.*` modules
  `apps/cli`'s own boundary forbids itself, with no test noticing.
- The advisory convention (an authored strategy should need only
  `trading_framework.model_authoring`, `trading_framework.strategy.*`, and
  `trading_framework.time.models.timeframe`) is documented in
  `docs/reference/modules/STRATEGY_AUTHORING.md`, not enforced anywhere.

### Safe Operating Boundary

Nobody may read a green `test_cli_only_imports_application_layer` result as
evidence about what a *loaded* strategy file imports -- it only proves
`apps/cli/src` itself stayed within the allow-list.

### Repayment Trigger

The loader is ever extended to run strategy files that are not the
operator's own trusted code (e.g. a shared strategy marketplace, a
third-party plugin mechanism) -- at that point this becomes a real gap
requiring a real mechanism (import hooks, subprocess isolation, or similar),
not a static scan.

### Repayment Direction

Not designed here; ADR-0027 Sec6 alternative 5 lists sandboxing options
considered and rejected for this sprint's trust model. A future increment
that needs to repay this would need its own ADR.

### Related Tasks

- `docs/adr/ADR-0027-operator-authored-strategy-loading.md` Sec6
- `docs/planning/sprints/S047_WAVE0_DECISIONS.md` D-S047-08
- `tests/unit/test_apps_boundaries.py`

---

## TD-026 — EquityPercentRiskModel Is Static, Authoring-Time Sizing Only

```text
Status: ACCEPTED
Priority: MEDIUM
Domain: Strategy / Research Simulation
Introduced: Sprint 048 (2026-09-01)
Target Review: A demonstrated need for dynamic sizing, or a request to
  cross-validate stop_distance against a bracket's stop_loss_bps
Owner: Unassigned
```

### Accepted Shortcut

`EquityPercentRiskModel` (`strategy/risk_model.py`) resolves
`quantity = (account_equity * risk_percent) / stop_distance` exactly ONCE,
in `__post_init__`. `position_quantity()` always returns that one stored
value, for every entry, for the life of a run. It has no access to running
equity, entry price, realized P&L, or the trade being sized, because
`RiskModel.position_quantity()` takes no arguments (ADR-0028 §4). It also
does not cross-validate `stop_distance` against a `BracketExitModel`'s
`stop_loss_bps` — the risk model has no reference price with which to
convert a basis-point offset into a price-point distance.

### Reason

`RiskModel.position_quantity()`'s no-argument shape is the same MVP
contract from ADR-0016 and is deliberately unchanged by Sprint 048
(D-S048-06 — the Protocol definitions are locked). "Equity-percentage
sizing" can therefore only mean sizing resolved once, at authoring time,
from values the author supplies. This is a real improvement over
hand-computing a lot size, but it is not compounding or
equity-curve-following sizing, and must never be described as such.

### Consequences

- An operator who wants sizing to track realized equity as a run
  progresses cannot get that from this model; they must re-author the
  strategy with new numbers, or accept static sizing.
- `EquityPercentRiskModel.stop_distance` and a paired `BracketExitModel`'s
  `stop_loss_bps` describe the same stop from two directions and can
  silently disagree; the operator owns keeping them consistent (documented
  in `STRATEGY_AUTHORING.md`, not enforced by validation).

### Safe Operating Boundary

No docstring, test name, log line, or guide text may describe
`EquityPercentRiskModel` as dynamic, compounding, or
equity-curve-following. No workflow may assume `stop_distance` and a
bracket's `stop_loss_bps` are cross-validated — they are not.

### Repayment Trigger

Dynamic sizing requires passing simulation state into
`position_quantity()` — a `RiskModel` protocol change also affecting the
paper broker and live execution runtime
(`execution/runtime/strategy_orders.py`,
`execution/broker_sim/paper_broker.py`) — a separate increment with its
own ADR. The stop-distance/stop_loss_bps cross-validation is a smaller,
independent follow-on once a reference price is available to convert
between them.

### Repayment Direction

Design the dynamic-sizing `RiskModel` protocol change through its own ADR,
covering research simulation, paper broker and live execution impact
together rather than widening the Protocol as a side effect of a research
sprint. The cross-validation helper (if pursued) does not require a
Protocol change and can land independently.

### Related Tasks

- `docs/adr/ADR-0028-bracket-exit-and-equity-relative-sizing.md` §4
- `docs/planning/sprints/S048_WAVE0_DECISIONS.md` D-S048-05
- `src/trading_framework/strategy/risk_model.py`
- `tests/unit/strategy/test_risk_model.py`

---

## TD-027 — Robustness Delay Stress Rejects Bracket Exits

```text
Status: ACCEPTED
Priority: MEDIUM
Domain: Research Robustness / Strategy Research
Introduced: Sprint 048 (2026-09-01)
Target Review: First request to stress a bracket strategy
Owner: Unassigned
```

### Accepted Shortcut

`research/robustness/stress.py::apply_stress_strategy_model` (the delay stress
dimension) raises `ValidationError` for any `BracketExitModel`, naming the
model and the reason, instead of defining a delay semantics for it.

### Reason

"Delay a price-triggered exit by N bars" has no obviously correct meaning: a
bracket's exit is driven by price (stop/target trigger), not by a fixed bar
offset, so there is nothing analogous to `FixedBarsExitModel.exit_after_bars`
to extend. Inventing a semantic here would be an unreviewed research-semantics
decision smuggled into an engine sprint (D-S048-08, D-S048-09).

### Consequences

- An operator cannot run the entry/exit delay stress dimension against a
  bracket strategy; the scenario fails fast with an explicit error instead of
  silently producing a meaningless result.
- Commission/slippage-multiplier and post-process (remove-top-N) stress
  dimensions are unaffected — they do not touch the exit model.

### Safe Operating Boundary

No workflow may assume the delay stress dimension works for a
`BracketExitModel` strategy. The rejection is deliberate, not a bug.

### Repayment Trigger

The first request to stress a bracket strategy's entry/exit timing, or the
bracket-parameter stress dimensions (stressing `stop_loss_bps` /
`take_profit_bps`) named as a Sprint 048 follow-on.

### Repayment Direction

Design a bracket-aware stress dimension (e.g. widening/narrowing
`stop_loss_bps` / `take_profit_bps`) through its own ADR/Wave 0 decision
rather than overloading "delay by N bars".

### Related Tasks

- `docs/planning/sprints/S048_WAVE0_DECISIONS.md` D-S048-08, D-S048-09
- `src/trading_framework/research/robustness/stress.py`
- `tests/unit/research/robustness/test_stress.py`

---

## TD-028 — No Independent Reference Implementation for the Bracket Kernel

```text
Status: ACCEPTED
Priority: MEDIUM
Domain: Research Simulation
Introduced: Sprint 048 (2026-09-01)
Target Review: First bracket-path numerical bug, or first change to bracket
  fill semantics
Owner: Unassigned
```

### Accepted Shortcut

`research/simulation/kernels/bracket.py` (Sprint 048 Wave 2) will have no
Python cross-check counterpart, unlike `kernels/fixed_bars.py`, which is
verified against `kernels/reference.py`. `kernels/reference.py` stays typed
to `FixedBarsExitModel` / `FixedQuantityRiskModel` and is not widened.

### Reason

A second reference implementation doubles the surface that must stay
numerically consistent, for a new path with no legacy behaviour to protect.
The bracket kernel is instead verified against hand-computed fixtures whose
expected fill prices are written out by hand in the test, never derived from
the implementation (D-S048-09, D-S048-10).

### Consequences

- A numerical bug in the bracket kernel has one fewer independent check than
  the fixed-bars path has.
- `kernels/reference.py` is explicitly typed to `FixedBarsExitModel` /
  `FixedQuantityRiskModel`; passing a `BracketExitModel` through it is a type
  error and would fail loudly (its `default_exit_reason` attribute lookup
  raises `AttributeError`), not silently misbehave.

### Safe Operating Boundary

No workflow may treat `kernels/reference.py` as a cross-check for
`kernels/bracket.py` results. The hand-computed fixtures are the only
independent check until this is repaid.

### Repayment Trigger

The first numerically surprising bracket-path result, or the first change to
bracket fill semantics (D-S048-04's locked stop/target/timeout rules).

### Repayment Direction

Add a Python reference implementation of the bracket kernel, built
independently from `kernels/bracket.py`, and cross-check it the same way
`kernels/fixed_bars.py` is cross-checked today.

### Related Tasks

- `docs/planning/sprints/S048_WAVE0_DECISIONS.md` D-S048-08, D-S048-09
- `src/trading_framework/research/simulation/kernels/reference.py`
- `src/trading_framework/research/simulation/kernels/bracket.py` (Sprint 048
  Wave 2, not yet built as of this entry)

---

## TD-029 — Tree and Neural Predictive Model Promotion Is Deferred to a Version-Pinned Joblib Path

```text
Status: ACCEPTED
Priority: LOW
Domain: Predictive Research / Model Promotion
Introduced: Sprint 049 (2026-09-02)
Target Review: Once linear/logistic promotion (ADR-0029) is proven end to
  end, or the first real BTC candidate model that shows structure is a tree
  model
Owner: Unassigned
```

### Accepted Shortcut

`promote_predictive_run` and `load_promoted_artifact` support exactly three
model families — `sklearn.ridge`, `sklearn.elastic_net`, `sklearn.logistic`
(`research/datasets/promoted_artifact.py::MODEL_FAMILY_ALLOWLIST`,
`research/predictive/promotion/evaluator.py::MODEL_FAMILY_ALLOWLIST`).
Attempting to promote a tree family (XGBoost, LightGBM, CatBoost) or a
neural family (torch feedforward/LSTM/GRU) raises
`PromotedFamilyUnsupportedError` (`infrastructure/ml/promotion.py`), naming
the family, and writes nothing. No implementation of the tree/neural
promotion path exists anywhere.

### Reason

The v1 promoted-artifact format (ADR-0029) is a closed-form NumPy expression
that only linear/logistic families reduce to. Tree ensembles and neural
networks have no equivalent closed form; promoting them would require a
different, version-pinned serialization path (most likely a pinned
joblib/ONNX-style blob per ADR-0029's Alternatives Considered), which would
put scikit-learn, XGBoost/LightGBM/CatBoost, or torch into the dry-run/live
runtime image — the exact outcome the NumPy parameter-file format exists to
avoid. Building that second path in the same sprint that proves the first
one would have doubled the sprint's risk surface for no immediate benefit,
per ADR-0029's Alternatives Considered table ("Version-pinned joblib blob
for v1... Deferred, not rejected: it is the intended path for tree and
neural families once this mechanism is proven").

### Consequences

- An operator whose best-performing BTC candidate model is a tree or neural
  family cannot promote it today; they hit a named refusal, not a silent
  failure or an unsupported-forever wall.
- The PRD's v1 scope is smaller than Predictive Research's full family
  coverage (Sprints 042/043 shipped tree and neural training; promotion
  does not yet reach them).

### Safe Operating Boundary

No workflow may assume tree or neural families are promotable. The refusal
in `infrastructure/ml/promotion.py::require_supported_model_family` is the
only gate; nothing bypasses it.

### Repayment Trigger

Either linear/logistic promotion has been exercised end to end (proving the
mechanism, the store, and the parity harness work) and Predictive Research
research priorities turn to it next, or a real candidate model with genuine
BTC structure turns out to be a tree model, making the refusal an active
blocker rather than a documented gap.

### Repayment Direction

Design a version-pinned joblib (or equivalent) promotion path for tree and
neural families through its own ADR — it changes the runtime deployment
footprint (ADR-0029's whole point was keeping that footprint at zero for
linear/logistic), so it cannot be added as a side effect of another sprint.
The design should reuse `infrastructure/ml/promotion.py`'s guard ordering
(family allow-list check, then a version guard, before any unpickling) as
its starting shape.

### Related Tasks

- `docs/adr/ADR-0029-promoted-predictive-artifact.md` — Alternatives
  Considered ("Version-pinned joblib blob for v1")
- `docs/reference/modules/PREDICTIVE_PROMOTION.md` §6
- `src/trading_framework/infrastructure/ml/promotion.py`

### Planned repayment route (2026-09-04)

ROADMAP §13H increment **16C — Signal Quality Scoring** (phase APPROVED,
increment not planned) collides with this entry directly. 16C's premise is
training and comparing estimator families — including the tree and neural
families Sprints 042/043 already ship — and using the winner's score to gate
a strategy. Under today's allow-list, only `sklearn.ridge`,
`sklearn.elastic_net` and `sklearn.logistic` can ever reach a promoted
artifact, so a tree scorer could win 16C's comparison and still be unusable
downstream. This entry's repayment trigger ("a real candidate model with
genuine BTC structure turns out to be a tree model") is therefore reachable
*inside* 16C.

**Maintainer decision (2026-09-04, ROADMAP §13H.12 Q6): 16C's scope stays
narrow.** 16C's v1 estimator comparison is explicitly restricted to
promotable families; tree and neural scorers are **research-only** and are
refused **at config load time, with a named error**, if used as a strategy
gate. **TD-029's repayment moves to increment 16G**, where it is restated
and owned. TD-029 stays ACCEPTED longer, but its safe operating boundary is
unchanged and its named refusal in
`infrastructure/ml/promotion.py::require_supported_model_family` stays in
place until an ADR replaces it.

The rejected alternative is recorded for history: growing 16C to also design
the version-pinned joblib/ONNX-style promotion path (repaying TD-029 in 16C)
was **considered and not chosen**, because it lands a
runtime-deployment-footprint change inside the phase's central vertical
slice. It is not a live option; reopening it requires a new maintainer
decision.

When 16G does repay this entry, the design must still reuse
`infrastructure/ml/promotion.py::require_supported_model_family`'s guard
ordering, as this entry's Repayment Direction already prescribes, and must
go through its own ADR.

---

## TD-030 — Root `.gitignore` Does Not Cover Nested `<subdir>/user_data/` Directories

```text
Status: ACCEPTED
Priority: LOW
Domain: Repository Hygiene / Data Boundary (ADR-0002)
Introduced: Sprint 051 (2026-09-03), discovered during S051-T002
Target Review: Opportunistic — next time a nested user_data/ directory is
  created under any workspace member (apps/cli, apps/dashboard, etc.)
Owner: Unassigned
```

### Accepted Shortcut

The root `.gitignore`'s `user_data/**` pattern is anchored to the repo root
(git rewrites a mid-string-slash pattern as relative to the `.gitignore`
file's own directory, per git's own documented semantics). It does **not**
match a nested `<subdir>/user_data/**` path, such as `apps/cli/user_data/`.
Confirmed live during S051-T002: running the Binance importer from `apps/cli`
as the working directory (instead of the repo root) resolved
`storage_root: user_data/workspace` to `apps/cli/user_data/workspace`, and
`git status` showed those files as untracked, not ignored.

### Reason

ADR-0002 (separate `src` and `user_data`) establishes `user_data/` as the
operator's local, non-committed workspace at the repo root. No workspace
member (`apps/cli`, `apps/dashboard`, `scripts/`, etc.) is expected to have
its own `user_data/` directory — the S051-T002 occurrence was an operator
invocation mistake (wrong working directory), not a designed nested-workspace
feature. Because the mistake is easy to make (any relative `storage_root`
path resolves against process `cwd`, not repo root) and the consequence
(accidentally committing real market data or credentials) is expensive, the
gap is worth tracking even though no incident occurred this time — the
misplaced directory was caught and deleted before anything was staged.

### Consequences

- A future operator or agent invoking any CLI command with a relative
  `storage_root` from a non-repo-root working directory could produce a
  nested `<subdir>/user_data/` directory that `git status` reports as
  untracked rather than ignored, risking an accidental `git add -A` capture
  of market data or, worse, a locally-configured credential.
- No functional code is affected; this is a pure repository-hygiene gap.

### Safe Operating Boundary

Invoke CLI commands that accept a `storage_root` from the repository root, or
pass an absolute `storage_root` path — both avoid the gap entirely without
requiring the `.gitignore` fix. `apps/cli/CLAUDE.md` now documents this as an
operator-facing gotcha (added in S051-T002, PR #400).

### Repayment Trigger

Opportunistic — no functional risk forces this. Repay whenever a nested
`user_data/` directory is next created under any workspace member, or during
a routine `.gitignore` audit.

### Repayment Direction

Add an additional pattern to the root `.gitignore` covering nested
`user_data/` directories at any depth (e.g. `**/user_data/` in addition to
the existing `user_data/**`), and add a regression check (a test or a
pre-commit hook) asserting no `user_data/` directory anywhere in the tree is
ever tracked, rather than relying on operators invoking commands from the
correct working directory.

### Related Tasks

- `docs/planning/sprints/S051_BTC_DATA_INVENTORY.md` §5 — where this was
  discovered and the false start it caused
- `src/trading_framework/apps/cli/CLAUDE.md` — the operator-facing gotcha note
- `.gitignore` (root)

---

## TD-031 — No Loader Turns a Declared `signal_model_file` Into a `SignalModelDefinition`

```text
Status: ACCEPTED
Priority: MEDIUM
Domain: Predictive Research / Phase 16 (Sprint 056, increment 16B)
Introduced: Sprint 056 (2026-09-05), discovered during S056-T004 QA
Target Review: Before 16C (Signal Quality Scoring) is planned, or any CLI-
  driven `signal_occurrences` predictive study is requested
Owner: Unassigned
```

### Accepted Shortcut

`SampleSpec.signal_model_file` (ADR-0031) declares a path to an
operator-authored Signal Model, but no code anywhere in the framework turns
that path into a `SignalModelDefinition`. `BuildPredictiveDatasetRequest`
instead gained a `signal_model: SignalModelDefinition | None` seam — the
same externally-supplied-object pattern already used by `preloaded_bars`
and `preloaded_view` — so a caller who already holds the object in memory
(a test, a script) can supply it directly. Neither real caller in the repo
(`apps/cli/src/trading_cli/commands/research.py::_run_predictive`,
`scripts/predictive_research/build_predictive_dataset.py`) passes it today.

### Reason

Signal Models are authored as Python DSL calls (`build_strategy()`-style),
not YAML/JSON like `PredictiveStudySpec` itself, so a file-based loader is a
distinct trust-model decision — akin to `apps/cli`'s `strategy_file` /
ADR-0027 — not a small addition. Sprint 056 / S056-T004's own acceptance
criteria (D-S056-08) only require resolving `signal_occurrences` against a
synthetic, in-memory fixture; no task in the sprint asks for a file-driven
CLI path. Building the loader inside S056-T004 would have smuggled a new
trust-model decision into a task scoped as a resolution mechanism.

### Consequences

- An operator cannot run a real (non-synthetic-fixture) `signal_occurrences`
  predictive study through `trading-cli research run` today — a
  `signal_occurrences` spec with no `signal_model` object supplied fails
  fast with a named `PredictiveDatasetError` identifying the missing input
  (not a silent no-op, not an obscure crash).
- Phase 16 increment 16C (Signal Quality Scoring, `docs/planning/roadmap/PHASE_16_QUANT_WORKBENCH.md`
  §13H.3) is the first increment that plausibly needs a real, file-driven
  `signal_occurrences` study and does not yet have a way to get one.

### Safe Operating Boundary

No workflow may assume `signal_model_file` alone is sufficient to resolve a
`signal_occurrences` sample. Every current caller must supply
`BuildPredictiveDatasetRequest.signal_model` explicitly, in-process.

### Repayment Trigger

16C is planned, or an operator needs a CLI-driven `signal_occurrences`
study before then.

### Repayment Direction

Design a `signal_model_file` loader through its own decision record (Wave 0
decision or ADR, depending on how much a trust-model question it raises by
then) — do not add it as a side effect of another task. The likely shape
mirrors ADR-0027's `strategy_file` convention (a fixed entry-point function
convention, an explicit trust-model statement, a pre-flight error taxonomy).

### Related Documents

- `docs/adr/ADR-0031-predictive-sample-spec-and-task.md`
- `docs/planning/sprints/SPRINT_056.md` (S056-T004)
- `docs/planning/roadmap/PHASE_16_QUANT_WORKBENCH.md` §13H.3 (16C)
- `docs/adr/ADR-0027-operator-authored-strategy-loading.md` (the precedent
  this loader would likely follow)

### Related Tasks

- PR #450 (`feat/predictive-signal-occurrence-samples`) — where this gap
  was found and deliberately left open, flagged in the PR description

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
