# Trading Research Framework

# ROADMAP.md

```text
Status: ACCEPTED
```

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
  Phase 2F — Exchange REST Historical Import      COMPLETE  (Sprint 045; Binance USD-M)

Research Capability Track
  Phase 3  — Market Analysis Engine MVP           COMPLETE
  Phase 4A — Bar-Based and MTF Market Analysis    COMPLETE  (Sprints 004–006)
  Phase 4B — Orderflow Market Analysis            PLANNED
  Phase 4C — Options-Derived Market Analysis      PLANNED
  Phase 5  — Signal Research MVP                  COMPLETE  (Sprints 008–010)
  Phase 6A — OHLCV Strategy Research MVP          COMPLETE  (Sprints 013–014)
  Phase 6B — Multi-Data Strategy Research         PLANNED
  Phase 7  — Robustness Research                  COMPLETE  (Sprint 016)
  Phase 10A — Predictive Research Foundation      COMPLETE  (Sprints 039–041)
  Phase 10B — Tree-Based Predictive Models        COMPLETE  (Sprint 042)
  Phase 10C — Neural Predictive Models            COMPLETE  (Sprints 043–044)
  Phase 14 — Predictive Model Promotion           APPROVED  (Sprints 049 + 050; 049 COMPLETE, 14A only — 050 NOT planned)
  Phase 15 — Predictive Catalog Expansion + Real-Data Study   APPROVED  (Sprints 051 + 052; 051 IN PROGRESS, 052 NOT planned)

Execution Capability Track
  Phase 8 — Replay and Paper Execution            PLANNED
  Phase 9 — Live and Multi-Account Execution        PLANNED

Operator Experience Track
  Phase 11 — Universal Operator CLI                  COMPLETE  (Sprint 046; trading-cli)
  Phase 12 — Custom Strategy Authoring               COMPLETE  (Sprint 047)
  Phase 13 — Exit/Risk Model Expansion               COMPLETE  (Sprint 048)
```

### Cross-track dependencies (summary)

```text
Phase 2A ──┬── Phase 5 — Signal Research
           └── Phase 6A — OHLCV Strategy Research

Phase 2C → Phase 4B → Phase 6B
Phase 2D → Phase 4C → Phase 6B

Phase 4A ──┬── Phase 10A — Predictive Research Foundation
Phase 5  ──┘        ├── Phase 10B — Tree-Based Models
                    └── Phase 10C — Neural Models
```

Phase 10 consumes Market Analysis outputs as **features** and Phase 5 forward outcomes as **labels**.
It does not extend Strategy Research or Execution; see **§13A**.

Strategy Research (**Phase 6A**) may start on OHLCV without waiting for trades or options. That validates Strategy contracts first; it does **not** mean target data coverage is complete (**§15.3**).

Completed phases retain their historical sprint records. New increments (2B, 4B, 6A, …) extend capability without rewriting Sprint 002–010 scope.

Market Data policy (facts not indicators, vendor independence): **§14 Research Data Strategy**.

Test data tiers and live-data gate: **§15**.

**Phase 10 is COMPLETE** (Sprints 039–044): predictive dashboard page, ADR-0024, and the
IDEA-014 gate all merged.

**Phase 2F is COMPLETE** (Sprint 045, 14/14 tasks): Binance USD-M historical
OHLCV import publishes an ordinary `DatasetRef` from `providers/binance/`,
network-free by default, no change to any research code or to the live
dry-run path.

**Phase 11 is COMPLETE** (Sprint 046, 14/14 tasks): `apps/cli` ships
`trading-cli` over four command groups (`data fetch`, `research run`,
`dry-run start`, `report render`), driven by one YAML config contract, wired
to the existing application-layer workflows with no new capability and no
change to any wrapped script.

**Phase 12 is COMPLETE** (Sprint 047, 10/10 tasks, see §13D): `trading-cli
research run strategy` accepts an optional `research.strategy.strategy_file`
key naming an operator-authored Python file, closing the strategy-model
third of SPRINT_046.md §4 Finding 2. Two new Market Analysis components
(`candle.wick`, `structure.level_distance`) and two worked example strategies
prove the loader composes with the catalog end to end. Exit/Risk model
expansion (ADR-0028) was declined for this sprint and deferred.

**Phase 13 is COMPLETE** (Sprint 048, 13/13 tasks, see §13E): resumed
ADR-0028 (Status flipped to ACCEPTED, with corrections found by
re-verifying the engine-change plan against the post-Sprint-047 tree) —
`BracketExitModel`, `EquityPercentRiskModel`, a new `kernels/bracket.py`,
five bounded engine changes across three files, a golden-run regression, two
new Market Analysis components (`trend.ema_distance`,
`volatility.range_expansion`), and three worked example strategies.

**Next tracked increment:** none scheduled by default — see SPRINT_048.md
§12 for unscheduled candidates (bracket-aware Robustness stress dimensions,
dynamic equity-curve-following sizing, arithmetic in the model-expression
IR, among others).

Phase 12 absorbs the previously parallel catalog follow-ons (wick, then
distance-to-level — named as next in D-S037-08 and D-S038-03), because those
components are what an authored strategy has to compose from. Deferred by
default: Phase 4B/6B, Phase 8 Replay, PBO/CSCV ADR. Stage 3 (`available_at`
column / lineage sidecar) and Stage 4 (`MarketFrame`) remain independently
sequenced.

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

# 13A. Phase 10 — Predictive (ML) Research

**Status:** COMPLETE. Phase 10A COMPLETE on `main`; Phase 10B COMPLETE (Sprint 042, #335,
22/22); Phase 10C COMPLETE — Sprint 043 (#342, 21/21) and Sprint 044 (predictive dashboard
page + ADR-0024 + IDEA-014 gate, 18/18) both merged. Numbered `13A` to avoid renumbering
sections cited elsewhere.

Sprint 039 (dataset foundation: labelled matrix, purged walk-forward folds, persisted envelope,
leakage suite, ADR-0023), Sprint 040 (estimator seam, sklearn baselines, run envelope, metrics,
CLIs), and Sprint 041 (offline HTML report) are on `main`. Phase 10A is complete. Sprint 042
(tree-based models, bounded selection, importance, leaderboard, report panels) is on `main`
(#335). Sprint 043 (sequence windows, extra `dl`, feedforward + LSTM/GRU, learning curves,
synthetic comparison) is complete on `main` (#342). Sprint 044 (Predictive Research dashboard
page, ADR-0024 promotion conditions, IDEA-014 gate document, boundary test and Phase 10
closure docs) closes the phase.

**Sprint plans:** `SPRINT_039.md` … `SPRINT_044.md`

## Purpose

Learn a relationship between Market Analysis outputs and forward market behaviour, and measure
honestly whether that relationship survives out of sample.

Phase 10 is a **research methodology**, not a trading capability. It answers *is there predictable
structure in these features?* — not *should we trade this?*

## Phase family

```text
Phase 10A — Predictive Research Foundation   Sprints 039–041
Phase 10B — Tree-Based Predictive Models     Sprint 042
Phase 10C — Neural Predictive Models         Sprints 043–044
```

## Primary flow

```text
Market Analysis outputs (Phase 4A + S037/S038 catalog)
        ↓
