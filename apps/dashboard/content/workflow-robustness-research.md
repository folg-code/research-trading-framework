---
slug: workflow-robustness-research
title: Robustness Research Workflow
status: AS_BUILT
updated: 2026-09-10
order: 19
links: docs/reference/workflows/RESEARCH_METHODOLOGIES.md, docs/reference/workflows/STRATEGY_RESEARCH.md, docs/reference/system/MODULE_MAP.md
---

Robustness Research asks whether an observed strategy result survives credible
changes in time, parameters, costs and path assumptions.

## Architecture

It consumes explicit Strategy Model identity and research assumptions. It does
not redefine Market, Signal, Exit or Risk components and is not a required
stage before another workflow may run.

## Workflow and methodology

```text
Strategy definition + persisted evidence + robustness specification
  → parameter and neighbouring-variant tests
  → walk-forward and subperiod evaluation
  → cost, fill and missing-trade stress
  → Monte Carlo path analysis
  → persisted robustness artifacts and diagnostics
```

Every method records its assumptions. Walk-forward windows preserve train,
validation and test roles; Monte Carlo methods state what is resampled or
perturbed. Stability is interpreted with sample size, concentration and
execution sensitivity.

## What it protects against

The workflow helps reveal dependence on one exact parameter, a narrow period,
unrealistic costs or a small cluster of trades. It does not convert a weak
result into a good one, and passing one diagnostic is not universal validation.

## Evidence limits

Robustness evidence remains conditional on the selected datasets, models and
assumptions. Cross-asset support requires comparable, published data and does
not imply that all assets have identical market structure.
