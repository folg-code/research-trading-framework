# Sprint 002 — Market Data MVP

## Metadata

```text
Sprint: 002
Phase: Phase 2 — Market Data MVP
Status: COMPLETED
Planned Start: 2026-06
Planned End: 2026-06
Sprint Goal Owner: Project Maintainer
Depends On: SPRINT_001 (COMPLETED)
```

---

## Sprint Goal

```text
Import one OHLCV dataset from an external CSV file,
normalize timestamps to UTC, validate bars, persist to Parquet,
register and publish a dataset version, and query it through a repository.
```

Success means a contributor can run the import workflow locally without external APIs, obtain a `DatasetRef` to a `PUBLISHED` immutable version, and query `MarketBar` records through framework contracts.

---

## Phase Alignment

This sprint implements the first vertical slice of **Phase 2 — Market Data MVP** from `ROADMAP.md`.

It completes the primary flow:

```text
External OHLCV File
        ↓
Inspect
        ↓
Normalize to UTC
        ↓
Validate
        ↓
Persist in Parquet
        ↓
Register Dataset Version
        ↓
Finalize
        ↓
Publish
        ↓
Query Through Repository
```

Phase 2 completion criteria not in this sprint remain explicitly out of scope (see below).

---

## Scope

In scope:

- MVP resolution of PRB-001, PRB-008 and PRB-010 for OHLCV CSV import,
- domain models: `Instrument`, `MarketBar`, `DatasetId`, `DatasetRef`, `DatasetMetadata`,
- dataset lifecycle: `WORKING → FINALIZED → PUBLISHED`,
- importer inspection for external CSV files,
- CSV OHLCV importer (infrastructure),
- UTC timestamp and OHLCV normalization,
- OHLCV validation with explicit results,
- Parquet writer and repository (infrastructure),
- dataset registry with metadata persistence,
- application workflows: import, finalize, publish, query,
- unit and integration tests including one end-to-end CSV flow,
- ADR-0007 and ADR-0008.

Out of scope:

- live ingestion and provider API synchronization,
- Databento, Rithmic, Binance, MT5 or other provider adapters,
- Parquet-as-source import (CSV only in this sprint),
- continuous futures construction,
- trades, quotes, DOM and options data,
- missing-range calculator and historical synchronization,
- partition repair and superseded-version management beyond basic registration,
- `INVALID` and `SUPERSEDED` lifecycle automation,
- trading calendar implementation (PRB-007),
- Research dataset consumption workflows.

---

## Dependencies

```text
Sprint 001 — repository foundation (complete)
docs/reference/modules/DATA_MODULE_UPDATED.md
docs/agents/AGENTS_UPDATED.md
```

New runtime dependencies expected:

- `pyarrow` — Parquet read/write (demonstrated need),
- `pandas` — optional; prefer pyarrow/polars only if a demonstrated need appears during implementation.

Prefer the smallest dependency set that satisfies the Parquet vertical slice.

---

## Risks

| Risk | Mitigation |
|------|------------|
| PRB-001 blocks registry design | Resolve MVP identity algorithm in S002-T002 before registry implementation |
| PRB-010 delays `MarketBar` | Resolve MVP numeric types in S002-T001 before bar model |
| PRB-008 causes temporal bugs | Fix interval-start convention in S002-T003 with explicit metadata field |
| God-object import service | Separate inspect, normalize, validate, write, register, publish workflows |
| Storage path coupled to identity | `DatasetId` independent from file path; paths derived from identity |
| Sprint too large for one week | Strict CSV-only scope; defer provider and live workflows |

---

## Task Summary