Feature matrix (declared columns + lineage)
        ↓
Labels from forward outcomes (Phase 5)
        ↓
Purged + embargoed walk-forward split
        ↓
Estimator training per fold (statistical / tree / neural)
        ↓
Out-of-sample predictions + metrics
        ↓
Predictive Research Report (offline HTML)
```

## Expected capabilities

- declarative feature matrix specification with component lineage,
- regression and classification label definitions derived from forward outcomes,
- purged and embargoed walk-forward splitting as a first-class domain object,
- estimator protocol in the domain, ML libraries behind infrastructure adapters,
- statistical metrics (RMSE, R², rank IC, AUC, log loss, Brier) and finance-aware metrics
  (mean forward return per prediction bucket, hit rate),
- persistent Predictive Research Dataset and run envelope with full run identity,
- offline HTML report with fold timeline, stability, calibration, bucket, importance, leaderboard and selection-trace panels,
- tree-based estimators (XGBoost, LightGBM, CatBoost) with deterministic configuration,
- feedforward and recurrent (LSTM / GRU) sequence estimators,
- a documented gate for promoting a trained model to a Market Analysis State component.

## Binding rules

```text
Domain code must not import scikit-learn, XGBoost, LightGBM, CatBoost or torch
ML libraries are optional dependency extras — never runtime dependencies of the framework
Scalers, encoders and feature selection are fitted on the training fold only
Label horizon overlap between train and test folds is purged, not tolerated
Predictive runs are persisted separately from Signal and Strategy Research runs
A trained model is never promoted to a tradable signal inside Phase 10
```

## Completion criteria

Phase 10 is complete when the framework can:

- build a reproducible feature matrix with labels and prove absence of temporal leakage in tests,
- split it into purged, embargoed walk-forward folds,
- train and evaluate statistical, tree-based and neural estimators through one shared protocol,
- persist predictions, metrics and run identity for every fold,
- render one report that makes overfitting and fold instability visible,
- compare estimator families on an identical dataset fingerprint,
- state explicit conditions for promoting a model to Market Analysis (IDEA-014).

## Dependencies

- Phase 4A Market Analysis outputs and `AnalysisFrame` column lineage,
- Phase 5 forward outcome calculation (`forward_return`, `mfe`, `mae`, outcome status),
- S037 component libraries and S038 `structure.session_range` — the catalog bounds feature quality;
  further catalog PRs (wick, distance-to-level) widen it without blocking Phase 10 entry.

## Main risks

- leakage through feature availability, label horizon overlap or preprocessing fitted on all data,
- overfitting presented as discovery because only aggregate metrics are reported,
- heavy dependencies leaking into the default install or standard CI,
- non-reproducible results from unseeded or thread-nondeterministic estimators,
- silent drift into strategy generation without robustness validation.

## Out of scope (phase family)

- automatic promotion of predictions into Signal Models or Strategy Research,
- online / incremental learning and live inference,
- distributed or GPU training infrastructure,
- a general model registry product,
- reinforcement learning and generative approaches,
- automated feature engineering search.

---

# 13B. Phase 2F — Exchange REST Historical Import (COMPLETE)

**Status:** COMPLETE — Sprint 045 (14/14 tasks, `sprint/binance-historical-ohlcv`).
**ADR:** ADR-0025 (ACCEPTED).
**First provider:** Binance USD-M futures.

## Purpose

Obtain historical bars from an exchange **REST API over a date range**, not only
from a local vendor archive (Phase 2B) or a CSV file (Phase 2A).

The framework's downstream layers are already provider-agnostic; the gap is
purely at the acquisition boundary. Closing it makes crypto data available to
Signal, Strategy, Robustness and Predictive Research with **no change to any
research code**.

## Primary flow

```text
Binance USD-M REST /fapi/v1/klines
        ↓
paginated fetch over [start, end) with weight-aware backoff
        ↓
map_kline_payload → canonical MarketBar   (shared with the live path)
        ↓
OHLCV validation
        ↓
bars.parquet + import_manifest.json       (ADR-0008 layout, unchanged)
        ↓
register WORKING → finalize → publish
        ↓
