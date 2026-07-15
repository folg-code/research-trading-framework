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
Status Date: 2026-07-14
Current Phase: Post-Sprint 015 — platform MVP on OHLCV + continuous futures (on main)
Current Milestone: Research platform vertical slice complete; next increment TBD (Phase 7, 4B, or 6B)
Implementation Status: Sprints 001–006, 008–015 COMPLETE on main; Sprint 007 SKIPPED
Overall Status: IN_PROGRESS
Active Sprint: none (portfolio demo + next sprint selection)
Last Completed Sprint: SPRINT_015 (merged to main, 2026-07-14)
Capability Tracks: Foundation COMPLETE; Data 2A + 2B/2C.1 + 2B.3 + 2C.4 COMPLETE; Research 3/4A/5 COMPLETE; Strategy 6A COMPLETE
Recent perf: columnar OHLCV + shared eval → **~6 s** half-year NQ strategy research (178k bars, 45M ticks ingested); see README § Scale & performance and DATA_WORKFLOWS §1.1
```

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

**Portfolio demo** (scripts): `scripts/demo/run_portfolio_demo.py` — offline HTML for all major workflows.

Delivered Signal Research flow (on `main`):

```text
Published OHLCV → run_signal_research → persisted envelope
    → analyze_signal_research_run → summaries / grouping / conditional
    → optional HTML report (ADR-0013)
```

Phase 6A (Strategy Research on OHLCV + dashboard Phase A) is complete on `main`. See `ROADMAP.md` §10.

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

**Next sprint selection** — no active sprint. Candidates: Phase 7 robustness, Phase 4B orderflow, Phase 6B multi-data, or research-at-scale on continuous NQ. See §11.

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

Nothing is technically blocked. Next step: choose next sprint increment (§11) or ship portfolio demo from `scripts/demo/`.

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
Post-Sprint 015 (choose one):
    A — Research at scale on multi-year NQ continuous OHLCV + portfolio polish
    B — Phase 7: Robustness Research (walk-forward, OOS on persisted strategy runs)
    C — Phase 4B: Orderflow Market Analysis on published trades
    D — Phase 2C.2 / 6B: MarketQuote datasets and multi-data strategy research
```

See `ROADMAP.md` §10–§11.

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
