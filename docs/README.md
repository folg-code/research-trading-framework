# Documentation

Start here to understand the framework from product intent through system architecture, module ownership and implementation details. The same route serves a new developer and an agent; open deeper pages only for the topic at hand.

## Learn the system

1. [System Overview](reference/system/SYSTEM_OVERVIEW.md) — what the system does and how the major parts interact.
2. [Module Map](reference/system/MODULE_MAP.md) — which package owns each responsibility.
3. [Dependency Rules](reference/system/DEPENDENCY_RULES.md) — allowed directions and test-enforced boundaries.
4. [Module guides](reference/modules/README.md) — package entry points and detailed contracts.
5. [Workflows](reference/workflows/README.md) — end-to-end data, research and execution paths.

## Work on a change

Read [Current Status](planning/CURRENT_STATUS.md) and the active task, then open the affected module guide, workflow and ADR. Verify the concrete contracts in `src/` and `tests/`. For future capabilities, start at [Vision](vision/README.md) and [Roadmap](planning/ROADMAP.md) instead of inferring implementation from proposals.

## Documentation layers

| Layer | Purpose | What it can prove |
|---|---|---|
| [Reference](reference/README.md) | Current system, modules, workflows, runbooks and examples | What is implemented, subject to code and tests |
| [Vision](vision/README.md) | Future product and architecture directions | Intent, not implementation |
| [Planning](planning/README.md) | Current status, active work, roadmap and open registries | What is planned or in progress |
| [Product](product/) | PRDs and product requirements | Accepted requirement context |
| [ADRs](adr/README.md) | Durable decisions and their rationale | Why a decision was made |
| [Archive](archive/README.md) | Completed sprints, audits and superseded material | Historical evidence at the recorded time |
| [Onboarding](onboarding/DEVELOPER_GUIDE.md) | Setup and development checks | How to work locally |

`reference/` is organized by system view, capability-oriented module guides, workflows and operational runbooks. It follows source-code ownership without mirroring every source directory. Long historical records remain in the archive and are not part of the normal reading path.

## Maintenance

Each fact should have one current owner. Update the relevant module/workflow page and [Module Map](reference/system/MODULE_MAP.md) when paths or responsibilities change; update [System Overview](reference/system/SYSTEM_OVERVIEW.md) when the system-level story changes. Move a delivered future capability from Vision into Reference after verifying its current contract. Keep decision rationale in ADRs and completed task evidence in the Archive.
