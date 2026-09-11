# Sprint 061 T001 — Public Content Evidence Matrix

```text
Status: REVIEWED DRAFT
Prepared: 2026-09-10
Scope: evidence and wording constraints for Sprint 061 public dashboard content
```

## 1. Purpose and method

This matrix is the factual gate for Sprint 061 public copy. It maps each
material project or infrastructure claim to current implementation, an
accepted ADR, a workflow reference, an operations runbook, or persisted study
evidence. A source supports a public claim only when its current-state wording
is corroborated by code or an as-built reference. Vision and planning sources
may support only explicitly labelled future direction.

The review distinguishes four classes:

- **AS BUILT** — implemented and supported by current code, tests, persisted
  evidence, or an operational runbook;
- **IN DEVELOPMENT** — partially implemented, with the missing boundary named;
- **FUTURE IDEAS** — proposed direction, never described in the present tense;
- **STALE / CONFLICTING** — wording that must be corrected before publication.

The maintainer-provided Polish note
`AI Research Infrastructure — kierunek rozwoju.md` is an editorial input, not
an instruction or approved architecture. Public copy derived from it is
English and labelled `FUTURE IDEAS`.

## 2. Product and shared architecture

| Public claim | Evidence | Classification | Required wording / guardrail |
|---|---|---|---|
| The project is a modular Python framework for systematic trading research and simulated strategy operation. | `docs/vision/PRODUCT_DIRECTION.md` §§1–3; `docs/reference/system/SYSTEM_OVERVIEW.md` §§1–2; package layout under `src/trading_framework/` | AS BUILT | Say "simulated strategy operation" or "dry-run execution", not live broker trading. |
| Stable domain contracts are shared without making all capabilities stages of one mandatory pipeline. | `PRODUCT_DIRECTION.md` §§1,3; `docs/planning/DASHBOARD_DEVELOPMENT_DIRECTION.md` §3; architecture-boundary tests under `tests/unit/` | AS BUILT | Use a hub-and-spoke model; do not draw workflow-to-workflow arrows on the overview. |
| Market Analysis is a shared capability rather than a seventh workflow. | `DASHBOARD_DEVELOPMENT_DIRECTION.md` §3; `docs/reference/modules/MARKET_ANALYSIS_MODULE.md`; `src/trading_framework/market_analysis/` | AS BUILT | Name it as shared computation and contracts, not a public workflow. |
| The six public workflows are Market Data, Signal Research, Strategy Research, Robustness Research, Predictive Research, and Strategy Execution. | `DASHBOARD_DEVELOPMENT_DIRECTION.md` §3; `apps/dashboard/src/dashboard_app/views/overview.py`; `apps/dashboard/tests/test_overview_acceptance.py` | AS BUILT | Strategy Execution must carry its dry-run limitation. |
| Framework code and maintainer-owned data, configurations, definitions, and results are separated. | ADR-0002; ADR-0022; `docs/reference/system/SYSTEM_OVERVIEW.md` §2; `tests/unit/test_architecture_boundaries.py` | AS BUILT | Explain `src/` / `user_data/` as an ownership and dependency boundary, not as security isolation. |
| Deployable apps remain consumers rather than owners of research or execution logic. | ADR-0022; `tests/unit/test_apps_boundaries.py`; `apps/dashboard/src/dashboard_app/` | AS BUILT | The dashboard reads persisted facts and a read-only status endpoint; it does not run research. |

## 3. Workflow claims

