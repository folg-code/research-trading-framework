# As-Implemented Reference

Documentation of **what is built and how it works** in the current codebase.

Update after merged sprint waves and contract changes.
Index: [../README.md](../README.md). Vision docs: [../vision/README.md](../vision/README.md).

Layout: `system/` (cross-cutting architecture), `workflows/` (end-to-end
research/operational workflows), `runbooks/` (operator how-to-run/deploy
guides), `modules/` (per-package/per-app implementation reference). See
`docs/planning/sprints/SPRINT_054_T007_REFERENCE_FOLDER_AUDIT.md` for the
original rationale behind this split, and
`docs/planning/sprints/SPRINT_055_T001_REFERENCE_TARGET_IA.md` /
`SPRINT_055_T004_DECISIONS.md` for the Sprint 055 re-cut that produced the
tree below (subject-based `system/` files instead of provenance-based ones,
plus the four new `workflows/` files).

---

## System (cross-cutting architecture)

| File | Purpose |
|------|---------|
| [system/SYSTEM_OVERVIEW.md](system/SYSTEM_OVERVIEW.md) | Architectural modules, problems solved, workflow boundaries, future directions |
| [system/DOMAIN_MODEL.md](system/DOMAIN_MODEL.md) | The five domains (Market, Market Analysis, Strategy, Research, Execution), their Owns/Does-Not-Own boundaries, domain relationships, framework/user space, accepted clarifications |
| [system/ARCHITECTURE_PRINCIPLES.md](system/ARCHITECTURE_PRINCIPLES.md) | Cross-cutting build principles — priority order, separation of concerns, reproducibility, immutability, modular monolith |
| [system/MARKET_ANALYSIS_ARCHITECTURE.md](system/MARKET_ANALYSIS_ARCHITECTURE.md) | The Market Analysis engine — component contract, registry, dependency graph, lazy execution, cache identity, execution context; includes the G-04 executor-enforcement note |
| [system/TIME_AND_ALIGNMENT.md](system/TIME_AND_ALIGNMENT.md) | UTC/Clock policy, futures contract rolls, multitimeframe identity, resampling, temporal alignment and look-ahead protection, `observed_at`/`available_at` |
| [system/DATA_REPRESENTATION_POLICY.md](system/DATA_REPRESENTATION_POLICY.md) | Canonical carrier per kind of work, six directional rules, target primitives, null semantics |
| [system/ANALYSIS_WORKSPACE_AND_DERIVED_DATA.md](system/ANALYSIS_WORKSPACE_AND_DERIVED_DATA.md) | Analysis workspace, result store, and frame materialization — authoritative on derived analytical data (note: "workspace" here means the execution-scoped `AnalysisWorkspace`, not the `user_data/` storage root in `MODULE_MAP.md` §11) |
| [system/MODULE_MAP.md](system/MODULE_MAP.md) | Packages, status ✅/🟡/⬜, entry points |
| [system/DEPENDENCY_RULES.md](system/DEPENDENCY_RULES.md) | Allowed dependency direction, which boundaries are test-enforced vs. only documented, and one known unenforced exception |

The point-in-time Sprint 036 data-representation measurement record and
decision register (superseded by `DATA_REPRESENTATION_POLICY.md` above) now
live at
[`docs/planning/sprints/SPRINT_036_DATA_REPRESENTATION_AUDIT.md`](../planning/sprints/SPRINT_036_DATA_REPRESENTATION_AUDIT.md).

## Workflows (end-to-end, conceptual)

| File | Purpose |
|------|---------|
| [workflows/RESEARCH_METHODOLOGIES.md](workflows/RESEARCH_METHODOLOGIES.md) | **Which methodology should I choose** — all research workflows, the questions they answer, choosing a path (Signal, Model, Strategy, Robustness, Predictive) |
| [workflows/SIGNAL_RESEARCH.md](workflows/SIGNAL_RESEARCH.md) | Signal Research scopes, contracts, dependency plan and persisted outputs |
| [workflows/STRATEGY_RESEARCH.md](workflows/STRATEGY_RESEARCH.md) | Strategy Research: Strategy Model composition, simulation, analytics, walk-forward, Monte Carlo, robustness |
| [workflows/STRATEGY_EXECUTION.md](workflows/STRATEGY_EXECUTION.md) | Strategy Execution runtime flow, position management, strategy-risk vs. operational-risk separation, persistence |
| [workflows/MARKET_DATA.md](workflows/MARKET_DATA.md) | Market Data: import paths, external dataset import, local historical access, partition finalization, dataset publication, futures contract identity, validation, prohibited designs |

`RESEARCH_METHODOLOGIES.md` answers "which methodology and why"; the four
workflow files above answer "what are this workflow's scopes, contracts and
persisted outputs" — the two are deliberately not merged (see the reciprocal
pointers at the top of each file).

## Runbooks (operator how-to-run/deploy)

| File | Purpose |
|------|---------|
| [runbooks/LOCAL_BTC_FUTURES_DRY_RUN.md](runbooks/LOCAL_BTC_FUTURES_DRY_RUN.md) | Local BTCUSDT live-data, simulated-execution operator notes |
| [runbooks/AWS_BTC_FUTURES_DRY_RUN.md](runbooks/AWS_BTC_FUTURES_DRY_RUN.md) | AWS BTCUSDT dry-run worker container packaging and smoke checklist |
| [runbooks/LIVE_PAPER_PIPELINE_INSPECTION.md](runbooks/LIVE_PAPER_PIPELINE_INSPECTION.md) | Live paper / AWS dry-run pipeline architecture verdict and operator checklist |

All three cover one demo family (BTC futures dry-run: local / AWS / pipeline
verification) with the same safety boundary (simulated only, no
credentials, no real orders). There are no research-workflow runbooks —
see `modules/OPERATOR_CLI.md` for the research-side CLI surface.

## Modules (per-package/per-app reference)

Implementation references:

| File | Purpose |
|------|---------|
| [modules/MARKET_ANALYSIS_MODULE.md](modules/MARKET_ANALYSIS_MODULE.md) | Market Analysis — implementation guide (flow, key types, verification, design notes) |
| [modules/ANALYSIS_COMPONENT_CATALOG.md](modules/ANALYSIS_COMPONENT_CATALOG.md) | The full built-in component catalog — per-component semantics, warm-up, output fields, zero-denominator conventions |
| [modules/PREDICTIVE_PROMOTION.md](modules/PREDICTIVE_PROMOTION.md) | Predictive model promotion (`research/predictive/promotion/`) — parameter-file schema, store layout, fingerprint derivation, guards |
| [modules/DASHBOARD_APPLICATION.md](modules/DASHBOARD_APPLICATION.md) | Research Dashboard (`apps/dashboard`) — boundary, contracts, pages, publishing runbook |

Operator/author-facing guides:

| File | Purpose |
|------|---------|
| [modules/MODEL_AUTHORING.md](modules/MODEL_AUTHORING.md) | Authoring DSL — one copy-pasteable market + signal model |
| [modules/STRATEGY_AUTHORING.md](modules/STRATEGY_AUTHORING.md) | Custom strategy authoring (`strategy_file`) — loading contract, trust model, error table |
| [modules/STRATEGY_EXAMPLES.md](modules/STRATEGY_EXAMPLES.md) | Worked example strategies (`build_strategy()`) using the catalog above |
| [modules/OPERATOR_CLI.md](modules/OPERATOR_CLI.md) | Operator CLI (`trading-cli` / `apps/cli`) — command groups, config schema pointer, exit codes |

Domain-level questions ("what does Market Analysis own?", "which package
implements the Strategy domain?") belong in `system/DOMAIN_MODEL.md` and
`system/MODULE_MAP.md`, not here — there is deliberately no
`modules/SIGNALS.md`, `modules/STRATEGY.md`, `modules/EXECUTION.md` or
`modules/DATA.md` (no module-level implementation reference exists for
those; see `SPRINT_055_T001_REFERENCE_TARGET_IA.md` §5.4).

---

## When to read

- Onboarding and day-to-day implementation
- Code review against actual behaviour
- Updating docs after a merged PR

If reference and vision disagree, **reference + tests** describe as-is behaviour.
