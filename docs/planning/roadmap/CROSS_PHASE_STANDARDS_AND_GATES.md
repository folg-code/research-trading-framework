# Cross Phase Standards And Gates

This is the detailed planning record extracted from the accepted roadmap. Use [Roadmap](../ROADMAP.md) for phase status and navigation; use [Reference](../../reference/README.md) for current behavior.

# 15. Cross-Cutting Standards

These standards apply across Market Data, Market Analysis and Research. They are not separate linear phases.

## 15.1 Test and Research Data Tiers

Three tiers of test and research data coexist by design.

### Tier 1 — Small Deterministic Fixtures

```text
Scope:     tens to hundreds of records
Location:  committed to repository
CI:        standard unit and contract tests
```

Use for: edge cases, temporal alignment, join semantics, incomplete outcomes, session boundaries, validation errors.

Small fixtures are valid test tools. They must not be replaced by large datasets in unit tests.

### Tier 2 — Representative Integration Datasets

```text
Scope:     several days to weeks per data type
Location:  local or opt-in test fixtures (not required in standard CI)
CI:        opt-in integration markers only
```

Separate datasets for OHLCV, trades, quotes and options snapshots where applicable.

Use for: importer tests, normalization, partitioning, futures contract boundaries, multi-session behaviour, orderflow calculations, realistic distributions, local performance checks.

### Tier 3 — Full Research Datasets

```text
Scope:     months to years
Location:  user_data (not committed)
CI:        not required
```

Use for: Signal Research, Strategy Research, robustness validation, walk-forward, Monte Carlo, stability over time.

Published as concrete `DatasetRef` values with lineage, version and validation status.

**Problem registry:** PRB-017 — representative integration and research-validation dataset gap.

## 15.2 Live Market Data Entry Gate

Concrete paid live CME adapters (**Phase 2E**) are deferred until at least one of:

- a candidate strategy passes defined historical robustness validation,
- replay and paper parity require a live normalized feed,
- a data property available only live is required to validate a model,
- runtime operational testing cannot continue on recorded or replayed data,
- expected research or execution value justifies ongoing data cost.

**Not sufficient alone:** a positive backtest does not justify live feed cost.

Until the gate opens:

- historical research uses archives (Databento and similar),
- replay uses published datasets,
- live provider **contracts** may exist without expensive adapter implementation.

## 15.3 Strategy Research Scope Clarification

Completing **Phase 6A — OHLCV Strategy Research MVP** validates Strategy Model and simulation contracts on bar-based facts.

It does **not** mean:

- Market Data development is complete,
- the simulation engine's target data coverage is complete,
- orderflow or options context is supported in Strategy Research.

**Phase 6B — Multi-Data Strategy Research** extends simulation when Phase 2C/2D and Phase 4B/4C deliver new fact types.

## 15.4 Planning Increment and Sprint 011

Before Sprint 011 implementation, complete a short **Roadmap Revision / Phase Entry Review** (planning only):

- update `ROADMAP.md`, `CURRENT_STATUS.md`, `PROBLEM_REGISTRY.md`, `DATA_MODULE.md`,
- confirm capability tracks, test-data tiers and live-data gate,
- decide phase entry and publish `SPRINT_011.md`.

**Recommended Sprint 011 goal:** Phase 2B — Historical Archive Import Foundation.

**First vertical slice:**

```text
Databento DBN OHLCV archive
    ↓
inspection → decoding → canonical MarketBar
    ↓
validation → partitioned Parquet → published DatasetRef
```

Sprint 011 must **not** simultaneously include: trades, quotes, options, orderflow, continuous futures, full resumability, live adapters, or a complete backtest engine.

After this slice, choose the next sprint among:

- **Phase 2C.1** — `MarketTrade` archive import, or
- **Phase 6A** — OHLCV Strategy Research MVP.

See `docs/archive/phases/phase-02-market-data/SPRINT_011.md`.

---

# 16. Cross-Phase Architectural Gates

A phase must not be considered complete if it violates these gates.

## Reproducibility Gate

Results identify all material:

- datasets,
- versions,
- configurations,
- component identities,
- model identities,
- time semantics,
- execution assumptions.

## Temporal Correctness Gate

No result uses information before its legal `available_at`.

## Domain Ownership Gate

Responsibilities remain in their owning domains.

## Workflow Independence Gate

Signal Research, Strategy Research and Strategy Execution do not require each other's workflow state.

## User-Space Gate

Proprietary definitions and data remain in `user_data/`.

## Complexity Gate

New infrastructure solves a demonstrated problem.

## Test Gate

Critical contracts have unit, integration, regression or workflow tests as appropriate.

---

# 17. Deferred Capabilities

The following remain deferred until evidence justifies them:

```text
Microservices
Kubernetes
Kafka
Spark
Distributed Market Analysis Engine
Multi-node research scheduler
Dedicated feature-store product
Remote component registry
Visual workflow or DAG editor
Full event sourcing
MBP-10 / full DOM as primary storage (see §14 — sample validation first)
Raw option tick streams (snapshots preferred; see §14)
Separate Position Sizing Model
Distributed Strategy Execution
Automated feature engineering search
Online / incremental learning and live model inference
GPU or distributed model training
```

Deferred does not mean rejected.

**Promoted 2026-08-25:** *Automatic ML feature vector layer* left this list and became **Phase 10A**
(**§13A**). The declared feature matrix is explicit and bounded — it is not an automatic layer over
every available component.

Each item requires a decision trigger, design review and usually an ADR before implementation.

---