| ID | Task | Status | Depends On |
|----|------|--------|------------|
| S002-T001 | MVP numeric types for OHLCV (PRB-010) | DONE | — |
| S002-T002 | MVP dataset identity algorithm (PRB-001) | DONE | — |
| S002-T003 | Bar timestamp convention (PRB-008) | DONE | — |
| S002-T004 | `Instrument` domain model | DONE | S002-T001 |
| S002-T005 | `MarketBar` domain model | DONE | S002-T001, S002-T003 |
| S002-T006 | `DatasetId` and `DatasetRef` | DONE | S002-T002 |
| S002-T007 | `DatasetMetadata` model | DONE | S002-T006 |
| S002-T008 | `DatasetLifecycle` state model | DONE | S002-T006 |
| S002-T009 | External file inspection contract | DONE | — |
| S002-T010 | CSV file inspector (infrastructure) | DONE | S002-T009 |
| S002-T011 | OHLCV normalization contract | DONE | S002-T003, S002-T005 |
| S002-T012 | UTC OHLCV normalizer (infrastructure) | DONE | S002-T011 |
| S002-T013 | OHLCV validation contract and result model | DONE | S002-T005 |
| S002-T014 | OHLCV validator implementation | DONE | S002-T013 |
| S002-T015 | CSV OHLCV importer (infrastructure) | DONE | S002-T010, S002-T012 |
| S002-T016 | Parquet writer (infrastructure) | DONE | S002-T005 |
| S002-T017 | Dataset registry | DONE | S002-T007, S002-T008 |
| S002-T018 | Parquet repository and query contract | DONE | S002-T016, S002-T017 |
| S002-T019 | `import_external_dataset` use case | DONE | S002-T015, S002-T014, S002-T018 |
| S002-T020 | `finalize_dataset` use case | DONE | S002-T017, S002-T018 |
| S002-T021 | `publish_dataset` use case | DONE | S002-T020 |
| S002-T022 | `query_historical` use case | DONE | S002-T018, S002-T021 |
| S002-T023 | Test fixtures and unit tests | DONE | S002-T004–S002-T014 |
| S002-T024 | Integration and e2e test: full CSV flow | DONE | S002-T019–S002-T022 |
| S002-T025 | ADR-0007 and ADR-0008 | DONE | S002-T002, S002-T008 |
| S002-T026 | Sprint review and status update | DONE | All preceding tasks |

---

## Tasks

### S002-T001 — MVP numeric types for OHLCV (PRB-010)

**Status:** DONE  
**Category:** Architecture  
**Domain:** Core / Market

#### Context

`MarketBar` requires concrete numeric representations. Full asset-class coverage is not needed for the first CSV OHLCV slice.

#### Scope

Define and implement MVP types for Sprint 002:

```text
Price    → Decimal (OHLC fields)
Volume   → int (non-negative)
Quantity → defer unless required by import flow
```

Add `src/trading_framework/core/types/` with price and volume value objects or typed aliases with validation helpers.

Document the decision in task output and reference from `MarketBar`.

#### Out of Scope

- PnL, money and order-quantity types (Execution domain),
- float arrays for analytics,
- full PRB-010 resolution across all asset classes.

#### Architecture References

- `docs/reference/modules/DATA_MODULE_UPDATED.md` §6
- `docs/planning/PROBLEM_REGISTRY.md` — PRB-010

#### Acceptance Criteria

- [ ] Price type rejects invalid values explicitly
- [ ] Volume type rejects negative values
- [ ] Serialization rules are documented in code or module docstring
- [ ] Unit tests cover validation and equality
- [ ] PRB-010 updated with MVP decision note

---

### S002-T002 — MVP dataset identity algorithm (PRB-001)

**Status:** DONE  
**Category:** Architecture  
**Domain:** Market

#### Context

Dataset registry and publication require a deterministic identity scheme before implementation.

#### Scope

Specify and implement MVP algorithm:

```text
DatasetId     = stable logical key (instrument + data_type + timeframe + provider/source semantics)
Version       = monotonically increasing integer per DatasetId
DatasetRef    = (DatasetId, version)
New version   = created on material semantic change (source, normalization, schema, validation outcome)
```

Define material vs non-material change rules for Sprint 002 scope.
Implement version allocation in registry.

#### Out of Scope

- content-addressed versioning,
- partition-level replacement semantics,
- superseded-version automation.

#### Architecture References

- `docs/reference/modules/DATA_MODULE_UPDATED.md` §7.1
- `docs/planning/PROBLEM_REGISTRY.md` — PRB-001

#### Acceptance Criteria

- [ ] Written specification with at least three examples (unchanged rewrite, corrected bar, changed normalization)
- [ ] `DatasetId` and version generation implemented
- [ ] Unit tests for version creation rules
- [ ] PRB-001 status updated to MITIGATED or RESOLVED for MVP scope

---

### S002-T003 — Bar timestamp convention (PRB-008)

