# Sprint 063: Reproducible Strategy Simulation Series

Status: Draft — requires maintainer approval before implementation and data runs
Goal: Execute and publish a bounded, reproducible series of Strategy Research
simulations over existing public/non-proprietary strategy examples so the new
study-grouped catalog contains materially richer positive, negative, zero-trade
and incomplete evidence without inventing a strategy ranking.
Sources:

- `docs/reference/workflows/STRATEGY_RESEARCH.md`
- `docs/reference/modules/OPERATOR_CLI.md`
- `docs/reference/modules/STRATEGY_AUTHORING.md`
- `docs/planning/DASHBOARD_DEVELOPMENT_DIRECTION.md`
- `docs/planning/PROBLEM_REGISTRY.md` (`PRB-020`)
- `apps/cli/examples/research_run_strategy*.yaml`
- `scripts/strategy_research/run_strategy_research.py`
- `docs/planning/sprints/SPRINT_061.md`

Architecture triage: none if the sprint uses an explicit reviewed experiment
matrix and existing Strategy Research contracts. If implementation requires a
generic family/sweep engine, stop and move that work to Phase 16E rather than
silently closing PRB-020 inside this sprint.

## Scope

In scope:

- Inventory one real, publishable BTCUSDT.P 1m OHLCV DatasetRef with sufficient
  coverage and freeze three non-overlapping evaluation periods.
- Freeze six existing public/non-proprietary strategy compositions from the
  canonical and documented strategy-authoring examples.
- Run an explicit 6 strategies × 3 periods = 18-case matrix with the same
  baseline simulation assumptions and engine version.
- Persist run manifests, trade/equity facts, analytics sidecars, zero-trade
  outcomes, failures and reproducibility identities.
- Publish every safe result through Sprint 061's projection and group the series
  as one catalog study with experiment/run detail.
- Add a neutral Research & Engineering Note describing construction, coverage,
  limitations and failures without selecting a winner or claiming an edge.
- Sync the immutable publication bundle to the dashboard VPS and visually verify
  the catalog/study pages.

Out of scope:

- New strategy components, parameter optimization or automatic search.
- Strategy Families/bounded-expansion machinery from Phase 16E / PRB-020.
- Predictive scoring, promotion to runtime, dry-run strategy replacement or live trading.
- Cross-asset claims, proprietary strategies or committing `user_data`.
- Changing thresholds or assumptions after seeing results.
- Hiding negative, zero-trade, incomplete or unsupported outcomes.

## Decisions

| Decision | Recommendation | Status |
|---|---|---|
| D063-01 — matrix | Use exactly six reviewed strategy definitions across three fixed, non-overlapping periods. Freeze the 18 case identities before the first run; do not add favorable variants after inspecting results. | Pending maintainer approval; blocks T002 |
| D063-02 — assumptions | Use one shared baseline `SimulationAssumptions`, timeframe, session semantics and engine version for all cases. Any incompatible strategy is recorded unsupported rather than silently receiving different assumptions. | Pending maintainer approval; blocks T002 |
| D063-03 — publication | Publish all safely identifiable dispositions. A zero-trade or negative run is complete evidence; a failed/preflight-rejected case remains visible in study accounting when its identity is safe. | Inherited from dashboard direction |
| D063-04 — interpretation | No leaderboard or universal winner in this sprint. Comparisons describe persisted compatibility, coverage and outcomes only. | Recommended; pending maintainer approval |

## Tasks

| Task | Outcome | Dependencies | Ownership | Risk | Status | PR |
|---|---|---|---|---|---|---|
| T001 | Verify the DatasetRef, date coverage, source/license/publication safety and six strategy definitions; freeze the 18-case matrix, assumptions, seeds, expected artifact set and stop conditions before execution | approved sprint; Sprint 061 catalog contract | research inventory + documentation | high | Blocked by D063-01/02 | — |
| T002 | Add only the minimal explicit run specifications/operator script needed to execute the frozen matrix through existing Strategy Research APIs; preflight every case and avoid a generic sweep/family abstraction | T001 | scripts/config + tests | standard | Ready after T001 | — |
| T003 | Execute the 18 cases in a controlled workspace, recording start/end, run identity, success/failure/unsupported disposition and resource/runtime observations without committing research data | T002 | operator execution | high | Ready after T002 | — |
| T004 | Validate manifests, assumptions fingerprints, temporal coverage, analytics sidecars and duplicate/reuse behavior; rerun only cases invalidated by an implementation or operational failure, never because of an unfavorable result | T003 | research QA + analytics | high | Ready after T003 | — |
| T005 | Generate the safe projection, study manifest and neutral note; confirm all 18 planned identities are accounted for and every eligible completed result appears in the catalog | T004 | dashboard publication + content | high | Ready after T004 | — |
| T006 | Sync the immutable bundle to the VPS and run catalog/study visual QA, route checks and negative/zero-trade/incomplete-state acceptance tests | T005 | deploy + dashboard QA | standard | Requires explicit deploy approval | — |
| T007 | Reconcile Strategy Research/dashboard/reference docs and record follow-ups for genuine family analytics or new research questions without expanding this sprint | T005–T006 | documentation + independent review | standard | Ready after T006 | — |

## Acceptance criteria

- The experiment matrix is frozen before results: six named existing strategies,
  three non-overlapping periods and 18 deterministic case identities.
- All cases use the same declared DatasetRef, timeframe, session semantics,
  baseline assumptions and engine version, or are explicitly marked unsupported.
- All 18 cases have a final persisted or documented disposition; at least 12 are
  complete, safely publishable Strategy Research runs spanning at least four
  strategies and all three periods. If this minimum is missed, the sprint does
  not claim catalog enrichment and records the blocker.
- Every complete run has traceable strategy identity, dataset reference, time
  range, assumptions fingerprint, trades, equity and analytics; zero trades is
  represented explicitly rather than treated as missing data.
- The catalog groups the series as one study, exposes experiment/run detail and
  retains negative, zero-trade, incomplete and `NO VERDICT` evidence.
- No result changes the matrix, thresholds or assumptions after inspection, and
  no dashboard code computes a new research metric or verdict.
- No proprietary strategy source, raw dataset or `user_data` path is committed
  or exposed by the public projection.
- The public note states methodology, coverage and limitations and makes no
  profitability, validation, promotion or live-trading claim.
- The deployed dashboard displays the new series through the Sprint 061 catalog
  without requiring direct workspace discovery.

## Integration risks

- The existing CLI hardcodes assumptions/session resolution. T001 must verify
  that all selected strategies are compatible; do not add a broad config schema
  merely to rescue one case.
- An 18-run operator script can drift into the unbuilt Strategy Families feature.
  Keep it explicit and study-specific; stop if reusable expansion machinery is needed.
- Data availability or licensing may prevent public projection. Freeze the actual
  DatasetRef and publishability before execution.
- Results may all be negative or contain zero trades. That is valid research
  evidence and not grounds for post-hoc strategy substitution.

## Closeout

- Integrated checks:
- Documentation reconciliation:
- Review:
- Remaining work:
