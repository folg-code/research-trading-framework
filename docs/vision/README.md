# Vision & Assumptions

Principles, target architecture, binding design decisions and future direction.

**These documents describe intent and constraints — not necessarily what is implemented today.**

For what exists in code: [../reference/README.md](../reference/README.md).  
Index: [../README.md](../README.md).

---

## Core Architecture

| File | Purpose |
|------|---------|
| [ARCHITECTURE_FOUNDATIONS_UPDATED.md](ARCHITECTURE_FOUNDATIONS_UPDATED.md) | Domain principles, module boundaries, long-term model |
| [ARCHITECTURE_TECHNICAL_UPDATED.md](ARCHITECTURE_TECHNICAL_UPDATED.md) | Cross-cutting target technical architecture |

---

## Domain Design (binding decisions)

| File | Purpose |
|------|---------|
| [MARKET_ANALYSIS_WITH_DECISIONS.md](MARKET_ANALYSIS_WITH_DECISIONS.md) | Market Analysis decisions D-001–D-036 |
| [ANALYSIS_WORKSPACE_AND_DERIVED_DATA.md](ANALYSIS_WORKSPACE_AND_DERIVED_DATA.md) | Workspace, result store, frames — authoritative on derived data |
| [MULTITIMEFRAME_MARKET_MODEL_ARCHITECTURE_UPDATED.md](MULTITIMEFRAME_MARKET_MODEL_ARCHITECTURE_UPDATED.md) | Multitimeframe market model (future) |

---

## Process

| File | Purpose |
|------|---------|
| [WORKFLOWS_AI_ADR_UPDATED.md](WORKFLOWS_AI_ADR_UPDATED.md) | Workflow, AI usage and ADR process |

---

## When to read

- Designing a new capability or ADR
- Resolving “what should we build?” questions
- Before changing public contracts (check binding decisions here, then verify as-is in `reference/`)

Do not use vision docs alone to determine implementation status — check [MODULE_MAP.md](../reference/MODULE_MAP.md) and tests.
