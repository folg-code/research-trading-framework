# Documentation

**Start here.** Single index — folder READMEs are catalogs only.

For a **role-based entry point** (recruiter, data engineer, software engineer, new developer), see the table at the top of the repository **[README.md](../README.md#start-here--pick-your-path)**.

---

## Folder Layout

```text
docs/
├── README.md                 ← you are here
├── onboarding/
│   └── DEVELOPER_GUIDE.md    setup: install, quality checks, repo layout
├── vision/                   assumptions, target architecture, binding decisions
├── reference/                as-implemented: module map, flows, module docs
│   └── modules/
├── planning/                 roadmap, status, sprints
├── adr/                      decision records (why)
├── agents/                   AI agent module notes
└── architecture/README.md    redirect (legacy path)
```

---

## Two Layers (important)

| Layer | Folder | Answers | Trust for “is it built?” |
|-------|--------|---------|--------------------------|
| **Vision** | [vision/](vision/README.md) | What we assume, target design, binding decisions | No — may include future work |
| **Reference** | [reference/](reference/README.md) | What exists in code, how data moves | **Yes** — with tests |

Planning ([planning/](planning/README.md)) defines **what we intend to build next**.  
ADRs ([adr/](adr/README.md)) freeze **why** durable choices were made.

Maintenance: `.cursor/rules/documentation.mdc`

---

## Reading Paths

| Role | Path |
|------|------|
| **Recruiter / hiring manager** | [README § In 60 seconds](../README.md#in-60-seconds) → [Scale & performance](../README.md#scale--performance-reference-run) → [Portfolio demo](../README.md#portfolio-demo-try-it-in-the-browser) |
| **Data engineer** | [README § For data engineers](../README.md#for-data-engineers) → [DATA_WORKFLOWS.md](reference/DATA_WORKFLOWS.md) §1.1 → [DATA_MODULE_UPDATED.md](reference/modules/DATA_MODULE_UPDATED.md) |
| **Software engineer** | [README § For software engineers](../README.md#for-software-engineers) → [MODULE_MAP.md](reference/MODULE_MAP.md) → [adr/](adr/README.md) |
| **New developer** | [Developer Guide](onboarding/DEVELOPER_GUIDE.md) → [DATA_WORKFLOWS.md](reference/DATA_WORKFLOWS.md) → [MODULE_MAP.md](reference/MODULE_MAP.md) |

### Implementing a change

1. [Current Status](planning/CURRENT_STATUS.md)
2. [Module Map](reference/MODULE_MAP.md) — affected packages
3. [Data Workflows](reference/DATA_WORKFLOWS.md) — if data paths change
4. [Vision](vision/README.md) — binding decisions for the domain
5. `src/` and `tests/`

### AI agent

`AGENTS.md` at repository root.

---

## Reference Trio (update per wave)

| Doc | Owns |
|-----|------|
| [MODULE_MAP.md](reference/MODULE_MAP.md) | Packages and status |
| [DATA_WORKFLOWS.md](reference/DATA_WORKFLOWS.md) | Data paths and diagrams |
| [RESEARCH_METHODOLOGIES.md](reference/RESEARCH_METHODOLOGIES.md) | Research workflows — Signal, Model Research, Strategy, Robustness |
| [MARKET_ANALYSIS_MODULE.md](reference/modules/MARKET_ANALYSIS_MODULE.md) | MA entry points (thin) |

---

## Legend

| Symbol | Meaning |
|--------|---------|
| ✅ | Implemented with tests |
| 🟡 | Partial |
| ⬜ | Skeleton |