| Workflow | Public claim | Evidence | Classification | Required wording / guardrail |
|---|---|---|---|---|
| Market Data | Provider-specific inputs are normalized into provider-independent market facts and published dataset versions. | `docs/reference/workflows/MARKET_DATA.md`; `src/trading_framework/application/market_data/`; `src/trading_framework/market/datasets/` | AS BUILT | Name the implemented CSV, Databento trade-archive, and Binance USD-M OHLCV paths; do not imply every provider or data type is supported. |
| Market Data | Dataset metadata records identity, version, checksum, lifecycle state, validation facts, and optional lineage. | `market/datasets/{identity,versioning,lifecycle,metadata}.py`; `application/market_data/{finalize_dataset,publish_dataset}.py`; relevant unit tests | AS BUILT | "Versioned and traceable" is supported; "fully reproducible from the repository alone" is not. |
| Market Data | Raw acquisition and expensive normalization are separated from repeat research consumption. | ADR-0007, ADR-0014, ADR-0015; market-data application workflows | AS BUILT | Avoid claiming every raw source is retained by every importer; describe the lifecycle pattern. |
| Market Data | Quotes, full order-book history, options snapshots, and generic paid live feeds are available. | `ROADMAP.md` §§6,14–15 | FUTURE IDEAS | These remain planned or gated and must not appear as current capability. |
| Signal Research | Market Models, Signal Models, or both can be evaluated without a complete Strategy Model. | `docs/reference/workflows/SIGNAL_RESEARCH.md`; `research/signal_research/definition.py`; `application/signal_research/run_signal_research.py` | AS BUILT | Name the three explicit scopes; do not imply a Strategy Research dependency. |
| Signal Research | Computation produces persistent, queryable datasets and analytics can operate without rerunning unchanged computation. | ADR-0011, ADR-0013; `research/datasets/signal_research.py`; `research/analytics/`; repository tests | AS BUILT | Reuse is identity-dependent, not an unconditional cache guarantee. |
| Signal Research | Bounded family expansion exists for Signal Research. | `research/signal_research/family_planning.py`; `research/datasets/signal_research_family.py`; `SIGNAL_RESEARCH.md` reuse note | AS BUILT | Do not generalize the family mechanism to Strategy Research; PRB-020 records that gap. |
| Strategy Research | Complete Market × Signal × Exit × Risk compositions run under explicit historical simulation assumptions. | `docs/reference/workflows/STRATEGY_RESEARCH.md`; ADR-0016; `research/simulation/`; `application/strategy_research/` | AS BUILT | Results are simulations, not live performance or trading approval. |
| Strategy Research | Trade-level results, equity, summary facts, identities, and assumption fingerprints are persisted for read-only analysis. | `research/datasets/strategy_research.py`; `research/analytics/strategy_*`; `tests/unit/research/simulation/test_golden_run.py` | AS BUILT | Avoid promising every possible order/fill field for every historical run. |
| Strategy Research | Strategy-family generation and comparison match the Signal Research family capability. | `STRATEGY_RESEARCH.md` reuse note; PRB-020 | IN DEVELOPMENT | State that no equivalent Strategy Research family mechanism exists today. |
| Robustness Research | Parameter sweeps, walk-forward analysis, stress tests, statistical diagnostics, and trade-level Monte Carlo are separate persisted analyses over Strategy Research evidence. | ADR-0019; `research/robustness/`; `application/robustness_research/`; `research/datasets/robustness.py` | AS BUILT | A robustness verdict is method-specific and is not automatic deployment approval. |
| Robustness Research | Robustness covers portfolio, cross-asset, market-impact, and full order-book simulation. | `ROADMAP.md` §11; ADR-0019 | FUTURE IDEAS | These remain deferred. Bracket-aware delay stress also remains limited (TD-027). |
| Predictive Research | Declared Market Analysis features and forward outcomes are evaluated with purged walk-forward folds and fold-local preprocessing. | ADR-0023; `docs/reference/workflows/RESEARCH_METHODOLOGIES.md` §8; `research/predictive/`; predictive tests | AS BUILT | Describe this as research methodology, not a signal generator or strategy. |
| Predictive Research | Linear, tree, and neural estimator families use optional extras while persisted predictions and metrics remain the durable evidence. | `pyproject.toml`; `application/predictive_research/run_predictive_research.py`; `research/datasets/predictive*.py`; Phase 10 references | AS BUILT | Do not imply all families are promotable; promotion v1 is narrower. |
| Predictive Research | A versioned verdict can be generated from persisted artifacts without loading model binaries. | ADR-0032; `research/predictive/verdict.py`; `application/predictive_research/evaluate_run_verdict.py`; `docs/reference/PREDICTIVE_VERDICT.md` | AS BUILT | Display the persisted verdict verbatim; the dashboard must not derive one. |
| Strategy Execution | The current BTC path consumes live public Binance market data and performs simulated execution without real orders. | ADR-0021; `docs/reference/runbooks/LOCAL_BTC_FUTURES_DRY_RUN.md`; `application/execution/local_btc_futures.py`; `execution/broker_sim/paper_broker.py` | AS BUILT | Always show `LIVE MARKET DATA / SIMULATED EXECUTION / NO REAL ORDERS`. |
| Strategy Execution | Runtime state, orders, fills, positions, health, and bounded status are persisted or exposed read-only for monitoring. | `execution/models/`; `execution/repositories/`; `apps/dashboard/src/dashboard_app/datasources/live_paper_http.py`; live-paper tests | AS BUILT | Status may be unavailable or stale; an old snapshot must not be presented as current. |
| Strategy Execution | Replay, real broker routing, reconciliation, and multi-account live execution are working capabilities. | `docs/reference/workflows/STRATEGY_EXECUTION.md`; `PRODUCT_DIRECTION.md` §3; roadmap phases 8–9 | FUTURE IDEAS | Only the `DRY_RUN` path is supported. There is no real-broker adapter or reconciliation implementation. |

