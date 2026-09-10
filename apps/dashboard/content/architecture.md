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

## Module contracts: consume, process, produce

### Provider adapters

**Consume:** an external API, vendor archive or file schema. **Process:**
pagination/file decoding, provider mapping and rate-limit/error behavior.
**Produce:** canonical bars or trades. Provider objects stop here, so adding a
new vendor does not rewrite research code.

### Market Data

**Consume:** canonical provider records and dataset metadata. **Process:**
normalization, validation, partitioning, checksum, versioning and publication.
**Produce:** immutable market facts plus a published `DatasetRef`. It produces
research inputs, never research conclusions.

### Market Analysis engine

**Consume:** a DatasetRef, a requested set of Features, Structures or States,
parameters, time range and timeframe/alignment policy. **Process:** resolve
component requests into a directed acyclic graph, reject cycles, calculate
dependencies in topological order, deduplicate equivalent nodes, cache by full
computation identity and align higher-timeframe outputs backward from their
legal `available_at`. **Produce:** typed analysis outputs with lineage.

The DAG is both a correctness and performance design: ATR requested by three
models is one deterministic node, not three hidden calculations, while an
unrelated component is not executed. A cache key includes the dataset version,
parameters and material time semantics, preventing reuse across incompatible
computations.

### Time and alignment

**Consume:** UTC observations, bar intervals and availability metadata.
**Process:** distinguish `observed_at` from `available_at`, explicit resampling
and backward as-of alignment. **Produce:** causally aligned inputs. This is the
primary defense against look-ahead bias in multitimeframe computation.
Chronological predictive folds add purge and embargo around label horizons.
One limitation remains explicit: batch alignment honors `available_at`, while
general inference-time rejection is not yet enforced by the executor.

### Model definitions

**Consume:** controlled Market Analysis outputs and logical conditions.
**Process:** evaluate declarative Market and Signal contexts, plus contract-based
Exit and Risk behavior. **Produce:** versioned component/model identities and a
composed Strategy Model. Models never open provider connections or arbitrary
DataFrames.

### Research compute

**Consume:** published data identities, model definitions, time ranges and a
bounded methodology specification. **Process:** deterministic occurrence
analysis, simulation, robustness testing or leakage-aware predictive training.
**Produce:** workflow-owned datasets, manifests, predictions, trades, metrics,
diagnostics and verdicts.

### Historical simulator / backtester

**Consume:** a complete Strategy Model, canonical bars, signal occurrences and
explicit commission, slippage, latency, fill and capital assumptions.
**Process:** compile aligned bars/signals into deterministic arrays, simulate
orders, fills, positions, cash and exits using optimized kernels, and preserve
failure states. **Produce:** a Strategy Research Dataset with individual trades,
orders/fills, equity and return series—not only aggregate KPIs. The simulator
consumes strategy definitions; it does not define or promote them.

### Persistence and provenance

**Consume:** workflow computations and material identities. **Process:** write
versioned manifests and structured Parquet/JSON artifacts. **Produce:** a
reusable research record that analytics can query without recomputation.

### Dashboard and publication

**Consume:** persisted artifacts or a deny-by-default sanitized projection.
**Process:** read-only selection, comparison and visualization. **Produce:**
human-facing explanations and charts, never a new research fact or verdict.

### Strategy Execution

**Consume:** a selected Strategy Model, normalized runtime data, account state
and operational limits. **Process:** deterministic decisions and safety checks.
**Produce:** simulated orders, fills, positions and status in `DRY_RUN` today.
It does not consume research rankings and cannot be controlled by this public UI.

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

The same boundaries were chosen with future ML/AI work in mind. A promoted ML
artifact can eventually occupy a controlled Market Analysis State or score
condition while preserving feature lineage, `available_at`, artifact identity
and offline/runtime parity. Strategies therefore do not need a separate “AI
strategy” architecture. Today, linear/logistic score gates have a bounded
promotion path; tree and neural strategy gates remain research-only until the
documented promotion conditions are implemented. Future AI agents may propose
components and experiments, but deterministic contracts still execute them.

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
