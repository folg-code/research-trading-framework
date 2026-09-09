---
slug: portfolio-overview
title: Portfolio Overview
status: AS_BUILT
updated: 2026-09-09
order: 1
links: apps/dashboard/docs/ARCHITECTURE.md, docs/vision/PRODUCT_DIRECTION.md
---

A modular Python framework for market-data processing, declarative market
and signal models, strategy backtesting, robustness analysis, predictive
research, and paper-runtime observability.

This public dashboard is a **read-only** view of persisted research
artifacts and live paper status. It does not run research engines and does
not submit exchange orders.

Six independent workflows below share the same underlying market data,
market analysis and time-model contracts, but each can run on its own —
this is not one mandatory pipeline. For the full architecture map, see the
[architecture one-pager](https://github.com/folg-code/research-trading-framework/blob/main/apps/dashboard/docs/ARCHITECTURE.md).
Module contracts and setup instructions live in the
[project README on GitHub](https://github.com/folg-code/research-trading-framework).