## 4. Determinism, persistence, and provenance

| Public claim | Evidence | Classification | Required wording / guardrail |
|---|---|---|---|
| Material research identities include dataset/model/configuration or assumption fingerprints appropriate to each workflow. | `research/datasets/{signal_research,strategy_research,predictive,predictive_run,robustness}.py`; identity unit tests | AS BUILT | Say "workflow-specific identity" rather than claiming one universal run schema. |
| Stable hashing and explicit seeds make declared computations repeatable for the same supported inputs and environment. | signal definition hash tests; strategy assumptions fingerprint tests; predictive dataset/run fingerprint code; golden-run regression | AS BUILT | Do not promise bit-for-bit reproducibility across every external library/platform combination. |
| Research computation and read-only analytics are separate. | ADR-0013; `research/datasets/`; `research/analytics/`; reporting application modules | AS BUILT | Visualizations may format, filter, and aggregate persisted facts but must not silently recompute research. |
| The repository alone contains all source data and every real run artifact. | `docs/reference/BTC_PREDICTIVE_STUDY.md` §8; ADR-0002 | STALE / CONFLICTING | Real datasets and most run directories live under private, gitignored `user_data/`; only sanitized fixtures/projections are committed. |
| Persisted evidence is automatically proof of a tradable edge. | ADR-0024; BTC study references; Signal Quality study | STALE / CONFLICTING | Negative and inconclusive results are first-class evidence; no metric grants trading approval. |

## 5. Public dashboard and publication

