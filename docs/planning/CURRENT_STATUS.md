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
Status Date: 2026-09-01
Current Phase: Phase 10 — Predictive (ML) Research — COMPLETE (Sprints 039-044);
  Phase 2F — Exchange REST Historical Import — COMPLETE (Sprint 045);
  Phase 11 — Universal Operator CLI — COMPLETE (Sprint 046);
  Phase 12 — Custom Strategy Authoring — COMPLETE (Sprint 047);
  Phase 13 — Exit/Risk Model Expansion — PROPOSED, approved, in progress (Sprint 048)
Current Milestone: Sprint 048 (Phase 13) approved and starting — resumes ADR-0028
  (BracketExitModel, EquityPercentRiskModel, five bounded engine changes, a new
  bracket kernel, two catalog components, three example strategies)
Implementation Status: Sprints 001-047 on main (S044 merged via #348; S045 merged via
  #355; S046 merged via #361; S047 merged via #366); S048 in progress (4/13, Wave 1
  complete via #368-#370) on sprint/exit-risk-and-catalog
Overall Status: STABLE
Active Sprint: SPRINT_048 (Exit/Risk Model Expansion, Catalog Growth and New Strategies,
  Phase 13) — Wave 1 complete (golden run + gate widening + run-identity generalization),
  Wave 2 (BracketExitModel, EquityPercentRiskModel, kernels/bracket.py) starting
Last Completed Sprint: SPRINT_047 (Custom Strategy Authoring, Phase 12 opening and closing
  increment) — 10/10 tasks complete, merged to main via #366. Sprint 046 (Universal
  Operator CLI, Phase 11) is merged to main (#361).
Capability Tracks: Foundation COMPLETE; Data COMPLETE (core); Research COMPLETE (core); Strategy 6A COMPLETE; Phase 8A dry-run + S024 on main; Dashboard / Live Paper / public demo COMPLETE; Phase 10 COMPLETE (S039-S044: Foundation, Tree-Based and Neural Predictive Models, dashboard page, ADR-0024 + IDEA-014 gate); Phase 2F COMPLETE (S045: Binance USD-M historical OHLCV import, ADR-0025, merged to main #355); Phase 11 COMPLETE (S046: Universal Operator CLI trading-cli, ADR-0026, merged to main #361); Phase 12 COMPLETE (S047: Custom Strategy Authoring, `strategy_file` loader + candle.wick + structure.level_distance, ADR-0027, merged to main #366; ADR-0028 declined for S047); Phase 13 APPROVED, IN PROGRESS (S048: resumes ADR-0028 with corrections, Status flipped to ACCEPTED — BracketExitModel, EquityPercentRiskModel, trend.ema_distance, volatility.range_expansion, three example strategies)
Recent: S047 merged to main via #366, closing Phase 12. S048 (Phase 13) planning PR
  opened ADR-0028's resumption (Status flip PROPOSED-declined -> ACCEPTED, with five
  corrections found by re-verifying the original engine-change plan against the
  post-S047 tree), SPRINT_048.md, S048_WAVE0_DECISIONS.md and ROADMAP §13E; approved by
  the maintainer 2026-09-01. Wave 1 (golden-run capture) is the next task.
```

---

## 2.1 Current Phase 8A Update

Phase 8A (BTC futures live dry-run) is **on main** through Sprint 022/023 integration (#199 / #202).
Streamlit Live Paper is the primary public UI (Sprints 031–034).

Sprint 024 dry-run reliability polish is **on main** (#270): feed≠heartbeat, reconnect/last_error,
SIGTERM→STOPPED, Live Paper RuntimeHealth badges, DynamoDB TTL, failure-mode tests, architecture
one-pager. CloudWatch alarm spec, operator runbook base, and cost modes remain from Sprint 022.

Sprint 019 live-data boundary:

```text
Binance public WebSocket
  -> infrastructure/providers/binance parser + mapper
  -> MarketBar / BestBidAskSnapshot / MarketFeedStatusSnapshot
  -> Sprint 020/021 dry-run runtime + execution read model
  -> AWS worker + read-only status API + dashboard Live Paper
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

**Sprint 036 — Research Infra Audit** is **complete** on `main` (#288, 2026-08-25).

Delivered:

```text
Wave 0 path inventory
    → authoring bench + ranked DATA_REPRESENTATION_AUDIT
    → Stage 0.5–2 (session resolver, resample without MarketBar,
       derive table validation, scan_parquet, lazy analysis frame)
    → ADRs for Stage 3/4 (code not started)
    → S037_GATE.md
```

Audit: `docs/reference/DATA_REPRESENTATION_AUDIT.md`. Gate: `docs/planning/sprints/S037_GATE.md`.
Bench: `scripts/ops/bench_authoring_analysis_evaluate.py`. See `SPRINT_036.md` and `S036_WAVE0_DECISIONS.md`.

**Sprint 037 — Component libraries + DSL simplification** is **complete** on
`main` (#296, 2026-08-25). Working PRs: #289–#295.

Delivered:

```text
Wave 0 lock (D-S037-01 … D-S037-09)
    → volatility.atr / volatility.true_range DSL
    → structure.swing HH/HL/LH/LL events + latest_*_level
    → copy-pasteable model_authoring example
    → trend.slope (causal OLS of close) + DSL
```

`compile.py` was not changed; T006 bench re-run is N/A.

**Sprint 038 — Session Range Structure** is **complete** on `main` (#300, 2026-08-25).
Working PRs: #297–#299.

Delivered:

```text
Wave 0 lock A/A/A/A (D-S038-04 … D-S038-07)
    → session_metadata on AnalysisWorkspaceView (HTF re-resolve + cache)
    → structure.session_range running RTH OHLC/range + session_completed
    → model_authoring structure.session_* namespace
```

IDEA-014 training remains deferred. Next catalog: wick, then distance-to-level.
See `SPRINT_038.md` and `S038_WAVE0_DECISIONS.md`.

**Sprint 039 — Predictive Research Dataset Foundation (Phase 10A)** is **COMPLETED**
on `main` (#309, 2026-08-26). Working PRs: #302–#308.

Delivered dataset flow (on `main`):

```text
Published DatasetRef + PredictiveStudySpec
    → labelled evaluation-bar matrix + purged walk-forward fold roles
    → PredictiveDatasetEnvelope under research/predictive_research/datasets/{dataset_id}/
```

ADR: ADR-0023 (ACCEPTED). CLI: `scripts/predictive_research/build_predictive_dataset.py`.
See `SPRINT_039.md` and `S039_WAVE0_DECISIONS.md`. S040 landed as #319; S041
landed as #325. Phase 10A is complete.

**Sprint 040 — Baseline Regression and Classification (Phase 10A)** is **COMPLETED**
on `main` (#319, 2026-08-26). Working PRs: #310–#318.

Delivered run flow (on `main` via #319):

```text
PredictiveDatasetEnvelope
    → EstimatorSpec + fold-local preprocessing
    → run_predictive_research
    → PredictiveRunEnvelope (predictions, metrics, opaque fold blobs)
    → analyze_predictive_run
```

Extra `ml` = scikit-learn (`scikit-learn>=1.6,<2.0`), not in default `dev`.
Dedicated CI job `ml`. CLIs: `scripts/predictive_research/run_predictive_research.py`,
`analyze_predictive_run.py`. See `SPRINT_040.md` and `S040_WAVE0_DECISIONS.md`.
No new ADR (ADR-0024 reserved for IDEA-014). S041 landed as #325;
Phase 10A is complete.

**Sprint 041 — Predictive Research Report v1 (Phase 10A)** is **COMPLETED**
on `main` (#325, 2026-08-26). Working PRs: #320–#324.

Delivered report flow:

```text
PredictiveRunEnvelope + PredictiveMetricsReport + PredictiveDatasetEnvelope
    → build_predictive_report_view_model (read-only)
    → Plotly panels + quality flags
    → render_predictive_research_report → <run-dir>/report.html
```

CLI: `scripts/predictive_research/render_predictive_report.py`. Offline Plotly
(inline embed; no CDN). See `SPRINT_041.md` and `S041_WAVE0_DECISIONS.md`.

**Sprint 042 — Tree-Based Predictive Models (Phase 10B)** is **COMPLETED**
on `main` (#335, 2026-08-26, 22/22). Working PRs #326–#334.

Delivered tree-model flow:

```text
EstimatorSpec family = xgboost.* | lightgbm.* | catboost.*
    → extra ml-trees adapters (thread count = 1, GPU rejected)
    → optional CandidateSetSpec (cap 8 default / 16 hard max; inner 20% of TRAIN)
    → native + permutation importance + |train - test| gap
    → compare_predictive_runs (one dataset fingerprint, S040 baselines as rows)
    → report panels feature_importance / leaderboard / selection_trace
```

Extra `ml-trees` is opt-in and not in default `dev`. Resolving a tree family
needs both `ml` and `ml-trees`. CLI: `scripts/predictive_research/compare_predictive_runs.py`.
No new ADR (ADR-0024 reserved for IDEA-014). See `SPRINT_042.md` and
`S042_WAVE0_DECISIONS.md`.

**Sprint 043 — Neural Predictive Models (Phase 10C)** is **COMPLETE**
on `main` (#342; Wave 0 #336, Wave 1 #337, Wave 2 #338, Wave 3 #339,
Wave 4 #340, Wave 5 #341).

See `SPRINT_043.md` and `S043_WAVE0_DECISIONS.md`. Sequence windowing is
domain-only. Extra `dl` is CPU PyTorch, not in default `dev`, and independent
of extra `ml`. Sequence families consume rank-3 windows built by application
before `fit()` / `predict()`, and fit the scaler on 2d TRAIN rows. On the
synthetic known-signal fixture, feedforward ranked above LSTM; both beat
`RANDOM_PERMUTATION`.

**Sprint 044 — Predictive dashboard + IDEA-014 gate (Phase 10C)** is
**COMPLETE** (18/18), merged to `main` via #348. Plan: `SPRINT_044.md`. Locks:
`S044_WAVE0_DECISIONS.md`. ADR-0024 (Wave 3) is ACCEPTED. **Phase 10 is
closed** — see ROADMAP §13A.

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

**Active sprint:** Sprint 048 (Exit/Risk Model Expansion, Catalog Growth and
New Strategies, Phase 13) — approved by the maintainer 2026-09-01, cut from
`main` after Sprint 047 merged; Wave 1 complete (4/13, #368-#370), Wave 2
starting. Sprint 047 is merged
to `main` (#366, 10/10) and closes Phase 12. Sprint 046 is merged to `main`
(#361, 14/14) and closes Phase 11. Sprint 045 is merged to `main` (#355,
14/14) and closes Phase 2F. Sprint 044 is complete on `main` (#348, 18/18).
Sprint 043 is complete on `main` (#342, 21/21).

**Portfolio demo packaging** — `scripts/demo/run_portfolio_demo.py` generates offline HTML artifacts for showcase (workflows + dashboards).

**Sprint 017 — Model Research Methodology MVP (Phase 5B)** — **complete** on `sprint/model-research-methodology-mvp` (Wave 6, 2026-07-15). Final integration PR to `main` pending.

**Plan:** `docs/planning/sprints/SPRINT_017.md` · **Wave 0:** `S017_WAVE0_DECISIONS.md` · **ADR:** ADR-0020 (ACCEPTED) · **Branch:** `sprint/model-research-methodology-mvp`

### Sprint 048 — Active (Phase 13 opening increment)

**Status:** IN PROGRESS (Wave 0 signed off 2026-09-01; Wave 1 complete)
**Plan:** `docs/planning/sprints/SPRINT_048.md`
**Wave 0:** `docs/planning/sprints/S048_WAVE0_DECISIONS.md`
**ADR:** ADR-0028 (ACCEPTED — declined for Sprint 047, resumed with
corrections for Sprint 048; Status flipped in place, dated decline record
preserved under "History")
**Tasks:** 4 / 13 — Wave 1 complete (#368, #369, #370)
**Branch:** `sprint/exit-risk-and-catalog` (cut from `main` after #366)
**Scope:** `BracketExitModel` + `EquityPercentRiskModel`; five bounded engine
changes across three files plus a new `kernels/bracket.py`; a golden-run
regression protecting the fixed-bars path; `trend.ema_distance` and
`volatility.range_expansion` Market Analysis components; three worked
example strategies (`ema_reversion_bracket`, `range_expansion_breakout`,
`quiet_wick_rejection`) proving the new models compose with the catalog and
the unchanged Sprint 047 loader.

### Sprint 047 — Closed (Phase 12 opening and closing increment; Phase 12 complete)

**Status:** COMPLETE (10/10), merged to `main` via #366
**Plan:** `docs/planning/sprints/SPRINT_047.md`
**Wave 0:** `docs/planning/sprints/S047_WAVE0_DECISIONS.md`
**ADR:** ADR-0027 (ACCEPTED); ADR-0028 (declined for this sprint — Wave 2
dropped, see SPRINT_047.md §4 Finding 1; resumed for Sprint 048)
**Tasks:** 10 / 10 (S047-T005–T008 retired with Wave 2, not renumbered)
**PRs:** #363 (`strategy_file` loader, T001–T004), #364 (`candle.wick` +
`structure.level_distance` components, T009–T010), #365/#366 (examples +
end-to-end metric test + docs + closure, T011–T014; #366 merged to `main`)
**Branch:** `sprint/strategy-authoring` (merged)
**Scope:** `research.strategy.strategy_file` config key loading an
operator-authored Python strategy file (`trading_cli/strategy_loader.py`,
fixed `build_strategy()` convention, full pre-flight error taxonomy);
`candle.wick` and `structure.level_distance` Market Analysis components;
two worked example strategies + example configs proving the loader composes
with the catalog end to end; `docs/reference/STRATEGY_AUTHORING.md`;
`OPERATOR_CLI.md` / `apps/cli/CLAUDE.md` / `MODULE_MAP.md` updates; Phase 12
closure documentation. Wave 2 (`BracketExitModel`, `EquityPercentRiskModel`,
engine dispatch) was declined by the maintainer for this sprint — resumed
for Sprint 048.

### Sprint 046 — Closed (Phase 11 opening and closing increment; Phase 11 complete)

**Status:** COMPLETE (14/14), merged to `main` via #361
**Plan:** `docs/planning/sprints/SPRINT_046.md`
**Wave 0:** `docs/planning/sprints/S046_WAVE0_DECISIONS.md`
**ADR:** ADR-0026 (ACCEPTED)
**Tasks:** 14 / 14
**PRs:** #356 (skeleton + config loader + exit-code taxonomy), #357 (command
groups wired to existing workflows), #358 (ADR-0026 Amendment 1: Wave 2
import-boundary exceptions), #359 (Binance wiring + example configs +
operator guide + module context), #361 (roadmap/status closure, merged to
`main`)
**Branch:** `sprint/operator-cli` (merged)
**Scope:** `apps/cli` workspace member exposing `trading-cli` over the four
command groups (`data fetch`, `research run`, `dry-run start`, `report
render`), YAML config contract with strict validation, `--dry-run` /
`--json` / exit-code taxonomy, import-boundary test, example configs,
`docs/reference/OPERATOR_CLI.md`, `apps/cli/CLAUDE.md`, Phase 11 closure
documentation

### Sprint 045 — Closed (Phase 2F opening increment; Phase 2F complete)

**Status:** COMPLETE (14/14), merged to `main` via #355
**Plan:** `docs/planning/sprints/SPRINT_045.md`
**Wave 0:** `docs/planning/sprints/S045_WAVE0_DECISIONS.md`
**ADR:** ADR-0025 (ACCEPTED)
**Tasks:** 14 / 14
**PRs:** #349 (Wave 0), #350 (reader + rate-limit governor), #351 (import
workflow), #352 (docs fix), #353 (CLI + tests + boundary guard), #354 (docs +
roadmap/status closure)
**Branch:** `sprint/binance-historical-ohlcv`
**Scope:** paginated Binance USD-M historical klines reader, weight-aware
rate limiting, optional API key, `import_binance_futures_ohlcv` workflow,
thin CLI, Tier 1/2 tests, provider boundary test, Phase 2F closure
documentation

### Sprint 044 — Closed (Phase 10C closing increment; Phase 10 complete)

**Status:** COMPLETE (18/18), merged to `main` via #348
**Plan:** `docs/planning/sprints/SPRINT_044.md`
**Wave 0:** `docs/planning/sprints/S044_WAVE0_DECISIONS.md`
**ADR:** ADR-0024 (ACCEPTED)
**Tasks:** 18 / 18
**PRs:** #343 (Wave 0), #344 (catalog), #345 (gate + ADR-0024), #346 (page),
#347 (boundary test + Phase 10 closure docs); #348 (integration to main)
**Branch:** `sprint/predictive-dashboard-and-gate` (merged)
**Scope:** read-only Predictive Research page in the dashboard; IDEA-014
promotion **conditions** (ADR-0024), not an ML Market Analysis component;
dashboard boundary test; Phase 10 closure documentation

### Sprint 043 — Closed (Phase 10C neural)

**Status:** COMPLETE on `main` (#342, 21/21, 2026-08-27)
**Plan:** `docs/planning/sprints/SPRINT_043.md`
**Wave 0:** `docs/planning/sprints/S043_WAVE0_DECISIONS.md`
**ADR:** ADR-0023 (ACCEPTED; no new ADR this sprint; ADR-0024 reserved for IDEA-014)
**Tasks:** 21 / 21
**PRs:** #336–#341 (working); #342 (sprint → main)
**Scope:** extra `dl` (CPU PyTorch), sequence windows, feedforward / LSTM / GRU,
learning-curve and window-accounting panels, leaderboard vs trees and baselines,
synthetic comparison (feedforward > LSTM on known-signal; both > permutation)

### Sprint 042 — Closed (Phase 10B trees)

**Status:** COMPLETE on `main` (#335, 22/22, 2026-08-26)
**Plan:** `docs/planning/sprints/SPRINT_042.md`
**ADR:** ADR-0023 (ACCEPTED; no new ADR this sprint; ADR-0024 reserved for IDEA-014)
**Tasks:** 22 / 22
**PRs:** #326–#334 (working); #335 (sprint → main)
**Scope:** extra `ml-trees`, XGBoost / LightGBM / CatBoost adapters, bounded
candidate selection, native + permutation importance, train/test gap,
single-study leaderboard, report panels, known-signal comparison study

### Sprint 041 — Closed (Phase 10A report)

**Status:** COMPLETE on `main` (#325, 2026-08-26)
**Plan:** `docs/planning/sprints/SPRINT_041.md`
**ADR:** ADR-0023 (ACCEPTED; no new ADR this sprint)
**Tasks:** 16 / 16
**PRs:** #320–#324 (working); #325 (sprint → main)
**Scope:** read-only view model, quality flags, diagnostic and task panels,
offline HTML assembly, CLI, regression + classification smoke tests

### Sprint 040 — Closed (Phase 10A baselines)

**Status:** COMPLETE on `main` (#319, 2026-08-26)
**Plan:** `docs/planning/sprints/SPRINT_040.md`
**ADR:** ADR-0023 (ACCEPTED; no new ADR this sprint)
**Tasks:** 23 / 23
**PRs:** #310–#318 (working); #319 (sprint → main)
**Scope:** estimator protocol, extra `ml`, sklearn ridge / elastic net / logistic,
fold-local preprocessing, run envelope, metrics + reference baselines, CLIs,
determinism and known-signal tests

### Sprint 039 — Closed (Phase 10A dataset foundation)

**Status:** COMPLETE on `main` (#309, 2026-08-26)
**Plan:** `docs/planning/sprints/SPRINT_039.md`
**ADR:** ADR-0023 (ACCEPTED)
**Tasks:** 20 / 20
**PRs:** #302–#308 (working); #309 (sprint → main)
**Scope:** study spec, labelled matrix, purged walk-forward folds, dataset envelope + CLI, leakage suite

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

Nothing is technically blocked. Sprint 043 is complete on `main` (#342).
Extra `dl` stays out of default CI. Sprint 017 integration PR from
`sprint/model-research-methodology-mvp` to `main` remains pending and does
not block Phase 10.

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
| ADR-MA-014 MarketFrame / Polars committed bulk engine | ACCEPTED (Sprint 036; D-REP-01) |
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
| ADR-0023 Predictive Research Domain Boundary | ACCEPTED (Sprint 039) |
| ADR-0004, ADR-0009, ADR-0010 | PLANNED |

Binding decisions D-001–D-036 and workspace invariants are documented in the architecture files above; ADR materialization is Sprint 003 Wave 6 (including ADR-MA-007 workspace).

---

## 10. Known Risks

- **Inherited S002/S003 complexity** — MarketBar list, AnalysisDataView, Store+Workspace+Cache; see Architecture Simplification Review and TD-011–TD-016. Sprint 004 must not stack new wrappers without checklist §5.
- **Phase 4 scope creep** — multitimeframe and component catalog can expand quickly; keep outcome-scoped PRs.
- **Polars boundary creep** — accepted in ADR-MA-014: Polars is the committed bulk engine;
  `AnalysisDataView` remains the live-runtime adapter. Stage 4 implements `MarketFrame`.
- **Implementation fingerprint gap** — PRB-002 parameter identity is resolved; full implementation hashing remains for research parity.
- **TA-Lib optional path** — deferred T027/S004-T016; NumPy adapter is the CI reference backend.

---

## 11. Next Planned Capability

```text
Public demo loop CLOSED (S028–S034 + follow-ups #261–#264).
Sprint 024 dry-run reliability → main (#270).
Sprint 035 track choice CLOSED.
Sprint 036 research infra audit COMPLETED on main (#288).
Sprint 037 component libraries + DSL COMPLETED on main (#296).
Sprint 038 Session Range COMPLETED on main (#300).
Sprint 039 Predictive Research dataset foundation COMPLETED on main (#309; #302–#308).
Sprint 040 Predictive Research baselines COMPLETED on main (#319; #310–#318).
Sprint 041 Predictive Research report COMPLETED on main (#325; #320–#324).
Sprint 042 tree-based predictive models COMPLETED on main (#335; #326–#334).
Sprint 043 neural predictive models COMPLETED on main (#342; #336–#341).
Sprint 044 predictive dashboard + IDEA-014 gate COMPLETE (18/18), merged to
main via #348. ADR-0023 and ADR-0024 ACCEPTED. Phase 10 (10A, 10B, 10C) is COMPLETE.
Sprint 045 Binance USD-M historical OHLCV ingestion (Phase 2F) COMPLETE
(14/14), merged to main via #355. ADR-0025 ACCEPTED. Phase 2F is COMPLETE
(ROADMAP §13B).
Sprint 046 Universal Operator CLI (Phase 11) COMPLETE (14/14), merged to
main via #361. ADR-0026 ACCEPTED. Phase 11 is COMPLETE (ROADMAP §13C).
Sprint 047 Custom Strategy Authoring (Phase 12) COMPLETE (10/10), merged to
main via #366. ADR-0027 ACCEPTED; ADR-0028 declined for this sprint (Wave 2
dropped). Phase 12 is COMPLETE (ROADMAP §13D).
Sprint 048 Exit/Risk Model Expansion, Catalog Growth and New Strategies
(Phase 13) APPROVED (2026-09-01) on sprint/exit-risk-and-catalog; 4/13,
Wave 1 complete, Wave 2 starting. ADR-0028 resumed with corrections and ACCEPTED (Status
flipped in place). Phase 13 is PROPOSED, in progress (ROADMAP §13E).

Active: Sprint 048 (Phase 13). Phase 10, Phase 2F, Phase 11 and Phase 12 are
closed (ROADMAP §13A, §13B, §13C, §13D). See SPRINT_048.md for the current
sprint's task breakdown; SPRINT_044.md §12, SPRINT_046.md §12 and
SPRINT_047.md §12 for unscheduled candidate follow-ons beyond Sprint 048 (ML
Market Analysis component gated by ADR-0024, cross-sectional predictive
studies, SHAP, content-addressed artifact store, Binance `trades` mode,
resume-after-failure imports, exposing the simulation assumptions / session
resolver through the application layer, additional CLI command groups, shell
completion, arithmetic in the model-expression IR).

Deferred relative to that track:
    Phase 4B — Orderflow Market Analysis
    Phase 6B — Multi-data Strategy Research
    Phase 8 Replay foundation
    PBO / CSCV / deflated Sharpe (ADR first)
    Residual docs / sample-data narrative

Recently completed (dashboard / demo / dry-run / authoring infra / Phase 10A–10C, 2F, 11, 12):
    Sprint 047 — Custom Strategy Authoring → main (#366; working PRs
        #363–#365) — closes Phase 12
    Sprint 046 — Universal Operator CLI → main (#361; working PRs #356–#360)
        — closes Phase 11
    Sprint 045 — Binance USD-M historical OHLCV ingestion → main (#355;
        working PRs #350–#354) — closes Phase 2F
    Sprint 044 — Predictive dashboard + IDEA-014 gate → main (#348; working
        PRs #343–#347) — closes Phase 10
    Sprint 043 — Neural predictive models → main (#342; working PRs #336–#341)
    Sprint 042 — Tree-based predictive models → main (#335; working PRs #326–#334)
    Sprint 041 — Predictive Research report v1 → main (#325; working PRs #320–#324)
    Sprint 040 — Predictive Research baselines → main (#319; working PRs #310–#318)
    Sprint 039 — Predictive Research dataset foundation → main (#309; working PRs #302–#308)
    Sprint 038 — Session Range Structure → main (#300; working PRs #297–#299)
    Sprint 037 — Component libraries + DSL → main (#296; working PRs #289–#295)
    Sprint 036 — Research infra audit → main (#288; working PRs #272–#287)
    Sprint 024 — Dry-run reliability polish → main (#270)
    Sprint 034 — Public Dashboard Demo Polish → main (#260)
    Follow-ups — overview nav, English + diagrams, LWC OHLCV, README link (#261–#264)
    Sprint 033 — Dashboard presentation polish → main (#257)
    Sprint 032 — Live Strategy Evaluation Parity → main (#246)
    Sprint 031 — Live Paper in Dashboard → main (#241)
    Sprint 028 — Dashboard Application MVP → main (#232)

Deferred (explicit):
    packages/ shared presentation contracts (until second DTO consumer)
    Deep market_analysis/ reorg (TD-003) until Phase 4B/4C (S036 audit did not require it)
    Full ops/ nesting of deploy/ (rejected for S030)
    Further public-dashboard cosmetics as a default track
```

See `docs/planning/sprints/SPRINT_044.md`, `S044_WAVE0_DECISIONS.md`, `SPRINT_043.md`, `S043_WAVE0_DECISIONS.md`, `SPRINT_042.md`, `S042_WAVE0_DECISIONS.md`, `SPRINT_041.md`, `SPRINT_040.md`, `SPRINT_039.md`, `S041_WAVE0_DECISIONS.md`, `S040_WAVE0_DECISIONS.md`, `S039_WAVE0_DECISIONS.md`, `SPRINT_038.md`, `S037_GATE.md`, and `ROADMAP.md` §11–§13A.

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
| 022 | AWS Runtime MVP for BTC Futures Dry Run (Phase 8A) | COMPLETED | integrated to main (#199) |
| 023 | OVH portfolio live dry-run dashboard (Phase 8A) | COMPLETED | integrated to main (#199 / #202); Streamlit is now primary UI |
| 024 | Dry-run reliability wiring (Phase 8A) | COMPLETED | main #270 (waves 1–4) |
| 025 | Streamlit dashboard polish + VPS publish | COMPLETED | main #249; deploy fixes #250/#251; edge TLS ops; user_data deferred |
| 026 | Research hot-path performance (Signal + Robustness) | COMPLETED | integrated to main (#215) |
| 027 | Market Data import / continuous build performance | COMPLETED | integrated to main (#220) |
| 028 | Dashboard Application MVP (Streamlit + DuckDB) | COMPLETED | integrated to main (#232) |
| 029 | Repository Layout Foundations | COMPLETED | integrated to main (#235) |
| 030 | Repository Navigability Hygiene | COMPLETED | integrated to main (#238) |
| 031 | Live Paper in Dashboard | COMPLETED | integrated to main (#241) |
| 032 | Live Strategy Evaluation Parity | COMPLETED | integrated to main (#246) |
| 033 | Dashboard presentation polish | COMPLETED | 6 / 6 tasks; Waves A–C (#253–#256); main #257 |
| 034 | Public Dashboard Demo Polish | COMPLETED | Waves 1–5 (#258–#259); main #260; VPS deploy; follow-ups #261–#264 |
| 035 | Next increment selection (post public demo) | COMPLETED | chose S024 then S036→S037→AI/ML |
| 036 | Research infra audit (DSL/component gate) | COMPLETED | 11 / 11 tasks; main #288 |
| 037 | Component libraries + DSL simplification | COMPLETED | 7 / 7 tasks; main #296 |
| 038 | Session Range Structure | COMPLETED | 6 / 6 tasks; main #300 |
| 039 | Predictive Research dataset foundation (Phase 10A) | COMPLETED | 20 / 20 tasks; main #309; working PRs #302–#308 |
| 040 | Baseline regression + classification (Phase 10A) | COMPLETED | 23 / 23 tasks; main #319; working PRs #310–#318 |
| 041 | Predictive Research report v1 (Phase 10A) | COMPLETED | 16 / 16 tasks; main #325; working PRs #320–#324 |
| 042 | Tree-based predictive models (Phase 10B) | COMPLETED | 22 / 22 tasks; main #335; working PRs #326–#334 |
| 043 | Neural predictive models (Phase 10C) | COMPLETED | 21 / 21 tasks; main #342; working PRs #336–#341 |
| 044 | Predictive dashboard + IDEA-014 gate (Phase 10C) | COMPLETED | 18 / 18 tasks; main #348; working PRs #343–#347 |
| 045 | Binance USD-M historical OHLCV ingestion (Phase 2F) | COMPLETED | 14 / 14 tasks; main #355; working PRs #350–#354 |
| 046 | Universal Operator CLI (Phase 11, `trading-cli`) | COMPLETED | 14 / 14 tasks; main #361; working PRs #356–#360 |
| 047 | Custom Strategy Authoring (Phase 12, `strategy_file` loader) | COMPLETED | 10 / 10 tasks; main #366; working PRs #363–#365 |
| 048 | Exit/Risk Model Expansion, Catalog Growth and New Strategies (Phase 13) | IN PROGRESS | 4 / 13 tasks; Wave 1 complete (#368-#370); branch sprint/exit-risk-and-catalog |

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
