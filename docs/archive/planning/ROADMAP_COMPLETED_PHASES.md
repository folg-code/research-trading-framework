# Trading Research Framework

# ROADMAP_COMPLETED_PHASES.md

```text
Status: ACCEPTED
```

## Purpose of this file

Archived detail for **fully COMPLETE** roadmap phases. `ROADMAP.md` **§3
Capability Tracks and Phase Overview** remains the authoritative phase-status
index; this file exists so `ROADMAP.md` stays a working document instead of an
append-only history.

Only phases with **no open increment** live here. Any phase family that still
has planned or unstarted work (Phase 2 family, Phase 4 family, Phase 6 family,
Phase 8, Phase 9, Phase 14, Phase 15, Phase 16) stays in `ROADMAP.md` in full
detail, as do all cross-cutting sections (`ROADMAP.md` §14–§18).

## How section numbers work here

**Each section keeps the number it had in `ROADMAP.md`.** A cross-reference
written as "ROADMAP.md §13A" resolves both to the stub in `ROADMAP.md` and to
the full section `§13A` in this file — no renumbering, no searching. The
sections below are therefore non-contiguous by design (4, 5, 7, 9, 11, 13A–13E).

Content was moved verbatim, not rewritten (`ROADMAP.md` §2.11: *do not
retroactively rewrite completed sprint scope*). Sprint-era wording, dated
progress notes and unchecked completion boxes are preserved exactly as they
stood at the time of the move (2026-09-04).

## Index

```text
§4    Phase 0  — Project Governance                                COMPLETE
§5    Phase 1  — Repository Foundation                             COMPLETE
§7    Phase 3  — Market Analysis Engine MVP                        COMPLETE  (Sprint 003)
§9    Phase 5  — Signal Research MVP                               COMPLETE  (Sprints 008–010)
§11   Phase 7  — Robustness Research                               COMPLETE  (Sprint 016)
§13A  Phase 10 — Predictive (ML) Research                          COMPLETE  (Sprints 039–044)
§13B  Phase 2F — Exchange REST Historical Import                   COMPLETE  (Sprint 045)
§13C  Phase 11 — Universal Operator CLI                            COMPLETE  (Sprint 046)
§13D  Phase 12 — Custom Strategy Authoring                         COMPLETE  (Sprint 047)
§13E  Phase 13 — Exit/Risk Model Expansion and Catalog Growth      COMPLETE  (Sprint 048)
```

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
