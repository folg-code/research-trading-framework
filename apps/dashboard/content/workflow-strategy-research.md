---
slug: workflow-strategy-research
title: Strategy Research Workflow
status: AS_BUILT
updated: 2026-09-10
order: 18
links: docs/reference/workflows/STRATEGY_RESEARCH.md, docs/reference/workflows/RESEARCH_METHODOLOGIES.md, docs/reference/system/DOMAIN_MODEL.md
---

Strategy Research evaluates a complete trading-system hypothesis under
explicit historical and execution assumptions.

## The composition

```text
Strategy Model = Market Model × Signal Model × Exit Model × Risk Model
```

- **Market** defines when the surrounding context is eligible.
- **Signal** defines the opportunity or entry event.
- **Exit** defines how a position is closed.
- **Risk** defines exposure and position sizing in version 1.

The composition preserves each component identity, definition hash, parameters
and lineage. It is not a monolithic strategy class that also calculates market
analysis, opens files and talks to a broker.

## Why composition matters

Independent components make controlled comparisons possible: hold Market,
Signal and Risk constant while changing Exit, or reuse one Signal definition
across different market contexts. Each part can be tested and versioned on its
own. Research simulation and runtime execution can consume the same definition
without sharing workflow state or implementation classes.

This limits accidental coupling, makes provenance inspectable and exposes
which component changed when two runs differ.

## Workflow and methodology

```text
Published DatasetRef + Strategy Model + simulation assumptions
  → deterministic historical simulation
  → trades, fills, positions, equity and failure states
  → persistent Strategy Research Dataset
  → analytics and reports
```

Profitability, drawdown, exposure and stability are interpreted together; no
single metric decides strategy quality. Unchanged data, component definitions,
assumptions, engine version, configuration and seeds should reuse persisted
computation rather than trigger another backtest.

## Evidence limits

A historical simulation is conditional evidence, not live-trading approval.
Robustness questions and operational risk controls remain separate concerns.
