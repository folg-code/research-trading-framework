# ADR-0007 — Dataset Lifecycle and Publication

## Status

ACCEPTED

## Context

Market datasets must be reproducible research inputs. The framework needs explicit lifecycle states, immutable published versions, and separation between in-progress ingestion and consumer-ready data.

PRB-001 identified that dataset identity and versioning were conceptually defined but not yet algorithmically specified for the MVP slice.

Sprint 002 implemented:

- `DatasetId` and `DatasetRef`,
- `DatasetMetadata`,
- lifecycle states `WORKING`, `FINALIZED`, `PUBLISHED`,
- separate application workflows for import, finalize, publish and query.

## Decision

Adopt an explicit dataset lifecycle for MVP market data:

```text
WORKING → FINALIZED → PUBLISHED
```

Rules:

1. **WORKING** — ingestion and validation in progress; metadata and bars may be written for the allocated version.
2. **FINALIZED** — validation passed, checksum and row count computed, version closed for normal writes.
3. **PUBLISHED** — version is immutable and available to consumers through repository contracts.

Additional decisions:

- `finalize_dataset` and `publish_dataset` are separate application workflows.
- A published dataset version must not be mutated through the repository API.
- Consumer historical queries accept only `PUBLISHED` dataset versions in the MVP.
- Dataset identity (`DatasetId`) is independent from storage path; `DatasetRef` includes a monotonic version per identity.

MVP version allocation policy:

- allocate a new version for material semantic changes,
- reuse the current version only for physical rewrites with unchanged logical content.

## Consequences

### Positive

- reproducible consumer entry point via `DatasetRef`,
- clear boundary between ingestion and research consumption,
- explicit immutability after publication,
- lifecycle transitions are testable and auditable.

### Negative

- additional workflow steps compared with a single import-and-publish operation,
- `INVALID` and `SUPERSEDED` automation remain future work,
- registry currently uses file-backed metadata for the MVP slice.

## References

- `src/trading_framework/market/datasets/`
- `src/trading_framework/application/market_data/`
- `docs/architecture/DATA_MODULE_UPDATED.md` §7, §17
- `docs/planning/PROBLEM_REGISTRY.md` — PRB-001