**Status:** DONE  
**Category:** Architecture  
**Domain:** Time / Market

#### Context

Providers differ on bar timestamp semantics. The framework needs one canonical rule for MVP.

#### Scope

Adopt for Sprint 002:

```text
observed_at  = interval start (UTC-aware)
available_at = interval end   (UTC-aware), derived from timeframe where not supplied
```

Document invariant in `MarketBar` and normalization layer.
Record convention in dataset metadata where relevant.

#### Architecture References

- `docs/vision/ARCHITECTURE_TECHNICAL_UPDATED.md` §2.9
- `docs/planning/PROBLEM_REGISTRY.md` — PRB-008

#### Acceptance Criteria

- [ ] Convention documented in market module
- [ ] Normalizer applies interval-start rule for CSV import
- [ ] Unit tests with explicit timestamp examples
- [ ] PRB-008 updated with accepted MVP convention

---

### S002-T004 — `Instrument` domain model

**Status:** DONE  
**Category:** Feature  
**Domain:** Market  
**Depends On:** S002-T001

#### Scope

Implement immutable `Instrument` in `src/trading_framework/market/models/instrument.py`:

```text
instrument_id
symbol
asset_class
exchange (optional)
metadata (optional, bounded)
```

#### Acceptance Criteria

- [ ] Model is immutable and provider-independent
- [ ] Invalid identifiers rejected
- [ ] Unit tests for creation and equality

---

### S002-T005 — `MarketBar` domain model

**Status:** DONE  
**Category:** Feature  
**Domain:** Market  
**Depends On:** S002-T001, S002-T003

#### Scope

Implement immutable `MarketBar` in `src/trading_framework/market/models/bar.py` with invariants:

```text
high >= open, close
low <= open, close
high >= low
volume >= 0
observed_at UTC-aware
available_at UTC-aware
```

#### Acceptance Criteria

- [ ] Invariants enforced at construction
- [ ] Uses MVP price and volume types
- [ ] Unit tests cover valid and invalid bars

---

### S002-T006 — `DatasetId` and `DatasetRef`

**Status:** DONE  
**Category:** Feature  
**Domain:** Market  
**Depends On:** S002-T002

#### Scope

Implement in `src/trading_framework/market/datasets/identity.py`:

- `DatasetId` — logical stable identity
- `DatasetRef` — `(dataset_id, version)` reference for consumers

#### Acceptance Criteria

- [ ] Both types are immutable and hashable
- [ ] `DatasetRef` string representation is stable and parseable
- [ ] Unit tests for validation and equality

---

### S002-T007 — `DatasetMetadata` model

**Status:** DONE  
**Category:** Feature  
**Domain:** Market  
**Depends On:** S002-T006

#### Scope

Implement metadata model with Sprint 002 minimum fields:

```text
dataset_ref
instrument_id
timeframe
provider
source_id
data_type
start_at
end_at
schema_version
normalization_version
validation_status
lifecycle_status
row_count
checksum
created_at
published_at (optional)
lineage (minimal)
```

#### Acceptance Criteria

- [ ] Metadata is serializable (JSON or TOML compatible dict)
- [ ] Required fields validated
- [ ] Unit tests for minimal valid metadata

---

### S002-T008 — `DatasetLifecycle` state model

**Status:** DONE  
**Category:** Feature  
**Domain:** Market  
**Depends On:** S002-T006

#### Scope

Implement lifecycle enum and legal transitions:

```text
WORKING → FINALIZED → PUBLISHED
```

Reject illegal transitions explicitly.
`PUBLISHED` versions are immutable.

#### Acceptance Criteria

- [ ] Transition helpers or service methods enforce rules
- [ ] Unit tests for legal and illegal transitions
- [ ] Published immutability rule tested

---

### S002-T009 — External file inspection contract

**Status:** TODO  
**Category:** Architecture  
**Domain:** Market

#### Scope

Define `FileInspector` protocol in `src/trading_framework/market/importers/protocols.py`:

```text
inspect(path) -> FileInspectionResult
```

Result includes detected format, columns, row estimate, timestamp column hints, encoding.

#### Acceptance Criteria

- [ ] Protocol defined with typed result model
- [ ] No provider-specific logic in domain layer

---

