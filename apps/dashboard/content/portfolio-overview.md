---
slug: portfolio-overview
title: Portfolio Overview
status: AS_BUILT
updated: 2026-09-11
order: 1
links: apps/dashboard/docs/ARCHITECTURE.md, docs/vision/PRODUCT_DIRECTION.md
---

This dashboard is the public view of a research system built to answer a
general data-engineering question: how do you turn a stream of time-stamped
data into evidence you can actually trust, instead of a black box that just
prints a number? Systematic trading is the domain used to test that —
free, high-quality historical data made it a practical choice — but the
engineering problem underneath (reproducible pipelines, versioned data,
keeping computation separate from presentation) is domain-independent.

The project keeps every stage inspectable instead of hiding it inside one
large class: data preparation, feature computation, research methodology,
simulation assumptions and runtime operation are each owned separately.
That separation means a negative result stays usable evidence instead of
disappearing when it fails to support a hypothesis.

This public dashboard is itself a **read-only** view of persisted research
artifacts and live paper status. It does not run research engines and does
not submit exchange orders.

## How it works under the hood

The system processes provider OHLCV data (open/high/low/close/volume market
bars) through adapters, canonical schemas, validation, immutable versions and
a published `DatasetRef` — a versioned, immutable snapshot identifier,
similar in spirit to a content-addressed build artifact. Market Analysis
then resolves requested Features, Structures and States through a directed
acyclic graph (DAG): dependencies are ordered, equivalent nodes are
deduplicated, and only requested outputs plus their transitive dependencies
are computed.

Temporal correctness is part of the data model. UTC timestamps distinguish
when a fact was observed from when it became available. Backward alignment,
chronological folds, purge/embargo rules (gaps enforced around each
train/test split so future data cannot leak backward) and explicit
simulation timing reduce look-ahead bias — the accidental use of information
that would not yet have existed at the decision time. The architecture also
documents the remaining inference-time availability-enforcement gap instead
of claiming it solved.

Research compute writes structured datasets, trades, predictions, metrics,
diagnostics and provenance. Reports and this dashboard are read-only views of
those artifacts; they do not become a second computation engine.

Six independent workflows share published DatasetRefs, market-analysis
outputs, time rules and declarative model definitions, but each owns its own
computation and evidence. Market Data prepares and publishes inputs; it does
not produce research results. A complete Strategy Model explicitly composes
Market × Signal × Exit × Risk rather than hiding those responsibilities in one
class. This is not one mandatory pipeline. For the full architecture map, see the
[architecture one-pager](https://github.com/folg-code/research-trading-framework/blob/main/apps/dashboard/docs/ARCHITECTURE.md).
Module contracts and setup instructions live in the
[project README on GitHub](https://github.com/folg-code/research-trading-framework).

The featured studies use BTCUSDT.P (a BTC/USDT perpetual futures contract)
because a free public API provides accessible, high-quality historical
OHLCV data. BTC is the asset selected during development because crypto
exchanges — and Binance in particular — offer the most practical free
provider access for this phase. It is not an architectural limit: adapter
and repository patterns allow another provider and asset to use the same
contracts after its data and instrument semantics are normalized and
published as a DatasetRef.
