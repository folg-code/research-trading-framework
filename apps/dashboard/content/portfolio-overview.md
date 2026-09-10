---
slug: portfolio-overview
title: Portfolio Overview
status: AS_BUILT
updated: 2026-09-10
order: 1
links: apps/dashboard/docs/ARCHITECTURE.md, docs/vision/PRODUCT_DIRECTION.md
---

A modular Python research system for building reproducible data pipelines,
dependency-aware analytical features, declarative models, historical
simulations, robustness experiments and machine-learning studies. Systematic
trading is the application domain; the engineering problem is how to turn
time-indexed data into inspectable evidence without mixing ingestion,
computation, methodology and presentation.

The project exists to make trading research inspectable rather than hide it
inside a monolithic strategy class. Data preparation, analytical components,
research methods, simulation assumptions and runtime operation have separate
owners. That separation makes a negative result reusable evidence instead of
an experiment that disappears when it fails to support a hypothesis.

## From raw observations to evidence

The system processes provider OHLCV through adapters, canonical schemas,
validation, immutable versions and a published `DatasetRef`. Market Analysis
then resolves requested Features, Structures and States through a directed
acyclic graph (DAG): dependencies are ordered, equivalent nodes are
deduplicated, and only requested outputs plus their transitive dependencies
are computed.

Temporal correctness is part of the data model. UTC timestamps distinguish
when a fact was observed from when it became available. Backward alignment,
chronological folds, purge/embargo rules and explicit simulation timing reduce
look-ahead bias—the accidental use of information that would not yet have
existed at the decision time. The architecture also documents the remaining
inference-time availability-enforcement gap instead of claiming it solved.

Research compute writes structured datasets, trades, predictions, metrics,
diagnostics and provenance. Reports and this dashboard are read-only views of
those artifacts; they do not become a second computation engine.

This public dashboard is a **read-only** view of persisted research
artifacts and live paper status. It does not run research engines and does
not submit exchange orders.

Six independent workflows below share published DatasetRefs, market-analysis
outputs, time rules and declarative model definitions, but each owns its own
computation and evidence. Market Data prepares and publishes inputs; it does
not produce research results. A complete Strategy Model explicitly composes
Market × Signal × Exit × Risk rather than hiding those responsibilities in one
class. This is not one mandatory pipeline. For the full architecture map, see the
[architecture one-pager](https://github.com/folg-code/research-trading-framework/blob/main/apps/dashboard/docs/ARCHITECTURE.md).
Module contracts and setup instructions live in the
[project README on GitHub](https://github.com/folg-code/research-trading-framework).

The featured studies use BTCUSDT.P because a free public API provides
accessible, high-quality historical OHLCV. BTC is the asset selected during
development because crypto exchanges—and Binance in particular—offer the most
practical free provider access for this phase. It is not an architectural
limit: adapter and repository patterns allow another provider and asset to use
the same contracts after its data and instrument semantics are normalized and
published as a DatasetRef.
