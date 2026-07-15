# Trading Research Framework

# ROADMAP.md

## 1. Purpose

This document defines the strategic development roadmap of the Trading Research Framework.

It describes:

- major development phases,
- expected capabilities,
- dependencies between phases,
- completion criteria,
- major risks,
- intentionally deferred work.

The roadmap defines direction.

It is not:

- a detailed task list,
- a sprint plan,
- a replacement for GitHub Issues,
- a fixed delivery schedule,
- a promise that later phases will be implemented exactly as currently described.

Detailed planning should cover only the current and next phase.

---

## 2. Roadmap Principles

The roadmap follows these rules:

1. Deliver small vertical slices.
2. Validate architecture through implementation.
3. Keep the modular monolith until demonstrated needs justify distribution.
4. Preserve the separation between `src/` and `user_data/`.
5. Preserve the independence of:
   - Signal Research,
   - Strategy Research,
   - Strategy Execution.
6. Prefer correctness and reproducibility over raw speed.
7. Do not introduce infrastructure for hypothetical scale.
8. Update the roadmap when implementation produces new evidence.
9. Keep later phases directional rather than over-specified.
10. Treat rejected or deferred ideas as valid learning outcomes.
11. **Do not retroactively rewrite completed sprint scope.** Clarify actual delivery; add new increments for future work (see **§3**).

---

## 3. Capability Tracks and Phase Overview

The project no longer advances as a single linear pipeline:

```text
Market Data → Market Analysis → Signal Research → Strategy Research → Execution
```

Research can progress on **currently available** data types. Market Data expansion is justified by concrete research or execution need, not by collecting everything upfront.

### Parallel tracks

```text
Foundation Track
  Phase 0 — Project Governance                    COMPLETE
  Phase 1 — Repository Foundation               COMPLETE

Data Capability Track
  Phase 2A — OHLCV Market Data MVP                COMPLETE  (Sprint 002; roadmap label: Phase 2)
  Phase 2B — Historical Archive Import Foundation COMPLETE  (Sprint 011 trades; OHLCV archive PLANNED)
  Phase 2C — Trades and Quotes                    COMPLETE  (2C.1 + 2C.4 on main; 2C.2 quotes PLANNED)
  Phase 2D — Options Snapshot Data                PLANNED
  Phase 2E — Live Market Data                     GATED

Research Capability Track
  Phase 3  — Market Analysis Engine MVP           COMPLETE
  Phase 4A — Bar-Based and MTF Market Analysis    COMPLETE  (Sprints 004–006)
  Phase 4B — Orderflow Market Analysis            PLANNED
  Phase 4C — Options-Derived Market Analysis      PLANNED
  Phase 5  — Signal Research MVP                  COMPLETE  (Sprints 008–010)
  Phase 6A — OHLCV Strategy Research MVP          COMPLETE  (Sprints 013–014)
  Phase 6B — Multi-Data Strategy Research         PLANNED
  Phase 7  — Robustness Research                  COMPLETE  (Sprint 016)

Execution Capability Track
  Phase 8 — Replay and Paper Execution            PLANNED
  Phase 9 — Live and Multi-Account Execution        PLANNED
```

### Cross-track dependencies (summary)

```text
Phase 2A ──┬── Phase 5 — Signal Research
           └── Phase 6A — OHLCV Strategy Research

Phase 2C → Phase 4B → Phase 6B
Phase 2D → Phase 4C → Phase 6B
```

Strategy Research (**Phase 6A**) may start on OHLCV without waiting for trades or options. That validates Strategy contracts first; it does **not** mean target data coverage is complete (**§15.3**).

Completed phases retain their historical sprint records. New increments (2B, 4B, 6A, …) extend capability without rewriting Sprint 002–010 scope.

Market Data policy (facts not indicators, vendor independence): **§14 Research Data Strategy**.

Test data tiers and live-data gate: **§15**.

**Recommended next increment:** **Phase 8 Replay and Paper Execution** (candidate) — see `ROADMAP.md` §12. Deferred: Phase 4B orderflow, Phase 6B multi-data, PBO/CSCV (separate ADR).

---

# 4. Phase 0 — Project Governance

## Purpose

Create the minimum project-management system required for iterative development.

## Expected Capabilities