| Public claim | Evidence | Classification | Required wording / guardrail |
|---|---|---|---|
| The Streamlit dashboard is a separate, read-only presentation application. | ADR-0022; ADR-0034; `apps/dashboard/`; `tests/unit/test_apps_boundaries.py` | AS BUILT | It is not the Research Workbench and exposes no write or command surface. |
| New portfolio pages consume a versioned, deny-by-default sanitized projection. | ADR-0034; `dashboard_app/publication/`; `apps/dashboard/tests/test_publication.py` | AS BUILT | Unknown and forbidden fields are omitted; no fallback to workspace scanning is allowed. |
| The current Signal Quality public slice can render without mounting the private workspace. | committed `apps/dashboard/publication_data/`; `scripts/dashboard/generate_btc_signal_quality_projection.py`; study contract tests | AS BUILT | This applies to the new portfolio slice, not yet to legacy technical pages 1–6. |
| All current catalog and technical pages already use only the public projection and never render internal paths. | ADR-0034 §Migration; `dashboard_app/catalog/scanner.py`; current view contracts | STALE / CONFLICTING | Sprint 061 must migrate these pages; until then they are grandfathered scanner-backed readers. |
| Study grouping may connect explicit projected artifacts without asserting hidden cross-workflow lineage. | ADR-0034 §2; `publication/manifest.py`; BTC Signal Quality manifest | AS BUILT | An explicit manifest is presentation grouping, not a framework Study aggregate. |
| Eligible negative, incomplete, unsupported, and `NO VERDICT` results belong in the complete catalog. | accepted D061-01/02; `DASHBOARD_DEVELOPMENT_DIRECTION.md` §8 | IN DEVELOPMENT | This is approved Sprint 061 behavior, not the current one-study implementation. |
| Missing upstream classification renders `NO VERDICT`. | accepted D061-01/02; ADR-0034 copy-not-derive rule | IN DEVELOPMENT | `NO VERDICT` means absence of a persisted classification; never infer a substitute from metrics. |
| Internal paths, configuration, strategy source, model binaries, credentials, host identifiers, and logs are excluded. | ADR-0034 §1; publication sanitizer tests | AS BUILT for projection; IN DEVELOPMENT for legacy pages | The complete claim becomes true only after pages 1–6 migrate. |

## 6. Quality, CI, deployment, and operations

| Public claim | Evidence | Classification | Required wording / guardrail |
|---|---|---|---|
| Pull requests to `main` and `sprint/**` run lint, format, typing, unit, integration, build, ML-extra, dashboard, and CLI jobs. | `.github/workflows/ci.yml` | AS BUILT | Describe the configured gates, not an unverified claim that every historical run passed them. |
| Root quality commands fully type-check and test dashboard code and dashboard scripts. | root `pyproject.toml`; `.pre-commit-config.yaml`; PRB-023 | STALE / CONFLICTING | Root mypy/pytest exclude these paths today; Sprint 061 must close or explicitly re-scope the gap. |
| Dashboard pages are scanned for forbidden framework imports. | `tests/unit/test_apps_boundaries.py`; PRB-022 closure | AS BUILT | `scripts/dashboard/` is not yet covered; PRB-024 remains open. |
| Dashboard code deployment is automated from `main` to a VPS through SSH and Docker Compose. | `.github/workflows/deploy-dashboard.yml`; `apps/dashboard/docs/RUNBOOK.md` | AS BUILT | The workflow deploys application code; storage synchronization remains operator-managed. |
| Production currently selects a validated immutable projection release and mounts it read-only. | accepted D061-03; current deploy workflow and Compose files | IN DEVELOPMENT | Sprint 061 must add the pre-deploy generation/selection and fail-closed activation lifecycle. |
| The dashboard container mounts research storage read-only. | `apps/dashboard/deploy/docker-compose.yml`; dashboard runbook | AS BUILT | After migration, production should mount the selected public bundle rather than the private workspace for public evidence. |
| Public TLS is managed by the dashboard Compose stack. | dashboard runbook | STALE / CONFLICTING | TLS terminates at a shared VPS edge outside this repository. |
| Live-paper status failures are surfaced without creating dashboard-side recovery behavior. | live-paper datasource/view tests; runbooks | AS BUILT | Recovery and feed repair belong to the runtime/operator, not the public dashboard. |

## 7. Evidence suitable for featured studies and notes

