# As-Implemented Reference

Documentation of **what is built and how it works** in the current codebase.

Update after merged sprint waves and contract changes.  
Index: [../README.md](../README.md). Vision docs: [../vision/README.md](../vision/README.md).

Layout: `system/` (cross-cutting architecture), `workflows/` (end-to-end
research/operational workflows), `runbooks/` (operator how-to-run/deploy
guides), `modules/` (per-package/per-app implementation reference). See
`docs/planning/sprints/SPRINT_054_T007_REFERENCE_FOLDER_AUDIT.md` for the
rationale behind this split.

---

## System (cross-cutting architecture)

| File | Purpose |
|------|---------|
| [system/SYSTEM_OVERVIEW.md](system/SYSTEM_OVERVIEW.md) | Architectural modules, problems solved, workflow boundaries, future directions (formerly `ARCHITECTURE_AND_WORKFLOWS.md`) |
| [system/MODULE_MAP.md](system/MODULE_MAP.md) | Packages, status ✅/🟡/⬜, entry points |
| [system/DATA_REPRESENTATION_AUDIT.md](system/DATA_REPRESENTATION_AUDIT.md) | Representation inventory, transformation map, **canonical type policy** and the D-REP decision register |
| [system/ARCHITECTURE_FOUNDATIONS.md](system/ARCHITECTURE_FOUNDATIONS.md) | As-built architecture foundations (domains, capabilities, principles) — moved from `docs/vision/` by Sprint 054 T004; confirmed-current sections only |
| [system/ARCHITECTURE_TECHNICAL.md](system/ARCHITECTURE_TECHNICAL.md) | As-built technical architecture (Time Model, Market Data, Market Analysis Engine, Configuration) — moved from `docs/vision/` by Sprint 054 T004; confirmed-current sections only |
| [system/MULTITIMEFRAME_MARKET_MODEL.md](system/MULTITIMEFRAME_MARKET_MODEL.md) | As-built multitimeframe/Market Model architecture — moved from `docs/vision/` by Sprint 054 T004; confirmed-current sections only |
| [system/WORKFLOWS_ARCHITECTURE.md](system/WORKFLOWS_ARCHITECTURE.md) | As-built Signal Research / Strategy Research / Strategy Execution workflow architecture — moved from `docs/vision/WORKFLOWS_AI_ADR.md` §1-5/§8 by Sprint 054 T006c; confirmed-current sections only |
| `system/DEPENDENCY_RULES.md` | **Not yet created** — deferred pending authoring of consolidated content from `AGENTS.md`/`ARCHITECTURE_CONTROL.md` (see Sprint 054 T007 §4.1) |

## Workflows (end-to-end, conceptual)

| File | Purpose |
|------|---------|
| [workflows/RESEARCH_METHODOLOGIES.md](workflows/RESEARCH_METHODOLOGIES.md) | **All research workflows** — methodologies, scopes, CLIs, choosing a path (Signal, Model, Strategy, Robustness, Predictive) |

## Runbooks (operator how-to-run/deploy)

| File | Purpose |
|------|---------|
| [runbooks/LOCAL_BTC_FUTURES_DRY_RUN.md](runbooks/LOCAL_BTC_FUTURES_DRY_RUN.md) | Local BTCUSDT live-data, simulated-execution operator notes |
| [runbooks/AWS_BTC_FUTURES_DRY_RUN.md](runbooks/AWS_BTC_FUTURES_DRY_RUN.md) | AWS BTCUSDT dry-run worker container packaging and smoke checklist |
| [runbooks/LIVE_PAPER_PIPELINE_INSPECTION.md](runbooks/LIVE_PAPER_PIPELINE_INSPECTION.md) | Live paper / AWS dry-run pipeline architecture verdict and operator checklist |

## Modules (per-package/per-app reference)

| File | Purpose |
|------|---------|
| [modules/DATA_MODULE.md](modules/DATA_MODULE.md) | Market Data module — as-implemented reference. Reclassified from the Sprint-002-era mixed document (Sprint 054 T007 §3 open item): target-architecture/not-yet-built sections moved to [../vision/DATA_MODULE_FUTURE.md](../vision/DATA_MODULE_FUTURE.md); see `docs/planning/DATA_MODULE_CLASSIFICATION.md` |
| [modules/MARKET_ANALYSIS_MODULE.md](modules/MARKET_ANALYSIS_MODULE.md) | Market Analysis — thin guide (expand after Sprint 003) |
| [modules/MODEL_AUTHORING.md](modules/MODEL_AUTHORING.md) | Authoring DSL — one copy-pasteable market + signal model |
| [modules/DASHBOARD_APPLICATION.md](modules/DASHBOARD_APPLICATION.md) | Research Dashboard (`apps/dashboard`) — boundary, contracts, pages, publishing runbook |
| [modules/OPERATOR_CLI.md](modules/OPERATOR_CLI.md) | Operator CLI (`trading-cli` / `apps/cli`) — command groups, config schema pointer, exit codes |
| [modules/PREDICTIVE_PROMOTION.md](modules/PREDICTIVE_PROMOTION.md) | Predictive model promotion (`research/predictive/promotion/`) — parameter-file schema, store layout, fingerprint derivation, guards |
| [modules/STRATEGY_AUTHORING.md](modules/STRATEGY_AUTHORING.md) | Custom strategy authoring (`strategy_file`) — loading contract, trust model, error table, worked examples |

## Other

| File | Purpose |
|------|---------|
| [ANALYSIS_WORKSPACE_AND_DERIVED_DATA.md](ANALYSIS_WORKSPACE_AND_DERIVED_DATA.md) | Analysis workspace, result store, and frame materialization — authoritative on derived analytical data |
| [../README.md](../README.md) | Project overview — stack, architecture, workflows (repository root) |

---

## When to read

- Onboarding and day-to-day implementation
- Code review against actual behaviour
- Updating docs after a merged PR

If reference and vision disagree, **reference + tests** describe as-is behaviour.