- strategic roadmap,
- concise current-status reporting,
- problem registry,
- idea inbox,
- technical-debt register,
- sprint planning and retrospectives,
- issue and PR conventions,
- ADR process,
- GitHub Project status model.

## Expected Outputs

```text
PROJECT_MANAGEMENT.md
ROADMAP.md
CURRENT_STATUS.md
PROBLEM_REGISTRY.md
IDEA_INBOX.md
TECHNICAL_DEBT.md
docs/planning/sprints/
docs/adr/
```

## Completion Criteria

- planning documents exist and have clear ownership,
- work statuses are defined,
- Definition of Ready and Definition of Done are defined,
- current and next phases can be planned without duplicating task state,
- GitHub Issues and Projects can become the operational source of truth,
- architectural decisions are separated from tasks and ideas.

**Progress (2026-06-19):** planning documents and Sprint 001 are in place. Remaining items: GitHub Project configuration, issue templates, and individual ADR files (started via `docs/adr/README.md`).

## Dependencies

None.

## Main Risks

- over-engineering project governance,
- duplicating status between Markdown and GitHub,
- creating detailed plans for distant phases,
- allowing planning files to become stale.

## Out of Scope

- detailed issues for every future phase,
- fixed dates for the full roadmap,
- productivity metrics based on lines of code or commit count.

---

# 5. Phase 1 — Repository Foundation

## Purpose

Create the implementation foundation shared by every domain.

## Expected Capabilities

- Python package structure,
- `src/` and `user_data/` separation,
- unit, integration and end-to-end test structure,
- Ruff formatting and linting,
- mypy type checking,
- pytest configuration,
- CI pipeline,
- core identifiers and errors,
- Timeframe and timestamp primitives,
- Clock contract,
- configuration loading,
- logging foundation,
- architecture-document references for AI agents.

## Primary Vertical Slice

```text
Repository
    ↓
Installable package
    ↓
Static checks
    ↓
Unit tests
    ↓
CI validation
```

## Completion Criteria

- project can be installed reproducibly,
- CI runs linting, formatting checks, typing and tests,
- domain packages exist without speculative implementation,
- `src/` does not import concrete `user_data/` modules,
- naive timestamps are rejected in core time models,
- one minimal configuration can be loaded and validated,
- framework tests do not require external systems.

## Dependencies

- Phase 0 planning conventions.

## Active Sprint

Sprint 001 implements this phase:

```text
docs/planning/sprints/SPRINT_001.md
```

## Main Risks

- creating empty abstractions for distant requirements,
- turning `core/` into a utilities dumping ground,
- adding web, database or distributed infrastructure prematurely,
- coupling configuration to implementation details.

## Out of Scope

- provider integrations,
- full Market Data workflows,
- Market Analysis Engine,
- research workflows,
- broker execution.

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

---

# 7. Phase 3 — Market Analysis Engine MVP

**Status:** COMPLETED in Sprint 003 (2026-07-12). Integration branch: `sprint/market-analysis-mvp`.  
ADRs: `docs/adr/ADR-0005-market-analysis-domain-and-taxonomy.md`, ADR-MA-001–011.

## Purpose

Calculate reusable analytical components through explicit dependency contracts.

## Expected Capabilities

- generic Market Analysis component contract,
- Component Registry,
- `ComponentRequest`,
- dependency DAG,
- cycle detection,
- lazy execution,
- shared-node deduplication,
- component fingerprinting,
- cache identity,
- typed analytical results,
- one complete component vertical slice.

## Recommended First Components

```text
Feature:
ATR

Structure:
Pivot or Session Range

State:
simple volatility or trend state
```

Only one complete vertical slice is required initially.

## Primary Flow

```text
Published DatasetRef
        ↓
ComponentRequest
        ↓
Dependency Resolution
        ↓
Execution Plan
        ↓
Component Result
        ↓
Lineage and Cache Identity
```

## Completion Criteria

Sprint 003 assessment (2026-07-12):

- [x] a component declares all dependencies before execution,
- [x] equivalent deterministic nodes are calculated once,
- [x] hidden component calls inside `compute()` are rejected by convention and tests,
- [x] cache identity includes dataset and implementation identity,
- [ ] working components can be loaded from controlled user space (deferred — no `user_data/` loader in MVP),
- [ ] research use of a working component stores an implementation fingerprint (partial — parameter identity only; PRB-002 remainder),
- [x] the engine remains independent from Market Model and Signal Model semantics.

