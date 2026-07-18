# Trading Research Framework

# CURRENT_STATUS.md

## 1. Purpose

This document provides a concise snapshot of the current state of the Trading Research Framework.

It answers:

- where the project is now,
- what has been completed,
- what is actively being prepared,
- what is blocked,
- what decisions remain open,
- what capability should be built next.

This file is a status summary.

It is not the operational task board.

Detailed task state belongs in `docs/planning/sprints/` and, once configured, GitHub Issues and GitHub Projects.

---

## 2. Status Metadata

```text
Status Date: 2026-07-18
Current Phase: Sprint 030 Repository Navigability Hygiene
Current Milestone: scratch/ + IDE excludes + artifacts/demo for cleaner Explorer
Implementation Status: Sprints 001-006, 008-021, 026-029 COMPLETE on main; Sprint 007 SKIPPED; Sprints 022-023 COMPLETE on sprint branch (pending integration PR to main)
Overall Status: IN_PROGRESS
Active Sprint: sprint/repo-navigability (SPRINT_030)
Last Completed Sprint: SPRINT_029 (sprint/repo-layout → main #235, 2026-07-18); SPRINT_028 (#232, 2026-07-18)
Capability Tracks: Foundation COMPLETE; Data 2A + 2B/2C.1 + 2B.3 + 2C.4 COMPLETE; Research 3/4A/5/5B/7 COMPLETE; Strategy 6A COMPLETE; Phase 8A local + AWS dry-run runtime + portfolio live dashboard COMPLETE on sprint branch; Dashboard app COMPLETE; Repo layout (ADR-0022 + uv workspace) COMPLETE
Recent: S028/S029 on main. Next: Sprint 030 navigability (scratch, artifacts/demo, IDE excludes); then Phase 8A polish or Phase 4B.
```

---

## 2.1 Current Phase 8A Update

As of 2026-07-16, Phase 8A has moved beyond local dry-run runtime setup:

- Sprint 018 delivered provider-independent dry-run execution contracts.
- Sprint 019 delivered the Binance BTCUSDT USD-M futures live-data adapter.
- Sprint 020 delivered the local BTC futures dry-run runtime.
- Sprint 021 delivered the local execution persistence read model and restart state.
- Current closure target: integration PR from `sprint/btc-futures-dry-run-execution` to `main`.

Sprint 019 live-data boundary:

```text
Binance public WebSocket
  -> infrastructure/providers/binance parser + mapper
  -> MarketBar / BestBidAskSnapshot / MarketFeedStatusSnapshot
  -> Sprint 020/021 dry-run runtime + execution read model
```

Standard CI remains network-free. Binance live smoke validation is opt-in through
`TRADING_FRAMEWORK_RUN_BINANCE_NETWORK_SMOKE=1`.

---

## 3. Current Objective

