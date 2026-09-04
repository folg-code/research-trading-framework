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

Detail for phases that are **entirely COMPLETE** (§4, §5, §7, §9, §11, §13A–§13E) has been
moved to `docs/planning/ROADMAP_COMPLETED_PHASES.md`, so this document stays a working
plan rather than an append-only history. Those sections remain here as short stubs under
their original numbers — a reference to "ROADMAP.md §13A" still resolves — and each links
to its full text, which is filed under the **same** section number in the archive.
Large **ACTIVE** phases (§6, §8, §13F, §13G, §13H) are extracted the same way, to
`docs/planning/roadmap/*.md` — but unlike the archive those files are LIVE and keep
changing, so phase detail is edited there, never by re-inflating the stub here. **§3's
Phase Index is the authoritative map of where every phase's detail lives.**

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
12. **Keep this file an index, not an archive.** Once a phase's roadmap text exceeds roughly 100–150 lines, or the next sprint will demonstrably keep revising it, extract it (completed phases to `ROADMAP_COMPLETED_PHASES.md`, active phases to `docs/planning/roadmap/`) and leave a numbered stub plus a §3 Phase Index row.

---

## 3. Capability Tracks and Phase Overview

The project no longer advances as a single linear pipeline:

```text
Market Data → Market Analysis → Signal Research → Strategy Research → Execution
```

Research can progress on **currently available** data types. Market Data expansion is justified by concrete research or execution need, not by collecting everything upfront.

### Phase Index — status and where each phase's detail lives

This table is the **single place** to find where any phase's detail actually lives. "this
file" means the section is still inline below; the other two locations are the frozen
completed-phase archive and the live per-phase files under `docs/planning/roadmap/`.