## Dependencies

- published Market Dataset access,
- stable time primitives,
- configuration contracts.

## Main Risks

- overbuilding graph infrastructure,
- forcing all payloads into one scalar representation,
- hidden data access from components,
- premature permanent directory taxonomy,
- cache reuse with incomplete identity.

## Out of Scope

- broad indicator library,
- advanced multitimeframe alignment,
- Signal Research,
- model ranking,
- distributed calculation.

---

# 8. Market Analysis Capability — Phase 4 Family

## Purpose

Support timeframe-aware Market Analysis safely and reproducibly.

Phase 4 is a **family of increments**, not a single delivery:

```text
Phase 4A — Bar-Based and Multitimeframe Foundation     COMPLETE
Phase 4B — Orderflow Market Analysis                   PLANNED
Phase 4C — Options-Derived Market Analysis             PLANNED
```

Sprints 004–006 delivered Phase 4A. Sprints 007–010 belong to other phases (007 optional catalog; 008–010 Signal Research / Phase 5). Historical sprint files are not rewritten.

---

## Phase 4A — Bar-Based and Multitimeframe Foundation (COMPLETE)

### Sprint increments (historical)

| Sprint | Increment | Focus |
|--------|-----------|-------|
| 004 | Multitimeframe Foundation MVP | DONE — `SPRINT_004.md` |
| 005 | Calendar + Pivot + visual inspection | DONE — `SPRINT_005.md` |
| 006 | Declarative models | DONE — `SPRINT_006.md` |
| 007 | Research-enabling catalog (conditional) | SKIPPED — scope gate — `SPRINT_007.md` |

**Direction (binding for 004–006):** `docs/planning/sprints/PHASE_4_5_SPRINT_DIRECTION.md`

### Delivered capabilities

- source, computation and evaluation timeframe distinction,
- explicit resampling nodes,
- derived dataset lineage,
- `observed_at`,
- `available_at`,
- `LAST_CLOSED_BAR`,
- backward as-of alignment,
- intrabar component contract,
- Trading Session integration,
- Trading Calendar integration,
- controlled `MarketFieldReference`,
- Market Model expression evaluation,
- Signal Model expression evaluation,
- initial reusable Features, Structures and States.

## Suggested Initial Analytical Set

```text
Features:
- ATR
- slope
- wick ratio
- distance to level

Structures:
- Pivot
- HH / HL / LH / LL
- Session Range
- Liquidity Sweep

States:
- trend / range
- volatility state
- active session state
```

This is an initial research-enabling set, not a permanent mandatory taxonomy.

## Completion Criteria

- higher-timeframe final values are unavailable before bar close,
- resampling is explicit and reused,
- temporal alignment is covered by regression tests,
- DST and session boundaries are tested,
- Market Models and Signal Models remain declarative,
- models cannot access arbitrary DataFrames,
- one-condition Market and Signal Models are supported,
- framework and local components use the same public contracts.

## Dependencies

- Market Data MVP,
- Market Analysis Engine MVP,
- Time Model and calendars.

## Main Risks

- look-ahead bias,
- timestamp-boundary ambiguity,
- incorrect session semantics,
- mixing implementation patterns with output categories,
- excessive early taxonomy,
- divergence between Research and runtime semantics.

## Out of Scope (Phase 4A)

- unrestricted component grid searches,
- complete Strategy Research,
- live broker execution,
- orderflow and options-derived analysis (Phase 4B/4C).

---

## Phase 4B — Orderflow Market Analysis (PLANNED)

Orderflow belongs in **Market Analysis**, not Market Data storage of derived indicators.

```text
MarketTrade / MarketQuote (Phase 2C)
    ↓
Market Data normalization
    ↓
Market Analysis components
    ↓
orderflow Features / Structures / States
```

**Features (examples):** traded volume, buy/sell volume, delta, CVD, imbalance, execution intensity, large-trade concentration, absorption ratio.

**Structures (examples):** footprint bar, imbalance cluster, absorption event, aggressive sweep, volume node.

**States (examples):** buying/selling pressure, balanced flow, aggressive expansion, absorption, liquidity exhaustion.

