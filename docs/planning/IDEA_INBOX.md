# Trading Research Framework

# IDEA_INBOX.md

## 1. Purpose

This file stores unvalidated ideas for the Trading Research Framework.

An idea is not:

- an approved feature,
- a backlog task,
- an architectural decision,
- a commitment to implement,
- a current priority.

Ideas may be valuable, but they must not enter implementation automatically.

Before promotion, an idea should be assessed for:

- value,
- fit with the project vision,
- current necessity,
- architectural impact,
- dependency impact,
- implementation and operational cost,
- alternatives,
- evidence.

---

## 2. Statuses

```text
INBOX
UNDER_REVIEW
PROMOTED
DEFERRED
REJECTED
```

---

## 3. Idea Entry Template

```markdown
## IDEA-XXX — Title

Status:
Category:
Added:
Owner:

### Summary

...

### Potential Value

...

### Main Questions

- ...

### Dependencies

- ...

### Risks

- ...

### Promotion Criteria

- ...
```

---

# 4. Architecture and Developer Experience

## IDEA-001 — Visual Dependency Graph Explorer

```text
Status: INBOX
Category: Developer Experience
Added: 2026-06-19
```

### Summary

Provide a visual representation of:

- Market Analysis dependencies,
- model expression trees,
- reused nodes,
- cache hits,
- execution order.

### Potential Value

Could make large analytical compositions easier to understand and debug.

### Main Questions

- Is textual graph inspection sufficient initially?
- Should this be a CLI, notebook view or web UI?
- Can visualization remain independent from engine semantics?

### Dependencies

- stable dependency graph,
- stable node identity,
- result lineage.

### Promotion Criteria

Promote only after real graphs become difficult to inspect using text output.

---

## IDEA-002 — Remote Component Registry

```text
Status: DEFERRED
Category: Architecture
Added: 2026-06-19
```

### Summary

Distribute framework or private component packages through a remote registry.

### Potential Value

Could support multiple machines, teams and controlled component releases.

### Main Questions

- Is a Python package index sufficient?
- How would private components be authenticated?
- How are compatibility and signatures verified?

### Dependencies

- mature local component lifecycle,
- stable component manifest,
- multiple independent environments.

### Promotion Criteria

A demonstrated need to share versioned components across machines or teams.

---

## IDEA-003 — Dedicated Feature Store

```text
Status: DEFERRED
Category: Data / Market Analysis
Added: 2026-06-19
```

### Summary

Introduce a dedicated offline/online store for Market Analysis results.

### Potential Value

Could support large-scale reuse across Research and Strategy Execution.

### Main Questions

- Are Parquet and local caches insufficient?
- Is online/offline consistency a demonstrated problem?
- What operational cost is acceptable?

### Dependencies

- significant repeated feature reuse,
- live runtime requirements,
- measured storage/query bottlenecks.

### Promotion Criteria

Local cache and Parquet architecture demonstrably fail required scale or parity.

---

## IDEA-004 — Declarative Workflow Graph Editor

```text
Status: DEFERRED
Category: Developer Experience
Added: 2026-06-19
```

### Summary

Create a visual editor for Research or Strategy Execution workflow configuration.

### Potential Value

Could lower configuration complexity for non-code users.

### Risks

May incorrectly imply that workflows and domains are arbitrary graph nodes.

### Promotion Criteria

Stable configuration schemas and demonstrated user need.

---

# 5. Market Data

## IDEA-005 — Databento DBN Importer

```text
Status: INBOX → candidate for Sprint 011 (Phase 2B)
Category: Market Data
Added: 2026-06-19
Last reviewed: 2026-07-12
```

### Summary

Import Databento DBN archives through provider-independent archive import contracts. First slice: **DBN OHLCV → canonical MarketBar** (Phase 2B). Later: trades (**Phase 2C.1**).

### Potential Value

High-quality futures data and efficient archive ingestion; validates archive workflow before new fact models.

### Dependencies

- Phase 2A lifecycle and repository (COMPLETE),
- import inspection and manifest,
- schema mapping to canonical models,
- partitioned Parquet persistence.

### Promotion Criteria

Promote as Sprint 011 when Roadmap Revision / Phase Entry Review is complete. See `ROADMAP.md` §6, §15.4 and `SPRINT_011.md`.

---

## IDEA-006 — Historical Provider Synchronization

```text
Status: INBOX
Category: Market Data
Added: 2026-06-19
```

### Summary

Resolve local coverage and fetch only missing historical ranges.

### Potential Value

