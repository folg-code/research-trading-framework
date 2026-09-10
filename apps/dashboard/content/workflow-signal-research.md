---
slug: workflow-signal-research
title: Signal Research Workflow
status: AS_BUILT
updated: 2026-09-10
order: 17
links: docs/reference/workflows/SIGNAL_RESEARCH.md, docs/reference/workflows/RESEARCH_METHODOLOGIES.md, docs/reference/system/DOMAIN_MODEL.md
---

Signal Research asks how a market context or signal behaves before the costs
and mechanics of a complete trading system are introduced.

## Research scopes

Each definition declares one scope: a Market Model, a Signal Model, or
Market Model × Signal Model. Exit, risk, position sizing and broker simulation
are deliberately excluded.

Market and Signal Models are declarative compositions over shared Market
Analysis outputs—Features, Structures and States. They do not open storage,
call providers or recalculate their own dependencies.

## Workflow and methodology

```text
Published DatasetRef + model definitions + time assumptions
  → shared dependency plan
  → deterministic occurrence evaluation
  → forward outcomes, MFE and MAE
  → persistent Signal Research Dataset
  → read-only analytics and reports
```

The research question, horizons and bounded experiment space are defined
explicitly. Computation and analytics are separate: a new chart should query
stored observations rather than silently rerun the experiment.

Look-ahead bias is controlled by explicit event availability and forward
outcome boundaries. A model can consume a higher-timeframe fact only after the
source bar closes, and outcome horizons are measured after the occurrence—not
fed back into the condition that selected it.

## Reuse and composition

Signal occurrences and model identities can be reused by Strategy Research,
but this is a contract-based option, not a mandatory pipeline. Signal Research
remains valuable when an idea never becomes a strategy; negative or
inconclusive outcomes stay part of the research record.

## Evidence limits

Forward-return behavior is not evidence that a complete strategy is profitable.
It excludes Exit and Risk Models, trading costs, account state and execution
assumptions by design.