Not one monolithic indicator or one giant DataFrame.

### Dependencies

- Phase 2C (`MarketTrade` minimum).

---

## Phase 4C — Options-Derived Market Analysis (PLANNED)

Interpretation of options context belongs in Market Analysis.

```text
OptionsSnapshot (Phase 2D)
    ↓
Options-derived Features
    ↓
Options Structures / States
    ↓
Market Model inputs
```

**Examples:** net gamma proxy, gamma concentration by strike, zero-gamma estimate, call/put wall, IV regime, expiration concentration, positioning state.

Market Models compose finished outputs (e.g. `negative_gamma_state AND price_below_zero_gamma`). Market Models do **not** compute GEX internally.

### Dependencies

- Phase 2D (options snapshots).

---

# 9. Phase 5 — Signal Research MVP

## Purpose

Evaluate Market Models and Signal Models independently or together without requiring a complete Strategy Model.

## Supported Scopes

```text
MARKET_MODEL_ONLY
SIGNAL_MODEL_ONLY
MARKET_AND_SIGNAL
```

## Expected Capabilities

- explicit Signal Research configuration,
- bounded experiment expansion,
- Market Model result materialization,
- `SignalOccurrence`,
- forward-return calculation,
- MFE and MAE,
- event frequency,
- persistent Signal Research Dataset,
- reusable analytics,
- sample-size filters,
- timeframe and period comparisons,
- computation/analytics separation.

## Primary Flows

```text
Market Model only
        ↓
Future Market Behaviour
```

```text
Signal Model only
        ↓
SignalOccurrence
        ↓
Forward Behaviour
```

```text
Market Model × Signal Model
        ↓
Conditional Signal Behaviour
```

## Completion Criteria

- all three scopes work explicitly,
- Signal Research does not require Exit or Risk Models,
- new analytics do not rerun unchanged computation,
- stored datasets remain queryable without loading implementation classes,
- independent experiment alternatives are not confused with logical `OR`,
- shared analytical dependencies are reused,
- run identity includes datasets, models, fingerprints and time semantics.

## Dependencies

- model expression evaluation,
- Market Analysis results,
- published datasets,
- persistent Research Dataset contracts.

## Main Risks

- accidental Cartesian-product growth,
- weak lineage,
- multiple-testing blindness,
- recomputing results for every report,
- treating one good result as validated edge.

## Out of Scope

- complete strategy PnL,
- position sizing,
- broker fill simulation,
- deployment decisions,
- automatic strategy promotion.

---

# 10. Strategy Research — Phase 6 Family

Phase 6 has started. Scope is split so OHLCV strategy research can proceed without waiting for trades or options.

```text
Phase 6A — OHLCV Strategy Research MVP     COMPLETE  (Sprints 013–014)
Phase 6B — Multi-Data Strategy Research    PLANNED
```

---

## Phase 6A — OHLCV Strategy Research MVP (COMPLETE)

**Delivered:** Sprints 013–014 on `main` (2026-07-14). Dashboard Phase B (FastAPI) deferred.

### Purpose

Validate Strategy Model and historical simulation contracts using **currently supported bar-based market facts** (Phase 2A).

### Strategy composition

```text
Market Model × Signal Model × Exit Model × Risk Model
```

Position sizing remains part of the Risk Model in Version 1.

### Expected capabilities

- Exit Model and Risk Model contracts,
- Strategy Model definition,
- minimal backtest or historical simulation engine,
- order and fill assumptions, commissions and slippage,
- trade-level results and equity history,
- persistent Strategy Research Dataset,
- basic strategy analytics and eligibility filters.

### Completion criteria

- complete Strategy Models can be simulated on OHLCV-backed facts,
- simulation assumptions are part of run identity,
- Strategy Research does not require a Signal Research run,
- Replay Execution remains separate.

**Important:** completing Phase 6A validates the **first Strategy Research vertical slice**. It does **not** mean target research-data coverage is complete.

### Dependencies

- Phase 2A, Phase 4A, Phase 5 (reusable upstream artifacts),
- Signal and Market Model contracts.

### Main risks

- monolithic backtest engine,
- unclear fill assumptions,
- conflating batch backtest with runtime replay,
- embedding bar-only assumptions permanently in the simulation engine.

