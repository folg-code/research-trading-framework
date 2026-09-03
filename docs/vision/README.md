# Vision & Assumptions

Principles, target architecture, binding design decisions and future direction.

**These documents describe intent and constraints — not necessarily what is implemented today.**

For what exists in code: [../reference/README.md](../reference/README.md).  
Index: [../README.md](../README.md).

---

## Core Architecture

| File | Purpose |
|------|---------|
| [ARCHITECTURE_FOUNDATIONS.md](ARCHITECTURE_FOUNDATIONS.md) | Domain principles, module boundaries, long-term model |
| [ARCHITECTURE_TECHNICAL.md](ARCHITECTURE_TECHNICAL.md) | Cross-cutting target technical architecture |

---

## Domain Design (binding decisions)

| File | Purpose |
|------|---------|
| [MARKET_ANALYSIS_WITH_DECISIONS.md](MARKET_ANALYSIS_WITH_DECISIONS.md) | Market Analysis decisions D-001–D-036 |
| [MULTITIMEFRAME_MARKET_MODEL_ARCHITECTURE.md](MULTITIMEFRAME_MARKET_MODEL_ARCHITECTURE.md) | Multitimeframe market model (future) |

Workspace, result store, and frame architecture — authoritative on derived
data — moved to
[../reference/ANALYSIS_WORKSPACE_AND_DERIVED_DATA.md](../reference/ANALYSIS_WORKSPACE_AND_DERIVED_DATA.md)
(Sprint 054 T005: it self-describes as authoritative, a reference-tier claim,
not a vision/future document).

---

## Process

| File | Purpose |
|------|---------|
| [WORKFLOWS_AI_ADR.md](WORKFLOWS_AI_ADR.md) | Workflow, AI usage and ADR process |

---

## When to read

- Designing a new capability or ADR
- Resolving “what should we build?” questions
- Before changing public contracts (check binding decisions here, then verify as-is in `reference/`)

Do not use vision docs alone to determine implementation status — check [MODULE_MAP.md](../reference/system/MODULE_MAP.md) and tests.