published DatasetRef, provider = "binance"
```

## Expected capabilities

- paginated historical klines fetch over an arbitrary UTC date range,
- open-bar exclusion and idempotent re-import (same range → same checksum),
- weight-aware rate limiting with bounded, jittered backoff (no busy-loop retry),
- optional API key raising public market-data limits, environment-variable only,
- gap recording (never gap filling) in an import manifest,
- a mode selector reserving a future `trades` mode without building it,
- a thin CLI under `scripts/market_data/`.

## Binding rules

```text
Downstream research must not branch on provider == "binance"
No signing code, no authenticated endpoint, no account surface — structurally, not by promise
Credentials live in TRADING_FRAMEWORK_BINANCE_API_KEY only; never in a file, never logged
A partially fetched range never produces a PUBLISHED version
Standard CI stays network-free (Tier 1 fake transport; Tier 2 opt-in marker)
```

## Completion criteria

- a multi-month Binance USD-M range publishes a queryable `DatasetRef`,
- `query_historical` returns those bars with no provider-specific handling,
- Strategy or Predictive Research runs on the result unmodified,
- rate-limit backoff is proven against 429 / 418 / 5xx without real sleeping,
- a boundary test proves no credential is required by any committed file,
- the live dry-run reconnect path (`fetch_closed_klines`) is unchanged.

## Dependencies

- Phase 2A lifecycle and repository contracts (ADR-0007 / ADR-0008),
- the Sprint 019 Binance mapper and symbol normalization.

## Main risks

- vendor-revisable history undermining reproducibility (mitigated by publishing versions),
- long wall-clock imports under weight limits with no resume in v1,
- validator behaviour on legitimate market gaps,
- credential convention drift if a second storage location is ever introduced.

## Out of scope

- Binance spot, options, or any authenticated endpoint,
- `trades` mode (reserved, not built),
- resume-after-failure and incremental "top-up" imports,
- a second exchange (the workflow generalizes only when a second one is needed).

---

# 13C. Phase 11 — Universal Operator CLI (COMPLETE)

**Status:** COMPLETE — Sprint 046 (14/14 tasks, `sprint/operator-cli`).
**ADR:** ADR-0026 (ACCEPTED).

## Purpose

Give the operator one entry point and one input contract for the working loop.
Today that loop is a remembered sequence of `uv run python scripts/.../foo.py`
invocations across 45 scripts with 45 flag sets.

This is an **interface** phase. It adds no research, data or execution
capability, and it deliberately does not replace `scripts/`.

## Primary flow

```text
one YAML config
        ↓
trading-cli <group> <command> --config <path>
        ↓
validate + resolve the plan (--dry-run stops here)
        ↓
call an existing application-layer workflow
        ↓
typed result → human or --json output
```

## Command groups (v1)

```text
data fetch     Binance (Phase 2F) and Databento historical import
research run   Predictive Research and Strategy Research
dry-run start  the existing BTC futures dry-run runtime (Sprints 018–024)
report render  offline HTML reports for the above
```

## Binding rules

```text
apps/cli may import trading_framework.application.* — and nothing deeper
apps/cli contains no research, simulation or execution logic
No workflow is reimplemented; no command parses another command's stdout
Existing scripts, their flags and their tests remain valid
No credentials in any config file
```

## Completion criteria

- the four commands run end to end from a YAML config,
- an invalid config fails before any side effect, with a clear message,
- `--dry-run` prints the resolved plan without executing,
- an import-boundary test proves the CLI touches only the application layer,
- CI is green for the new workspace member,
- the operator guide documents one config schema, once.

## Dependencies

- Sprint 045 / ADR-0025 for the `data fetch binance` command only,
- existing application workflows for the other three groups.

## Main risks

- the CLI drifting from script behaviour (two front doors, one can rot),
- scope creep toward wrapping all 45 scripts,
- config schema growing a fat "common" section that couples unrelated commands,
- hardcoded choices inside scripts (canonical strategy model, session resolver)
  being mistaken for CLI limitations rather than upstream ones.

## Out of scope

- replacing `scripts/`; ops, demo, robustness and signal-research groups,
- any change to execution or order-routing logic,
- interactive/TUI modes, shell completion, packaging for global install,
- a job scheduler, queue, or run history — the CLI is stateless.

---

# 13D. Phase 12 — Custom Strategy Authoring (COMPLETE)

**Status:** COMPLETE — Sprint 047 (10/10 tasks, `sprint/strategy-authoring`).
**ADRs:** ADR-0027 (strategy loading) — ACCEPTED. ADR-0028 (bracket exit /
equity sizing) — PROPOSED, **declined for this sprint** (2026-09-01); its
Exit/Risk expansion is deferred to a possible future sprint with its own
engine-focused ADR, not part of Phase 12's Sprint 047 delivery.
**PRD:** `docs/product/PRD-strategy-authoring.md` (confirmed).

## Purpose

Make the framework's own strategy vocabulary usable **by the operator, from the
CLI**, rather than only by an engineer editing Python inside the repository.

Phase 11 gave the operator one front door. Behind that door,
`research run strategy` still always evaluates the Sprint 013 canonical example
(SPRINT_046.md §4 Finding 2). Phase 12 opens it — and closes the two structural
gaps that made the limitation more than a CLI oversight: a thin component
catalog, and Exit/Risk models that were placeholders rather than
strategy-construction primitives.

This is a **capability** phase, unlike Phase 11's interface-only scope: it adds
Market Analysis components. Exit/Risk model expansion was scoped (ADR-0028)
but declined for Sprint 047 — see Out of scope.

## Primary flow

```text
operator writes user_data/.../my_strategy.py
        def build_strategy() -> StrategyModelDefinition
        ↓
research:
  strategy:
    strategy_file: user_data/.../my_strategy.py
        ↓
trading-cli research run strategy --config <path>
        ↓
resolve_plan: import the file, call build_strategy(), validate the definition
        (--dry-run stops here and prints the resolved strategy_model_id)
        ↓
run_strategy_research(strategy_model=<the loaded definition>)
        ↓
run manifest strategy_model_id == the operator's strategy
```

## Expected capabilities

- one config key, `research.strategy.strategy_file`, naming a Python file; a
  fixed zero-argument `build_strategy()` entry-point convention (ADR-0027),
- a pre-flight error taxonomy covering missing file, import failure, missing or
  non-callable entry point, wrong return type, and invalid definition — every
  one an exit-2 config error naming the key, before any side effect,
- an explicitly documented trust model: the loaded file is operator code and is
  not sandboxed or import-restricted (ADR-0027 §2, §6),
- Market Analysis catalog: `candle.wick` and `structure.level_distance`, the
  two items D-S037-08 / D-S038-03 named as the next catalog increments,
- working example strategies composing the new catalog components, runnable
  through the CLI.
- *(Exit/Risk expansion — `BracketExitModel`, `EquityPercentRiskModel`, and
  the simulation kernel dispatch that would make them runnable — was scoped
  in ADR-0028 and declined for this sprint on 2026-09-01. Deferred, not
  delivered by Phase 12's Sprint 047.)*

## Binding rules

```text
The loaded strategy file is the operator's own trusted code — no sandbox, no
    import restriction, and the boundary test does not and cannot scan it (TD-025)