---

## Phase 6B — Multi-Data Strategy Research (PLANNED)

Future extension when Phase 2C/2D and Phase 4B/4C exist:

- orderflow-enhanced strategies,
- options-context-enhanced strategies,
- research datasets with heterogeneous physical schemas,
- verification that simulation does not assume regular bars only.

Detailed design deferred until Phase 6A and data increments justify it.

### Dependencies

- Phase 6A,
- relevant Phase 2C/2D and Phase 4B/4C increments.

---

# 11. Phase 7 — Robustness Research

## Purpose

Assess whether a candidate Strategy Model is **stable enough** to justify paper execution or deeper
validation — not merely which parameter set ranked highest in-sample.

**Sprint plan:** `SPRINT_016.md` · **Wave 0:** `S016_WAVE0_DECISIONS.md` · **ADR:** ADR-0019

## MVP Scope (Sprint 016)

### Experiment Infrastructure

- declarative experiment specification,
- configuration generator (grids, folds, scenarios),
- batch execution via `run_strategy_research`,
- experiment registry and resume after interrupt,
- comparison of multiple experiments.

### Parameter Robustness

- parameter grid sweep,
- configuration ranking,
- neighbor-parameter stability,
- heatmaps,
- isolated-optimum detection.

### Walk-Forward

- rolling and expanding windows,
- train-only parameter selection,
- out-of-sample evaluation per fold,
- stitched OOS equity curve.

### Stress Testing

- commission and slippage scenarios,
- entry and exit delay,
- remove top trades and top days by PnL.

### Statistical Diagnostics

- temporal stability,
- PnL concentration,
- trade bootstrap,
- block bootstrap,
- IS/OOS degradation (walk-forward linked).

### Monte Carlo (trade-level, MVP)

- trade-sequence shuffle (permutation without replacement),
- trade PnL bootstrap (with replacement),
- block bootstrap (session-day blocks),
- equity path envelope (percentile bands, tail probabilities).

Monte Carlo operates on **persisted simulated trades** — not synthetic price paths or order-book
simulation.

### Deliverable

One **Robustness Report** (offline HTML) plus explicit **verdict**: PASS / CONDITIONAL / FAIL with
documented strengths and weaknesses.

## Outside MVP (deferred)

- full order-book simulation, market impact models,
- portfolio-level and cross-asset robustness,
- distributed experiment execution,
- Bayesian and genetic optimization,
- Probability of Backtest Overfitting, CSCV, Deflated Sharpe Ratio, White's Reality Check,
  Hansen's SPA.

## Completion Criteria

Phase 7 MVP is complete when the system can:

- define a reproducible robustness experiment,
- generate and run a parameter sweep with ranking and neighbor stability,
- run rolling and expanding walk-forward with train-only selection and stitched OOS equity,
- execute stress scenarios (costs, delays, trade/day removal),
- run trade shuffle, bootstrap, block bootstrap, and Monte Carlo equity envelopes,
- assess temporal stability, PnL concentration, and IS/OOS degradation,
- emit one coherent Robustness Report with an explicit verdict.

Binding principles (unchanged):

- robustness methods record their assumptions,
- top ranking is **not** treated as validation,
- validation outputs are stored separately from base Strategy Research runs,
- no train/OOS leakage in walk-forward.

## Dependencies

- persistent Strategy Research envelopes (ADR-0016),
- stable strategy metrics and simulation assumptions fingerprint,
- published OHLCV datasets (including continuous NQ, ADR-0018).

## Main Risks

- false confidence from sophisticated statistics,
- misuse of Monte Carlo (mitigated: trade-level only, verdict gates),
- data leakage between train and test periods,
- uncontrolled grid size / runtime explosion,
- robustness analytics coupled to one strategy type only in first slice.

## Out of Scope (phase family)

- automatic live deployment,
- universal hard-coded candidate score,
- distributed research infrastructure without evidence.

---

# 12. Phase 8 — Replay and Paper Execution

## Purpose

Run selected Strategy Models with runtime-style semantics without real-money execution.

## Expected Capabilities

- Replay Clock,
- Replay Execution,
- Paper Execution,
- runtime Market Analysis updates,
- SignalOccurrence processing,
- strategy decisions,
- order lifecycle,
- partial fills,
- positions,
- operational risk controls,
- persistence,
- reconciliation,
- recovery,
- monitoring.

