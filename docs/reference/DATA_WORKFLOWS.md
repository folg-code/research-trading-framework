# Data Workflows (Technical)

> **Reference doc** — [as-implemented layer](README.md).  
> Package index: [MODULE_MAP.md](MODULE_MAP.md). Index: [docs/README.md](../README.md).

Technical reference for how data moves through the framework: ingestion, persistence, lifecycle, query and analysis execution.

**As-is scope:** Market Data Phase 2A (Sprint 002 CSV OHLCV) through Signal Research (Sprints 008–010 on `main`). Multitimeframe and declarative models: Sprints 004–006.  
**Planned next (not implemented):** Phase 2B archive import — `ROADMAP.md` §6, `SPRINT_011.md`.  
**Deep market data reference:** [modules/DATA_MODULE_UPDATED.md](modules/DATA_MODULE_UPDATED.md)

---

## 1. System Overview

The framework separates **user-owned storage** (`user_data/`, passed at runtime) from **framework code** (`src/trading_framework/`). All workflows below use a `storage_root: Path` argument — typically `user_data/storage`.

```mermaid
flowchart TB
    subgraph external["External"]
        CSV["CSV file"]
    end

    subgraph user["user_data/ (runtime)"]
        SR["storage_root/"]
        META["metadata/…/vN.json"]
        PQ["normalized/…/vN/bars.parquet"]
    end

    subgraph app["application/"]
        IMP["import_external_dataset"]
        FIN["finalize_dataset"]
        PUB["publish_dataset"]
        QH["query_historical"]
        LDV["load_analysis_data_view"]
    end

    subgraph domain["domain"]
        MB["MarketBar"]
        DR["DatasetRef"]
        ADV["AnalysisDataView"]
        AR["AnalysisResult"]
    end

    subgraph infra["infrastructure/"]
        CSVIMP["CsvOhlcvImporter"]
        NORM["UtcOhlcvNormalizer"]
        VAL["OhlcvBarValidator"]
        PQR["ParquetDatasetRepository"]
        REG["FileDatasetRegistry"]
    end

    subgraph analysis["market_analysis/"]
        PLAN["DependencyPlanner"]
        EXEC["SequentialBatchExecutor"]
        WS["AnalysisWorkspace"]
    end

    CSV --> CSVIMP --> NORM --> MB
    IMP --> CSVIMP
    IMP --> VAL
    IMP --> PQR
    IMP --> REG
    PQR --> PQ
    REG --> META

    FIN --> REG
    PUB --> REG

    QH --> REG
    QH --> PQR
    PQR --> MB

    LDV --> QH
    LDV --> ADV

    PLAN --> EXEC
    ADV --> EXEC
    EXEC --> WS
    WS --> AR
```

**Dependency direction:** `application` → `domain` + `infrastructure`. Domain packages do not import infrastructure. `market_analysis` consumes market data through application bridges and `DatasetRef`, not by reading Parquet directly.

---

## 2. Architectural Layers

```mermaid
flowchart LR
    subgraph consumers["Consumers (future)"]
        STRAT["strategy/"]
        RES["research/"]
    end

    subgraph usecases["application/"]
        MD["market_data/"]
        MA["market_analysis/"]
    end

    subgraph domains["domain"]
        MKT["market/"]
        MAN["market_analysis/"]
    end

    subgraph adapters["infrastructure/"]
        IMP["importers/"]
        STOR["storage/"]
        VAL2["validation/"]
    end

    consumers -.->|planned| usecases
    MD --> MKT
    MD --> adapters
    MA --> MAN
    MA --> MD
    MAN --> MKT
```