apps/cli's own ADR-0026 Amendment 1 allow-list is NOT widened by this phase
strategy_file is optional; its absence keeps the canonical example (additive)
No declarative YAML strategy schema is introduced — Python loading only
Existing FixedBars strategies produce byte-identical runs (no engine change)
kernels/fixed_bars.py, ExitModel/RiskModel protocols, and BarSequentialSimulator
    are untouched this sprint (ADR-0028 declined; not merely unedited by luck)
```

## Completion criteria

- `trading-cli research run strategy --config <path>` runs a user-authored
  strategy and the run manifest's `strategy_model_id` is that strategy's,
- every loader failure mode fails pre-flight with an exit-2 message naming
  `research.strategy.strategy_file` and the resolved absolute path,
- at least one new Market Analysis component is exercised by a passing
  example composed through the loader (the Exit/Risk half of this criterion
  is deferred with ADR-0028),
- the canonical example still runs unchanged with no `strategy_file` key, and
  every Sprint 046 example config still works,
- the fixed-bars simulation path, the simulator, and both Exit/Risk protocols
  are unchanged — trivially true this sprint since the engine was not touched,
- the trust model is stated in the operator guide and in `--help`, not implied.

## Dependencies

- Phase 11 / ADR-0026 (the CLI, its config contract and its error taxonomy),
- Phase 6A / ADR-0016 (Strategy Model, Exit/Risk contracts, the simulator),
- Sprint 037/038 (`model_authoring` DSL and the component reference pattern),
- session metadata on the component compute view (Sprint 038) for
  `structure.level_distance`.

## Main risks

- **Arbitrary code execution by config.** Accepted deliberately and documented;
  it is the same trust level as running any script in this repository.
- **`--dry-run`'s promise narrows** from "touches nothing" to "the CLI touches
  nothing" — a loaded module executes at import (ADR-0027 §4).
- Catalog scope creep — exactly two components, no more.

## Out of scope

- a declarative (YAML/JSON) strategy specification format,
- sandboxing, import restriction, or static analysis of loaded strategy files,
- a strategy registry, catalog UI, or any discovery mechanism,
- exposing `SimulationAssumptions` or the session resolver through config (the
  other two thirds of SPRINT_046.md §4 Finding 2),
- **`BracketExitModel`, `EquityPercentRiskModel`, and any change to
  `BarSequentialSimulator` or its kernels** — ADR-0028's requested non-goal
  narrowing was declined by the maintainer (2026-09-01); deferred to a
  possible future sprint with its own engine-focused ADR,
- dynamic, equity-curve-following position sizing (TD-026, deferred with the above),
- Robustness Research stress dimensions over bracket parameters (deferred with the above),
- any change to live trading, order routing, or the dry-run runtime,
- deleting or rewriting `user_data/run_example_strategies.py`.

---

# 13E. Phase 13 — Exit/Risk Model Expansion and Catalog Growth (COMPLETE)

**Status:** COMPLETE — Sprint 048 (13/13 tasks, `sprint/exit-risk-and-catalog`).
Approved by the maintainer on 2026-09-01. Numbered `13E` to continue the
§13A-§13D pattern without renumbering earlier phases.
**ADRs:** ADR-0028 (bracket exits + equity-relative sizing) — **ACCEPTED**
(declined for Sprint 047, resumed with corrections for Sprint 048; Status
flipped in place, dated decline record preserved under "History").
**PRD:** `docs/product/PRD-exit-risk-and-catalog-expansion.md` (confirmed).

## Purpose

Turn Exit and Risk models from placeholders into strategy-construction
primitives — the third piece Phase 12 scoped, designed and deliberately did
not ship.

Phase 12 made a strategy authorable. But every authorable strategy still exits
`N` bars after entry and sizes at a hand-computed constant, because
`ExitModel`'s whole contract is a function of one integer and three separate
`isinstance` gates refuse anything but the two Sprint 013 placeholders. A
framework whose backtests cannot express a stop-loss cannot honestly evaluate
risk.

This is a **capability** phase that deliberately narrows a Phase 12 non-goal:
it changes `BarSequentialSimulator`.

## Primary flow

```text
BracketExitModel(stop_loss_bps=50, take_profit_bps=120, max_bars=40)
EquityPercentRiskModel(account_equity=100_000, risk_percent=0.01, stop_distance=...)
        ↓
build_strategy() in an operator file        (Phase 12 loader, UNCHANGED)
        ↓
validate_strategy_model_definition  -> supported-combination check
run_strategy_research               -> structural check
BarSequentialSimulator              -> dispatch on PriceBracketExit
        ↓
kernels/bracket.py  (@njit over open/high/low)     kernels/fixed_bars.py untouched
        ↓
trades table with per-trade exit_reason:
    stop_loss | take_profit | max_bars
```

## Expected capabilities

- `BracketExitModel`: stop-loss and take-profit as **basis-point** offsets from
  the entry fill, plus a mandatory `max_bars` timeout so no position can be held
  to the end of the dataset; satisfies `ExitModel` unchanged plus an additive
  `PriceBracketExit` protocol,
- `EquityPercentRiskModel`: **static, authoring-time** sizing
  (`equity x risk_percent / stop_distance`, resolved once at construction) —
  explicitly not equity-curve-following,
- five bounded engine changes across three files plus one new `@njit` kernel,
  with `kernels/fixed_bars.py`, `compile.py`, `input.py` and both Protocol
  definitions untouched,
- a **golden-run regression** as the binding safety net: the canonical Sprint 013
  strategy produces byte-identical trades, equity and `run_id`,
- Market Analysis catalog: `trend.ema_distance` and
  `volatility.range_expansion` — both chosen because the authoring DSL has no
  arithmetic, so a ratio or a signed difference must be a component,
- three worked example strategies covering bracket-only, bracket + equity
  sizing, and equity sizing on the unchanged fixed-bars path.

## Binding rules

```text
kernels/fixed_bars.py is NOT edited — not one character
research/simulation/compile.py and input.py are NOT edited (high/low already compiled)
ExitModel and RiskModel Protocol definitions are NOT modified
apps/cli is NOT modified — the Phase 12 loader already returns any definition
The fixed-bars path's fill, accounting AND RUN-IDENTITY semantics are unchanged
A sixth engine change is a STOP-and-ask with a fresh ADR amendment, never a
    quiet widening