| Phase # | Name | Status | Location |
|---|---|---|---|
| 0 | Project Governance | COMPLETE | `ROADMAP_COMPLETED_PHASES.md` §4 |
| 1 | Repository Foundation | COMPLETE | `ROADMAP_COMPLETED_PHASES.md` §5 |
| 2A | OHLCV Market Data MVP | COMPLETE | `roadmap/PHASE_02_MARKET_DATA.md` §6 |
| 2B | Historical Archive Import Foundation | PLANNED | `roadmap/PHASE_02_MARKET_DATA.md` §6 |
| 2C.1 | MarketTrade datasets | COMPLETE | `roadmap/PHASE_02_MARKET_DATA.md` §6 |
| 2C.2 | MarketQuote datasets | PLANNED | `roadmap/PHASE_02_MARKET_DATA.md` §6 |
| 2C.3 | Order-book data (MBO/MBP) | PLANNED | `roadmap/PHASE_02_MARKET_DATA.md` §6 |
| 2C.4 | Continuous Futures Materialization | COMPLETE (Sprint 015) | `roadmap/PHASE_02_MARKET_DATA.md` §6 |
| 2D | Options Snapshot Data | PLANNED | `roadmap/PHASE_02_MARKET_DATA.md` §6 |
| 2E | Live Market Data | GATED (§15.2) | `roadmap/PHASE_02_MARKET_DATA.md` §6 |
| 2F | Exchange REST Historical Import | COMPLETE | `ROADMAP_COMPLETED_PHASES.md` §13B |
| 3 | Market Analysis Engine MVP | COMPLETE | `ROADMAP_COMPLETED_PHASES.md` §7 |
| 4A | Bar-Based and Multitimeframe Foundation | COMPLETE | `roadmap/PHASE_04_MARKET_ANALYSIS.md` §8 |
| 4B | Orderflow Market Analysis | PLANNED | `roadmap/PHASE_04_MARKET_ANALYSIS.md` §8 |
| 4C | Options-Derived Market Analysis | PLANNED | `roadmap/PHASE_04_MARKET_ANALYSIS.md` §8 |
| 5 | Signal Research MVP | COMPLETE | `ROADMAP_COMPLETED_PHASES.md` §9 |
| 6A | OHLCV Strategy Research MVP | COMPLETE | this file, §10 |
| 6B | Multi-Data Strategy Research | PLANNED | this file, §10 |
| 7 | Robustness Research | COMPLETE | `ROADMAP_COMPLETED_PHASES.md` §11 |
| 8 | Replay and Paper Execution | PLANNED | this file, §12 |
| 9 | Live and Multi-Account | PLANNED | this file, §13 |
| 10A | Predictive Research Foundation | COMPLETE | `ROADMAP_COMPLETED_PHASES.md` §13A |
| 10B | Tree-Based Predictive Models | COMPLETE | `ROADMAP_COMPLETED_PHASES.md` §13A |
| 10C | Neural Predictive Models | COMPLETE | `ROADMAP_COMPLETED_PHASES.md` §13A |
| 11 | Universal Operator CLI | COMPLETE | `ROADMAP_COMPLETED_PHASES.md` §13C |
| 12 | Custom Strategy Authoring | COMPLETE | `ROADMAP_COMPLETED_PHASES.md` §13D |
| 13 | Exit/Risk Model Expansion and Catalog Growth | COMPLETE | `ROADMAP_COMPLETED_PHASES.md` §13E |
| 14A | Promotable Predictive Artifact | COMPLETE (Sprint 049) | `roadmap/PHASE_14_PREDICTIVE_PROMOTION.md` §13F |
| 14B | Model-Backed Market Analysis State | NOT PLANNED | `roadmap/PHASE_14_PREDICTIVE_PROMOTION.md` §13F |
| 15A | Momentum and Regime Component Catalog | COMPLETE (Sprint 051) | `roadmap/PHASE_15_PREDICTIVE_CATALOG.md` §13G |
| 15B | Real-Data BTC Predictive Study | PLANNED, not opened | `roadmap/PHASE_15_PREDICTIVE_CATALOG.md` §13G |
| 16A | Analyst Verdict Artifact | APPROVED, no sprint (gated on 15B) | `roadmap/PHASE_16_QUANT_WORKBENCH.md` §13H |
| 16B | SampleSpec Foundation | APPROVED, no sprint (may run parallel to 15B) | `roadmap/PHASE_16_QUANT_WORKBENCH.md` §13H |
| 16C | Signal Quality Scoring | APPROVED, no sprint | `roadmap/PHASE_16_QUANT_WORKBENCH.md` §13H |
| 16D | Quant Lab Dashboard | DIRECTIONAL | `roadmap/PHASE_16_QUANT_WORKBENCH.md` §13H |
| 16E | Strategy Families | DIRECTIONAL | `roadmap/PHASE_16_QUANT_WORKBENCH.md` §13H |
| 16F | Trade Outcome and No-Trade Models | DIRECTIONAL | `roadmap/PHASE_16_QUANT_WORKBENCH.md` §13H |
| 16G | Promotion Candidate Gate | DIRECTIONAL | `roadmap/PHASE_16_QUANT_WORKBENCH.md` §13H |

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
  Phase 16 — Quant Research Workbench (16A–16G)   APPROVED  (§13H; no sprint opened)

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

**Phase 16 (§13H) is APPROVED** (maintainer, 2026-09-04): a seven-increment
capability track turning the existing runners into one quant research
workbench over a single neutral Market Analysis component catalog. Approval
of the phase is **not** approval to open a sprint — 16A–16C are the
committed direction, 16D–16G stay directional (§2.9). Its increment 16A
does **not** re-plan Phase 15B — Sprint 052 remains the real-data study and
is Phase 16's entry condition, not one of its increments (§13H.0); the one
carve-out is 16B, which may start in parallel with Sprint 052. Phase 16 is
also the planned repayment route for six standing registry entries —
`PRB-012`, `PRB-013`, `PRB-020`, `TD-021`/`TD-022`/`TD-029` — see §13H.13.

---

# 4. Phase 0 — Project Governance

**Status:** COMPLETE. Delivered by Sprint 001 (planning-system bootstrap).

Purpose: create the minimum project-management system required for iterative development —
roadmap, current status, problem registry, idea inbox, technical-debt register, sprint
plans and retrospectives, issue/PR conventions, ADR process.

Binding outcomes still in force:

- architectural decisions are separated from tasks and ideas (`docs/adr/`),
- GitHub Issues and Projects are the operational source of truth for task state; planning
  Markdown holds context, decisions and summaries, not a second task board,
- Definition of Ready and Definition of Done are defined (`PROJECT_MANAGEMENT.md`).

Full detail: `docs/planning/ROADMAP_COMPLETED_PHASES.md` §4.

---

# 5. Phase 1 — Repository Foundation

**Status:** COMPLETE. Delivered by Sprint 001 (`SPRINT_001.md`).

Purpose: create the implementation foundation shared by every domain — package structure,
`src/` vs `user_data/` separation, unit/integration/e2e test structure, Ruff, mypy, pytest,
CI, core identifiers and errors, Timeframe/timestamp primitives, Clock, configuration
loading, logging.

Binding outcomes still in force:

- `src/` does not import concrete `user_data/` modules,
- naive timestamps are rejected in core time models,
- framework tests do not require external systems,
- CI runs linting, formatting checks, typing and tests on every change.

Full detail: `docs/planning/ROADMAP_COMPLETED_PHASES.md` §5.

---

# 6. Market Data Capability — Phase 2 Family

**Status:** ACTIVE — 2A COMPLETE (Sprint 002); 2C.1 and 2C.4 COMPLETE (Sprint 015).
**2B, 2C.2, 2C.3 and 2D remain PLANNED; 2E remains GATED** on §15.2. Phase 2F is a
separate, COMPLETE section (§13B).

Purpose: the Market Data capability track — OHLCV import and publication (2A), vendor
archive import (2B), trades / quotes / order-book and continuous futures (2C), options
snapshots (2D), live adapters (2E).

Key open items: 2B (Databento DBN archive import foundation), 2C.2 quotes, 2C.3 order-book
(MBO/MBP, only when justified), 2D options snapshots, 2E live adapters — none scheduled.
Roadmap sections historically titled "Phase 2 — Market Data MVP" mean **Phase 2A**, and 2A's
completion does **not** close this track.

**Full detail (maintained here, not in ROADMAP.md):**
`docs/planning/roadmap/PHASE_02_MARKET_DATA.md` §6.

This phase is ACTIVE: edit the linked file, not this stub. Market Data policy (facts not
indicators, vendor independence) stays in §14; the live-data entry gate stays in §15.2.

---

# 7. Phase 3 — Market Analysis Engine MVP

**Status:** COMPLETE — Sprint 003 (2026-07-12), branch `sprint/market-analysis-mvp`.
**ADRs:** `docs/adr/ADR-0005-market-analysis-domain-and-taxonomy.md`, ADR-MA-001–011.

Purpose: calculate reusable analytical components through explicit dependency contracts —
component contract, Component Registry, `ComponentRequest`, dependency DAG, cycle
detection, lazy execution, shared-node deduplication, fingerprinting, cache identity.

Binding outcomes still in force:

- a component declares all dependencies before execution; hidden component calls inside
  `compute()` are rejected by convention and by tests,
- equivalent deterministic nodes are calculated once,
- cache identity includes dataset **and** implementation identity,
- the engine remains independent from Market Model and Signal Model semantics.

Two completion criteria are recorded as **not met** and remain tracked, not closed:
loading working components from controlled user space (deferred — no `user_data/` loader in
the MVP), and storing an implementation fingerprint for research use of a working component
(partial — parameter identity only; PRB-002 remainder).

Full detail: `docs/planning/ROADMAP_COMPLETED_PHASES.md` §7.

---

# 8. Market Analysis Capability — Phase 4 Family

**Status:** ACTIVE — 4A COMPLETE (Sprints 004–006); **4B and 4C remain PLANNED**, neither
scheduled.

Purpose: timeframe-aware Market Analysis, delivered as a family of increments — bar-based
and multitimeframe foundation (4A), orderflow analysis (4B), options-derived analysis (4C).

Key open items: 4B is gated on Phase 2C (`MarketTrade` minimum); 4C is gated on Phase 2D
(options snapshots). Both are deferred by default (§3). 4A's binding outcome still in
force: Market and Signal Models stay declarative and cannot access arbitrary DataFrames.