### S002-T010 — CSV file inspector (infrastructure)

**Status:** TODO  
**Category:** Feature  
**Domain:** Market / Infrastructure  
**Depends On:** S002-T009

#### Scope

Implement CSV inspector in `src/trading_framework/infrastructure/importers/csv/`.

Detect OHLCV column mapping candidates without full import.

#### Acceptance Criteria

- [ ] Inspector works on fixture CSV files
- [ ] Explicit errors for unreadable files
- [ ] Unit tests with sample files

---

### S002-T011 — OHLCV normalization contract

**Status:** TODO  
**Category:** Architecture  
**Domain:** Market  
**Depends On:** S002-T003, S002-T005

#### Scope

Define `OhlcvNormalizer` protocol and normalized row DTO in `src/trading_framework/market/normalization/protocols.py`.

Contract covers timestamp parsing, UTC conversion, column mapping, interval-start semantics.

#### Acceptance Criteria

- [ ] Protocol and DTO defined
- [ ] Domain layer has no CSV or pandas imports

---

### S002-T012 — UTC OHLCV normalizer (infrastructure)

**Status:** TODO  
**Category:** Feature  
**Domain:** Market / Infrastructure  
**Depends On:** S002-T011

#### Scope

Implement normalizer for CSV rows → normalized bar inputs.
Use `require_utc_aware` / `normalize_to_utc` from Sprint 001.

#### Acceptance Criteria

- [ ] Naive timestamps rejected or converted with explicit source timezone from import config
- [ ] Interval-start convention applied
- [ ] Unit tests for timezone and column mapping cases

---

### S002-T013 — OHLCV validation contract and result model

**Status:** TODO  
**Category:** Architecture  
**Domain:** Market  
**Depends On:** S002-T005

#### Scope

Define in `src/trading_framework/market/validation/protocols.py`:

- `OhlcvValidator` protocol
- `ValidationResult` with errors, warnings, row-level issues

#### Acceptance Criteria

- [ ] Validation result is explicit and serializable
- [ ] Domain contract does not depend on storage

---

### S002-T014 — OHLCV validator implementation

**Status:** TODO  
**Category:** Feature  
**Domain:** Market  
**Depends On:** S002-T013

#### Scope

Validate:

- OHLCV field presence,
- bar invariants,
- timestamp ordering within import batch,
- duplicate `observed_at` detection.

#### Acceptance Criteria

- [ ] Invalid data produces explicit `ValidationResult`
- [ ] Unit tests for each failure mode

---

### S002-T015 — CSV OHLCV importer (infrastructure)

**Status:** TODO  
**Category:** Feature  
**Domain:** Infrastructure  
**Depends On:** S002-T010, S002-T012

#### Scope

Implement streaming or chunked CSV reader producing normalized bar inputs.
Place in `src/trading_framework/infrastructure/importers/csv/ohlcv.py`.

#### Acceptance Criteria

- [ ] Reads fixture CSV without loading entire file into memory if reasonably avoidable
- [ ] Integrates inspector and normalizer
- [ ] Unit tests with fixtures

---

### S002-T016 — Parquet writer (infrastructure)

**Status:** TODO  
**Category:** Feature  
**Domain:** Infrastructure  
**Depends On:** S002-T005

#### Scope

Implement Parquet writer in `src/trading_framework/infrastructure/storage/parquet/writer.py`.
Write `MarketBar` batches with stable schema.

#### Acceptance Criteria

- [ ] Written Parquet round-trips schema correctly
- [ ] Uses pyarrow
- [ ] Unit test writes and reads back bars

---

### S002-T017 — Dataset registry

**Status:** TODO  
**Category:** Feature  
**Domain:** Market  
**Depends On:** S002-T007, S002-T008

#### Scope

Implement registry persisting `DatasetMetadata` to local metadata store.
Suggested location: `src/trading_framework/infrastructure/storage/metadata/` or market service.

Registry allocates new versions per S002-T002 rules.

#### Acceptance Criteria

- [ ] Register WORKING dataset version
- [ ] Metadata retrievable by `DatasetRef`
- [ ] Identity independent from file path
- [ ] Unit tests for registration

---

### S002-T018 — Parquet repository and query contract