Same-bar stop/target ambiguity resolves to the STOP. Always. No configuration flag.
Equity-percent sizing is STATIC and must never be described as compounding
```

## Completion criteria

- a strategy using `BracketExitModel` runs end to end through
  `trading-cli research run strategy` and produces trades distinguishable by
  `exit_reason` (more than one distinct reason in one run),
- the golden run passes: byte-identical trades, equity, `run_id` and
  deterministic manifest fields for the canonical strategy,
- the three ADR-0016-era `isinstance` MVP gates no longer block Exit/Risk models
  by class, while still rejecting genuinely unsupported models clearly,
- both new catalog components are registered, causal, warmup-correct and
  reachable from the DSL,
- three example strategies run through the CLI with no loader change,
- TD-026, TD-027 and TD-028 are logged with named repayment triggers.

## Dependencies

- Phase 12 / ADR-0027 (the loader and the two Sprint 047 components),
- Phase 6A / ADR-0016 (the Strategy Model, Exit/Risk contracts, the simulator
  and the MVP gates this widens),
- Phase 11 / ADR-0026 (the CLI this runs through, unchanged),
- **ADR-0028 ACCEPTED (resumed)** — no fallback: there is no useful subset of
  this phase that leaves the engine alone, which is exactly what Sprint 047
  established.

## Main risks

- **It narrows a non-goal that was previously declined**, and by a wider margin
  than the version declined on 2026-09-01 (five changes, not four, plus a
  run-identity signature change). The golden run bounds the risk; it does not
  eliminate it.
- **Run identity.** `derive_strategy_run_id` hashes a FixedBars-only field; a
  careless generalization silently re-identifies every persisted run.
- Two fill conventions inside one strategy (trigger-price for stop/target,
  next-bar-open for the timeout) is a real cognitive cost.
- A second `@njit` kernel with no reference counterpart (TD-028).

## Out of scope

- dynamic, equity-curve-following position sizing (TD-026),
- any change to the `ExitModel` / `RiskModel` Protocol definitions,
- bracket-aware Robustness stress dimensions; the delay stress keeps rejecting
  bracket exits, loudly and for a stated reason (TD-027),
- a reference (non-njit) implementation of the bracket kernel (TD-028),
- a declarative (YAML/JSON) strategy specification format,
- arithmetic in the model-expression IR,
- cross-validating `stop_distance` against `stop_loss_bps` — the operator owns
  that consistency in v1,
- any third catalog component, any fourth example strategy.

---

# 13F. Phase 14 — Predictive Model Promotion (APPROVED)

**Status:** **APPROVED** (maintainer, 2026-09-02). **Sprint 049 (increment
14A) is COMPLETE** (15/15, on `sprint/promotable-predictive-artifact`; final
integration PR to `main` pending) — ADR-0024 conditions 1 and 5 closed,
condition 4's offline half (Path A) built and passing at its locked bars
(measured maximum `y_proba` deviation: `0.0`). **Sprint 050 (increment 14B)
is NOT planned yet.** Phase 14 as a whole is **NOT complete** — 14A ships no
Market Analysis component, no State, no executor change, and no dry-run
session; see `docs/planning/sprints/SPRINT_049.md` §13 Review.
**Product source:** `docs/product/PRD-ml-signal-promotion.md` — the maintainer's
discovery record; authoritative on scope, format, fold selection and the parity
bar.
**ADRs:** ADR-0024 (promotion conditions) — ACCEPTED, the binding input.
**ADR-0029** (promoted artifact parameter format, promotion store, parity bars,
and the narrow ADR-0023 §7 amendment) — **ACCEPTED 2026-09-02**. ADR-0030
(inference-time availability enforcement) — the S049-T001 finding concluded
the mechanism ADR-0024 condition 2 presupposes does not exist in the executor
today; ADR-0030 is needed and sizes Sprint 050.
**Gate:** `docs/planning/sprints/S044_GATE.md` — entry criteria and the parity
test design sketch (§4).

## Purpose

Close the gap Phase 10 deliberately left open: a trained predictive model can be
evaluated offline, but nothing trained is reachable from a strategy. Phase 14
makes a trained model produce a Market Analysis **State**, consumed by a Signal
Model exactly like a rule-based component, all the way into the **BTC futures
dry-run runtime** (the existing Phase 8A infrastructure, Sprints 019–024) — under
ADR-0024's five conditions, none of them waived.

This is the phase ADR-0024 was written to gate. Its own Consequences section
says it "will not be small."

## v1 scope, locked by the PRD and ADR-0029

```text
IN    one instrument (BTC futures), one horizon
IN    LINEAR AND LOGISTIC model families only
IN    a framework-owned NumPy parameter format — ZERO ML dependency in the
      dry-run/live runtime image
IN    exact offline/online parity as a RELEASE GATE, not a follow-up
IN    dry-run only, composed via strategy_file (ADR-0027) with Phase 13's
      BracketExitModel / EquityPercentRiskModel (ADR-0028)

OUT   real-money trading; multi-instrument / cross-asset; auto-retraining or
      online learning; a model registry or promotion UI; tree (xgboost /
      lightgbm / catboost) and neural (torch) families; ONNX or any
      cross-library exchange format
```

Tree/neural promotion is **deferred, not rejected** — it needs the
version-pinned joblib path that v1 declines to build. It becomes a candidate
follow-on track once this mechanism is proven end to end.

## Two increments, deliberately sequenced

```text
14A — Promotable Predictive Artifact          Sprint 049 (COMPLETE, 15/15)
      ADR-0024 conditions 1 and 5 closed; condition 4's OFFLINE half (Path A)
      built and passing (measured maximum y_proba deviation: 0.0). Touches
      the research pipeline and storage only. Ships NO Market Analysis
      component, NO executor change, NO State.