**Full detail (maintained here, not in ROADMAP.md):**
`docs/planning/roadmap/PHASE_04_MARKET_ANALYSIS.md` §8.

This phase is ACTIVE: edit the linked file, not this stub.

---

# 9. Phase 5 — Signal Research MVP

**Status:** COMPLETE — Sprints 008–010.

Purpose: evaluate Market Models and Signal Models independently or together, without
requiring a complete Strategy Model. Supported scopes: `MARKET_MODEL_ONLY`,
`SIGNAL_MODEL_ONLY`, `MARKET_AND_SIGNAL`.

Binding outcomes still in force:

- Signal Research does not require Exit or Risk Models,
- independent experiment alternatives are not confused with logical `OR`,
- new analytics do not rerun unchanged computation; shared analytical dependencies are reused,
- stored datasets remain queryable without loading implementation classes,
- run identity includes datasets, models, fingerprints and time semantics.

Out of scope for this phase and still so: complete strategy PnL, position sizing, broker
fill simulation, deployment decisions, automatic strategy promotion.

Full detail: `docs/planning/ROADMAP_COMPLETED_PHASES.md` §9.

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

**Status:** COMPLETE — Sprint 016. **Wave 0:** `S016_WAVE0_DECISIONS.md`. **ADR:** ADR-0019.

Purpose: assess whether a candidate Strategy Model is **stable enough** to justify paper
execution or deeper validation — not merely which parameter set ranked highest in-sample.

Delivered in the MVP: declarative experiment specification with a config generator, batch
execution and a resumable experiment registry; parameter sweep with ranking, neighbor
stability and isolated-optimum detection; rolling and expanding walk-forward with train-only
selection and a stitched OOS curve; stress testing (costs, entry/exit delay, top-trade and
top-day removal); statistical diagnostics (temporal stability, PnL concentration, bootstrap,
block bootstrap, IS/OOS degradation); trade-level Monte Carlo; and one offline-HTML
Robustness Report carrying an explicit PASS / CONDITIONAL / FAIL verdict.

Binding principles still in force:

- robustness methods record their assumptions,
- top ranking is **not** treated as validation,
- validation outputs are stored separately from base Strategy Research runs,
- no train/OOS leakage in walk-forward,
- Monte Carlo operates on **persisted simulated trades** — not synthetic price paths and
  not order-book simulation.

Still deferred (unchanged): full order-book simulation and market impact, portfolio-level
and cross-asset robustness, distributed experiment execution, Bayesian/genetic optimization,
and the PBO / CSCV / Deflated Sharpe / White's Reality Check / Hansen's SPA family. Also out
of scope: automatic live deployment and a universal hard-coded candidate score. Note that the
delay stress still rejects bracket exits (TD-027, see §13E).

Full detail: `docs/planning/ROADMAP_COMPLETED_PHASES.md` §11.

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

