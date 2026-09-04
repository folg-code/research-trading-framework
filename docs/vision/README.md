# Vision & Assumptions

Principles, target architecture, binding design decisions and future direction.

**These documents describe intent and constraints — not necessarily what is implemented today.**

For what exists in code: [../reference/README.md](../reference/README.md).
Index: [../README.md](../README.md).

> **Sprint 055 T008 note:** this folder was reorganized from 6
> provenance-shaped files (`ARCHITECTURE_FOUNDATIONS.md`,
> `ARCHITECTURE_TECHNICAL.md`, `MULTITIMEFRAME_MARKET_MODEL_ARCHITECTURE.md`,
> `WORKFLOWS_AI_ADR.md`, `MARKET_ANALYSIS_WITH_DECISIONS.md`,
> `DATA_MODULE_FUTURE.md`) into 10 topic-grouped files — see
> `docs/planning/sprints/SPRINT_055_T002_VISION_TARGET_IA.md` for the
> rationale and `SPRINT_055_T004_DECISIONS.md` for what was approved. **This
> index is a minimal placeholder pending the full topic-grouped context map
> (Sprint 055 T006)** — it lists the current files so links are not broken,
> without yet providing T006's planned maturity markers per file.

---

## Direction and principles

| File | Purpose |
|------|---------|
| [PRODUCT_DIRECTION.md](PRODUCT_DIRECTION.md) | Product-level vision, target capabilities, the three-capability contract |

## Domain target architecture

| File | Purpose |
|------|---------|
| [TIME_MODEL_FUTURE.md](TIME_MODEL_FUTURE.md) | Time Model target architecture (sessions, calendars, holidays) |
| [MARKET_DATA_FUTURE.md](MARKET_DATA_FUTURE.md) | Market Data target architecture (not-yet-built sections) |
| [MARKET_ANALYSIS_FUTURE.md](MARKET_ANALYSIS_FUTURE.md) | Market Analysis target architecture (States, intrabar, Component Request) |
| [MARKET_ANALYSIS_DECISIONS.md](MARKET_ANALYSIS_DECISIONS.md) | Binding Market Analysis decision register D-001–D-036 |

## Research and execution

| File | Purpose |
|------|---------|
| [RESEARCH_SPACE_AND_ANALYTICS.md](RESEARCH_SPACE_AND_ANALYTICS.md) | Bounded research spaces, staged research methodology, automated screening/multi-objective selection |
| [EXECUTION_RUNTIME_FUTURE.md](EXECUTION_RUNTIME_FUTURE.md) | Replay/Paper/Live execution modes, broker abstraction, reconciliation, recovery |

## Cross-cutting capabilities

| File | Purpose |
|------|---------|
| [EVENT_SYSTEM_FUTURE.md](EVENT_SYSTEM_FUTURE.md) | Event System target architecture (largest fully-unbuilt block) |
| [COMPONENT_PROMOTION_LIFECYCLE.md](COMPONENT_PROMOTION_LIFECYCLE.md) | Local component development, promotion lifecycle, fingerprints |
| [RUN_IDENTITY_AND_CONFIGURATION.md](RUN_IDENTITY_AND_CONFIGURATION.md) | Workflow/run identity, configuration layering and versioning |

## Redirects (content that left `docs/vision/`)

| Former content | Current home |
|---|---|
| Workspace, result store, and frame architecture | [../reference/ANALYSIS_WORKSPACE_AND_DERIVED_DATA.md](../reference/ANALYSIS_WORKSPACE_AND_DERIVED_DATA.md) (Sprint 054 T005) |
| AI Agent Contract (former `WORKFLOWS_AI_ADR.md` §6) | `AGENTS.md` (root) / `.cursor/rules/ARCHITECTURE_CONTROL.md` (Sprint 054 T006b) |
| ADR process (former `WORKFLOWS_AI_ADR.md` §7) | [../adr/README.md](../adr/README.md) (Sprint 054 T006a) |
| Superseded module/`user_data/` layout proposals | [../historical/SUPERSEDED_LAYOUT_PROPOSALS.md](../historical/SUPERSEDED_LAYOUT_PROPOSALS.md) (Sprint 055 T008) |
| Closed Sprint-003 Market Analysis planning note | [../planning/sprints/SPRINT_003.md](../planning/sprints/SPRINT_003.md) / [S003_WAVE0_ARCHITECTURE_CLOSURE.md](../planning/sprints/S003_WAVE0_ARCHITECTURE_CLOSURE.md) (already covers the same content in English) |

---

## When to read

- Designing a new capability or ADR
- Resolving "what should we build?" questions
- Before changing public contracts (check binding decisions here, then verify as-is in `reference/`)

Do not use vision docs alone to determine implementation status — check [MODULE_MAP.md](../reference/system/MODULE_MAP.md) and tests.