Automates dataset preparation while preserving explicit policies.

### Dependencies

- dataset registry,
- missing-range calculator,
- Trading Calendar,
- provider adapter.

### Promotion Criteria

Phase 2A (OHLCV MVP) completed; archive import foundation (2B) or provider sync may follow per `ROADMAP.md` §6.

---

## IDEA-007 — Continuous Futures Builder

```text
Status: PROMOTED → Sprint 015
Category: Market Data
Added: 2026-06-19
Promoted: 2026-07-14
```

### Summary

Build continuous futures datasets from explicit contract datasets.

Sprint 015 (`SPRINT_015.md`, ADR-0018 ACCEPTED) delivers four-layer materialization:
raw DBN → contract datasets → roll schedule → continuous trades + derived OHLCV.

### Potential Value

Supports long-term NQ, ES and other futures research.

### Main Questions

- calendar, volume or open-interest roll — **MVP: volume @ RTH close**
- adjusted or unadjusted series — **MVP: unadjusted trades; back-adjust deferred**
- Research use by purpose — **continuous for long backtests; contract datasets for roll validation**

### Dependencies

- contract metadata,
- contract dataset identity,
- roll policies,
- derived dataset lineage.

### Promotion Criteria

Contract-level futures datasets are stable. — **Sprint 011 trades import on main satisfies input path; Sprint 015 extends to multi-contract materialization.**

---

## IDEA-008 — Data Quality Dashboard

```text
Status: INBOX
Category: Market Data / Observability
Added: 2026-06-19
```

### Summary

Visualize:

- coverage,
- gaps,
- duplicate counts,
- validation status,
- partition health,
- dataset versions.

### Promotion Criteria

Dataset registry and validation reports produce stable metadata.

---

## IDEA-009 — Automated Partition Compaction Policy

```text
Status: INBOX
Category: Storage
Added: 2026-06-19
```

### Summary

Select and execute compaction based on small-file count, size and partition age.

### Promotion Criteria

Live or incremental ingestion produces a demonstrated small-file problem.

---

# 6. Market Analysis

## IDEA-010 — Component Scaffolding CLI

```text
Status: INBOX
Category: Developer Experience
Added: 2026-06-19
```

### Summary

Generate a local working component structure with:

- component file,
- tests,
- manifest,
- notes,
- example configuration.

### Potential Value

Encourages consistent local component development.

### Promotion Criteria

The component contract and local directory pattern are stable.

---

## IDEA-011 — Automatic Candidate Promotion Report

```text
Status: INBOX
Category: Governance / Market Analysis
Added: 2026-06-19
```

### Summary

Evaluate whether a local component meets candidate or framework-promotion criteria.

Possible checks:

- tests,
- documentation,
- strategy independence,
- stable output schema,
- dependency declaration,
- proprietary thresholds,
- compatibility readiness.

### Important Rule

The tool may recommend promotion.

It must never promote automatically.

---

## IDEA-012 — Order-Flow Component Pack

```text
Status: DEFERRED
Category: Market Analysis
Added: 2026-06-19
```

### Summary

Add reusable components for:

- volume delta,
- imbalance,
- footprint structures,
- absorption,
- DOM-derived states.

### Dependencies

- tick/trade/quote data models,
- high-volume storage,
- order-flow dataset contracts.

### Promotion Criteria

Market Data support for required source facts is stable.

---

## IDEA-013 — Options-Derived Context Components

```text
Status: DEFERRED
Category: Market Analysis
Added: 2026-06-19
```

### Summary

Support Features and States derived from:

- gamma exposure,
- zero gamma,
- options positioning,
- implied volatility structures.

### Dependencies

- OptionsSnapshot model,
- provider data,
- timestamp and availability semantics.

---

## IDEA-014 — Machine-Learned State Classifiers

```text
Status: DEFERRED
Category: Market Analysis / ML
Added: 2026-06-19
```

### Summary

Allow trained statistical or ML models to produce Market Analysis States.

### Main Questions

- training artifact identity,
- data leakage,
- feature lineage,
- offline/online parity,
- model registry.

### Promotion Criteria

Rule-based Market Analysis and Research infrastructure are mature.

---

# 7. Research

## IDEA-015 — Research Preflight Cost Estimator

```text
Status: INBOX
Category: Research
Added: 2026-06-19
```

### Summary

Estimate before execution:

- candidate count,
- unique dependency count,
- reused nodes,
- expected storage,
- approximate memory and runtime class.

### Potential Value