14B — Model-Backed Market Analysis State      Sprint 050 (NOT planned yet)
      ADR-0024 conditions 2, 3 and condition 4's RUNTIME half (Path B) closed.
      The model component, the registry-injection seam in the dry-run runtime,
      and the parity harness as a RELEASE GATE. Touches market_analysis/
      execution and execution/runtime. Ends in a 3-5 day BTC dry-run session.
```

Sprint 050 is **not** planned in the same pass as Sprint 049. The reasoning was
re-checked after the PRD narrowed v1, and one original reason is now spent:

- ~~its design depends on the serialization format, which is unknown~~ —
  **closed** by ADR-0029; Sprint 050's deployment footprint is now known to be
  *zero extras*.
- ~~its design depends on the S049-T001 finding — whether the executor
  mechanism ADR-0024 condition 2 presupposes actually exists~~ — **closed**:
  S049-T001 concluded the mechanism does not exist, and ADR-0030 will be
  needed. Sprint 050 must include writing and getting that ADR approved.
- **still standing:** whether Path A holds at its locked bars is not yet known
  (Sprint 049 Wave 3 work).
- **added:** conditions 2 and 3 and the online half of condition 4 are
  executor/runtime work whose cost is **independent of the serialization
  format**. The format choice shrank Sprint 050's deployment concerns to
  nothing; it did not shrink its executor concerns at all. That is the structural
  reason the split survives the narrower scope.

## Primary flow (the phase's end state, reached only after 14B)

```text
PredictiveRunEnvelope (Phase 10), LAST walk-forward fold
        ↓  promote_predictive_run  (one-time blob read, ml extra)     [14A]
research/predictive_research/promoted/{artifact_fingerprint}/
        manifest.json  +  artifact.json  (weights + intercept + fitted
        preprocessing statistics, as PLAIN NUMBERS, as one unit)
        ↓  load, format/family-guarded, evaluated by PURE NUMPY       [14A]
Path A: re-predict the run's TEST rows vs predictions.parquet         [14A]
        exact for linear; y_proba for logistic within atol=1e-15
        ↓
Market Analysis STATE component; artifact_fingerprint as a STR        [14B]
        parameter → CanonicalParameters → Lineage → cache identity
        ↓  features read through AnalysisDataView, available_at enforced
Path B: dry-run runtime State values == research values, EXACTLY      [14B]
        ↓
Signal Model consumes the State exactly like a rule-based one,        [14B]
        composed via strategy_file with a Bracket exit and equity sizing
        ↓
Phase 7 robustness on the resulting strategy — MANDATORY, never skipped
        (must account for TD-027: delay stress rejects bracket exits)
```

## Expected capabilities

- a `promote_predictive_run` workflow turning a Phase 10 run's **last fold** into
  a single, content-addressed, deterministically loadable **parameter file**
  whose **fitted preprocessing statistics travel inside it** as one unit with the
  estimator parameters,
- a pure-NumPy evaluator for that file, living in the domain layer and requiring
  **no optional extra** — so the dry-run/live image is unchanged,
- a load-time format and model-family guard with no bypass, plus a
  promotion-time library-version guard for the one blob read,
- a Market Analysis State component backed by that artifact, identified in
  `Lineage` by the artifact fingerprint and declaring its features as
  `OutputRef` values like any rule-based component,
- executor-enforced inference-time feature availability for model components
  (per ADR-0030, needed per the S049-T001 finding),
- a parity harness proving batch research and the dry-run runtime produce
  **identical** State values from the same artifact — running in **default CI**,
  because there is no ML dependency to gate it behind.

## Binding rules

```text
ADR-0024's five conditions are inherited whole; none is waived by this phase
Condition 5 is a NEGATIVE constraint: no model registry, no lifecycle state, no
    serving API. A plan that starts building one has misread the ADR.
Condition 4's bar is EXACT EQUALITY for the offline/online comparison (the
    release gate). The single ulp-bounded tolerance ADR-0029 §6 permits applies
    ONLY to the Sprint 049 sklearn cross-check's y_proba column, and is NOT
    inherited by the release gate.
ADR-0023 §4 (purge, embargo, dataset fingerprint) is NOT reopened
ADR-0023 §7 is amended NARROWLY by ADR-0029 — one workflow, one read, one
    purpose; research-run blobs stay non-reloadable by everything else
Strong Phase 10 metrics are a PRECONDITION for promotion, never a verdict that
    the model should trade (ADR-0024, "What is not sufficient for promotion")
ml / ml-trees / dl remain out of the default install and default CI — and, per
    ADR-0029, out of the RUNTIME IMAGE entirely. Promotion needs `ml`;
    inference needs nothing.
No new dependency of any kind: the parameter format needs only NumPy, already
    a default-install dependency