**Status:** TODO  
**Category:** Feature  
**Domain:** Market / Infrastructure  
**Depends On:** S002-T016, S002-T017

#### Scope

Define `DatasetRepository` protocol in `src/trading_framework/market/repositories/protocols.py`.
Implement Parquet-backed repository:

- write bars for a `DatasetRef`,
- query bars by instrument, timeframe and time range.

#### Acceptance Criteria

- [ ] Query returns `MarketBar` domain objects
- [ ] Storage path derived from `DatasetId` and version, not arbitrary paths
- [ ] Integration test covers write and read

---

### S002-T019 — `import_external_dataset` use case

**Status:** TODO  
**Category:** Feature  
**Domain:** Application  
**Depends On:** S002-T015, S002-T014, S002-T018

#### Scope

Implement `src/trading_framework/application/market_data/import_external_dataset.py`:

```text
CSV file + import config → inspect → normalize → validate → write WORKING version → register
```

Return `DatasetRef` and `ValidationResult`.

#### Acceptance Criteria

- [ ] Orchestrates separate components; no god-object
- [ ] Invalid validation prevents publication-ready state
- [ ] Unit test with mocked infrastructure or fixture path

---

### S002-T020 — `finalize_dataset` use case

**Status:** TODO  
**Category:** Feature  
**Domain:** Application  
**Depends On:** S002-T017, S002-T018

#### Scope

Transition `WORKING → FINALIZED`:

- verify validation status,
- compute checksum and row count,
- close normal writes.

#### Acceptance Criteria

- [ ] Illegal transitions rejected
- [ ] Metadata updated atomically where practical
- [ ] Unit tests for success and failure paths

---

### S002-T021 — `publish_dataset` use case

**Status:** TODO  
**Category:** Feature  
**Domain:** Application  
**Depends On:** S002-T020

#### Scope

Transition `FINALIZED → PUBLISHED`:

- set `published_at`,
- mark version immutable,
- return stable `DatasetRef` for consumers.

#### Acceptance Criteria

- [ ] Published dataset cannot be mutated through repository API
- [ ] Unit tests enforce immutability

---

### S002-T022 — `query_historical` use case

**Status:** TODO  
**Category:** Feature  
**Domain:** Application  
**Depends On:** S002-T018, S002-T021

#### Scope

Implement `src/trading_framework/application/market_data/query_historical.py`:

```text
DatasetRef + time range → List[MarketBar]
```

Only `PUBLISHED` datasets accepted for consumer query in MVP.

#### Acceptance Criteria

- [ ] Rejects query against non-published datasets
- [ ] Returns UTC-aware bars in time order
- [ ] Unit or integration test with fixture dataset

---

### S002-T023 — Test fixtures and unit tests

**Status:** TODO  
**Category:** Maintenance  
**Domain:** Market  
**Depends On:** S002-T004–S002-T014

#### Scope

- `tests/fixtures/market_data/` sample OHLCV CSV files,
- unit tests for all domain models, normalizer, validator, identity rules.

#### Acceptance Criteria

- [ ] Fixtures are small and committed
- [ ] Unit test coverage for all public market domain contracts introduced in this sprint

---

### S002-T024 — Integration and e2e test: full CSV flow

**Status:** TODO  
**Category:** Maintenance  
**Domain:** Market  
**Depends On:** S002-T019–S002-T022

#### Scope

One integration test executing:

```text
CSV → import → finalize → publish → query
```

Use temporary directory for Parquet and metadata storage.

#### Acceptance Criteria

- [ ] Test runs in CI without external services
- [ ] Asserts lifecycle transitions and bar count
- [ ] Located in `tests/integration/` or `tests/e2e/`

---

### S002-T025 — ADR-0007 and ADR-0008

**Status:** TODO  
**Category:** Documentation  
**Domain:** Architecture  
**Depends On:** S002-T002, S002-T008

#### Scope

Create:

```text
docs/adr/ADR-0007-dataset-lifecycle-and-publication.md
docs/adr/ADR-0008-parquet-historical-storage.md
```

Update `docs/adr/README.md`.

#### Acceptance Criteria

- [ ] Both ADRs have ACCEPTED status
- [ ] Cross-reference PRB-001 resolution and storage layout

---

### S002-T026 — Sprint review and status update

