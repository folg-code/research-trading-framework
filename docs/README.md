# Documentation

**Start here.** Single index — folder READMEs are catalogs only.

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

### New developer

1. [Developer Guide](onboarding/DEVELOPER_GUIDE.md)
2. [Data Workflows](reference/DATA_WORKFLOWS.md)
3. [Module Map](reference/MODULE_MAP.md)
4. [Current Status](planning/CURRENT_STATUS.md)

### Portfolio / demo showcase

1. Repository [README.md](../README.md) — capabilities, architecture, workflows
2. [scripts/demo/README.md](../scripts/demo/README.md) — generate offline HTML dashboards
3. [DATA_WORKFLOWS.md](reference/DATA_WORKFLOWS.md) §3 — workflow entry points

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
| [MARKET_ANALYSIS_MODULE.md](reference/modules/MARKET_ANALYSIS_MODULE.md) | MA entry points (thin) |

---

## Legend

| Symbol | Meaning |
|--------|---------|
| ✅ | Implemented with tests |
| 🟡 | Partial |
| ⬜ | Skeleton |