Prevents accidental large experiment expansion.

### Dependencies

- stable planner,
- node identities,
- measured component costs.

---

## IDEA-016 — Pareto Frontier Candidate Explorer

```text
Status: INBOX
Category: Research Analytics
Added: 2026-06-19
```

### Summary

Compare candidates across:

- expectancy,
- drawdown,
- stability,
- sample size,
- complexity,
- cross-asset consistency.

### Promotion Criteria

Strategy Research metrics and persistent datasets are stable.

---

## IDEA-017 — Automated Family Discovery

```text
Status: DEFERRED
Category: Research Analytics
Added: 2026-06-19
```

### Summary

Group nearby Market or Strategy Model variants automatically.

### Main Questions

- semantic versus parameter distance,
- stable family identifiers,
- explainability.

### Promotion Criteria

Manual family definitions become a demonstrated bottleneck.

---

## IDEA-018 — Research Insight Generator

```text
Status: DEFERRED
Category: AI / Research
Added: 2026-06-19
```

### Summary

Generate structured summaries of:

- stable effects,
- weak samples,
- contradictory assets,
- sensitivity regions,
- potential follow-up hypotheses.

### Important Rule

Generated insights must remain interpretations of stored facts.

They must not mutate Research Datasets or declare a strategy validated automatically.

---

## IDEA-019 — Distributed Research Workers

```text
Status: DEFERRED
Category: Infrastructure
Added: 2026-06-19
```

### Summary

Distribute independent research workloads across machines.

### Dependencies

- stable local execution,
- task identity,
- deterministic artifacts,
- measurable single-machine bottleneck.

### Promotion Criteria

One machine repeatedly fails required throughput or memory constraints.

---

# 8. Strategy Execution

## IDEA-020 — Unified Replay/Paper/Live Strategy Runtime

```text
Status: INBOX
Category: Strategy Execution
Added: 2026-06-19
```

### Summary

Use one runtime contract with mode-specific market feeds and broker adapters.

### Potential Value

Improves parity and reduces duplicated strategy logic.

### Risks

May create a god-object runtime if boundaries are not explicit.

### Promotion Criteria

Strategy Model and Execution contracts are stable.

---

## IDEA-021 — Multi-Account Execution Coordinator

```text
Status: DEFERRED
Category: Strategy Execution
Added: 2026-06-19
```

### Summary

Coordinate one or more Strategy Models across multiple broker or prop-firm accounts.

### Dependencies

- reliable single-account execution,
- account isolation,
- reconciliation,
- allocation policies,
- operational monitoring.

### Promotion Criteria

Single-account live execution is validated.

---

## IDEA-022 — Operational Risk Policy Engine

```text
Status: INBOX
Category: Strategy Execution
Added: 2026-06-19
```

### Summary

Configure reusable operational controls such as:

- daily loss limit,
- account drawdown,
- duplicate-order prevention,
- stale-data protection,
- connection-health rules,
- kill switch.

### Important Rule

This remains separate from the Strategy Domain Risk Model.

---

## IDEA-023 — Execution Incident Timeline

```text
Status: INBOX
Category: Observability
Added: 2026-06-19
```

### Summary

Create an audit view combining:

- market events,
- strategy decisions,
- risk decisions,
- commands,
- broker acknowledgements,
- fills,
- reconciliation incidents.

### Promotion Criteria

Execution event and persistence contracts are stable.

---

# 9. Infrastructure and Interfaces

## IDEA-024 — Web Research Dashboard

```text
Status: DEFERRED
Category: Interface
Added: 2026-06-19
```

### Summary

Browse datasets, runs, rankings, families and reports through a web UI.

### Promotion Criteria

CLI and stored schemas become stable enough to avoid UI-driven domain design.

---

## IDEA-025 — Notebook Helper Package

```text
Status: INBOX
Category: Developer Experience
Added: 2026-06-19
```

### Summary

Provide safe notebook helpers for querying published datasets and Research Datasets.

### Important Rule

Reusable business logic must not remain only in notebooks.

---

## IDEA-026 — Local Research API

```text
Status: DEFERRED
Category: Interface
Added: 2026-06-19
```

### Summary

Expose framework capabilities through a local REST or WebSocket API.

### Promotion Criteria

A concrete external consumer requires it.

The domain must remain independent from FastAPI or another web framework.

---

# 10. Rejected Ideas

No ideas have yet been formally rejected.

A rejected idea should remain recorded with:

- rejection reason,
- date,
- evidence,
- conditions under which it may be reconsidered.