## Completion Criteria

- replay consumes published historical data,
- paper mode consumes live normalized market data,
- Strategy Model is execution-mode independent,
- order transitions are explicit,
- duplicate events are handled safely,
- runtime state survives restart where required,
- broker-like state can be reconciled,
- Research workflow state is not required.

## Dependencies

- stable Strategy Model contracts,
- Market Analysis runtime semantics,
- Event System where justified,
- replay data access,
- execution persistence.

## Main Risks

- divergence between research and runtime behaviour,
- hidden event ordering assumptions,
- insufficient idempotency,
- in-memory-only state,
- operational risk logic leaking into Strategy Risk Models.

## Out of Scope

- real broker orders,
- multi-account orchestration,
- prop-firm-specific controls.

---

# 13. Phase 9 — Live and Multi-Account

## Purpose

Support safe operational execution with real brokers and eventual account scaling.

## Expected Capabilities

- broker adapters,
- live order submission,
- account state,
- durable execution records,
- reconnect and recovery,
- reconciliation,
- monitoring and alerts,
- kill switches,
- account-specific operational limits,
- multi-account coordination,
- strategy allocation,
- audit trails.

## Completion Criteria

To be defined only after Replay and Paper Execution validate runtime contracts.

Minimum future requirements include:

- fail-safe live behaviour,
- no silent order or fill loss,
- deterministic reconciliation policy,
- account isolation,
- explicit deployment and rollback process,
- operational observability.

## Dependencies

- successful replay and paper validation,
- stable broker contracts,
- mature operational controls,
- deployment architecture.

## Main Risks

- financial loss,
- broker/provider inconsistency,
- stale data,
- duplicate orders,
- partial failures across accounts,
- insufficient recovery and monitoring.

## Out of Scope Until Phase Entry

- distributed execution services,
- 50+ account coordination,
- Kubernetes,
- Kafka,
- global high-availability architecture.

---

# 14. Research Data Strategy

**Status:** ACCEPTED (2026-07-12)

## Purpose

The Market Data layer must **not** aim to collect every available market feed.

It must collect the **smallest set of source datasets** from which the framework can derive the largest number of analytical features.

Priorities:

- information density,
- research value,
- long-term maintainability,
- storage efficiency,
- vendor independence.

## Design Principles

### Store facts, not indicators

Persist raw market facts. Compute derived datasets internally.

Examples of derived data (not primary storage formats):

```text
Footprint, Delta, CVD, Volume Profile, Imbalance, Stacked Imbalance,
VWAP, ATR, Session statistics, Gamma Exposure, Dealer positioning
```

### Evaluate every new dataset

Each new source must justify itself:

- additional information,
- implementation complexity,
- storage requirements,
- acquisition cost,
- long-term usefulness.

## Target Research Scope

```text
Instruments:   ES / NQ futures (initial focus)
Style:         day trading
Holding time:  minutes to several hours
Not in scope:  HFT, nanosecond market reconstruction
```

## Futures Data

### Initial source dataset

Primary stored facts:

```text
OHLCV              (Phase 2A — Sprint 002)
Tick Trades        (Phase 2C — primary expansion target)
Instrument Definitions
Market Statistics
Market Status
```

**Tick Trades** are the primary source dataset for order-flow research.

From trades, derive internally:

```text
Footprint, Bid/Ask Delta, CVD, Volume Profile, Imbalance, Stacked Imbalance,
Absorption proxies, Session Delta, Large Trades, Execution statistics
```

### Level 1 Quotes

Secondary dataset. Enables spread, mid price, microprice, quote imbalance, slippage estimation.

### Level 2 Order Book (MBP-10)

**Initially rejected as a primary dataset.**

Reasons:

- ~2 TB/year for NQ (MBP-10),
- high storage cost,
- uncertain marginal research value for the target holding horizon.

Current decision:

- do not build the framework around MBP-10,
- validate research value on selected samples later,
- add only if measurable improvement is demonstrated.

## Order-Flow Philosophy

Reproduce analyses typically available in ATAS-class tooling.

Required analytical outputs (mostly reconstructible from Tick Trades without full L2 history):

