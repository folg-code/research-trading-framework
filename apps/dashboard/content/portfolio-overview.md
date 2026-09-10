---
slug: portfolio-overview
title: Portfolio Overview
status: AS_BUILT
updated: 2026-09-10
order: 1
links: apps/dashboard/docs/ARCHITECTURE.md, docs/vision/PRODUCT_DIRECTION.md
---

A modular Python framework for market-data processing, declarative market
and signal models, strategy backtesting, robustness analysis, predictive
research, and paper-runtime observability.

The project exists to make trading research inspectable rather than hide it
inside a monolithic strategy class. Data preparation, analytical components,
research methods, simulation assumptions and runtime operation have separate
owners. That separation makes a negative result reusable evidence instead of
an experiment that disappears when it fails to support a hypothesis.

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
accessible, high-quality historical OHLCV. BTC is an evidence choice, not an
architectural limit: any asset can use the same research contracts after its
data and instrument semantics are normalized and published as a DatasetRef.
