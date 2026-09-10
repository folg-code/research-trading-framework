---
slug: workflow-predictive-research
title: Predictive Research Workflow
status: AS_BUILT
updated: 2026-09-10
order: 20
links: docs/reference/workflows/RESEARCH_METHODOLOGIES.md, docs/adr/ADR-0023-predictive-research-boundary.md, docs/adr/ADR-0024-machine-learned-state-promotion.md, docs/reference/PREDICTIVE_VERDICT.md
---

Predictive Research tests whether selected Market Analysis columns contain
out-of-sample information about a defined future outcome. It is research, not
a trading strategy or an automatic model-promotion mechanism.

## Architecture

A study specification references a published `DatasetRef`, feature lineage,
target definition, time range and chronological fold policy. Those inputs form
a deterministic dataset fingerprint. Training libraries remain behind adapters;
durable evidence is predictions and metrics, not a fitted binary.

## Workflow and methodology

```text
DatasetRef + feature lineage + target + temporal folds
  → leakage-aware Predictive Dataset
  → baselines and bounded model families
  → out-of-sample predictions
  → metrics, diagnostics and persisted verdict
  → read-only comparison and report
```

Purged and embargoed rows retain explicit roles. Results are compared with
simple baselines and interpreted across folds, sample sizes, calibration and
train–test gaps. The dashboard displays the persisted verdict; it does not
derive a new one from a chart.

## Relationship to other workflows

Predictive Research reuses DatasetRef and Market Analysis identities, but does
not require a Signal or Strategy Research run. A predictive finding may inform
a later hypothesis only through an explicit decision and a shared definition;
it cannot promote itself into execution.

## Evidence limits

Predictive lift is not profitability. Costs, exits, risk, capacity and runtime
behavior belong to other questions and must not be inferred from this workflow.