```text
Footprint, Delta, CVD, Imbalance, Stacked Imbalance, Volume Profile,
Cluster Analysis, Absorption, Execution Analysis
```

## Options Data

Options are **independent market context**, not a substitute for futures order flow.

Preferred source: **option chain snapshots** (not raw option tick streams).

Preferred frequency: **1 minute**.

Required fields include timestamp, expiry, strike, call/put, bid, ask, volume, open interest, implied volatility, delta, gamma, theta, vega.

Derive internally:

```text
Gamma Exposure, Delta Exposure, Gamma Flip, Call Wall, Put Wall,
IV Surface, IV Skew, Term Structure, Dealer Positioning metrics
```

Raw option trade streams are currently unnecessary.

## Vendor Independence

Providers terminate at **importer boundaries** only. The framework must not depend on any vendor API at runtime.

```text
Databento DBN OHLCV  →  Importer  →  Canonical MarketBar   →  Published Dataset   (Phase 2B)
Databento DBN trades →  Importer  →  Canonical MarketTrade →  Published Dataset   (Phase 2C)
Sierra SCID          →  Importer  →  Canonical MarketTrade →  Published Dataset   (Phase 2C.2+)
```

Each path must produce identical internal models for the same fact type.

## Data Providers

### Futures — Phase 2B / 2C (archive import)

**Databento** — initial archive provider (**Phase 2B**).

Reasons: startup credits, Python API, DBN format, fast pipeline development, clean normalization.

Initial scope:

- archive import workflow on DBN OHLCV (Sprint 011 recommended slice),
- then `MarketTrade` import (**Phase 2C.1**),
- instrument definitions, validation and publication wiring.

### Futures — Phase 2C.2+ (historical expansion)

**Sierra Chart** — acquisition tool only, not a runtime dependency.

```text
Sierra  →  SCID  →  Importer  →  Canonical MarketTrade  →  Validation  →  Parquet  →  Published Dataset
```

Download once, convert once, store locally. Never depend on Sierra afterward.

### Options

**Intrinio** — preferred provider for option chain snapshots (Greeks, IV, open interest).

Plan: start with standard history (~5 years); purchase longer history (e.g. back to 2008) only after validating research value.

## Data Acquisition Roadmap

This is the **Data Capability Track** expansion sequence. It runs in parallel with Research and Execution tracks where dependencies allow.

| Roadmap phase | Provider | Scope | Purpose |
|---------------|----------|-------|---------|
| **2B** | Databento | DBN archive import foundation; first slice: OHLCV bars | Provider-independent import workflow; validate lifecycle on archives |
| **2C.1** | Databento | `MarketTrade` datasets, instrument definitions | Canonical trade model; orderflow input |
| **2C.2+** | Databento / Sierra | Quotes; optional bulk historical via Sierra SCID | Spread, microprice; one-time local archive expansion |
| **2D** | Intrinio | Option chain snapshots, Greeks, IV, OI | Options context research |

Phase 2B does not block Signal Research or Phase 6A Strategy Research on existing OHLCV. Trades and options extend analytical depth when ready (**§6**, **§15**).

## Architectural Principle

Maximize reusable information while minimizing external dependencies, storage and vendor lock-in.

The framework becomes more capable through **better analytical models**, not through continuously hoarding raw market data.

---

# 15. Cross-Cutting Standards

These standards apply across Market Data, Market Analysis and Research. They are not separate linear phases.

## 15.1 Test and Research Data Tiers

Three tiers of test and research data coexist by design.

### Tier 1 — Small Deterministic Fixtures

```text
Scope:     tens to hundreds of records
Location:  committed to repository
CI:        standard unit and contract tests
```

Use for: edge cases, temporal alignment, join semantics, incomplete outcomes, session boundaries, validation errors.

Small fixtures are valid test tools. They must not be replaced by large datasets in unit tests.

### Tier 2 — Representative Integration Datasets

```text
Scope:     several days to weeks per data type
Location:  local or opt-in test fixtures (not required in standard CI)
CI:        opt-in integration markers only
```

Separate datasets for OHLCV, trades, quotes and options snapshots where applicable.

Use for: importer tests, normalization, partitioning, futures contract boundaries, multi-session behaviour, orderflow calculations, realistic distributions, local performance checks.

