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

## Provider-neutral data infrastructure

Market Data has one job: turn external market facts into validated,
versioned inputs. Provider-specific APIs, archives and field mappings are
isolated behind adapters. CSV, Databento and Binance historical imports are
the current implementations; another OHLCV provider can be integrated without
changing research logic as long as its adapter produces the canonical market
contracts.

```text
OHLCV provider or file
  → provider adapter
  → normalize, validate, finalize and version
  → published DatasetRef
```

That final `DatasetRef` is the shared data identity used by research
consumers. Market Data ends there. It never produces a research result,
verdict, equity curve or strategy ranking.

## Shared foundation

- **Market data contracts** remove provider-specific formats before research.
- **Market Analysis** computes reusable Features, Structures and States through
  an explicit dependency graph.
- **The Time model** keeps UTC and availability semantics visible.
- **Declarative models** describe conditions and composition without opening
  storage or calling providers.

## Strategy composition

```text
Strategy Model = Market Model × Signal Model × Exit Model × Risk Model
```

Market defines eligible context, Signal defines the opportunity, Exit defines
how a position closes, and Risk defines exposure and sizing in version 1.
Their identities and definition hashes remain visible inside the composed
Strategy Model.

This design makes components independently replaceable and testable. A study
can compare two exits while holding Market, Signal and Risk constant, or reuse
one Signal Model across several market contexts. It also lets Strategy
Research and Strategy Execution consume the same definition without sharing
research state. The result is more precise provenance and fewer accidental
changes than a monolithic strategy class containing data access, analysis,
entry, exit, sizing and broker behavior.

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

The public BTC studies reflect data availability, not an asset boundary.
BTCUSDT.P was selected because high-quality historical OHLCV is accessible
through a free public API. The same contracts can analyze another asset once
its provider and instrument semantics are normalized into a validated,
published DatasetRef.

The deepest contracts remain in the repository's
[system overview](https://github.com/folg-code/research-trading-framework/blob/main/docs/reference/system/SYSTEM_OVERVIEW.md)
and [module map](https://github.com/folg-code/research-trading-framework/blob/main/docs/reference/system/MODULE_MAP.md).
