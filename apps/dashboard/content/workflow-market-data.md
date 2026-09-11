---
slug: workflow-market-data
title: Market Data Workflow
status: AS_BUILT
updated: 2026-09-10
order: 16
links: docs/reference/workflows/MARKET_DATA.md, docs/adr/ADR-0007-dataset-lifecycle-and-publication.md, docs/adr/ADR-0008-parquet-historical-storage.md, docs/adr/ADR-0025-binance-usdm-historical-klines-import.md
---

Market Data prepares trustworthy inputs. It does **not** test hypotheses,
simulate strategies or produce research results.

## Architecture

Provider-specific code stops at an adapter boundary. CSV files, Databento
archives and the Binance historical REST API are the current import paths;
another OHLCV source can be added behind the same boundary without changing
research consumers. This is an extensibility contract, not a claim that every
provider already has an adapter.

All paths converge on canonical market-bar contracts. Provider SDK objects,
field names and pagination rules do not enter domain or research logic.

## Workflow

```text
OHLCV source
  → provider or file adapter
  → canonical normalization
  → validation
  → partition finalization
  → version and checksum
  → published DatasetRef
```

Finalization and publication are separate, recorded transitions. A published
version is immutable. Gaps and provenance remain visible rather than being
silently repaired.

## Shared input, separate outcomes

`DatasetRef` is the stable identity through which research and replay resolve
market data. Signal, Strategy and Predictive Research can reuse that identity;
runtime consumers use the same normalized market concepts. Each consumer still
owns its computation and persisted output. Market Data ends at the published
dataset boundary.

## Asset scope

The architecture is not tied to BTC or crypto. BTC is the development asset
because crypto exchanges—and Binance in particular—provide unusually
accessible, high-quality historical OHLCV through a free API. Futures, forex,
equities, indices, commodities or other crypto assets can follow the same
contracts once a suitable adapter maps their data and identity into a validated,
published DatasetRef.

## Methodological limits

A common schema does not make providers economically or statistically
equivalent. Session rules, contract identity, corporate actions, roll policy,
timestamp semantics and source quality remain explicit dataset concerns.
