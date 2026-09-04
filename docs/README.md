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
└── historical/               completed audits, closed investigations
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
| **Data engineer** | [README § For data engineers](../README.md#for-data-engineers) → [MARKET_DATA.md](reference/workflows/MARKET_DATA.md) |
| **Software engineer** | [README § For software engineers](../README.md#for-software-engineers) → [MODULE_MAP.md](reference/system/MODULE_MAP.md) → [adr/](adr/README.md) |
| **New developer** | [Developer Guide](onboarding/DEVELOPER_GUIDE.md) → [MARKET_DATA.md](reference/workflows/MARKET_DATA.md) → [MODULE_MAP.md](reference/system/MODULE_MAP.md) |

### Implementing a change

1. [Current Status](planning/CURRENT_STATUS.md)
2. [Module Map](reference/system/MODULE_MAP.md) — affected packages
3. [Market Data workflow](reference/workflows/MARKET_DATA.md) — if data paths change
4. [Vision](vision/README.md) — binding decisions for the domain
5. `src/` and `tests/`

### AI agent

`AGENTS.md` at repository root.

---

## Reference Trio (update per wave)

| Doc | Owns |
|-----|------|
| [MODULE_MAP.md](reference/system/MODULE_MAP.md) | Packages and status |
| [MARKET_DATA.md](reference/workflows/MARKET_DATA.md) | Data paths and diagrams |
| [RESEARCH_METHODOLOGIES.md](reference/workflows/RESEARCH_METHODOLOGIES.md) | Research workflows — Signal, Model Research, Strategy, Robustness, Predictive |
| [MARKET_ANALYSIS_MODULE.md](reference/modules/MARKET_ANALYSIS_MODULE.md) | MA entry points (thin) |
| [MODEL_AUTHORING.md](reference/modules/MODEL_AUTHORING.md) | Authoring DSL copy-paste example |

---

## Legend

| Symbol | Meaning |
|--------|---------|
| ✅ | Implemented with tests |
| 🟡 | Partial |
| ⬜ | Skeleton |
