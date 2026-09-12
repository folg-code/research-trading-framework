# Market Data — Future Direction

This document contains proposed capabilities beyond the [implemented Market Data module](../reference/modules/MARKET_DATA.md) and [workflow](../reference/workflows/MARKET_DATA.md). It is not an implementation-status source or permission to change an accepted ADR. The [pre-review target-architecture snapshot](../archive/snapshots/MARKET_DATA_FUTURE_pre_review.md) preserves the detailed earlier proposal and its historical classification notes.

## Goal and boundaries

Market facts should remain provider-independent, versioned and reproducible. Future providers may expose bars, trades, quotes, order-book updates, DOM or option snapshots; the framework must not assume a provider supplies every type. New fact types require explicit canonical models and validation before publication. Derived interpretation belongs in Market Analysis, not primary Market Data storage.

## Local resolution and historical synchronization

A future resolver should make the data-access policy explicit: `LOCAL_ONLY`, `LOCAL_FIRST`, `PROVIDER_REFRESH` or `PROVIDER_ONLY`. It should inspect local coverage, calculate missing ranges, apply the selected policy, normalize and validate fetched data, update only affected partitions, publish a new dataset version and return a `DatasetRef`. It must not silently switch policy or forward-fill unknown market prices.

Missing-range detection must account for sessions, holidays, shortened days, outages, provider availability and futures contract lifecycle. An expected market closure differs from an unexpected gap. The [future Time Model](TIME_MODEL_FUTURE.md) is a dependency for calendar-aware decisions.

Provider APIs and external file imports remain separate use cases even if they share normalizers. Proposed provider/importer protocols and exact signatures require review before implementation.

## Instrument and source coverage

Instrument mappings between research and execution symbols must be explicit and user-owned; similarity of symbol strings is insufficient. Quote, option-snapshot and deeper order-book models are future extensions, each justified by research value and storage cost. Source acquisition should avoid a permanent runtime dependency on a vendor API.

The [research data strategy](../planning/roadmap/RESEARCH_DATA_STRATEGY.md) records the target emphasis on high-information market facts rather than collecting every available feed. Paid live-data adapters remain gated by that roadmap.

## Live ingestion, recording and replay

Future live ingestion should normalize provider events before runtime delivery. Storage recording, monitoring and Strategy Runtime are separate consumers; a slow or failed disk write must be visible without becoming the main delivery latency path. Duplicate events, reconnect ordering and event identity need explicit contracts.

A recorder may batch working artifacts and finalize validated partitions before publication as research datasets. Historical replay should expose ordered normalized events with an explicit replay clock. Replay/runtime validation remains separate from vectorized Strategy Research. These are target capabilities; see [Execution Runtime Future](EXECUTION_RUNTIME_FUTURE.md) for their execution-side implications.

## Dataset storage and lineage extensions

Future retention is policy-driven (`DISCARD_RAW`, temporary/permanent raw retention, or source-archive retention), based on reacquisition cost, information loss and audit needs. Even when raw records are discarded, source identity, checksum, normalization version, row counts, validation and mapping decisions should remain in metadata.

Partitioning should follow volume, updates and queries while avoiding excessive small files. Historical monthly-partition suggestions in the snapshot are **not** the current rule: [ADR-0014](../adr/ADR-0014-historical-archive-import-and-market-trade-storage.md) and [ADR-0018](../adr/ADR-0018-continuous-futures-materialization.md) record the accepted day/session-date layouts. A change to those layouts needs a new decision.

Continuous futures remain distinct derived datasets with source versions, roll schedule and construction lineage. Other roll policies or back-adjusted analytical series would be separate future artifacts; back-adjustment was explicitly outside the ADR-0018 MVP.

## Future contract design

Potential contracts include a range resolver, missing-range calculator, live ingestion service, recorder, partition finalizer and replay service. Their precise names, method signatures, policies and persistence shapes are **proposals** until an implementation task and ADR resolve them. Configuration must be declarative, validated and reproducible, with secrets kept outside committed files.