**Status:** COMPLETE. 10A — Sprints 039–041; 10B — Sprint 042 (#335, 22/22); 10C —
Sprints 043 (#342, 21/21) and 044 (18/18). Numbered `13A` to avoid renumbering sections
cited elsewhere.
**ADRs:** ADR-0023 (predictive research boundary), ADR-0024 (promotion conditions).
**Gate:** IDEA-014.

Purpose: learn a relationship between Market Analysis outputs and forward market behaviour,
and measure honestly whether that relationship survives out of sample. Phase 10 is a
**research methodology**, not a trading capability.

Binding rules still in force:

```text
Domain code must not import scikit-learn, XGBoost, LightGBM, CatBoost or torch
ML libraries are optional dependency extras — never runtime dependencies of the framework
Scalers, encoders and feature selection are fitted on the training fold only
Label horizon overlap between train and test folds is purged, not tolerated
Predictive runs are persisted separately from Signal and Strategy Research runs
A trained model is never promoted to a tradable signal inside Phase 10
```

Promotion of a trained model is Phase 14 (§13F), gated by IDEA-014 and ADR-0024 — not part
of this phase.

Full detail: `docs/planning/ROADMAP_COMPLETED_PHASES.md` §13A.

---

# 13B. Phase 2F — Exchange REST Historical Import (COMPLETE)

**Status:** COMPLETE — Sprint 045 (14/14 tasks, `sprint/binance-historical-ohlcv`).
**ADR:** ADR-0025 (ACCEPTED). **First provider:** Binance USD-M futures.

Purpose: obtain historical bars from an exchange **REST API over a date range**, not only
from a local vendor archive (Phase 2B) or a CSV file (Phase 2A). Downstream layers were
already provider-agnostic; this closed the gap at the acquisition boundary with no change to
any research code.

Binding rules still in force:

```text
Downstream research must not branch on provider == "binance"
No signing code, no authenticated endpoint, no account surface — structurally, not by promise
Credentials live in TRADING_FRAMEWORK_BINANCE_API_KEY only; never in a file, never logged
A partially fetched range never produces a PUBLISHED version
Standard CI stays network-free (Tier 1 fake transport; Tier 2 opt-in marker)
```

Still out of scope: Binance spot/options and any authenticated endpoint, `trades` mode
(reserved, not built), resume-after-failure and incremental top-ups, and a second exchange.

Full detail: `docs/planning/ROADMAP_COMPLETED_PHASES.md` §13B.

---

# 13C. Phase 11 — Universal Operator CLI (COMPLETE)

**Status:** COMPLETE — Sprint 046 (14/14 tasks, `sprint/operator-cli`).
**ADR:** ADR-0026 (ACCEPTED).

Purpose: give the operator one entry point and one input contract for the working loop.
An **interface** phase — no research, data or execution capability, and it deliberately does
not replace `scripts/`. Command groups (v1): `data fetch`, `research run`, `dry-run start`,
`report render`, all driven by one YAML config.

Binding rules still in force:

```text
apps/cli may import trading_framework.application.* — and nothing deeper
apps/cli contains no research, simulation or execution logic
No workflow is reimplemented; no command parses another command's stdout
Existing scripts, their flags and their tests remain valid
No credentials in any config file
```

Still out of scope: replacing `scripts/`; ops/demo/robustness/signal-research groups; any
change to execution or order routing; interactive/TUI modes and shell completion; a job
scheduler, queue or run history — the CLI is stateless.

SPRINT_046.md §4 Finding 2 (hardcoded strategy model, `SimulationAssumptions`, session
resolver) is a Phase 11 limitation: its strategy-model third was closed by Phase 12 (§13D).

Full detail: `docs/planning/ROADMAP_COMPLETED_PHASES.md` §13C.

---

# 13D. Phase 12 — Custom Strategy Authoring (COMPLETE)

**Status:** COMPLETE — Sprint 047 (10/10 tasks, `sprint/strategy-authoring`).
**ADRs:** ADR-0027 (strategy loading) — ACCEPTED. ADR-0028 — PROPOSED and **declined for
this sprint** (2026-09-01); its Exit/Risk expansion was later delivered by Phase 13 (§13E).
**PRD:** `docs/product/PRD-strategy-authoring.md` (confirmed).

Purpose: make the framework's own strategy vocabulary usable **by the operator, from the
CLI** — one config key, `research.strategy.strategy_file`, naming a Python file with a
zero-argument `build_strategy()` entry point, plus the catalog components `candle.wick` and
`structure.level_distance`.

Binding rules still in force:

```text
The loaded strategy file is the operator's own trusted code — no sandbox, no
    import restriction, and the boundary test does not and cannot scan it (TD-025)
apps/cli's own ADR-0026 Amendment 1 allow-list is NOT widened by this phase
strategy_file is optional; its absence keeps the canonical example (additive)
No declarative YAML strategy schema is introduced — Python loading only
Existing FixedBars strategies produce byte-identical runs (no engine change)
```

Note: the final Sprint 047 binding rule ("kernels/fixed_bars.py, ExitModel/RiskModel
protocols, and BarSequentialSimulator are untouched this sprint") was scoped to that sprint;
Phase 13 (§13E) deliberately narrowed it with ADR-0028 ACCEPTED.

Still out of scope: a declarative strategy format; sandboxing or static analysis of loaded
files; a strategy registry or catalog UI; exposing `SimulationAssumptions` or the session
resolver through config; any change to live trading, order routing or the dry-run runtime.

Accepted risk, still current: **arbitrary code execution by config** — the same trust level
as running any script in this repository; and `--dry-run` promises only that *the CLI*
touches nothing, since a loaded module executes at import (ADR-0027 §4).

Full detail: `docs/planning/ROADMAP_COMPLETED_PHASES.md` §13D.

---

# 13E. Phase 13 — Exit/Risk Model Expansion and Catalog Growth (COMPLETE)

**Status:** COMPLETE — Sprint 048 (13/13 tasks, `sprint/exit-risk-and-catalog`), approved by
the maintainer 2026-09-01. Numbered `13E` to continue the §13A–§13D pattern.
**ADR:** ADR-0028 (bracket exits + equity-relative sizing) — **ACCEPTED** (declined for
Sprint 047, resumed with corrections for Sprint 048).
**PRD:** `docs/product/PRD-exit-risk-and-catalog-expansion.md` (confirmed).

Purpose: turn Exit and Risk models from placeholders into strategy-construction primitives.
Delivered `BracketExitModel` (bps stop-loss / take-profit plus a mandatory `max_bars`
timeout), `EquityPercentRiskModel` (**static**, authoring-time sizing), `kernels/bracket.py`,
five bounded engine changes across three files, a golden-run regression, the catalog
components `trend.ema_distance` and `volatility.range_expansion`, and three worked examples.

Binding rules still in force:

```text
kernels/fixed_bars.py is NOT edited — not one character
research/simulation/compile.py and input.py are NOT edited (high/low already compiled)
ExitModel and RiskModel Protocol definitions are NOT modified
The fixed-bars path's fill, accounting AND RUN-IDENTITY semantics are unchanged
A sixth engine change is a STOP-and-ask with a fresh ADR amendment, never a
    quiet widening
Same-bar stop/target ambiguity resolves to the STOP. Always. No configuration flag.
Equity-percent sizing is STATIC and must never be described as compounding
```

Standing deferrals recorded by this phase, cited elsewhere:

- **TD-026** — dynamic, equity-curve-following position sizing,
- **TD-027** — the Robustness delay stress still **rejects** bracket exits, loudly and for a
  stated reason; bracket-aware stress dimensions are not available (see §11, and
  SPRINT_049.md §4 Finding 8 for the Sprint 050 planning consequence),
- **TD-028** — no reference (non-njit) implementation of the bracket kernel.

Also out of scope: any change to the `ExitModel` / `RiskModel` Protocol definitions, a
declarative strategy format, arithmetic in the model-expression IR, cross-validating
`stop_distance` against `stop_loss_bps` (the operator owns that in v1), and any third catalog
component or fourth example strategy.

Full detail: `docs/planning/ROADMAP_COMPLETED_PHASES.md` §13E.

---

# 13F. Phase 14 — Predictive Model Promotion (APPROVED)

**Status:** **APPROVED** (maintainer, 2026-09-02). **14A is COMPLETE** — Sprint 049 (15/15,
`sprint/promotable-predictive-artifact`), ADR-0024 conditions 1 and 5 closed and condition
4's offline half (Path A) passing at its locked bars. **14B / Sprint 050 is NOT planned.**
Phase 14 as a whole is NOT complete — 14A ships no Market Analysis component, no State, no
executor change and no dry-run session.

Purpose: make a trained predictive model produce a Market Analysis State consumed by a
Signal Model exactly like a rule-based component, all the way into the BTC futures dry-run
runtime, under ADR-0024's five conditions with none waived. v1 is linear/logistic only, on a
framework-owned NumPy parameter format with zero ML dependency in the runtime image.

Key open items for 14B: **ADR-0030** (inference-time `available_at` enforcement — the
S049-T001 finding proved the executor mechanism ADR-0024 condition 2 presupposes does not
exist today), a real non-synthetic BTC candidate model (actively pursued by Phase 15, §13G),
and a named downstream robustness plan (S044_GATE §1.5). The binding rules — ADR-0024's five
inherited conditions, the exact-equality parity bar, and condition 5's no-registry negative
constraint — are **not restated here**; see the linked file.

**Full detail (maintained here, not in ROADMAP.md):**
`docs/planning/roadmap/PHASE_14_PREDICTIVE_PROMOTION.md` §13F.

This phase is ACTIVE: edit the linked file, not this stub.

---

# 13G. Phase 15 — Predictive Research Catalog Expansion and Real-Data Study (APPROVED)

**Status:** **APPROVED** (maintainer, 2026-09-02). **15A is COMPLETE** — Sprint 051 (11/11,
`sprint/momentum-and-regime-catalog`), including the BTC import (`BTCUSDT.P`, 1m,
`2024-01-01 -> 2026-06-29`, 911 days, 1,311,840 rows, zero gaps). **15B / Sprint 052 is
PLANNED but NOT approved or opened.** Phase 15 as a whole is NOT complete — no real-data
predictive study has been run.

Purpose: close §13F's Q5 gap — Phase 10's methodology was validated on synthetic fixtures
only — by running one real-data BTC predictive study through the unmodified Phase 10
pipeline, or reporting with the same rigour that it cannot be closed on an OHLCV-only
catalog.

Key open items: opening Sprint 052 is a separate maintainer approval step. Two binding
rules a reader needs without following the link: **non-BTC data is a HARD STOP, not a
fallback**, and **a negative result is a legitimate, reportable outcome** — never repaired
by adding features until something sticks. The remaining binding rules are in the linked
file. Phase 15B is Phase 16's entry condition (§13H) and is neither re-scoped nor absorbed
by it.

**Full detail (maintained here, not in ROADMAP.md):**
`docs/planning/roadmap/PHASE_15_PREDICTIVE_CATALOG.md` §13G.

This phase is ACTIVE: edit the linked file, not this stub.

---

# 13H. Phase 16 — Quant Research Workbench (APPROVED)

**Status:** **APPROVED** (maintainer, 2026-09-04). **No sprint is opened, planned or
numbered for any increment.** 16A–16C are the committed direction; **16D–16G are
directional** and will be re-specified from evidence before any of them is planned (§2.9).

Purpose: turn the existing independently-reached runners (Signal, Strategy, Robustness and
Predictive Research plus the dashboard) into one quant research workbench over a single
neutral Market Analysis component catalog — one catalog, many consumers, no "ML-only
feature" concept.

```text
16A — Analyst Verdict Artifact     16B — SampleSpec Foundation
16C — Signal Quality Scoring       16D — Quant Lab Dashboard
16E — Strategy Families            16F — Trade Outcome and No-Trade Models
16G — Promotion Candidate Gate
```

Key open items and gates: **Phase 15B / Sprint 052 must have RUN** before 16A or anything
after it opens — the single carve-out is 16B, which may start in parallel (Q3). All eight
maintainer questions (Q1–Q8) are RESOLVED; Q5 (sequencing vs. Phase 14B), Q7 (parity
tolerances) and Q8 (no PRB-012 retrofit) were resolved as deliberate deferrals or refusals.
Five ADRs are anticipated, none written. Planned closure route for `PRB-012`, `PRB-013`,
`PRB-020`, `TD-021`, `TD-022`, `TD-029` — all still OPEN/ACCEPTED until their increment ships.

The phase's binding-rules list is long and is deliberately **not** reproduced here — see the
binding rules in the linked file (§13H.8). The one that governs this stub: **approving this
phase is not opening a sprint**, and no increment constitutes trading approval of anything.

**Full detail (maintained here, not in ROADMAP.md):**
`docs/planning/roadmap/PHASE_16_QUANT_WORKBENCH.md` §13H.

This phase is ACTIVE: edit the linked file, not this stub. Its substance was negotiated with
the maintainer (Q1–Q8, 2026-09-04); wording changes go through that process, not through a
roadmap edit.

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