Phase 13's Exit/Risk work (ADR-0028) is CONSUMED, never modified
```

## Completion criteria

- a trained **linear or logistic** model, promoted through a content-addressed
  artifact store with no registry, produces a Market Analysis State consumed by a
  Signal Model,
- the artifact fingerprint appears on every `AnalysisResult.Lineage` the model
  component emits (condition 1),
- a leakage counter-fixture proves the **executor** — not a code-review
  convention — rejects a model component reading a feature before its
  `available_at` (condition 2),
- the model component declares its features as `OutputRef` values, covered by
  the existing DAG/lineage tests plus one model-component fixture (condition 3),
- the **parity harness passes as a release gate**: batch research and the
  dry-run runtime produce **exactly identical** State values for identical
  inputs, from the same promoted artifact including its fitted preprocessing
  (condition 4, PRD success metric 1),
- a **BTC futures dry-run session runs 3–5 consecutive days** on a promoted
  model with no divergence from an offline re-run over the same recorded window
  (PRD success metric 2),
- a named downstream Signal Model has a Phase 7 robustness plan and it is
  executed, not skipped (S044_GATE §1.5, PRD success metric 3),
- no registry, lifecycle state, or serving API exists anywhere in the delivery
  (condition 5).

## Dependencies

- Phase 10 complete (Sprints 039–044) — **satisfied**,
- ADR-0024 and `S044_GATE.md` on `main` — **satisfied** (#348),
- ADR-0029 — **ACCEPTED** (2026-09-02); on the sprint branch,
- Phase 12's `strategy_file` loader (ADR-0027) and Phase 13's Exit/Risk models
  (ADR-0028) — **satisfied** (merged #366, #368–#383); consumed by 14B's dry-run
  composition, not modified,
- **a real (non-synthetic) trained candidate model showing genuine out-of-sample
  structure on BTC data** — **does not exist**; Phase 10's validated results are
  on synthetic known-signal fixtures (ADR-0023 §8). Tracked as a prerequisite
  **outside** Sprint 049 (no 14A task depends on it); it gates 14B and the PRD's
  success metrics 2 and 3. **Now being actively pursued by Phase 15 (§13G,
  Sprints 051+052)** — closes this dependency only on a positive result,
- **a named downstream robustness plan** (S044_GATE §1.5) — **does not exist**;
  same status: prerequisite outside Sprint 049, gates 14B,
- **ADR-0030** (inference-time availability enforcement) — needed per
  S049-T001's finding; must be written and approved before 14B implementation.

## Main risks

- **Exact parity may not survive contact with two implementations.** The release
  gate (offline NumPy == online NumPy) is structurally exact — same code, same
  artifact. But Sprint 049's Path A compares the NumPy evaluator against
  **sklearn's** own recorded predictions, and sklearn's logistic `predict_proba`
  uses `scipy.special.expit` rather than a NumPy sigmoid. The maintainer chose to
  keep both families with a bounded `atol=1e-15` on that one column rather than
  drop logistic (ADR-0029 §6, Q7). This is the maintainer's named riskiest
  assumption meeting its first real test, deliberately in 14A rather than 14B.
- **Condition 2 is larger than ADR-0024 priced it — confirmed, not just risked.**
  S049-T001 verified line-by-line that the executor does not enforce
  inference-time `available_at` rejection today (`executor.py`, `planner.py`,
  `assembler.py` all checked; no such mechanism exists). ADR-0030 is required
  before 14B can close condition 2.
- **The framework now owns a `predict` implementation** that must stay in step
  with scikit-learn's; only the Path A cross-check detects drift.
- **The linear/logistic restriction may bind sooner than expected** — the first
  real BTC candidate model that shows structure may well be a tree model, in
  which case the operator hits a refusal and the deferred joblib path becomes the
  next increment rather than a distant one.
- **TD-027 constrains 14B's robustness plan:** the Robustness delay stress still
  rejects bracket exits (§13E). If the promoted-model strategy uses
  `BracketExitModel`, not every stress dimension is available, and the S044_GATE
  §1.5 plan must say so rather than assume a full stress suite.
- **Promotion drifting into a registry by accretion** — an index file, then a
  `latest` pointer, then a status field. Guarded as an acceptance criterion with
  a test, not as a principle in prose.
- **A synthetic-fixture model mistaken for a tradeable one.** If 14B promotes one
  as plumbing, that must be stated loudly, not left implicit.

## Out of scope

- real-money trading; multi-instrument or cross-asset portfolios; auto-retraining,
  online learning, drift detection, or any automatic re-promotion (PRD Non-goals),
- tree and neural model families, and the version-pinned joblib format they
  require — **deferred to a later increment**, not rejected,
- ONNX or any cross-library exchange format — rejected for v1 because a second
  numerical implementation threatens the exact-match bar,
- a model registry, model lifecycle states, a promotion workflow product, or a
  serving API (ADR-0024 condition 5; TD-021 restated, not repaid),
- IDEA-003 (a dedicated feature/model store) — stays deferred,
- **any change to Phase 13's Exit/Risk models, the bracket kernel, or the
  simulator** — this phase consumes them,
- new estimator families, new predictive features, cross-sectional studies, or
  SHAP — extending Predictive Research itself is a separate track, sequenced
  **after** this phase at the maintainer's stated direction (PRD preamble:
  research expansion is the explicit next priority; report expansion is third),
- report/dashboard extensions for promoted models — likewise a later track,
- any claim that a promoted State is a validated trading edge — that is Phase 7
  robustness's answer, and it is never substituted by Phase 10 metrics.

---

# 13G. Phase 15 — Predictive Research Catalog Expansion and Real-Data Study (APPROVED)

**Status:** **APPROVED** (maintainer, 2026-09-02). Sprint 051 (increment 15A)
is **COMPLETE** (11/11, on `sprint/momentum-and-regime-catalog`; final
integration PR to `main` pending) — see `SPRINT_051.md` §13 Review. Sprint 052
(increment 15B) is **PLANNED but NOT approved/opened** (`SPRINT_052.md`,
`Status: PLANNED`); it now has its delivered prerequisite fact from Sprint
051 (`BTCUSDT.P`, 1m, `2024-01-01 -> 2026-06-29`, 911 days, 1,311,840 rows,
zero gaps — `S051_BTC_DATA_INVENTORY.md`), but opening it remains a separate
maintainer approval step. **Phase 15 as a whole is NOT complete** — no
real-data predictive study has been run.
**Product source:** `docs/product/PRD-predictive-research-catalog-expansion.md`
— the maintainer's grill-me discovery record; authoritative on scope,
non-goals and success metrics.
**Sprints:** Sprint 051 (increment 15A — catalog) and Sprint 052 (increment
15B — the real-data study).
**ADRs:** **none proposed.** The components follow the existing
`model_authoring` DSL / registry / NumPy-implementation pattern exactly
(precedent: `candle.wick` Sprint 047, `trend.ema_distance` and
`volatility.range_expansion` Sprint 048 — none needed its own ADR), and the
study runs the Phase 10 pipeline unmodified. If Sprint 052 finds the pipeline
must change to run a real-data study, that is a STOP-and-report finding that
would earn an ADR then — not now.

## Purpose

Phase 10 validated its whole methodology — leakage guards, purged/embargoed
walk-forward, estimator families — against **synthetic known-signal fixtures
only** (ADR-0023 §8, D-S039-CI-dataset). No real candidate model exists. §13F
records that gap as "Q5", a named prerequisite gating Phase 14B and the
ML-promotion PRD's success metrics 2 and 3.

This phase closes that gap — or reports, with the same rigour, that it cannot
be closed with an OHLCV-only catalog at this instrument and horizon. Both
outcomes are deliverable results.

```text
15A — Momentum and Regime Component Catalog        Sprint 051 (COMPLETE)
      momentum.rsi / momentum.macd / momentum.stochastic;
      volatility.relative_volatility, statistics.return_autocorrelation,
      statistics.return_distribution.
      SHARED catalog: consumable by rule-based Signal Models AND declarable
      as predictive FeatureSpec entries — one catalog, two consumers, exactly
      like every existing component. No ML-only component concept is created.
      Also carried the LONG-LEAD BTC data-acquisition task — SUCCEEDED,
      measured (BTCUSDT.P, 1m, 2024-01-01 -> 2026-06-29, 911 days,
      1,311,840 rows, zero gaps; S051_BTC_DATA_INVENTORY.md).
      Shipped NO study result and NO change to the Phase 10 pipeline.

