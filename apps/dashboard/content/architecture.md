---
slug: architecture
title: Architecture
status: AS_BUILT
updated: 2026-09-10
order: 10
links: docs/vision/PRODUCT_DIRECTION.md, docs/reference/system/SYSTEM_OVERVIEW.md, docs/reference/system/MODULE_MAP.md, docs/adr/ADR-0022-repository-top-level-layout.md
---

The framework is a modular monolith with deliberately separate workflows.
They share stable concepts—market facts, DatasetRef identities, time rules,
Market Analysis outputs and declarative model definitions—but do not share a
mandatory workflow state.

## Shared foundation

- **Market data contracts** remove provider-specific formats before research.
- **Market Analysis** computes reusable Features, Structures and States through
  an explicit dependency graph.
- **The Time model** keeps UTC and availability semantics visible.
- **Declarative models** describe conditions and composition without opening
  storage or calling providers.

Signal Research can inspect occurrences without a Strategy Research run.
Strategy Research can simulate a complete model without a prior Signal
Research dataset. Robustness and Predictive Research own different questions
and artifacts. Strategy Execution consumes selected definitions without
loading rankings, notebooks or research reports.

## Ownership boundaries

Reusable framework behavior lives under `src/trading_framework/`. Private
datasets, configurations, user models and run artifacts belong under
`user_data/`; framework packages do not import that workspace. This is an
ownership and dependency boundary, not a claim that local files are a security
sandbox.

Deployable applications form another boundary. The public Streamlit dashboard
is a read-only consumer. It does not import research engines, start jobs,
submit orders or become the owner of research truth.

## Evidence flow

Each workflow persists its own identity and evidence. Dataset checksums,
definition hashes, configuration or assumption fingerprints, explicit seeds
and workflow-specific manifests make material inputs inspectable. Analytics
and presentation read those artifacts after computation, so a new chart does
not silently become a new experiment.

The deepest contracts remain in the repository's
[system overview](https://github.com/folg-code/research-trading-framework/blob/main/docs/reference/system/SYSTEM_OVERVIEW.md)
and [module map](https://github.com/folg-code/research-trading-framework/blob/main/docs/reference/system/MODULE_MAP.md).
