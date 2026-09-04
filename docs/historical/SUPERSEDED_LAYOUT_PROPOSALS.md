# Superseded Layout Proposals

> **Eviction record, not active guidance.** This file collects
> `docs/vision/` sections evicted by Sprint 055 T008 because they describe a
> module/`user_data/` directory layout that was never built and is not
> planned — self-annotated by their own source documents as superseded by
> [`docs/reference/system/MODULE_MAP.md`](../reference/system/MODULE_MAP.md).
> They are neither current (reference tier) nor intended (vision tier), so
> per Sprint 055 T004's decision they are preserved here rather than
> deleted (git history would have preserved them either way, but a
> discoverable landing spot is more useful than an archaeology session).
> Content is verbatim from the originating files; only this header and the
> per-block provenance notes are newly authored.

---

## 1. From `ARCHITECTURE_TECHNICAL.md` §10 — Module Structure

*(§10.1 High-Level Layout and §10.13 Application Module were classified
CURRENT and moved to
[`docs/reference/system/ARCHITECTURE_TECHNICAL.md`](../reference/system/ARCHITECTURE_TECHNICAL.md#module-structure)
before this eviction — not duplicated here.)*

### 10.2 Source Package

```text
src/
└── trading_framework/
    ├── core/
    ├── time/
    ├── market/
    ├── market_analysis/
    ├── strategy/
    ├── research/
    ├── execution/
    ├── events/
    ├── config/
    ├── infrastructure/
    ├── application/
    └── api/
```

### 10.3 Core Module

```text
src/trading_framework/core/
├── types/
├── enums/
├── identifiers/
├── protocols/
├── exceptions/
└── result/
```

The Core module contains only stable shared primitives. It must not become a generic utilities dumping ground.

### 10.4 Time Module

```text
src/trading_framework/time/
├── models/
├── calendars/
├── sessions/
├── clocks/
├── rolls/
└── protocols.py
```

### 10.5 Market Module

```text
src/trading_framework/market/
├── models/
├── datasets/
├── requests/
├── providers/
├── importers/
├── normalization/
├── validation/
├── repositories/
└── services/
```

Concrete providers and storage implementations belong to Infrastructure.

### 10.6 Market Analysis Module

Initial minimal structure:

```text
src/trading_framework/market_analysis/
├── components/
├── engine/
├── models/
└── protocols.py
```

Possible later structure:

```text
src/trading_framework/market_analysis/
├── features/
├── structures/
├── states/
├── engine/
├── graph/
├── registry/
├── cache/
├── alignment/
├── models/
└── protocols.py
```

The conceptual taxonomy is stable even if the folder hierarchy evolves.

### 10.7 Strategy Module

```text
src/trading_framework/strategy/
├── signal_models/
├── market_models/
├── exit_models/
├── risk_models/
├── strategy_models/
├── expressions/
├── occurrences/
├── models/
└── protocols.py
```

The module contains contracts, neutral generic implementations, expression evaluation, Strategy Domain value objects. Proprietary compositions belong to `user_data/`.

### 10.8 Research Module

```text
src/trading_framework/research/
├── signal_research/
├── strategy_research/
├── datasets/
├── simulation/
├── analytics/
├── insights/
├── families/
├── validation/
└── protocols.py
```

Batch and vectorized backtesting belong under Research.

### 10.9 Execution Module

```text
src/trading_framework/execution/
├── models/
├── brokers/
├── orders/
├── fills/
├── positions/
├── risk_controls/
├── reconciliation/
├── replay/
├── paper/
├── live/
└── services/
```

Concrete broker adapters belong to Infrastructure.

### 10.10 Events Module

*(Classified FUTURE by Sprint 054 T002. `events/` contains only `__init__.py` with a one-line docstring; none of the subdirectories below exist.)*

```text
src/trading_framework/events/
├── models/
├── bus/
├── handlers/
├── commands/
└── protocols.py
```

Domain-specific events may live near their owning domain where clearer.

### 10.11 Configuration Module

```text
src/trading_framework/config/
├── models/
├── loaders/
├── defaults/
├── validation/
└── resolution/
```

### 10.12 Infrastructure Module

```text
src/trading_framework/infrastructure/
├── providers/
│   ├── databento/
│   ├── binance/
│   ├── rithmic/
│   └── mt5/
├── importers/
├── brokers/
├── storage/
│   ├── parquet/
│   ├── duckdb/
│   └── postgres/
├── cache/
├── messaging/
└── observability/
```

Infrastructure depends on framework contracts. Domain modules do not depend on infrastructure implementations.

### 10.14 API Module

*(Classified FUTURE by Sprint 054 T002. No `src/trading_framework/api/` package exists at all. `apps/dashboard/` and `apps/cli/` are the actual current-day consumer surfaces.)*

```text
src/trading_framework/api/
├── rest/
├── websocket/
├── schemas/
└── dependencies/
```

The API layer must not contain business logic. FastAPI may be one adapter, but the domain does not depend on FastAPI.

---

## 2. From `ARCHITECTURE_TECHNICAL.md` §11 — User Data Structure

*(Classified MIXED/FUTURE/AMBIGUOUS across every subsection — the actual,
documented canonical `user_data/` layout is
[`docs/reference/MODULE_MAP.md`](../reference/system/MODULE_MAP.md) §11:
`user_data/{market_data,research,runtime,reports,config,components,models}/`,
a materially flatter structure than every proposal below.)*

### 11.1 Purpose

`user_data/` contains user-owned assets and proprietary know-how.

Suggested structure:

```text
user_data/
├── config/
├── data/
├── development/
├── candidates/
├── market_models/
├── signal_models/
├── exit_models/
├── risk_models/
├── strategies/
├── research/
├── analytics/
├── reports/
├── notebooks/
├── tests/
└── secrets/
```

### 11.2 Working Components

```text
user_data/development/market_analysis/
```

Contains unstable local components under active development. These may change freely. Research use requires implementation fingerprints.

### 11.3 Candidate Components

```text
user_data/candidates/market_analysis/
```

Contains stable candidates being prepared for possible promotion into `src/`.

### 11.4 Proprietary Model Definitions

```text
user_data/
├── market_models/
├── signal_models/
├── exit_models/
├── risk_models/
└── strategies/
```

Contains proprietary model definitions and compositions. Mutable definitions used in research require fingerprints.

### 11.5 Research Results

```text
user_data/research/
├── signal_research/
├── strategy_research/
├── datasets/
├── runs/
└── metadata/
```

Signal Research and Strategy Research results remain separate.

### 11.6 Analytics

```text
user_data/analytics/
├── insights/
├── rankings/
├── families/
├── correlations/
├── clusters/
└── robustness/
```

Analytics may be regenerated without recomputing unchanged research datasets.

### 11.7 Reports and Notebooks

```text
user_data/reports/
user_data/notebooks/
```

Notebooks are exploratory. Reusable logic should move into either `src/trading_framework/` or `user_data/development/`, `user_data/candidates/`, `user_data/*_models/`.

### 11.8 Secrets

```text
user_data/secrets/
```

This directory is not committed. Environment variables or external secret storage are preferred.

---

## 3. From `MULTITIMEFRAME_MARKET_MODEL_ARCHITECTURE.md` §17 — Proposed Module Structure

*(Classified AMBIGUOUS by Sprint 054 T003 — the actual `market_analysis/`
and `strategy/` layouts differ from both proposals below under different
directory names. The document's own framing anticipates this drift.)*

Start with a minimal structure:

```text
src/trading_framework/market_analysis/
├── components/
├── engine/
├── models/
└── protocols.py
```

Evolve only when the number and stability of components justify it:

```text
src/trading_framework/market_analysis/
├── features/
├── structures/
├── states/
├── engine/
├── graph/
├── registry/
├── cache/
├── alignment/
├── models/
└── protocols.py
```

Strategy definitions remain separate:

```text
src/trading_framework/strategy/
├── market_models/
├── signal_models/
├── exit_models/
├── risk_models/
├── strategy_models/
├── expressions/
├── occurrences/
└── protocols.py
```

The conceptual taxonomy is stable even if the directory structure evolves.

---

## 4. From `MULTITIMEFRAME_MARKET_MODEL_ARCHITECTURE.md` §18 — User Data Structure

*(Classified MIXED by Sprint 054 T003. `component_id`/`resolved_parameters`-shaped
identity concepts are pervasively implemented elsewhere and documented as
CURRENT in `docs/reference/system/ARCHITECTURE_FOUNDATIONS.md`. The
`reproducibility_status`/`implementation_hash` fields below returned zero
matches anywhere in `src/`. The on-disk `user_data/` folder layout itself
is a private workspace per ADR-0022, not part of the framework repo's own
tree, and was not independently verified.)*

```text
user_data/
├── development/
│   └── market_analysis/
├── candidates/
│   └── market_analysis/
├── market_models/
├── signal_models/
├── exit_models/
├── risk_models/
├── strategies/
└── research/
```

Working components may be used in experimental research when the result records:

```text
component_id
implementation_hash
dependency_hash
resolved_parameters
reproducibility_status = EXPERIMENTAL
```

Mutable local model definitions require:

```text
definition_hash
resolved_parameters
dependency identities
reproducibility_status = EXPERIMENTAL
```

---

## 5. From `WORKFLOWS_AI_ADR.md` §3.16 — Signal Research Storage layout block

*(Classified AMBIGUOUS by Sprint 054 T003b: a `user_data/` workspace
on-disk convention, out of `src/`-grep scope per ADR-0022.)*

```text
user_data/research/signal_research/
├── runs/
├── datasets/
├── metadata/
├── analytics/
└── reports/
```

Each run should record: `run_id`, `research_scope`, `resolved_config`, `dataset_references`, `component_versions or hashes`, `model_versions or hashes`, `execution_plan`, `result_manifest`, `validation_summary`. (The record-fields list is preserved in full in `RUN_IDENTITY_AND_CONFIGURATION.md`; only the layout tree is evicted here.)

---

## 6. From `WORKFLOWS_AI_ADR.md` §4.20 — Strategy Research Storage layout block

*(Classified AMBIGUOUS by Sprint 054 T003b, same reasoning as §3.16. Note:
the `families/` subfolder below is inconsistent with §4.14's confirmed
finding that Strategy Families have no code counterpart today — flagged
in-file but left unresolved by the source document, T002 finding F7.)*

```text
user_data/research/strategy_research/
├── runs/
├── datasets/
├── trades/
├── equity_curves/
├── analytics/
├── rankings/
├── families/
├── robustness/
└── reports/
```

---

## 7. From `MARKET_DATA_FUTURE.md` (formerly `DATA_MODULE_FUTURE.md`) §26 — Suggested Module Structure

```text
src/trading_framework/market/
├── models/
│   ├── instrument.py
│   ├── bar.py
│   ├── trade.py
│   ├── quote.py
│   └── event.py
├── datasets/
│   ├── identity.py
│   ├── metadata.py
│   ├── manifest.py
│   ├── lifecycle.py
│   └── lineage.py
├── requests/
│   ├── historical.py
│   ├── import_request.py
│   ├── query.py
│   └── subscription.py
├── providers/
│   └── protocols.py
├── importers/
│   └── protocols.py
├── repositories/
│   └── protocols.py
├── normalization/
│   └── protocols.py
├── validation/
│   └── protocols.py
└── services/
    ├── missing_ranges.py
    └── dataset_resolution.py
```

```text
src/trading_framework/application/market_data/
├── synchronize_historical.py
├── import_external_dataset.py
├── query_historical.py
├── ingest_live.py
├── record_live.py
├── finalize_partition.py
├── publish_dataset.py
└── replay_dataset.py
```

```text
src/trading_framework/infrastructure/
├── providers/
│   ├── databento/
│   ├── rithmic/
│   ├── binance/
│   └── mt5/
├── importers/
│   ├── databento_dbn/
│   ├── csv/
│   └── parquet/
└── storage/
    ├── parquet/
    ├── duckdb/
    └── metadata/
```

> Note: the real package structure is documented (and kept current) in
> `docs/reference/system/MODULE_MAP.md` §5. This suggested tree is
> partially superseded — e.g. `market/continuous/`, `market/contracts/`,
> `market/derivation/` exist and aren't anticipated here, while
> `infrastructure/storage/duckdb/`, `infrastructure/providers/{rithmic,mt5}/`
> don't exist.

---

## 8. From `MARKET_DATA_FUTURE.md` (formerly `DATA_MODULE_FUTURE.md`) §29 — Initial Implementation Scope

> **Partially stale, verified at Sprint 054 reclassification time.** Of the
> "Next increments" listed below, Partition Finalization, Dataset
> Publication, Futures Contract Datasets, and Continuous Futures Builder
> (narrower than described — see `MARKET_DATA_FUTURE.md` §21) are already
> built. Missing Range Calculator, Historical Provider Synchronization (in
> the local-first/policy sense), Live Stream Contract, Live Recorder, and
> Historical Replay remain unbuilt. See
> `docs/planning/DATA_MODULE_CLASSIFICATION.md` §29.
>
> This is a Sprint-002-era increment plan (not a layout proposal like the
> other sections in this file), kept here rather than in a separate
> `docs/planning/` note because it is short (~65 lines) and its only
> remaining value is historical context for what Sprint 002 originally
> scoped as "first slice" — the executor's call per Sprint 055 T004.

The first Market Data vertical slice should remain limited.

Recommended initial scope:

```text
Instrument
Timeframe
MarketBar
DatasetId
DatasetRef
DatasetMetadata
DatasetLifecycle
DatasetPublication
CSV or Parquet Importer
UTC Normalizer
OHLCV Validator
Parquet Writer
Parquet Repository
Dataset Registry
Historical Query
```

The first complete flow should be:

```text
External File
    ↓
Inspect
    ↓
Normalize
    ↓
Validate
    ↓
Store in Parquet
    ↓
Register Dataset Version
    ↓
Query Through Repository
```

Next increments:

```text
Missing Range Calculator
Historical Provider Synchronization
Live Stream Contract
Live Recorder
Partition Finalization
Dataset Publication
Historical Replay
Futures Contract Datasets
Continuous Futures Builder
```

Databento DBN should be implemented after the generic importer contracts and canonical storage rules are stable.

---

## 9. Pending Cursor-side / ADR-process moves (not executed by Sprint 055 T008)

Two `docs/vision/ARCHITECTURE_FOUNDATIONS.md` sections were approved for
relocation at T004 but their destinations are out of Sprint 055 T008's
scope (Cursor-side rules file, ADR process doc) — parked here, verbatim,
so the content is not silently dropped while awaiting that follow-up pass.

### 9.1 Composition Over Inheritance — pending move to `.cursor/rules/ARCHITECTURE_CONTROL.md`

*(Classified AMBIGUOUS by Sprint 054 T001 — as-built status unclear; a
codebase-wide style convention that would require a broader structural
audit than grep-level verification to confirm or refute.)*

Prefer: composition, dependency injection, immutable value objects, Protocols, explicit expression trees, registries, validated configuration.

Avoid: deep inheritance trees, shared mutable base classes, hidden dependencies, global service locators, runtime monkey patching.

### 9.2 Controlled Technology Adoption — pending move to `docs/adr/README.md` process section

A new technology may be introduced only when it solves a demonstrated problem.

A material decision must include: problem statement, expected benefit, operational cost, migration cost, alternatives, rollback strategy.

Technology must not be introduced solely for novelty or anticipated scale.

> A pointer to this pending move is also left in `docs/vision/PRODUCT_DIRECTION.md`.