15B — Real-Data BTC Predictive Study               Sprint 052 (NOT planned)
      One study on the imported BTCUSDT.P bars, through the UNMODIFIED
      build_predictive_dataset -> run_predictive_research ->
      analyze_predictive_run pipeline, reported against RANDOM_PERMUTATION
      per fold and pooled. Positive or negative, the result is written down.
      Ships NO new component and NO promotion work.
```

**Why two sprints, not one:** Sprint 051's acceptance is deterministic and
unit-testable; Sprint 052's acceptance is a reported comparison whose outcome
is unknown at planning time. Sprint 052 also has a hard external prerequisite
(real BTC data, network, maintainer wall-clock) not satisfied today —
bundling would let a data-acquisition stall block already-finished component
work from merging. Sprint 051 delivers standalone value even if Sprint 052 is
never opened.

## Binding rules

```text
OHLCV only. No orderflow, no options-derived, no cross-asset features
One instrument — BTCUSDT.P — and one horizon, consistent with ADR-0023 §9.
    NON-BTC DATA IS A HARD STOP, NOT A FALLBACK (maintainer, 2026-09-02):
    if the BTC import proves impractical, the work stops and returns to the
    maintainer. Substituting NQ.c.0 or any other instrument is forbidden —
    it would not satisfy this section's Q5 wording and would present a
    prerequisite as closed when it is not
ADR-0023 §8 is NOT reopened: CI fixtures stay synthetic-only, standard CI
    stays network-free. The real-data study is a maintainer-triggered
    research run, never a CI fixture and never a CI dependency
The Phase 10 pipeline is CONSUMED, never modified
NO estimator-family restriction is invented. §13F's linear/logistic limit is
    specific to ADR-0029's parity mechanism and is NOT inherited here
Sprint 049's artifact format, promotion store and evaluator are untouched
A negative result is a legitimate, reportable outcome — never repaired by
    adding features until something sticks
Sprint 050 / Phase 14B is not planned, resized or pre-empted by this phase;
    the only interface is supplying (or failing to supply) its Q5 input
```

## Dependencies

- Phase 10 complete (Sprints 039–044) — **satisfied** (#348),
- Phase 2F's Binance USD-M importer (Sprint 045, ADR-0025) — **the code was
  satisfied first; the data is now satisfied too.** Verified 2026-09-02: no
  `BTCUSDT.P` dataset had ever been imported at that point. Sprint 051 ran
  the import over the maintainer-fixed range and it **succeeded**:
  `BTCUSDT.P`, 1m, `2024-01-01 -> 2026-06-29` (911 days, 1,311,840 rows,
  zero gaps — measured, `S051_BTC_DATA_INVENTORY.md`), well within the
  wall-clock cost accepted as a known, priced cost (ADR-0025
  "Consequences") — the actual run took ~8m36s with zero rate-limit
  backoff,
- Phase 12/13's catalog and authoring work — consumed as precedent, unmodified.

## Main risks

- **The data acquisition risk is RESOLVED** — Sprint 051's import succeeded
  (measured: 911 days, 1,311,840 rows, zero gaps,
  `S051_BTC_DATA_INVENTORY.md`); the hard-stop-on-impracticability path
  (D-S051-07a) was never triggered.
- **The riskiest assumption:** the new components may add noise dimensions
  to overfit rather than signal — mitigated by the existing purge/embargo/
  permutation discipline and by treating a negative result as reportable.
- **MTF features are not expressible in a `PredictiveStudySpec` today** —
  verified in code (`FeatureSpec`, `AnalysisFrameColumnSpec` carry no
  computation timeframe). Single-timeframe-first is a structural fact, not a
  stylistic preference.
- **A negative result leaves this section's Q5 open**, and Sprint 050 then
  inherits S049 Wave 0's recorded option (b): promote a synthetic artifact
  as plumbing, loudly labelled — a maintainer decision, never a silent
  fallback.

## Out of scope

- orderflow / options-derived / cross-asset features,
- **any instrument other than `BTCUSDT.P`** — a study elsewhere would be
  separate, separately-approved work and would not close this section's Q5,
- any change to the promotion mechanism (Sprint 049) or Phase 14B's plan,
- MTF variants of the new components and the `FeatureSpec` contract change
  they would require,
- report/dashboard expansion for predictive results — the maintainer's
  stated third priority,
- promoting whatever this phase's study produces — that is Sprint 049's
  merged mechanism and the maintainer's separate act.

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
Separate Position Sizing Model
Distributed Strategy Execution
Automated feature engineering search
Online / incremental learning and live model inference
GPU or distributed model training
```

Deferred does not mean rejected.

**Promoted 2026-08-25:** *Automatic ML feature vector layer* left this list and became **Phase 10A**
(**§13A**). The declared feature matrix is explicit and bounded — it is not an automatic layer over
every available component.

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
