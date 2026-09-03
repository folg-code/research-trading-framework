# As-Implemented Reference

Documentation of **what is built and how it works** in the current codebase.

Update after merged sprint waves and contract changes.  
Index: [../README.md](../README.md). Vision docs: [../vision/README.md](../vision/README.md).

---

## Navigation (short, keep current)

| File | Purpose |
|------|---------|
| [MODULE_MAP.md](MODULE_MAP.md) | Packages, status ✅/🟡/⬜, entry points |
| [ANALYSIS_WORKSPACE_AND_DERIVED_DATA.md](ANALYSIS_WORKSPACE_AND_DERIVED_DATA.md) | Analysis workspace, result store, and frame materialization — authoritative on derived analytical data |
| [system/ARCHITECTURE_FOUNDATIONS.md](system/ARCHITECTURE_FOUNDATIONS.md) | As-built architecture foundations (domains, capabilities, principles) — moved from `docs/vision/` by Sprint 054 T004; confirmed-current sections only |
| [system/ARCHITECTURE_TECHNICAL.md](system/ARCHITECTURE_TECHNICAL.md) | As-built technical architecture (Time Model, Market Data, Market Analysis Engine, Configuration) — moved from `docs/vision/` by Sprint 054 T004; confirmed-current sections only |
| [system/MULTITIMEFRAME_MARKET_MODEL.md](system/MULTITIMEFRAME_MARKET_MODEL.md) | As-built multitimeframe/Market Model architecture — moved from `docs/vision/` by Sprint 054 T004; confirmed-current sections only |
| [system/WORKFLOWS_ARCHITECTURE.md](system/WORKFLOWS_ARCHITECTURE.md) | As-built Signal Research / Strategy Research / Strategy Execution workflow architecture — moved from `docs/vision/WORKFLOWS_AI_ADR.md` §1-5/§8 by Sprint 054 T006c; confirmed-current sections only |
| [DATA_WORKFLOWS.md](DATA_WORKFLOWS.md) | Data movement with diagrams; **§1.1** NQ half-year scale benchmarks *(file not in tree; research storage paths live in MODULE_MAP §11)* |
| [RESEARCH_METHODOLOGIES.md](RESEARCH_METHODOLOGIES.md) | **All research workflows** — methodologies, scopes, CLIs, choosing a path (Signal, Model, Strategy, Robustness, Predictive) |
| [DATA_REPRESENTATION_AUDIT.md](DATA_REPRESENTATION_AUDIT.md) | Representation inventory, transformation map, **canonical type policy** and the D-REP decision register |
| [LOCAL_BTC_FUTURES_DRY_RUN.md](LOCAL_BTC_FUTURES_DRY_RUN.md) | Local BTCUSDT live-data, simulated-execution operator notes |
| [AWS_BTC_FUTURES_DRY_RUN.md](AWS_BTC_FUTURES_DRY_RUN.md) | AWS BTCUSDT dry-run worker container packaging and smoke checklist |
| [../README.md](../README.md) | Project overview — stack, architecture, workflows (repository root) |

---

## Module Reference

| File | Purpose |
|------|---------|
| [modules/DATA_MODULE.md](modules/DATA_MODULE.md) | Market Data module — Sprint 002 implementation detail |
| [modules/MARKET_ANALYSIS_MODULE.md](modules/MARKET_ANALYSIS_MODULE.md) | Market Analysis — thin guide (expand after Sprint 003) |
| [modules/MODEL_AUTHORING.md](modules/MODEL_AUTHORING.md) | Authoring DSL — one copy-pasteable market + signal model |

---

## When to read

- Onboarding and day-to-day implementation
- Code review against actual behaviour
- Updating docs after a merged PR

If reference and vision disagree, **reference + tests** describe as-is behaviour.