| Candidate | Evidence | Publication readiness | Constraint |
|---|---|---|---|
| BTC Signal Quality Study | `docs/reference/BTC_SIGNAL_QUALITY_STUDY.md`; committed projection and manifest | Ready, already public | Preserve `INCONCLUSIVE` and the negative downstream result verbatim. |
| Real-Data BTC Predictive Study | `docs/reference/BTC_PREDICTIVE_STUDY.md`; three recorded run identities | Evidence reviewed; projection role/generalized manifest still required | Report the split regression/binary result and the triggered tree overfit; do not collapse it to a winner. |
| BTC dry-run reliability / live-paper status | ADR-0021; local/AWS runbooks; execution tests | Suitable as an engineering case study, not a research study | Always distinguish live data from simulated execution and current status from historical evidence. |
| Publication boundary | ADR-0034; sanitizer and boundary tests | Suitable Research & Engineering Note | Describe the migration gap honestly until pages 1–6 are projection-backed. |
| Negative-result discipline | BTC Signal Quality and Predictive Study references | Suitable Research & Engineering Note | No profitability marketing or post-hoc repair narrative. |

## 8. Future-direction source boundaries

| Future page | Approved editorial source | Facts that may be stated | Required disclaimer |
|---|---|---|---|
| AI Research Infrastructure | Maintainer-provided Polish note summarized in `SPRINT_061.md` §Content contract | Proposed AI control plane vs deterministic compute; lightweight local/free orchestration; structured Planner/Analyst/Critic roles and artifacts; model routing and official subscription-agent escalation; persistent knowledge; budgets and anti-data-mining policy | Not implemented; provider and runtime architecture undecided; unofficial web-UI automation excluded; no autonomous promotion to live execution. |
| Research Application | `docs/vision/RESEARCH_APPLICATION_PRODUCT_VISION.md` (`DRAFT`) | Proposed local-first Workbench; CLI/Python interoperability; immutable artifacts; compatibility-aware comparison; explicit publication; later separation of private live/paper control and public portfolio | Draft vision; no UI stack or sprint approved; not a second research engine, automatic selector, or public command surface. |

## 9. Conflicts and required Sprint 061 resolutions

1. **Visibility policy:** the Research Application vision says nothing becomes
   public automatically, while the accepted dashboard direction requires every
   safely publishable result to appear. D061-01 resolves this for the public
   catalog: safe roles and identity determine catalog inclusion; manual
   curation remains only for Home features and editorial notes.
2. **Study grouping:** the current implementation has one hand-authored study
   manifest. D061-02 adds deterministic fallback grouping without inventing
   cross-workflow lineage and labels the absence of editorial study context.
3. **Immutable releases:** the current deploy workflow rebuilds the app but
   does not generate or atomically select a versioned projection. D061-03
   requires an explicit pre-deploy generation/validation step that preserves
   the known-good release or fails the deployment closed.
4. **Technical-page exposure:** pages 1–6 remain scanner-backed and may render
   `storage_path` / `file://` links. Sprint 061 must migrate them to the public
   projection before claiming the whole dashboard excludes internal paths.
5. **Quality coverage:** CI has a dashboard Ruff/test job, but root mypy/pytest
   and pre-commit do not cover the dashboard or scripts, and the generator
   script is outside the import-boundary scan. PRB-023/024 must be closed or
   explicitly re-scoped by T007.
6. **Planning drift:** `CURRENT_STATUS.md`, `ROADMAP.md`, and
   `PHASE_16D_PORTFOLIO_DASHBOARD.md` still describe Sprints 059/060 as draft or
   pending even though both are on `main`. T005 owns this reconciliation.

## 10. Authoring gate

Public copy may use an `AS BUILT` claim only when it preserves the constraints
in this matrix. Any new material claim requires an additional evidence row or
must be labelled `IN DEVELOPMENT` / `FUTURE IDEAS`. Public content must never:

- infer a verdict, research metric, compatibility judgment, or market conclusion;
- present simulated results as live performance;
- expose private paths or reconstruct a workspace location;
- imply unsupported data types, real-broker execution, reconciliation, or
  autonomous research capability;
- treat a planning document or editorial note as proof of current implementation.
