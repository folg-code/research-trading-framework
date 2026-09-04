# Vision & Assumptions

Principles, target architecture, binding design decisions and future direction.

**These documents describe intent and constraints — not necessarily what is implemented today.**

For what exists in code: [../reference/README.md](../reference/README.md).
Index: [../README.md](../README.md).

> This folder was reorganized by Sprint 055 (T008 execution, T006 this
> context map) from 6 provenance-shaped files (`ARCHITECTURE_FOUNDATIONS.md`,
> `ARCHITECTURE_TECHNICAL.md`, `MULTITIMEFRAME_MARKET_MODEL_ARCHITECTURE.md`,
> `WORKFLOWS_AI_ADR.md`, `MARKET_ANALYSIS_WITH_DECISIONS.md`,
> `DATA_MODULE_FUTURE.md`) into 10 topic-grouped files — grouped by subject,
> not by which of the six they came from. See
> `docs/planning/sprints/SPRINT_055_T002_VISION_TARGET_IA.md` for the
> rationale and `SPRINT_055_T004_DECISIONS.md` for what was approved.

**Maturity key:** `FUTURE` = not yet built, code-verified as of the sprint
noted. `MIXED` = some sections built, some not — see the file's own
per-section notes. `BINDING DECISIONS` = an accepted decision register, not
a maturity claim.

---

## Direction and principles

| File | Purpose | Maturity | Verified as of |
|---|---|---|---|
| [PRODUCT_DIRECTION.md](PRODUCT_DIRECTION.md) | Product-level vision, target capabilities, the three-capability contract | FUTURE/principles | Sprint 054 |

## Domain target architecture

| File | Purpose | Maturity | Verified as of |
|---|---|---|---|
| [TIME_MODEL_FUTURE.md](TIME_MODEL_FUTURE.md) | Time Model target architecture (sessions, calendars, holidays) | FUTURE | Sprint 054 |
| [MARKET_DATA_FUTURE.md](MARKET_DATA_FUTURE.md) | Market Data target architecture (not-yet-built sections) | MIXED | Sprint 054, post-054 follow-up |
| [MARKET_ANALYSIS_FUTURE.md](MARKET_ANALYSIS_FUTURE.md) | Market Analysis target architecture (States, intrabar, Component Request) | FUTURE | Sprint 054 |
| [MARKET_ANALYSIS_DECISIONS.md](MARKET_ANALYSIS_DECISIONS.md) | Binding Market Analysis decision register D-001-D-036, with a D to ADR cross-reference table | BINDING DECISIONS | Sprint 055 T008 (F5 verification: D-029 confirmed superseded by ADR-MA-012; D-018/D-028 not confirmed superseded) |

## Research and execution

| File | Purpose | Maturity | Verified as of |
|---|---|---|---|
| [RESEARCH_SPACE_AND_ANALYTICS.md](RESEARCH_SPACE_AND_ANALYTICS.md) | Bounded research spaces, staged research methodology, automated screening/multi-objective selection | MIXED | Sprint 054 |
| [EXECUTION_RUNTIME_FUTURE.md](EXECUTION_RUNTIME_FUTURE.md) | Replay/Paper/Live execution modes, broker abstraction, reconciliation, recovery | FUTURE | Sprint 054 |

## Cross-cutting capabilities

| File | Purpose | Maturity | Verified as of |
|---|---|---|---|
| [EVENT_SYSTEM_FUTURE.md](EVENT_SYSTEM_FUTURE.md) | Event System target architecture (largest fully-unbuilt block - `events/` is an empty stub) | FUTURE | Sprint 054 |
| [COMPONENT_PROMOTION_LIFECYCLE.md](COMPONENT_PROMOTION_LIFECYCLE.md) | Local component development, promotion lifecycle, fingerprints | FUTURE | Sprint 054 |
| [RUN_IDENTITY_AND_CONFIGURATION.md](RUN_IDENTITY_AND_CONFIGURATION.md) | Workflow/run identity, configuration layering and versioning | MIXED | Sprint 054 |

## Redirects (content that left `docs/vision/`)

| Former content | Current home |
|---|---|
| Workspace, result store, and frame architecture | [../reference/system/ANALYSIS_WORKSPACE_AND_DERIVED_DATA.md](../reference/system/ANALYSIS_WORKSPACE_AND_DERIVED_DATA.md) (Sprint 054 T005, folder moved by Sprint 055 T007) |
| AI Agent Contract (former `WORKFLOWS_AI_ADR.md` section 6) | `AGENTS.md` (root) / `.cursor/rules/ARCHITECTURE_CONTROL.md` (Sprint 054 T006b) |
| ADR process (former `WORKFLOWS_AI_ADR.md` section 7) | [../adr/README.md](../adr/README.md) (Sprint 054 T006a) |
| Superseded module/`user_data/` layout proposals | [../historical/SUPERSEDED_LAYOUT_PROPOSALS.md](../historical/SUPERSEDED_LAYOUT_PROPOSALS.md) (Sprint 055 T008) |
| Closed Sprint-003 Market Analysis planning note | [../planning/sprints/SPRINT_003.md](../planning/sprints/SPRINT_003.md) / [S003_WAVE0_ARCHITECTURE_CLOSURE.md](../planning/sprints/S003_WAVE0_ARCHITECTURE_CLOSURE.md) (already covers the same content in English - Sprint 055 T008 did not duplicate it) |

## Pending moves (parked, not yet relocated)

Two small sections are parked in
[`../historical/SUPERSEDED_LAYOUT_PROPOSALS.md`](../historical/SUPERSEDED_LAYOUT_PROPOSALS.md)
with an explicit "pending move" note, rather than moved to their real
destination, because that destination is out of this sprint's scope:

| Content | Real destination | Why not moved now |
|---|---|---|
| Composition Over Inheritance (former `ARCHITECTURE_FOUNDATIONS.md` section 5.5) | `.cursor/rules/ARCHITECTURE_CONTROL.md` | Needs a Cursor-side maintainer pass (same constraint as Sprint 053's deferred T008) |
| Controlled Technology Adoption (former `ARCHITECTURE_FOUNDATIONS.md` section 5.14) | `docs/adr/README.md` process section | Editing the ADR process doc needs its own reviewed change, not a side effect of this sprint |

---

## When to read

- Designing a new capability or ADR
- Resolving "what should we build?" questions
- Before changing public contracts (check binding decisions here, then verify as-is in `reference/`)

Do not use vision docs alone to determine implementation status - check [MODULE_MAP.md](../reference/system/MODULE_MAP.md) and tests.