| Layer | Role in data flow |
|-------|-------------------|
| **infrastructure** | Read/write files (CSV, Parquet, JSON metadata). Converts between files and domain types. |
| **market/** | Canonical types: `MarketBar`, `DatasetRef`, lifecycle rules, repository protocols. |
| **application/market_data/** | Orchestrates ingest, lifecycle transitions and historical query. |
| **market_analysis/** | Read-only `AnalysisDataView`, planning, execution, `AnalysisResult` outputs. |
| **application/market_analysis/** | Bridge: `DatasetRef` → `query_historical` → `AnalysisDataView`. |

---

## 3. Market Data — Ingest Workflow

### 3.1 Sequence

```mermaid
sequenceDiagram
    participant User
    participant App as import_external_dataset
    participant CSV as CsvOhlcvImporter
    participant Norm as UtcOhlcvNormalizer
    participant Val as OhlcvBarValidator
    participant Repo as ParquetDatasetRepository
    participant Reg as FileDatasetRegistry

    User->>App: ImportExternalDatasetRequest(path, DatasetId, config)
    App->>CSV: iter_rows(path, OhlcvImportConfig)
    loop each CSV row
        CSV->>Norm: normalize_row(raw, config)
        Norm-->>CSV: NormalizedBarRow
    end
    CSV-->>App: NormalizedBarRow stream
    App->>App: map rows → list[MarketBar]
    App->>Val: validate(bars)
    Val-->>App: ValidationResult
    App->>Reg: allocate_ref(dataset_id) → DatasetRef vN
    alt validation passed
        App->>Repo: write_bars(dataset_ref, bars)
        Repo->>Repo: MarketBar → Parquet (bars.parquet)
    end
    App->>Reg: register(DatasetMetadata, lifecycle=WORKING)
    App-->>User: ImportExternalDatasetResult
```

**Entry point:** `trading_framework.application.market_data.import_external_dataset`

**Steps inside one call:**

1. **Inspect & stream** — `CsvOhlcvImporter` reads CSV row-by-row (no full-file load).
2. **Normalize** — `UtcOhlcvNormalizer` maps columns to UTC `observed_at` / `available_at`, decimal OHLC, integer volume → `NormalizedBarRow`.
3. **Domain mapping** — each row becomes `MarketBar` (`Price`, `Volume`, UTC datetimes).
4. **Validate** — `OhlcvBarValidator` checks OHLC consistency and bar invariants.
5. **Allocate version** — `FileDatasetRegistry.allocate_ref` creates `DatasetRef` with next version number.
6. **Persist** (only if valid) — `ParquetDatasetRepository.write_bars` writes `bars.parquet`.
7. **Register metadata** — JSON sidecar with lifecycle `WORKING`, validation status, row count, lineage.

### 3.2 Type Transformations (Ingest)

| Stage | Type | Price representation | Time |
|-------|------|---------------------|------|
| CSV row | `dict[str, str]` | strings from file | source TZ → normalized |
| After normalizer | `NormalizedBarRow` | `Decimal` | UTC-aware `datetime` |
| Domain bar | `MarketBar` | `Price(Decimal)` | UTC `observed_at`, `available_at` |
| Parquet on disk | Arrow columns | `string` (decimal text) | `timestamp(us)` UTC |
| Volume | — | — | `int64` in Parquet |

Prices are stored as **strings in Parquet** to preserve exact `Decimal` round-trip. See ADR-0008.

### 3.3 Dataset Lifecycle

```mermaid
stateDiagram-v2
    [*] --> WORKING: import_external_dataset
    WORKING --> FINALIZED: finalize_dataset
    WORKING --> INVALID: validation failed / manual
    FINALIZED --> PUBLISHED: publish_dataset
    FINALIZED --> INVALID: reject
    PUBLISHED --> SUPERSEDED: newer version published
    PUBLISHED --> [*]: immutable — consumer queries allowed
    INVALID --> [*]
    SUPERSEDED --> [*]
```

| Transition | Function | Preconditions |
|------------|----------|---------------|
| → `WORKING` | `import_external_dataset` | File readable; metadata registered |
| `WORKING` → `FINALIZED` | `finalize_dataset` | `validation_status == PASSED`; bars exist |
| `FINALIZED` → `PUBLISHED` | `publish_dataset` | Checksum computed at finalize |
| Consumer query | `query_historical` | **Only `PUBLISHED`** |

Published datasets are **immutable** — `ParquetDatasetRepository.write_bars` rejects writes when metadata says `PUBLISHED`.

### 3.4 Physical Storage Layout

Given `storage_root` and a `DatasetRef`:

```text
storage_root/
├── metadata/
│   └── {instrument_id}/
│       └── {data_type}/
│           └── {timeframe}/
│               └── {provider}/
│                   └── {source_id}/
│                       └── v{version}.json      ← DatasetMetadata
└── normalized/
    └── {instrument_id}/…/v{version}/
        └── bars.parquet                         ← OHLCV bars
```

`DatasetRef` canonical string form:

```text
{instrument}|{data_type}|{timeframe}|{provider}|{source_id}@{version}
```

Path helpers: `infrastructure/storage/paths.py` — `dataset_metadata_path`, `dataset_bars_path`.

### 3.5 Parquet Schema (canonical)

Defined in `infrastructure/storage/parquet/writer.py`:

| Column | Arrow type | Domain field |
|--------|------------|--------------|
| `open`, `high`, `low`, `close` | `string` | `Price.value` as decimal text |
| `volume` | `int64` | `Volume.value` |
| `observed_at` | `timestamp(us)` | bar interval boundary (UTC) |
| `available_at` | `timestamp(us)` | when bar became knowable (UTC) |

---

## 4. Market Data — Consumer Query Workflow

```mermaid
sequenceDiagram
    participant Consumer
    participant QH as query_historical
    participant Reg as FileDatasetRegistry
    participant Repo as ParquetDatasetRepository

    Consumer->>QH: QueryHistoricalRequest(dataset_ref, start, end)
    QH->>Reg: get(dataset_ref)
    Reg-->>QH: DatasetMetadata
    alt lifecycle != PUBLISHED
        QH-->>Consumer: ValidationError
    end
    QH->>Repo: query_bars(HistoricalBarQuery)
    Repo->>Repo: read bars.parquet → list[MarketBar]
    Repo->>Repo: filter observed_at in [start, end]
    Repo-->>QH: Sequence[MarketBar]
    QH->>QH: sort by observed_at
    QH-->>Consumer: list[MarketBar]
```

**Entry point:** `trading_framework.application.market_data.query_historical`

**Read path:** Parquet `string` → `Decimal` → `Price` / `Volume` → `MarketBar`.

**Contract:** returns `list[MarketBar]` sorted by `observed_at`. This is the **repository/application boundary** used by analysis and future consumers.

Integration test reference: `tests/integration/test_csv_import_flow.py`.

---

## 5. Market Analysis — Data Input Bridge

Analysis does not read Parquet directly. It goes through the market data application layer.

```mermaid
sequenceDiagram
    participant Caller
    participant LDV as load_analysis_data_view
    participant QH as query_historical
    participant ADV as AnalysisDataView

    Caller->>LDV: LoadAnalysisDataViewRequest(dataset_ref, TimeRange)
    LDV->>QH: QueryHistoricalRequest(ref, range.start, range.end)
    QH-->>LDV: list[MarketBar]
    LDV->>ADV: from_bars(bars)
    ADV-->>LDV: AnalysisDataView
    LDV-->>Caller: AnalysisDataView
```

**Entry point:** `trading_framework.application.market_analysis.load_analysis_data_view`

### 5.1 AnalysisDataView Shape

Immutable columnar view aligned to bar timestamps:

| Field | Type | Notes |
|-------|------|-------|
| `timestamps` | `tuple[datetime, …]` | UTC `observed_at` per bar |
| `open`, `high`, `low`, `close`, `volume` | `DataColumn` | `tuple[float, …]`, dtype `float64` |

Conversion: `MarketBar` (`Price`/`Decimal`) → `float64` at the analysis boundary (decision D-027). The view is **read-only** and validated for equal column lengths.

---

## 6. Market Analysis — Planning and Execution

### 6.1 Planning (DAG)

```mermaid
flowchart TD
    REQ["ComponentRequest(s)"]
    REG["ComponentRegistry.resolve()"]
    DEP["expand component + data dependencies"]
    CYCLE["cycle detection"]
    TOPO["topological sort"]
    PLAN["ExecutionPlan(PlannedNode…)"]

    REQ --> REG --> DEP --> CYCLE --> TOPO --> PLAN
```

**Entry point:** `DependencyPlanner.build_plan(context, requests)` → `ExecutionPlan`

Each `PlannedNode` carries:

- resolved `ComponentImplementation`,
- `ComputationIdentity` (component + parameters fingerprint),
- dependency keys for upstream results,
- canonical execution order.

### 6.2 Execution Loop

```mermaid
sequenceDiagram
    participant Exec as SequentialBatchExecutor
    participant Cache as ExecutionCache
    participant WS as AnalysisWorkspace
    participant Store as AnalysisResultStore
    participant Impl as ComponentImplementation

    Exec->>WS: new AnalysisWorkspace(market_view)
    loop each PlannedNode in order
        Exec->>Cache: get(computation_identity)
        alt cache hit
            Cache-->>Exec: AnalysisResult
            Exec->>WS: register(cached)
        else cache miss
            Exec->>WS: view_for(dependency_keys)
            WS->>Store: dependency_results(keys)
            WS-->>Exec: AnalysisWorkspaceView(market, deps)
            Exec->>Impl: compute(context, workspace_view, parameters)
            Impl-->>Exec: AnalysisResult
            Exec->>Exec: validate_analysis_result(length, warmup)
            Exec->>WS: register(result)
            Exec->>Cache: put(identity, result)
        end
    end
    Exec-->>Caller: AnalysisWorkspace
```

**Entry point:** `SequentialBatchExecutor.execute(plan, market_view=…, context=…)`

### 6.3 In-Memory Analysis Data Model

```mermaid
flowchart TB
    ADV["AnalysisDataView<br/>(input OHLCV)"]
    WS["AnalysisWorkspace"]
    STORE["AnalysisResultStore<br/>dict[computation_key → AnalysisResult]"]
    CACHE["ExecutionCache<br/>(same plan, exact identity)"]
    VIEW["AnalysisWorkspaceView<br/>(read-only per node)"]
    AR["AnalysisResult<br/>OutputSeries float64 + lineage"]

    ADV --> WS
    WS --> STORE
    EXEC["SequentialBatchExecutor"] --> CACHE
    EXEC --> VIEW
    STORE --> VIEW
    ADV --> VIEW
    VIEW --> IMPL["ComponentImplementation.compute()"]
    IMPL --> AR
    AR --> STORE
```

**AnalysisResult** (per computation):

- `computation_identity` — dedup key,
- `outputs` — `Mapping[OutputId, OutputSeries]` (`tuple[float, …]`),
- `lineage`, `validity`, `warmup`, `availability` metadata.

No shared mutable DataFrame. Components receive `AnalysisWorkspaceView` with market columns plus dependency results only.

---

## 7. End-to-End Flow (Implemented Today)

```mermaid
flowchart LR
    subgraph ingest["1. Ingest"]
        A1["CSV"] --> A2["import_external_dataset"]
        A2 --> A3["finalize_dataset"]
        A3 --> A4["publish_dataset"]
    end

    subgraph persist["2. Persist"]
        A4 --> P1["vN.json + bars.parquet"]
    end

    subgraph read["3. Read"]
        P1 --> B1["query_historical"]
        B1 --> B2["list[MarketBar]"]
    end

    subgraph analysis["4. Analysis (Waves 0–3)"]
        B2 --> C1["load_analysis_data_view"]
        C1 --> C2["AnalysisDataView"]
        C2 --> C3["DependencyPlanner"]
        C3 --> C4["SequentialBatchExecutor"]
        C4 --> C5["AnalysisWorkspace / AnalysisResult"]
    end

    ingest --> persist --> read --> analysis
```

### Minimal code path (conceptual)

```python
# 1–3: Market Data (see tests/integration/test_csv_import_flow.py)
result = import_external_dataset(request, storage_root=root)
finalize_dataset(result.dataset_ref, storage_root=root)
publish_dataset(result.dataset_ref, storage_root=root)
bars = query_historical(QueryHistoricalRequest(ref, start, end), storage_root=root)

# 4: Analysis input
view = load_analysis_data_view(
    LoadAnalysisDataViewRequest(dataset_ref=ref, computation_range=range_),
    storage_root=root,
)

# 4: Plan + execute (requires registered ComponentImplementation types)
plan = DependencyPlanner(registry).build_plan(context, requests)
workspace = SequentialBatchExecutor().execute(plan, market_view=view, context=context)
```

---

## 8. Representation Boundaries

Understanding **where the type changes** prevents confusion about floats vs decimals vs strings.

```mermaid
flowchart LR
    CSV["CSV strings"]
    DEC["Decimal / Price<br/>(domain)"]
    PQ["Parquet string<br/>(storage)"]
    BAR["MarketBar<br/>(application query)"]
    F64["float64 columns<br/>(AnalysisDataView)"]
    OUT["OutputSeries float64<br/>(AnalysisResult)"]

    CSV -->|"normalize"| DEC
    DEC -->|"write_bars"| PQ
    PQ -->|"read_bars"| DEC
    DEC --> BAR
    BAR -->|"from_bars"| F64
    F64 -->|"compute"| OUT
```

| Boundary | Left | Right | Why |
|----------|------|-------|-----|
| Import | CSV text | `Decimal` / `MarketBar` | Parse and validate in domain |
| Storage | `MarketBar` | Parquet `string` prices | Lossless decimal persistence |
| Query | Parquet | `list[MarketBar]` | Canonical consumer contract |
| Analysis input | `MarketBar` | `AnalysisDataView` float64 | Numeric backend for components (D-027) |
| Analysis output | component logic | `OutputSeries` float64 | Backend-neutral result contract |

---

## 9. Not Yet Implemented (Sprint 003 Remainder)

These appear in architecture diagrams and sprint plans but **have no production code path yet**:

| Capability | Planned role in data flow |
|------------|---------------------------|
| Built-in components (TR, ATR, EMA, Volatility State) | Produce `AnalysisResult` from `AnalysisWorkspaceView` |
| `AnalysisFrameAssembler` | Wide tabular consumer view over workspace outputs |
| `run_analysis` facade | Single entry point orchestrating load → plan → execute → frame |
| Persistent analysis cache | Cross-run deduplication (MVP uses in-memory `ExecutionCache` only) |
| Multitimeframe alignment | Separate bars per timeframe; not in MVP flow |

---

## 10. Quick Reference — Entry Points

| Workflow step | Module | Function / type |
|---------------|--------|-----------------|
| CSV import | `application.market_data` | `import_external_dataset` |
| Finalize / publish | `application.market_data` | `finalize_dataset`, `publish_dataset` |
| Historical bars | `application.market_data` | `query_historical` → `list[MarketBar]` |
| Analysis input | `application.market_analysis` | `load_analysis_data_view` → `AnalysisDataView` |
| Register components | `market_analysis.registry` | `ComponentRegistry` |
| Build DAG | `market_analysis.planning` | `DependencyPlanner.build_plan` |
| Execute plan | `market_analysis.execution` | `SequentialBatchExecutor.execute` |
| Result lookup | `market_analysis.storage` | `AnalysisResultStore`, `AnalysisWorkspace` |

---

## Maintenance

Update this document when:

- a new application workflow changes how data moves between layers,
- storage schema or lifecycle rules change,
- analysis input/output contracts change.

After small wave merges: update §9 and diagrams if status changed.  
Navigation status symbols stay in [MODULE_MAP.md](MODULE_MAP.md).