**Phase 5 — Signal Research MVP** is complete on `main` (PR #93, 2026-07-12).

**Sprint 011 — Historical Archive Import Foundation** is **complete** on `main` (PR #99, 2026-07-14).

Delivered trades import flow:

```text
Databento DBN trades → import_databento_trades_archive
    → day-partitioned MarketTrade Parquet + import_manifest.json
    → finalize → publish → query_trades
```

ADR: ADR-0014. See `SPRINT_011.md` and `S011_WAVE0_DECISIONS.md`.

**Sprint 012 — Derived OHLCV from Trades (Phase 2B.3)** is **complete** on `main` (PR #107, 2026-07-14).

Delivered derived bar flow:

```text
Published trades → derive_ohlcv_from_trades
    → TradesToBarsAggregator (1m) → bars.parquet + lineage
    → finalize → publish → query_historical
```

ADR: ADR-0015. CLI: `scripts/market_data/derive_bars_from_trades.py`. See `SPRINT_012.md` and `S012_WAVE0_DECISIONS.md`.

**Sprint 013 — OHLCV Strategy Research MVP (Phase 6A)** is **complete** on `main` (PR #113, 2026-07-14).

Delivered strategy research flow:

```text
Published OHLCV → Strategy Model (Market × Signal × Exit × Risk)
    → bar-sequential simulation → trades + equity envelope
    → analyze_strategy_research_run
```

ADR: ADR-0016. CLI: `scripts/strategy_research/run_strategy_research.py`. See `SPRINT_013.md` and `S013_WAVE0_DECISIONS.md`.

**Sprint 014 — Strategy Research Dashboard (Phase 6A Inspection, Phase A)** is **complete** on `main` (2026-07-14).

Delivered inspection flow:

```text
StrategyResearchRunEnvelope
    → build_strategy_dashboard_view_model (12 KPIs + panels + source bars)
    → render_strategy_research_dashboard → standalone HTML (Lightweight Charts, offline)
```

ADR: ADR-0017. CLI: `scripts/strategy_research/render_strategy_dashboard.py`. See `SPRINT_014.md` and `S014_WAVE0_DECISIONS.md`. Phase B (FastAPI lazy bars) deferred.

**Sprint 015 — Continuous Futures Materialization (Phase 2C.4)** is **complete** on `main` (PR #123, 2026-07-14).

Delivered preprocessing flow:

```text
Raw DBN → contract datasets (NQ.NQM5, …) → roll schedule (volume-rth-close)
    → materialized continuous trades + derived OHLCV (NQ.c.0)
    → query_historical / run_strategy_research (read-only)
```

ADR: ADR-0018 (ACCEPTED). CLI: `scripts/market_data/build_continuous.py`. See `SPRINT_015.md` and `S015_WAVE0_DECISIONS.md`.

**Research simulation refactor** (PRs #124–#129, #131–#132) on `main`: deep phase profiling, Numba fixed-bars kernel, simulation compile layer, columnar OHLCV for batch strategy research, shared model evaluation table.

**Portfolio demo** (scripts): `scripts/demo/run_portfolio_demo.py` — offline HTML for all major workflows plus live AWS dry-run status page.

Delivered Signal Research flow (on `main`):

```text
Published OHLCV → run_signal_research → persisted envelope
    → analyze_signal_research_run → summaries / grouping / conditional
    → optional HTML report (ADR-0013)
```

Phase 6A (Strategy Research on OHLCV + dashboard Phase A) is complete on `main`. See `ROADMAP.md` §10.

**Sprint 016 — Robustness Research MVP (Phase 7)** is **complete** on `main` (PR #141, 2026-07-15).

Delivered robustness flow:

```text
Declarative experiment spec → run_robustness_experiment / per-kind runners
    → batch Strategy Research child runs + resume registry
    → analyze_robustness_experiment → PASS / CONDITIONAL / FAIL verdict
    → render_robustness_report → human-readable HTML dashboard
```

ADR: ADR-0019 (ACCEPTED). CLIs: `scripts/robustness_research/`. Demo: `scripts/demo/run_robustness_demo.py`. See `SPRINT_016.md` and `S016_WAVE0_DECISIONS.md`.

**Sprint 017 — Model Research Methodology MVP (Phase 5B)** is **complete** on `sprint/model-research-methodology-mvp` (Wave 6 closure, 2026-07-15). Integration PR to `main` pending.

Delivered flow:

```text
SignalResearchDefinitionSpec (YAML/JSON)
    → bounded run_signal_research
    → analyze_signal_research_run (read-only + quality flags)
    → build_signal_research_report → Plotly HTML dashboard
    → NQ half-year demo (3 scopes) + fixture fallback
```

ADR: ADR-0020 (ACCEPTED). CLIs: `scripts/signal_research/`. Demos: `scripts/demo/run_model_research_nq_demo.py`, `run_portfolio_demo.py`. Methodology index: `docs/reference/RESEARCH_METHODOLOGIES.md`. See `SPRINT_017.md` and `S017_WAVE0_DECISIONS.md`.

---

## 4. Completed Capabilities

### Phase 0 — Project Governance

- planning documents, problem registry, roadmap and ADR index,
- Cursor rules and architecture documentation,
- Sprint 001 defined and completed.

Remaining non-blocking items: GitHub issue templates and Project board configuration.

### Phase 1 — Repository Foundation

Completed in Sprint 001:

- installable package (`trading_framework`, Python 3.12, uv, pydantic),
- quality toolchain: Ruff, mypy, pytest, pre-commit, GitHub Actions CI,
- domain package skeletons: `core`, `time`, `market`, `market_analysis`, `strategy`, `research`, `execution`, `events`, `config`, `infrastructure`, `application`,
- `user_data/README.md` placeholder and boundary documentation,
- core exceptions, `Identifier`, UTC time, `Timeframe`, `Clock`, `FrameworkConfig`,
- architecture boundary test,
- ADR-0001, ADR-0002, ADR-0003.

### Phase 2A — OHLCV Market Data MVP (roadmap: Phase 2)

Completed in Sprint 002 — OHLCV vertical slice only; trades, quotes, options and archive import are Phase 2B–2E:

- `Instrument`, `MarketBar`, `DatasetRef`, `DatasetState`, lifecycle contracts,
- CSV inspect → normalize → validate → Parquet → register → finalize → publish → query,
- application workflows: `import_external_dataset`, `finalize_dataset`, `publish_dataset`, `query_historical`,
- integration test for full CSV import flow,
- ADR-0007 (dataset lifecycle), ADR-0008 (Parquet storage),
- CI triggers for `main` and `sprint/**` branches.

### Phase 2B + 2C.1 — Trades Archive Import (Sprint 011)

Complete on `main` (2026-07-14, PR #99):

- `MarketTrade`, `Timeframe("tick")`, archive import contracts, `ImportManifest`,
- Databento adapter: inspect, chunked decode, side mapping,
- day-partitioned trade Parquet, `ParquetTradeDatasetRepository`, `query_trades`,
- `import_databento_trades_archive` workflow, CLI (`inspect_dbn.py`, `import_trades.py`),
- Tier 1 mocked tests + opt-in `tier2_databento` integration tests,
- ADR-0014; 458 tests at sprint closure.

### Phase 2B.3 — Derived OHLCV from Trades (Sprint 012)

Complete on `main` (2026-07-14, PR #107):

- `market/derivation/`: `DerivedOhlcvFromTradesConfig`, `TradesToBarsAggregator`,
- `derive_ohlcv_from_trades` workflow with lineage on derived `DatasetMetadata`,
- reuse `ParquetDatasetRepository` / `query_historical` (single-file `bars.parquet`),
- CLI `derive_bars_from_trades.py`; Tier 1 integration tests (E2E + mocked),
- spike `run_trades_to_bars_spike.py`; ADR-0015; 469 tests at sprint closure.

### Phase 3 — Market Analysis Engine MVP

Completed in Sprint 003 (merged to `main`):

- registry, DAG planner, sequential executor, execution cache, result store, workspace,
- NumPy adapter; vertical slice True Range → ATR → Volatility State + EMA,
- `AnalysisFrameAssembler`, `run_analysis` facade,
- ADR-0005, ADR-MA-001–011; 208 tests at sprint closure.

### Phase 4A — Bar-Based and Multitimeframe Market Analysis (Sprints 004–006)

Roadmap label **Phase 4A**. Sprints 004–006 delivered the bar-based and MTF foundation. Orderflow (4B) and options-derived analysis (4C) are future increments.

#### Sprint 004 — Multitimeframe Foundation

Completed on `main` (PR #60, 2026-07-12):

- timeframe roles: `computation_timeframe`, `evaluation_timeframe`, `RequestResolver`,
- `ResampleSpec`, `ResampleNode`, Polars resample/align, layered identities,
- `available_at` on HTF outputs, `LAST_CLOSED_BAR` + `join_asof` frame assembly,
- MTF behavior regressions and end-to-end vertical slice via `run_analysis`,
- ADR-MA-012; 240 tests at sprint closure.

#### Sprint 005 — Calendar, swing structure, visual inspection

Completed on `main` (2026-07-12):

- batch `TradingSessionResolver` and `CmeEsRthSessionResolver` (CME ES RTH),
- session metadata enrichment on `run_analysis` path,
- `structure.swing` component with event/state outputs and HH/HL/LH/LL classification,
- per-output MTF alignment: `EVENT_AT_AVAILABLE` vs `LAST_CLOSED_BAR`,
- behavior tests, S005 MTF vertical slice, Plotly inspection spike,
- ADR-MA-013; 280 tests at sprint closure.

#### Sprint 006 — Declarative Models

Completed on `main` (PR #75, 2026-07-12):

- `model_expression/` IR, validation, dependency extraction, evaluation,
- `market_model/` and `signal_model/` evaluators with firing policies,
- `model_authoring/` DSL compiling to IR,
- `evaluate_models` application orchestration,
- canonical examples, inspection overlay, ADR-0006,
- 338 tests at sprint closure.

### Phase 7 — Robustness Research MVP (Sprint 016)

Complete on `sprint/robustness-mvp` (2026-07-15, PRs #134–#140); integration PR to `main` pending:

- `research/robustness/`: experiment spec, parameter grid, walk-forward, stress, Monte Carlo, verdict
- `application/robustness_research/`: batch orchestration, per-kind runners, analyze + render report
- Human-readable HTML dashboard with section intros, plain-language labels, rounded metrics
- CLIs: analyze, render, Monte Carlo; demo script for NQ half-year
- ADR-0019; 665 tests at sprint closure

### Phase 6A — OHLCV Strategy Research MVP (Sprint 013)

Complete on `main` (2026-07-14, PR #113):

- `strategy/`: Exit/Risk/Strategy model contracts, canonical example
- `research/simulation/`: `SimulationAssumptions`, `BarSequentialSimulator`, trade/equity facts
- `run_strategy_research`, `analyze_strategy_research_run`, `StrategyResearchDatasetRepository`
- CLI `run_strategy_research.py`; integration test E2E round-trip
- ADR-0016; 495 tests at sprint closure.

### Phase 6A — Strategy Research Dashboard Phase A (Sprint 014)

Complete on `main` (2026-07-14):

- `build_strategy_dashboard_view_model` — 12 KPIs, performance/conditional panels, metric warnings
- `render_strategy_research_dashboard` — Lightweight Charts OHLCV + markers, equity/drawdown panes
- CLI `render_strategy_dashboard.py`; integration tests view model + HTML smoke
- ADR-0017; Phase B (inspection API) deferred

### Phase 5 — Signal Research (Sprint 008–010)

Complete on `main`:

- **Sprint 008:** `SIGNAL_MODEL_ONLY` computation, forward outcomes, envelope v1, ADR-0011
- **Sprint 009:** all three scopes (`MARKET_MODEL_ONLY`, `SIGNAL_MODEL_ONLY`, `MARKET_AND_SIGNAL`), envelope v2, context at `available_at`, ADR-0012, combined inspection spike
- **Sprint 010:** read-only analytics over persisted runs — scope-aware analysis frame, RunSummary, grouping (RTH, time-of-day, calendar month, context), conditional comparison with explicit true/false/missing context, join diagnostics, distribution quantiles, `analyze_signal_research_run`, optional HTML report, ADR-0013 ACCEPTED (PR #93)

### Architectural Foundations

Conceptual architecture: `docs/vision/`. As-implemented reference: `docs/reference/`.

Market Analysis (vision):

- `docs/vision/MARKET_ANALYSIS_WITH_DECISIONS.md` (D-001–D-036),
- `docs/vision/ANALYSIS_WORKSPACE_AND_DERIVED_DATA.md` (workspace, result store, frames; takes precedence on derived-data topics).

### Phase 2C.4 — Continuous Futures Materialization (Sprint 015)

Complete on `main` (2026-07-14, PR #123):

- multi-contract Databento import → per-contract `session_date` partitions (`market-trade-contract-v2`),
- volume-RTH-close roll schedule artifact with manifest,
- materialized continuous trades (`roll_id`, `is_roll_boundary`, fingerprint reuse),
- partitioned continuous OHLCV 1m from shared roll schedule,
- `build_continuous` orchestration CLI + consumer boundary tests,
- columnar batch paths for large-archive import and preprocessing,
- ADR-0018; 570 tests at sprint closure.

---

## 5. Documentation Baseline

Single index: **`docs/README.md`**

```text
docs/README.md                    taxonomy & reading paths
docs/vision/                      assumptions & target design
docs/reference/                   as-implemented (see reference/README.md)
docs/planning/                    status, roadmap, sprints
docs/adr/                         decision records
AGENTS.md
```

Maintenance: `.cursor/rules/documentation.mdc`

---

## 6. Work in Progress

**Portfolio demo packaging** — `scripts/demo/run_portfolio_demo.py` generates offline HTML artifacts for showcase (workflows + dashboards).

**Sprint 017 — Model Research Methodology MVP (Phase 5B)** — **complete** on `sprint/model-research-methodology-mvp` (Wave 6, 2026-07-15). Final integration PR to `main` pending.

**Plan:** `docs/planning/sprints/SPRINT_017.md` · **Wave 0:** `S017_WAVE0_DECISIONS.md` · **ADR:** ADR-0020 (ACCEPTED) · **Branch:** `sprint/model-research-methodology-mvp`

### Sprint 017 — Closed (Phase 5B)

**Status:** COMPLETE on sprint branch (2026-07-15, Waves 0–6)  
**Plan:** `docs/planning/sprints/SPRINT_017.md`  
**ADR:** ADR-0020  
**Tasks:** 10 / 10  
**PRs:** #142–#148 (estimated)  
**Scope:** research definition spec, quality diagnostics, report v2, CLI trio, model families, NQ half-year demo, `RESEARCH_METHODOLOGIES.md`

### Sprint 016 — Closed (Phase 7)

**Status:** COMPLETE on `main` (2026-07-15, PR #141)  
**Plan:** `docs/planning/sprints/SPRINT_016.md`  
**ADR:** ADR-0019  
**Tasks:** 34 / 34  
**PRs:** #134–#141  
**Scope:** experiment infra, parameter sweep, walk-forward, stress, diagnostics, Monte Carlo, verdict + human-readable HTML dashboard

### Sprint 015 — Closed

**Status:** COMPLETE on `sprint/continuous-futures-materialization` (2026-07-14)  
**Plan:** `docs/planning/sprints/SPRINT_015.md`  
**ADR:** ADR-0018  
**Tasks:** 19 / 19 done  
**PRs:** #115–#121 (implementation waves); closure docs in current PR

### Sprint 014 — Closed (Phase A)

**Status:** Phase A COMPLETE on `main` (2026-07-14)  
**Plan:** `docs/planning/sprints/SPRINT_014.md`  
**ADR:** ADR-0017  
**Tasks:** 13 / 13 Phase A done; Phase B (T014–T019) deferred  
**Commits:** `3808d1d` (view model), `9c14c7a` (HTML report + CLI); closure docs pending PR

### Sprint 013 — Closed

**Status:** COMPLETE on `main` (PR #113, 2026-07-14)  
**Plan:** `docs/planning/sprints/SPRINT_013.md`  
**ADR:** ADR-0016  
**Tasks:** 15 / 15 done  
**PRs:** #108–#112 (sprint waves), #113 (integration to main)

### Sprint 011 — Closed

**Status:** COMPLETE on `sprint/historical-archive-import` (2026-07-14)  
**Plan:** `docs/planning/sprints/SPRINT_011.md`  
**ADR:** ADR-0014  
**Tasks:** 27 / 27 done  
**PRs:** #95 (Wave 3), #96 (Wave 4), #97 (Wave 5); closure PR pending

### Sprint 010 — Closed

**Status:** COMPLETE on `main` (PR #93, 2026-07-12)  
**Plan:** `docs/planning/sprints/SPRINT_010.md`  
**ADR:** ADR-0013  
**Tasks:** 11 / 11 done

---

### Sprint 009 — Closed

**Status:** COMPLETE on `main`  
**Plan:** `docs/planning/sprints/SPRINT_009.md`  
**ADR:** ADR-0012  
**Tasks:** 11 / 11 done

---

### Sprint 008 — Closed

**Status:** COMPLETE on `main` (PR #81, 2026-07-12)  
**Plan:** `docs/planning/sprints/SPRINT_008.md`  
**ADR:** ADR-0011  
**Tasks:** 11 / 11 done

---

### Sprint 006 — Closed

**Status:** COMPLETE on `main` (PR #75, 2026-07-12)  
**Plan:** `docs/planning/sprints/SPRINT_006.md`  
**ADR:** ADR-0006  
**Tasks:** 26 / 26 done

---

## 7. Blocked Work

Nothing is technically blocked. Next step: merge closure docs PR, then Sprint 017 integration PR from `sprint/model-research-methodology-mvp` to `main`.

---

## 8. Open Critical Problems

From `PROBLEM_REGISTRY.md` — Sprint 004 delivered:

- PRB-002 — layered computation identity (Resample / Component / Alignment) — partial MVP resolution extended,
- PRB-007 — deferral documented (fixed UTC resampling; exchange calendar in Sprint 005+).

Sprint 005 delivered partial PRB-007 resolution (CME ES RTH batch resolver only).

Remaining high-priority items:

1. Public `user_data/` discovery contract (PRB-004).
2. Research Dataset physical schemas (PRB-006).
3. Full exchange/session Trading Calendar (PRB-007 — partial MVP only; Globex, missing-range, registry open).
4. Local model definition fingerprints (PRB-003).
5. Full component implementation fingerprints (PRB-002 — parameter identity resolved in MVP).
6. Vectorized backtest semantics (PRB-014).
7. Research/runtime parity (PRB-013).
8. Representative integration and research-validation datasets (PRB-017).

PRB-001, PRB-008 and PRB-010 received MVP resolution in Sprint 002.  
PRB-002 and PRB-005 received partial MVP resolution in Sprint 003.

---

## 9. Open Architectural Decisions

| ADR | Status |
|-----|--------|
| ADR-0001 Modular Monolith | ACCEPTED |
| ADR-0002 Separate src and user_data | ACCEPTED |
| ADR-0003 UTC Internal Time | ACCEPTED |
| ADR-0007 Dataset Lifecycle | ACCEPTED (Sprint 002) |
| ADR-0008 Parquet Storage | ACCEPTED (Sprint 002) |
| ADR-0005 Market Analysis Domain | ACCEPTED (Sprint 003) |
| ADR-MA-001–011 Market Analysis Engine | ACCEPTED (Sprint 003) |
| ADR-MA-012 Batch MTF with Polars | ACCEPTED (Sprint 004) |
| ADR-MA-013 CME ES RTH + Swing Structure MTF | ACCEPTED (Sprint 005) |
| ADR-0006 | ACCEPTED (Sprint 006) |
| ADR-0011 | ACCEPTED (Sprint 008) |
| ADR-0012 | ACCEPTED (Sprint 009) |
| ADR-0013 | ACCEPTED (Sprint 010) |
| ADR-0014 | ACCEPTED (Sprint 011) |
| ADR-0015 | ACCEPTED (Sprint 012) |
| ADR-0016 | ACCEPTED (Sprint 013) |
| ADR-0017 | ACCEPTED (Sprint 014) |
| ADR-0018 | ACCEPTED (Sprint 015) |
| ADR-0019 | ACCEPTED (Sprint 016) |
| ADR-0020 | ACCEPTED (Sprint 017) |
| ADR-0021 | ACCEPTED (Sprint 018) |
| ADR-0022 Repository Top-Level Layout | ACCEPTED (Sprint 029) |
| ADR-0004, ADR-0009, ADR-0010 | PLANNED |

Binding decisions D-001–D-036 and workspace invariants are documented in the architecture files above; ADR materialization is Sprint 003 Wave 6 (including ADR-MA-007 workspace).

---

## 10. Known Risks

- **Inherited S002/S003 complexity** — MarketBar list, AnalysisDataView, Store+Workspace+Cache; see Architecture Simplification Review and TD-011–TD-016. Sprint 004 must not stack new wrappers without checklist §5.
- **Phase 4 scope creep** — multitimeframe and component catalog can expand quickly; keep outcome-scoped PRs.
- **Polars boundary creep** — Polars for resample/align only until MarketFrame migration is explicitly planned.
- **Implementation fingerprint gap** — PRB-002 parameter identity is resolved; full implementation hashing remains for research parity.
- **TA-Lib optional path** — deferred T027/S004-T016; NumPy adapter is the CI reference backend.

---

## 11. Next Planned Capability

```text
Sprint 030 — Repository Navigability Hygiene (ACTIVE)
    scratch/ + IDE excludes + demo/ → artifacts/demo/

Also queued:
    Sprint 024/025 — Phase 8A dry-run reliability / visualization polish
    Phase 4B — Orderflow Market Analysis
    Phase 6B — Multi-data Strategy Research
    PBO / CSCV / deflated Sharpe increment (separate ADR)

Recently completed:
    Sprint 028 — Dashboard Application MVP → main (#232)
    Sprint 029 — Repository Layout Foundations → main (#235)

Deferred (explicit):
    packages/ shared presentation contracts (until second DTO consumer)
    Deep market_analysis/ reorg (TD-003) until Phase 4B/4C
    Full ops/ nesting of deploy/ (rejected for S030)
```

See `docs/planning/sprints/SPRINT_030.md`, `SPRINT_029.md`, and `ROADMAP.md` §11–§12.

---

## 12. Sprint Progress

| Sprint | Goal | Status | Progress |
|--------|------|--------|----------|
| 001 | Repository foundation | COMPLETED | 22 / 22 tasks |
| 002 | Market Data MVP | COMPLETED | 26 / 26 tasks |
| 003 | Market Analysis Engine MVP | COMPLETED | 40 / 41 tasks (T027 deferred) |
| 004 | Multitimeframe Foundation MVP | COMPLETED | 15 / 15 tasks (T016 deferred) |
| 005 | Calendar, swing structure, visual inspection | COMPLETED | 16 / 16 tasks (T017–T018 deferred) |
| 006 | Declarative Market Model and Signal Model | COMPLETED | 26 / 26 tasks |
| 007 | Research-enabling catalog | SKIPPED (scope gate) | 1 / 9 (T001 only) |
| 008 | Signal Research computation MVP | COMPLETED | 11 / 11 tasks |
| 009 | Combined research scopes | COMPLETED | 11 / 11 tasks |
| 010 | Signal Research analytics | COMPLETED | 11 / 11 tasks |
| 011 | Historical archive import — trades DBN (Phase 2B + 2C.1) | COMPLETED | 27 / 27 tasks |
| 012 | Derived OHLCV from trades (Phase 2B.3) | COMPLETED | 12 / 12 tasks |
| 013 | OHLCV Strategy Research MVP (Phase 6A) | COMPLETED | 15 / 15 tasks |
| 014 | Strategy Research dashboard Phase A | COMPLETED | 13 / 13 Phase A tasks |
| 015 | Continuous futures materialization (Phase 2C.4) | COMPLETED | 19 / 19 tasks |
| 016 | Robustness Research MVP (Phase 7) | COMPLETED | 34 / 34 tasks |
| 017 | Model Research Methodology MVP (Phase 5B) | COMPLETED | 10 / 10 tasks; integration PR to main pending |
| 018 | Dry-run Execution contracts (Phase 8A) | COMPLETED | 2 / 2 Wave 0 tasks + execution contracts |
| 019 | Binance BTC Futures Live Data Adapter (Phase 8A) | COMPLETED | 9 / 9 tasks |
| 020 | Local BTC Futures Dry-Run Runtime (Phase 8A) | COMPLETED | 8 / 8 tasks |
| 021 | Execution Persistence and Read Model (Phase 8A) | COMPLETED | 8 / 8 tasks |
| 022 | AWS Runtime MVP for BTC Futures Dry Run (Phase 8A) | COMPLETED | 9 / 9 tasks; integration PR to main pending |
| 023 | OVH portfolio live dry-run dashboard (Phase 8A) | COMPLETED | sprint branch; integration PR pending |
| 024 | Dry-run reliability / operating polish (Phase 8A) | PLANNED | after 023 integration |
| 025 | Live dry-run visualization polish (Phase 8A, optional) | PLANNED | after 024 |
| 026 | Research hot-path performance (Signal + Robustness) | COMPLETED | integrated to main (#215) |
| 027 | Market Data import / continuous build performance | COMPLETED | integrated to main (#220) |
| 028 | Dashboard Application MVP (Streamlit + DuckDB) | COMPLETED | integrated to main (#232) |
| 029 | Repository Layout Foundations | COMPLETED | integrated to main (#235) |
| 030 | Repository Navigability Hygiene | IN_PROGRESS | scratch + artifacts/demo + IDE excludes |

---

## 13. Status Update Rules

Update this document when:

- a sprint begins or ends,
- the current phase changes,
- a capability is completed,
- a critical blocker appears,
- an architectural decision materially changes direction,
- the next planned capability changes.

Do not use this file as a second task board.

Keep it concise enough to understand project state quickly.