**Status:** TODO  
**Category:** Documentation  
**Domain:** Core  
**Depends On:** All preceding tasks

#### Scope

- complete Sprint Review and Retrospective sections in this file,
- update `docs/planning/CURRENT_STATUS.md`,
- update `docs/planning/ROADMAP.md` Phase 2 progress if applicable.

#### Acceptance Criteria

- [ ] Sprint Review filled with actual outcomes
- [ ] `CURRENT_STATUS.md` reflects Phase 2 progress
- [ ] Incomplete work carried forward with explicit reason

---

## Recommended Implementation Order

```text
Wave 1 — decisions
  T001, T002, T003

Wave 2 — domain models
  T004, T005, T006, T007, T008

Wave 3 — contracts
  T009, T011, T013, T018 (protocol only)

Wave 4 — infrastructure
  T010, T012, T014, T015, T016, T017, T018 (implementation)

Wave 5 — application workflows
  T019, T020, T021, T022

Wave 6 — verification and docs
  T023, T024, T025, T026
```

---

## Sprint Review

### Completed

- Waves 1–6 delivered on `sprint/market-data-mvp` (26 / 26 tasks),
- full CSV OHLCV vertical slice: inspect → normalize → validate → Parquet → register → finalize → publish → query,
- domain models, contracts, infrastructure adapters and application workflows,
- `pyarrow` dependency for canonical bar persistence,
- ADR-0007 (dataset lifecycle) and ADR-0008 (Parquet storage),
- 113+ unit tests and one integration test for the end-to-end flow.

### Not Completed

- merge of `sprint/market-data-mvp` into `main` (awaiting sprint integration review),
- Wave 6 verification PRs may still be open at review time (`market-data-fixtures`, `csv-import-integration-test`, `dataset-and-storage-adrs`),
- out-of-scope items unchanged: live ingestion, provider adapters, Parquet import, calendar, Research consumption workflows.

### Demonstrated Capabilities

- import external CSV into a `WORKING` dataset version with explicit validation results,
- transition `WORKING → FINALIZED → PUBLISHED` with checksum and immutability enforcement,
- query published bars by `DatasetRef` and UTC time range through application contracts,
- storage paths derived from dataset identity, not arbitrary file paths.

### Deviations From Plan

- sprint executed in six implementation waves with one PR per task (post Wave 1),
- task branch namespace uses `sprint/market-data-mvp--<task-slug>` because Git cannot host both `sprint/foo` and `sprint/foo/bar`,
- `application.market_data` public exports were consolidated during Wave 6 verification.

### Carry-Forward Items

- sprint integration PR from `sprint/market-data-mvp` to `main`,
- missing-range calculator and historical synchronization policy,
- `INVALID` / `SUPERSEDED` lifecycle automation,
- Parquet-as-source import and provider adapters,
- trading calendar implementation (PRB-007).

---

## Retrospective

### What Worked

- strict wave ordering reduced dependency collisions,
- contract-first Wave 3 made infrastructure and application layers testable in isolation,
- separate application workflows avoided a god-object import service,
- integration test on temporary storage gives CI-friendly end-to-end confidence.

### What Did Not Work

- early local fast-forward merges before the namespaced PR workflow caused branch naming friction,
- duplicate export regression in `application.market_data.__init__` slipped through until Wave 6 fixture work,
- Windows environment required naive UTC Parquet timestamps and fixed-offset timezone tests.

### Process Improvements

- enforce `sprint/<sprint>--<task>` branches and stop-before-merge for all new tasks,
- keep committed fixtures under `tests/fixtures/market_data/` with shared pytest fixture,
- run integration tests in CI after application workflow merges.

### Next Recommended Sprint Goal

```text
Phase 2 increment: missing-range calculator, historical synchronization policy,
or Parquet import — based on Sprint 002 evidence.
```

---

## Definition of Done (Sprint Level)

The sprint is complete when:

```text
[x] Sprint Goal is achieved
[x] One OHLCV CSV dataset can be imported end to end
[x] Published DatasetRef is queryable through repository contracts
[x] All in-scope tasks are DONE or explicitly carried forward
[ ] CI is green on main
[x] CURRENT_STATUS.md is updated
[x] Sprint Review and Retrospective sections are filled
[x] No undocumented architectural deviation was introduced
```