### Tier 3 — Full Research Datasets

```text
Scope:     months to years
Location:  user_data (not committed)
CI:        not required
```

Use for: Signal Research, Strategy Research, robustness validation, walk-forward, Monte Carlo, stability over time.

Published as concrete `DatasetRef` values with lineage, version and validation status.

**Problem registry:** PRB-017 — representative integration and research-validation dataset gap.

## 15.2 Live Market Data Entry Gate

Concrete paid live CME adapters (**Phase 2E**) are deferred until at least one of:

- a candidate strategy passes defined historical robustness validation,
- replay and paper parity require a live normalized feed,
- a data property available only live is required to validate a model,
- runtime operational testing cannot continue on recorded or replayed data,
- expected research or execution value justifies ongoing data cost.

**Not sufficient alone:** a positive backtest does not justify live feed cost.

Until the gate opens:

- historical research uses archives (Databento and similar),
- replay uses published datasets,
- live provider **contracts** may exist without expensive adapter implementation.

## 15.3 Strategy Research Scope Clarification

Completing **Phase 6A — OHLCV Strategy Research MVP** validates Strategy Model and simulation contracts on bar-based facts.

It does **not** mean:

- Market Data development is complete,
- the simulation engine's target data coverage is complete,
- orderflow or options context is supported in Strategy Research.

**Phase 6B — Multi-Data Strategy Research** extends simulation when Phase 2C/2D and Phase 4B/4C deliver new fact types.

## 15.4 Planning Increment and Sprint 011

Before Sprint 011 implementation, complete a short **Roadmap Revision / Phase Entry Review** (planning only):

- update `ROADMAP.md`, `CURRENT_STATUS.md`, `PROBLEM_REGISTRY.md`, `DATA_MODULE.md`,
- confirm capability tracks, test-data tiers and live-data gate,
- decide phase entry and publish `SPRINT_011.md`.

**Recommended Sprint 011 goal:** Phase 2B — Historical Archive Import Foundation.

**First vertical slice:**

```text
Databento DBN OHLCV archive
    ↓
inspection → decoding → canonical MarketBar
    ↓
validation → partitioned Parquet → published DatasetRef
```

Sprint 011 must **not** simultaneously include: trades, quotes, options, orderflow, continuous futures, full resumability, live adapters, or a complete backtest engine.

After this slice, choose the next sprint among:

- **Phase 2C.1** — `MarketTrade` archive import, or
- **Phase 6A** — OHLCV Strategy Research MVP.

See `docs/planning/sprints/SPRINT_011.md`.

---

# 16. Cross-Phase Architectural Gates

A phase must not be considered complete if it violates these gates.

## Reproducibility Gate

Results identify all material:

- datasets,
- versions,
- configurations,
- component identities,
- model identities,
- time semantics,
- execution assumptions.

## Temporal Correctness Gate

No result uses information before its legal `available_at`.

## Domain Ownership Gate

Responsibilities remain in their owning domains.

## Workflow Independence Gate

Signal Research, Strategy Research and Strategy Execution do not require each other's workflow state.

## User-Space Gate

Proprietary definitions and data remain in `user_data/`.

## Complexity Gate

New infrastructure solves a demonstrated problem.

## Test Gate

Critical contracts have unit, integration, regression or workflow tests as appropriate.

---

# 17. Deferred Capabilities

The following remain deferred until evidence justifies them:

```text
Microservices
Kubernetes
Kafka
Spark
Distributed Market Analysis Engine
Multi-node research scheduler
Dedicated feature-store product
Remote component registry
Visual workflow or DAG editor
Full event sourcing
MBP-10 / full DOM as primary storage (see §14 — sample validation first)
Raw option tick streams (snapshots preferred; see §14)
Automatic ML feature vector layer
Separate Position Sizing Model
Distributed Strategy Execution
```

Deferred does not mean rejected.

Each item requires a decision trigger, design review and usually an ADR before implementation.

---

# 18. Roadmap Review

Review the roadmap:

- at the end of every phase,
- after a material architectural decision,
- after evidence invalidates an assumption,
- when a critical problem changes priorities,
- before detailed planning of the next phase.

Do not rewrite historical phase outcomes.

Record actual outcomes in sprint reviews and `CURRENT_STATUS.md`.
