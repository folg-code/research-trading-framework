# Data Representation Audit and Target Policy

```text
Status:        ACCEPTED (policy) — D-REP-06, D-REP-08, D-REP-09 remain PROPOSED
Audit Date:    2026-08-25
Decision Date: 2026-08-25 (maintainer)
Scope:         src/trading_framework/** (409 files, ~37k LOC), apps/**, scripts/** (boundary only)
Sprint:        036 — Research Infra Audit (task S036-T003)
Sprint Branch: sprint/research-infra-audit
Code Baseline: f0a82c5 (includes #273 bench harness, #274 session metadata, #275 evaluation
               dataframe vectorization, #276 UTC datetime series)
Method:        static read-only inspection; no measurements re-run in this pass
```

**Baseline note.** Sprint 036 optimizations #274–#276 had already landed when this audit was written.
Where they partially address a finding, §6.2 says so explicitly. Line references are valid as of
`f0a82c5` and should be re-checked after any Stage 1 PR.

**Progress note (2026-08-25).** Stage 0.5 shipped in #279 (`session_id` stays Utf8; timezone remains
its own eager pass). T006 harness coverage shipped in #278 (`--mtf`, `--parquet`). Measured H2/H6/H4
notes are in §6.3; Stage 1 H2 shipped in #281 and derive-path table validation in #282. Stage 2
step 1 (`scan_parquet` + session-date prune on `query_ohlcv_table`) is in §6.3.1; step 2
(lazy `build_analysis_frame`) is in §6.3.2 / §8.

**Decision summary (2026-08-25).** Accepted: D-REP-01 (with superseding ADR; `AnalysisDataView`
retained as a live-runtime adapter), D-REP-02 (two-step), D-REP-03, D-REP-04a, D-REP-05, D-REP-07,
D-REP-10 (sidecar variant). Deferred to a dedicated sprint: D-REP-04b. Still open: D-REP-06,
D-REP-08, D-REP-09. Research artifacts in `user_data/` **may be rebuilt**; market data must not be
migrated as part of this work.

This document answers three questions:

1. **What we have** — which objects exist, what data types carry them, where representations change (§2–§3, §6).
2. **What is canonical** — which type is the correct carrier for each kind of work (§4–§5).
3. **What to eliminate** — which conversions are redundant and in what order to remove them (§7–§8).

Sections §1–§3, §5.1 and §6 are **descriptive** (established facts about current code).
Sections §4, §5.2 and §7–§8 are **prescriptive** and carry decisions marked `PROPOSED`.
No `PROPOSED` item may be implemented before it is accepted by the maintainer and, where noted,
materialized as an ADR amendment.

---

## 1. Executive Summary

### 1.1 What representations exist

| Mechanism | Count | Where |
|---|---|---|
| `@dataclass(frozen=True, slots=True)` | 164 | domain facts, value objects, DTOs, configs, results — the dominant contract style |
| `@dataclass` mutable | 7 | `PaperBroker`, `LocalExecutionRuntimeSession`, `ContractChunkColumns`, `PhaseTimer`/`_PhaseFrame`, Binance WS clients, `_ComponentEntry`, `SharedStrategyEvaluationCache` |
| `pydantic.BaseModel` | 1 | `config/models.py::FrameworkConfig` only |
| `TypedDict` | 1 | `DatabentoStorageTradeFields` |
| `NamedTuple`, `NewType` | 0 | unused |
| `Protocol` | ~25 | ports only (clocks, repositories, sinks, readers, component contracts) |
| `StrEnum` | ~30 | classifications, statuses, policies |
| `pl.DataFrame` | 66 files | analytics, model evaluation, research facts, reporting |
| `pl.LazyFrame` / `.lazy()` / `scan_parquet` | **0 occurrences** | not used anywhere |
| `np.ndarray` | 19 files | component kernels, simulation kernels, Databento import buffers, Polars ingest helpers |
| `pa.Table` / `pa.schema` | ~20 files | all persistence |
| `tuple[float, ...]` | 39 declarations | the canonical Market Analysis series carrier |
| `iter_rows` / `to_dicts` / `Decimal(str(...))` | 9 / 14 / 84 | row-wise and precision-restoring conversion sites |

### 1.2 Where the largest inconsistency is

**Price.** One concept, five carriers:

```text
Price(Decimal)              domain          market/models, execution/models
pa.string()                 storage         bars, trades, continuous trades Parquet
int64 price_nanos           storage         contract trades Parquet v2
float64                     analysis        AnalysisDataView, Polars, research
float                       presentation    apps/dashboard TradeView
```

Two of these are **both persistence schemas for the same layer**, bridged at runtime by a hand-written
Polars expression (`_price_nanos_to_string_expr`). This was consciously accepted as
[D-S027-08](../planning/sprints/S027_WAVE0_DECISIONS.md) and remains the single largest
representation split in the system.

**Timestamp** is second, with four carriers: UTC-aware `datetime` (domain), naive `timestamp("us")`
(Parquet), `int64` nanoseconds (contract storage, simulation kernels), epoch-milliseconds (telemetry,
Binance). The "naive means UTC" convention is re-implemented by hand in every reader and writer.

### 1.3 What generates the largest cost

**Measured** on the authoring → analysis → evaluate path (§6.1, 10 000 bars):

1. **`resolve_sessions` — 59 % of `run_analysis` at the §6.1 baseline.** `CmeEsRthSessionResolver`
   was vectorized but ran four chained *eager* `with_columns` plus a timezone conversion and a Utf8
   `session_id` column. #279 fused the RTH/`session_id` work into one pass (**36.25 ms → ~29–31 ms**
   at 10k bars); timezone conversion remains its own pass. Still the clearest evidence for D-REP-02.
2. **`build_evaluation_table` — 89 % of `evaluate_models`.** Still dominant after the #275
   vectorization; the residue is frame construction plus per-AST-node scratch frames.
3. **Component `execute` — 39 % of `run_analysis`**, including the `tuple[float, ...]` ↔ `np.ndarray`
   crossings.

Planning, frame assembly, view loading and DSL compile together stay under 2 % and are flat in bar
count — DSL compile is 0.2 ms at every size, so Sprint 037 has headroom.

**Structural, now partly measured** (§6.3 after #278):

4. **No `LazyFrame` anywhere.** 66 Polars files run fully eager: no predicate or projection pushdown,
   no streaming, every Parquet read materializes the whole file. Synthetic `--parquet` at 500 1m bars
   showed file I/O cheap versus `ohlcv.build_column_batch`; dataset-scale H1 is still open.
5. **The resample round-trip (H2) is material.** `--mtf` at 500 1m bars: `execute.resample` **~24 ms**
   versus default `p2` **~10 ms**. Alignment (H6) is **~0.6 ms** at this scale — not a Stage 1 target.
6. **Object materialization on bulk paths** (TD-011 / H4): `list[MarketBar]` in `query_historical`,
   CSV import, derivation validation and dashboards. `--parquet` times `query_historical_columnar`,
   so H4 itself remains unmeasured.

### 1.4 The five target decisions

| ID | Decision | Status | Repays | Conflicts with |
|---|---|---|---|---|
| D-REP-01 | `MarketFrame(pl.LazyFrame, metadata)` becomes the canonical bulk representation contract | ACCEPTED — requires superseding ADR | TD-011, TD-015 | ADR-MA-004, ADR-MA-010 |
| D-REP-02 | Lazy is the default Polars mode at I/O boundaries and inside analytical pipelines | ACCEPTED — two-step | — | — |
| D-REP-03 | Eliminate the `MarketBar`/`Decimal` round-trip in resampling and in table validation | ACCEPTED — Sprint 036 | TD-011 | — |
| D-REP-04a | Simulation PnL persisted as `int64` minor units instead of `pl.Float64` | ACCEPTED | TD-012 | — |
| D-REP-04b | Unify Parquet price schemas on `price_nanos` | DEFERRED — dedicated sprint | TD-012, TD-020 | D-S027-08, ADR-0018 |
| D-REP-05 | `available_at` becomes a first-class column instead of being reconstructed downstream | ACCEPTED — additive first | — | — |

Full decision register with risk assessment: §7.

---

## 2. Current Representation Map

### 2.1 Layer overview

```text
provider / archive        pandas.DataFrame, raw JSON, DBN binary
        |
import adapters           ContractChunkColumns (NumPy SoA), DatabentoStorageTradeFields (TypedDict)
        |
persistence               pa.Table + pa.schema  ->  Parquet
        |                 metadata: frozen dataclass -> to_dict() -> JSON
        |
domain facts              MarketBar, MarketTrade, ContractTradeRecord (frozen dataclasses)
        |                 money: Price(Decimal) / Volume(int)
        |
analysis input            AnalysisDataView / OhlcvColumnBatch  (tuple[float, ...])
        |
component kernels         np.ndarray[float64]
        |
component results         OutputSeries (tuple[float, ...]) + AnalysisResult + Lineage
        |
frame assembly            AnalysisFrame (Mapping[str, tuple[float, ...]])
        |
model evaluation          pl.DataFrame  <-- the hinge; everything downstream stays Polars
        |
signal / strategy         pl.DataFrame (occurrences, emissions)
        |
simulation                np.ndarray (Numba kernels) -> Decimal facts -> pl.DataFrame (Float64)
        |
research analytics        pl.DataFrame + frozen dataclasses (Decimal for money, float for ratios)
        |
persistence / reporting   Parquet (bulk) + JSON (metadata, Decimal as str) + HTML
```

### 2.2 Objects and representations

Grouped by module. `frozen` is shorthand for `@dataclass(frozen=True, slots=True)`.

#### core, time, config, events

| Object | Module | Data type | Role | Notes |
|---|---|---|---|---|
| `Identifier` | `core/identifiers` | `frozen` over `str` | identity VO | normalizes via `object.__setattr__` |
| `Price` | `core/types` | `frozen` over `Decimal` | value object | `to_json`/`from_json` = `Decimal ⇄ str` |
| `Volume` | `core/types` | `frozen` over `int` | value object | JSON as `int` — asymmetric with `Price` |
| `Timeframe` | `time/models` | `frozen` over `str` | value object | regex `^(\d+)([mhd])$` or `"tick"` |
| `require_utc_aware` | `time/models` | function | invariant guard | rejects naive datetimes |
| `utc_datetime_series` | `time` | function | conversion helper | `tuple[datetime] → np.int64 epoch µs → pl.Series(Datetime("us","UTC"))`; the shared tuple→Polars timestamp boundary since #276, and the one place already producing tz-aware Polars datetimes |
| `Clock`, `TradingSessionResolver` | `time` | `Protocol` | ports | resolver: `pl.Series → pl.DataFrame` |
| `CmeEsRthSessionResolver` | `time/sessions` | `frozen` + Polars | policy object | only natively Polars time object |
| `FrameworkConfig` | `config` | **pydantic v2** | config DTO | only Pydantic model in `src/` |
| — | `events` | — | — | package is empty; the real event contract lives in `execution/models/events.py` |

#### market

| Object | Module | Data type | Role | Notes |
|---|---|---|---|---|
| `MarketBar` | `market/models` | `frozen` | OHLCV domain fact | `Price`/`Volume`; enforces UTC and OHLC consistency |
| `MarketTrade`, `TradeSide` | `market/models` | `frozen`, `StrEnum` | trade domain fact | invariant `received_at >= event_at` |
| `Instrument`, `AssetClass` | `market/models` | `frozen`, `StrEnum` | identity VO | metadata capped at 16 entries |
| `ContractTradeRecord` | `market/contracts` | `frozen` | storage DTO | already scalar: `ts_event_ns: int`, `price_nanos: int` |
| storage codecs | `market/contracts` | functions | encode/decode | `datetime ⇄ int64 ns`, `Decimal ⇄ int64 nanos` |
| `ContinuousTradeRecord` | `market/continuous` | `frozen` | storage DTO | only record nesting a domain object (`trade: MarketTrade`) |
| `RollSchedule`, `RollScheduleEntry` | `market/continuous` | `frozen` | result aggregate | `entries: tuple[...]` |
| `VolumeRthCloseRollPolicy`, `RollSwitchAt` | `market/continuous` | `frozen`, `StrEnum` | policy | |
| `DatasetId`, `DatasetRef`, `DatasetMetadata` | `market/datasets` | `frozen` | identity / metadata | hand-written `to_dict`/`from_dict` |
| `DatasetLifecycleState` | `market/datasets` | `StrEnum` + `dict[…, frozenset]` | state machine | legal transitions as module constant |
| `NormalizedBarRow` | `market/normalization` | `frozen` | pre-domain DTO | `Decimal` + `int` + `datetime` |
| `ValidationResult`, `ValidationIssue` | `market/validation` | `frozen` | result | `to_dict()` hand-written |
| `DerivedOhlcvFromTradesConfig` | `market/derivation` | `frozen` | config | `lineage()` returns plain dict |
| `TradesToBarsAggregator` | `market/derivation` | plain class | domain service | pure-Python bucketing over `Decimal` |
| repository/importer ports | `market/repositories`, `market/importers` | `Protocol` | ports | operate on `Sequence[MarketBar\|MarketTrade]`, never Arrow |

#### infrastructure

| Object | Module | Data type | Role | Notes |
|---|---|---|---|---|
| `MARKET_BAR_PARQUET_SCHEMA` | `storage/parquet` | `pa.schema` | serialization schema | prices `pa.string()`, timestamps **naive** `timestamp("us")` |
| `MARKET_TRADE_PARQUET_SCHEMA` | `storage/parquet` | `pa.schema` | serialization schema | price `pa.string()` |
| `MARKET_TRADE_CONTRACT_PARQUET_SCHEMA` v2 / v1 | `storage/parquet` | `pa.schema` ×2 | versioned schema | v2 fully `int64`; v1 upgraded inside the read path |
| `MARKET_TRADE_CONTINUOUS_PARQUET_SCHEMA` | `storage/parquet` | `pa.schema` | serialization schema | price `pa.string()` (D-S027-08) |
| `ROLL_SCHEDULE_PARQUET_SCHEMA` | `storage/parquet` | `pa.schema` | serialization schema | `date32()` session bounds |
| `ContractChunkColumns` | `importers/databento` | mutable dataclass, 8× `NDArray` | columnar SoA buffer | append-only, cached concat (TD-019 repaid) |
| `DatabentoStorageTradeFields` | `importers/databento` | `TypedDict` | per-row scalar bundle | only `TypedDict` in repo |
| `InstrumentIdentityCache` | `importers/databento` | plain class + `dict` | memoization | |
| `Binance*Payload` | `providers/binance` | `frozen` | raw payload DTO | numeric fields kept as `str`, parsing deferred |
| `*Manifest` (import, continuous, roll schedule) | `storage` | `frozen` | persisted record | `to_dict`/`from_dict` |
| `JsonExecutionStateRepository` | `storage` | `frozen` | repository adapter | largest hand-written JSON codec surface |
| `PhaseTimer`, `PhaseStats` | `observability` | mutable dataclass | metrics accumulator | |
| `DatasetMetadataReader` | `storage/parquet` ×4 | `Protocol` | port | **declared identically in four modules** |

#### market_analysis, model_expression, model_authoring, market_model, signal_model, strategy

| Object | Module | Data type | Role | Notes |
|---|---|---|---|---|
| `ComponentId`, `ImplementationId`, `*Version` | `identity` | `frozen` over `str` | identity VO | regex / SemVer validated |
| `ComputationIdentity`, `ResampleIdentity`, `AlignmentIdentity` | `identity` | `frozen` + `json.dumps` | cache key | canonical JSON **is** the key; `__hash__` over it |
| `CanonicalParameters` | `models` | `frozen`, sorted `tuple[tuple[str, Any], ...]` | parameters / fingerprint | `fingerprint()` = sorted-key JSON |
| `ParameterSchema`, `OutputSchema`, `OutputFieldSpec` | `models` | `frozen` | component contract | |
| `OutputSeries` | `models` | `frozen`, **`tuple[float, ...]`** | result payload | deliberately backend-neutral; no null representation, NaN is the sentinel |
| `AnalysisResult` | `models` | `frozen` | result contract | identity + schema + lineage + validity + warmup + availability |
| `Lineage` | `models` | `frozen` | provenance | `to_json_dict()` |
| `AnalysisDataView`, `DataColumn` | `data` | `frozen`, `tuple[float, ...]` | canonical market input | float64 per D-027; **does not carry `available_at`** |
| `OhlcvColumnBatch` | `data` | `frozen`, tuples | columnar batch | |
| `SwingStructureResult` | `adapters/numpy` | `frozen`, 21× `np.ndarray` | kernel result | only domain-adjacent dataclass holding ndarrays |
| `AnalysisWorkspace`, `AnalysisResultStore`, `ExecutionCache`, `ResampleCache`, `AlignmentCache` | `storage`, `execution`, `assembly` | plain classes + `dict[str, …]` | caches | keyed by `canonical_key()`; see TD-014 |
| `ExecutionPlan`, `PlannedNode`, `ResampleNode` | `planning` | `frozen`, tuples | DAG | Kahn sort over plain dict/set |
| `BatchAnalysisComponent`, `ComponentImplementation` | `protocols` | `Protocol` | component contract | structural typing |
| `_ComponentEntry` | `registry` | mutable dataclass | registry entry | only non-frozen dataclass in the module |
| `AnalysisFrame` | `assembly` | `frozen`, `Mapping[str, tuple[float, ...]]` | wide consumer view | carries `column_lineage` |
| `TradingSessionMetadata` | `assembly` | plain class with `__slots__` wrapping `pl.DataFrame` | session metadata | since #274 keeps the resolver frame and materializes tuples lazily per property; equality delegates to `frame.equals` — the only analysis object that already follows the D-REP-01 shape |
| `Expression` AST nodes | `model_expression` | `frozen` + union alias | IR | self-referential via quoted `"Expression"` |
| `ComponentOutputReference`, `MarketFieldReference` | `model_expression` | `frozen` | operands | factory methods producing `market_analysis` contracts |
| `Condition` + 5 subclasses, `Operand` | `model_authoring` | `frozen` | DSL IR | operator overloading builds conditions |
| model evaluation result | `model_expression/evaluation`, `market_model`, `signal_model` | **`pl.DataFrame`** | result payload | columns `timestamp`, `available_at`, `model_result` |
| `StrategyModelDefinition`, `FixedQuantityRiskModel`, `FixedBarsExitModel` | `strategy` | `frozen`, `Protocol` | composition root | `quantity: Decimal` |
| `ReferencePriceLookup` | `strategy` | `frozen`, `dict` + tuples | lookup | `to_frame()` → `pl.DataFrame` (TD-017 repayment) |
| signal occurrence table | `strategy` | `pl.DataFrame`, explicit schema | fact table | `occurrence_id` = SHA-256[:16] |

#### research

| Object | Module | Data type | Role | Notes |
|---|---|---|---|---|
| `CompiledBarSeries`, `CompiledEntrySignals` | `simulation` | `frozen`, `NDArray[int64/float64/int8]` | kernel input | Numba-compatible |
| `FixedBarsKernelResult` | `simulation/kernels` | `frozen`, 15× `NDArray` | kernel output | preallocate then slice `[:trade_count]` |
| `SimulatedTrade`, `EquityPoint` | `simulation` | `frozen`, `Decimal` | domain fact | |
| `simulated_trade_schema()` | `simulation` | `dict[str, pl.DataType]` | persistence schema | **money persisted as `pl.Float64`** |
| `SimulationAssumptions` | `simulation` | `frozen`, `Decimal` | binding config | part of run identity |
| outcome / observation / context tables | `outcomes`, `observations`, `context` | `pl.DataFrame` + explicit schema | fact tables | `pl.Float64`, nullable |
| `*Analytics` (5 families) | `robustness/analytics` | `frozen`, mixed `Decimal`/`float` | statistics result | each with `to_dict`/`from_dict` |
| `StitchedOosEquity` | `robustness/analytics` | `frozen` with embedded `pl.DataFrame` | result | only dataclass round-tripping a live frame through JSON |
| `*Spec` (experiment, walk-forward, MC, stress) | `robustness` | `frozen` | declarative spec | `Decimal` serialized as `str` |
| `SignalResearchDefinitionSpec` | `signal_research` | `frozen` | study contract | hash = SHA-256 of canonical JSON |
| `*RunEnvelope`, `*RunManifest` | `datasets` | `frozen` + 2–4 `pl.DataFrame` | dataset payload | envelope = frames, manifest = JSON |
| analytics schemas | `analytics/schemas.py` | functions → `dict[str, pl.DataType]` | validated schemas | `validate_*` checks columns **and** dtypes |
| `SignalResearchReportSource` | `reporting` | `Protocol` with `pl.DataFrame` fields | presentation port | only `Protocol` in `research/` |
| `StrategyDashboard*` view models | `analytics` | `frozen`, mixed `Decimal`/`float` | presentation model | |

#### application, execution, apps

| Object | Module | Data type | Role | Notes |
|---|---|---|---|---|
| `OrderIntent`, `SimulatedOrder`, `SimulatedFill`, `PaperPosition`, `PaperAccountSnapshot` | `execution/models` | `frozen`, `Decimal`/`Price` | execution facts | shared validators in `_validation.py` |
| `ExecutionEvent` | `execution/models` | `frozen`, **`Mapping[str, str]`** payload | event envelope | values pre-stringified by the caller |
| `Recent*View`, `RuntimeStatusView` | `execution/repositories` | `frozen` | read models | `from_event()` mapper |
| `PaperBroker` | `execution/broker_sim` | mutable dataclass | stateful service | `Decimal` arithmetic end to end |
| `LiveSignalEvaluation` | `execution/runtime` | `frozen`, **`float`** | live signal result | first `float` inside `execution/` |
| ~30 `*Request`/`*Result` pairs | `application/**` | `frozen` | use-case boundary | several return `pl.DataFrame` directly |
| `AwsBtcFuturesRuntimeConfig` | `application/execution` | `frozen` + hand parsers | env-sourced config | Pydantic's role, without Pydantic |
| `SharedStrategyEvaluationCache` | `application/strategy_research` | mutable dataclass | memoization | TD-018 repayment |
| `TradeView`, `RunSummary` | `apps/dashboard` | `frozen`, **`float`** | presentation DTO | deliberately decoupled from `trading_framework` |

---

## 3. Transformation Map

Every material representation crossing, grouped by pipeline stage.

### 3.1 Ingest — provider to storage

| Source | Source type | Transformation | Target type | Location | Reason |
|---|---|---|---|---|---|
| DBN archive | `pandas.DataFrame` | `DBNStore.to_df(count=…)` | chunk iterator | `importers/databento/reader.py:29-40` | bound memory on large archives |
| pandas column | int64 / datetime64 / float | `normalize_ts_series`, `normalize_price_series` | `np.ndarray[int64]` | `databento/storage_normalizer.py:81-163` | vectorize instead of per-row parsing |
| pandas chunk | frame + bool mask | `map_trades_chunk_to_contract_columns` | `ContractChunkColumns` | `databento/chunk_batch_mapper.py:23-68` | group by contract without Python objects |
| `ContractChunkColumns` | NumPy SoA | `contract_trade_columns_to_table` | `pa.Table` | `parquet/contract_trade_writer.py:117-153` | skip per-row dataclasses (TD-019) |
| `ContractChunkColumns` | NumPy SoA | `_storage_fields_from_columns` | `list[TypedDict]` → `MarketTrade` | `databento/contract_reader.py` | bridge for legacy row consumers |
| CSV row | `Mapping[str, str]` | `UtcOhlcvNormalizer.normalize_row` | `NormalizedBarRow` | `normalization/utc_ohlcv_normalizer.py:66-87` | first typed representation |
| Binance JSON | `dict[str, Any]` | `parse_kline_payload` → `map_kline_payload` | `MarketBar` | `providers/binance/futures_payloads.py:87-135`, `futures_mapper.py:44-48` | narrow untyped JSON before domain use |
| Binance REST | `list[object]` positional | `_rest_row_to_kline_payload` | `BinanceKlinePayload` | `providers/binance/futures_rest.py:108-132` | name positional array fields |

### 3.2 Numeric encoding

| Source | Source type | Transformation | Target type | Location | Reason |
|---|---|---|---|---|---|
| `Price` | `Decimal` | `price_nanos_from_decimal` (×1e9) | `int` | `market/contracts/storage_codec.py:29-32` | exact fixed-point storage, no float |
| nanos | `int` | `decimal_price_from_nanos` | `Decimal` | `storage_codec.py:35-37` | decode to domain |
| `Price` | `Decimal` | `str(value)` | `pa.string()` | `parquet/writer.py:31-34`, `trade_writer.py:29`, `continuous_trade_writer.py:39` | exact decimal as text (legacy schema) |
| Parquet | `pa.string()` | `Decimal(str(v))` | `Price` | `parquet/writer.py:75-78`, `trade_writer.py:69` | reconstruct domain |
| nanos | Polars `int64` | `_price_nanos_to_string_expr` | `pl.Utf8` | `continuous_trade_table_mapper.py:20-28` | bridge v2 contract schema to string continuous schema |
| price string | Polars | cast → `Float64` → OHLC agg → cast | `pa.Utf8` | `continuous_trades_to_ohlcv_table.py:73-83` | float only as aggregation intermediate |
| legacy v1 | `price: str` | `_upgrade_legacy_contract_trade_table` | `int64` v2 | `parquet/contract_trade_table_merge.py:95` | schema migration inside the read path |
| Binance | `str` | `_volume_from_decimal_text` (`ROUND_FLOOR`) | `Volume(int)` | `providers/binance/futures_mapper.py:20-26` | integer volume domain type |

### 3.3 Temporal encoding

| Source | Source type | Transformation | Target type | Location | Reason |
|---|---|---|---|---|---|
| `datetime` UTC | aware | `utc_ns_from_datetime` | `int64` ns | `storage_codec.py:21-26` | canonical scalar storage |
| `datetime` | aware | `.astimezone(UTC).replace(tzinfo=None)` | naive `timestamp("us")` | `parquet/writer.py:36-37`, `trade_writer.py:31`, `continuous_trade_writer.py:41` | Parquet schema has no timezone |
| Parquet | naive | `.replace(tzinfo=UTC)` | aware | `parquet/writer.py:80-81`; `application/market_data/ohlcv_columnar.py:30-31`; `materialize_continuous_trades.py:274` | **assumption, not validation** |
| `Sequence[datetime]` | tuple | `pl.Series` → session resolver | `list[date]` | `market/contracts/session_date.py:24-56` | vectorized CME session classification |
| `datetime` | aware | `datetime_to_epoch_ns` | `int64` | `research/simulation/compile.py:74-81` | Numba cannot hold datetime |
| `datetime` | aware | `int(ts.timestamp() * 1000)` | epoch-ms | `application/execution/aws_telemetry.py:153` | CloudWatch EMF format |
| `datetime` | aware | `.isoformat()` / parse | `str` | ~15 JSON codecs incl. `datasets/metadata.py:27-32`, `storage/execution_state.py:478-483` | JSON has no datetime type |

### 3.4 Storage to analysis

| Source | Source type | Transformation | Target type | Location | Reason |
|---|---|---|---|---|---|
| Parquet | `pa.Table` | `pc.cast(…, float64)` + `to_pylist` | `OhlcvColumnBatch` | `application/market_data/ohlcv_columnar.py:14-59` | **Decimal → float64 boundary** |
| `pa.Table` | Arrow | `market_bars_from_table` | `list[MarketBar]` | `application/market_data/derive_continuous_ohlcv.py:366` | validator only accepts dataclasses |
| `list[MarketBar]` | dataclass | `_legacy_bars_to_table` | `pa.Table` | `application/market_data/query_historical.py:106-109` | fallback for non-Arrow repositories |
| `MarketBar` | `Decimal` | `_as_float64_tuple` | `AnalysisDataView` | `market_analysis/data/view.py:15-16,66-81` | float64 analysis contract (D-027) |
| `pa.Table` | Arrow | `pl.from_arrow` | `pl.DataFrame` | `continuous_trade_table_mapper.py:50`, `contract_rth_volumes.py:25`, `continuous_trades_to_ohlcv_table.py:37,96` | need `group_by_dynamic` and expressions |
| `pl.DataFrame` | Polars | `.to_arrow()` | `pa.Table` | `continuous_trade_table_mapper.py:80`, `continuous_trades_to_ohlcv_table.py:83` | hand back to PyArrow writer |

### 3.5 Analysis internals

| Source | Source type | Transformation | Target type | Location | Reason |
|---|---|---|---|---|---|
| `AnalysisDataView` | tuples | `analysis_view_to_polars` | `pl.DataFrame` | `data/resample.py:22-33` | need `group_by_dynamic` |
| `pl.DataFrame` | Polars | `group_by_dynamic().agg(...)` | `pl.DataFrame` | `data/resample.py:36-67` | OHLCV resampling |
| `pl.DataFrame` | Polars | `iter_rows` → `Decimal(str(float))` → `Price` | `tuple[MarketBar, ...]` | `data/resample.py:70-94` | rebuild domain before `from_bars` |
| `tuple[MarketBar]` | dataclass | `from_bars` (`float(Decimal)`) | tuples | `data/resample.py:97-102` | close the resample loop |
| tuples | `tuple[datetime]` | `_timestamps_to_ns` | `NDArray[int64]` | `data/align.py:27-32` | `np.searchsorted` |
| tuples | `tuple[float]` | `np.asarray` → `np.full` → `tuple(float(v))` | tuples | `data/align.py:59-70` | `EVENT_AT_AVAILABLE` alignment |
| tuples ×2 | tuples | 2× `pl.DataFrame` → `join_asof` → `to_list` | tuples | `data/align.py:104-123` | `LAST_CLOSED_BAR` alignment |
| tuples | `tuple[float]` | `np.asarray(dtype=float64)` | `np.ndarray` | `components/trend/ema.py:84`, `volatility/true_range.py:82-84`, `structure/swing.py:247-248` | kernels require ndarray |
| `np.ndarray` | ndarray | `ndarray_to_output_series` | `OutputSeries` | `adapters/numpy/result_builder.py:34-35` | return to backend-neutral contract |
| `AnalysisResult` map | dataclass | `dependency_results_values` | `np.ndarray` | `adapters/numpy/result_builder.py:147-157` | dependent kernel input (ATR from TR) |
| tuples | `tuple[datetime]` | `utc_datetime_series` → resolver → retained frame | `TradingSessionMetadata` | `assembly/session_metadata.py:63-80` | session resolver is Polars-based; tuples materialized lazily on property access (#274) |
| `tuple[datetime]` | tuple | `np.fromiter` epoch µs → `pl.Series` | `pl.Series(Datetime("us","UTC"))` | `time/utc_datetime_series.py:14-33` | shared vectorized timestamp ingest, validates tz-awareness (#276) |

### 3.6 Analysis to models and research

| Source | Source type | Transformation | Target type | Location | Reason |
|---|---|---|---|---|---|
| `AnalysisFrame` | tuples | `build_evaluation_dataframe`: `np.asarray` per column → `pl.Series`; `available_at` via `pl.duration` | `pl.DataFrame` | `model_expression/evaluation/frame_adapter.py:11-30` | **the hinge**: tuples → Polars. Vectorized in #275; `available_at` is now derived from `evaluation_timeframe.total_seconds` rather than per-row `derive_bar_interval` |
| `pl.Series` | Polars | wrap in scratch `pl.DataFrame` for `when/then` | `pl.Series` | `evaluation/evaluator.py:131,164,179,192,205` | null-aware three-valued logic |
| `pl.DataFrame` | Polars | `select`/`rename`/`with_columns(lit)` | `pl.DataFrame` | `market_model/results.py:6-14`, `signal_model/results.py:6-16` | attach model identity |
| dense condition | `pl.Series` | `shift(1)` + `when/then` → `filter` | sparse emissions | `signal_model/firing.py:24-44`, `evaluation.py:54-64` | firing policy |
| emissions | `pl.DataFrame` | `join` + `to_list` + SHA-256 + `pl.Series` | occurrence table | `strategy/signal_occurrence.py:78-102` | deterministic occurrence identity |
| `Sequence[MarketBar]` | `Decimal` | `float(...)` + `np.fromiter` | `CompiledBarSeries` | `research/simulation/compile.py:84-156` | Numba input |
| `pl.DataFrame` | Polars | `iter_rows` → `int8` coding | `CompiledEntrySignals` | `research/simulation/compile.py:159-198` | Numba input |
| NumPy | ndarray | `@njit` kernel (plain float/int) | `FixedBarsKernelResult` | `kernels/fixed_bars.py:46-336` | no `Decimal` inside kernels |
| kernel result | ndarray | `Decimal(str(float(v)))` | `SimulatedTrade`, `EquityPoint` | `kernels/fixed_bars.py:127-189` | restore money semantics |
| `SimulatedTrade` | `Decimal` | `float(...)` → `pl.DataFrame(Float64)` | `pl.DataFrame` | `simulation/facts.py:98-140` | persistence schema |
| occurrences | `pl.DataFrame` | `.to_numpy()`, `.to_list()` → `int8` | `np.ndarray` ×3 | `research/outcomes/calculator.py:242-253` | vectorized forward outcomes |
| ndarrays | ndarray | `float(v)` → `list[dict]` → frame | outcome table | `research/outcomes/calculator.py:173-202` | `_STATUS_OMIT` rows dropped |

### 3.7 Research analytics, persistence and reporting

| Source | Source type | Transformation | Target type | Location | Reason |
|---|---|---|---|---|---|
| `pl.DataFrame` | Polars | `.to_dicts()` / `.to_list()` | `list[dict]`, `list[float]` | `analytics/quality_flags.py:61,160,223,292` | small per-row threshold checks |
| `pl.DataFrame` | Polars | `iter_rows(named=True)` + `float(...)` | row dataclasses | `analytics/strategy_dashboard.py:196-231`, `strategy_dashboard_metrics.py:311-359` | presentation without Polars |
| Polars aggregate | scalar | `Decimal(str(frame[col].sum()))` | `StrategyRunSummary` | `analytics/strategy_summarize.py:26-77` | money returns to Decimal |
| trades | `pl.DataFrame` | `Decimal(str(v))` over `to_list()` | `list[Decimal]` | `robustness/analytics/monte_carlo.py:163` | exact-arithmetic resampling |
| variance | `Decimal` | `float` → `math.sqrt` → `Decimal(str(...))` | `Decimal` | `robustness/analytics/diagnostics.py:304` | no Decimal `sqrt` |
| trades | `pl.DataFrame` | `iter_rows` + `Decimal` accumulation → `float` | `pl.Series` | `robustness/analytics/stress.py:148-170` | rebuild equity after removal |
| `*Analytics` | dataclass | `to_dict()` (`Decimal → str`) → `json.dumps` | JSON | 46 `to_dict` methods repo-wide | lossless Decimal round-trip |
| `*Analytics` | dataclass | `_optional_float` → rows → frame | Parquet | `robustness/analytics/parquet_tables.py:26-262` | **dual write** alongside JSON |
| `StitchedOosEquity` | `pl.DataFrame` | `.to_dicts()` → JSON → `pl.DataFrame(rows, schema)` | frame | `robustness/analytics/walk_forward.py:62,86-91` | only frame round-tripped through JSON |
| `AnalyzeSignalResearchResult` | frames | `.to_dicts()` ⇄ `pl.DataFrame(rows, schema)` | JSON envelope | `application/signal_research/analytics_envelope.py:44-241` | analytics cache sidecar |
| same result | frames | `signal_analytics_parquet_tables` | named Parquet | `application/signal_research/analytics_parquet.py:28-64` | **dual write** for dashboard |
| frames | Polars | `.to_dicts()` → lists → `go.Figure` → `pio.to_html` | HTML | `reporting/signal_research/report_html.py:124-564`, `plotly_figures.py:28-300` | Plotly needs Python lists |

### 3.8 Execution and application boundaries

| Source | Source type | Transformation | Target type | Location | Reason |
|---|---|---|---|---|---|
| TOML text | `str` | `tomllib.loads` → `model_validate` | `FrameworkConfig` | `config/loader.py:12-28` | validated local config |
| env vars | `Mapping[str, str]` | hand parsers `_decimal`/`_int`/`_float` | `AwsBtcFuturesRuntimeConfig` | `application/execution/aws_btc_futures_runtime.py:110-132,234-266` | same role, no Pydantic |
| `Decimal`/`datetime` | domain | `format(v, "f")`, `.isoformat()` | `Mapping[str, str]` | `execution/runtime/session.py:74,126,149-162` | event envelope is string-only |
| `RuntimeStatusView` | dataclass | `format(Decimal, "f")`, `Price.to_json()` | JSON dict | `application/execution/status_json.py:20-135` | canonical API/CLI serialization |
| `Price` | `Decimal` | `float(close.value)` | `float` | `execution/runtime/live_signals.py:100` | live path matches float64 analysis |
| `tuple[MarketBar]` | dataclass | `AnalysisDataView.from_bars` | analysis view | `execution/runtime/live_signals.py:267` | same engine in live and backtest |
| `Decimal` | domain | `str(v)` → manifest → `Decimal(v)` | `Decimal` | `run_walk_forward_experiment.py:308,311` → `analyze_walk_forward.py:134-135` | JSON round-trip |
| `Decimal` | domain | `format(v, "f")` → run id | `str` | `run_robustness_experiment.py:273` and 4 sibling runners | platform-stable identifier |
| `Sequence[MarketBar]` | dataclass | `str`/`isoformat` → JSON → SHA-256 | `str` | `application/market_data/checksum.py:10-25` | deterministic dataset checksum |
| Lambda event | `dict[str, Any]` | → dataclass → read model → JSON | `dict` → `str` | `application/execution/aws_status_api.py:76-157` | dict-in / dict-out boundary |

---

## 4. Target Representation Policy

> All rules in this section are `PROPOSED`. They become binding only after §7 approval.

### 4.1 Canonical carrier per kind of work

| Kind of work | Canonical type | Rationale |
|---|---|---|
| Persistence and storage boundary | `pa.Table` + explicit `pa.schema` → Parquet | already established; keeps schema versioning explicit |
| Bulk historical read | `MarketFrame(pl.LazyFrame, metadata)` | pushdown, no object-per-row cost; TD-011/TD-015 repayment direction |
| Tabular transforms (resample, align, join, group, aggregate) | Polars **lazy**, `collect()` only at the materialization point | one engine, one optimizer |
| Numeric kernels (indicators, simulation) | `np.ndarray` with explicit dtype | Numba and vectorized math require contiguous typed buffers |
| Columnar ingest buffers | `np.ndarray` structure-of-arrays | already the case after TD-019 |
| Single domain facts at live/event boundaries | frozen dataclass (`MarketBar`, `MarketTrade`) | semantics and invariants matter more than throughput at N=1 |
| Money in accounting and execution | `Decimal` via `Price` | exactness is a correctness requirement |
| Money in storage | `int64` fixed-point (minor units / nanos) | exact, sortable, aggregable, compact |
| Numbers in analysis and research | `float64` | D-027; matches Polars and NumPy natively |
| Identity and cache keys | canonical sorted-key JSON `str` | already consistent inside `market_analysis` |
| Configuration | frozen dataclass + explicit parsers | one mechanism for TOML and env |
| Metadata and manifests | frozen dataclass ⇄ JSON via `to_dict`/`from_dict` | already consistent; `Decimal` as `str` |
| Presentation DTOs | frozen dataclass with `float`/`str` | deliberate decoupling, already the case in `apps/` |

### 4.2 Directional rules

1. **Representations may narrow, never oscillate.** A value moves
   `storage → frame → array → result` in one direction per pipeline. Any path that returns to an
   earlier representation is a defect unless it crosses a process boundary.
2. **One conversion per boundary.** `Decimal → float64` happens exactly once, at the storage-to-analysis
   boundary. `float64 → Decimal` happens exactly once, at the kernel-to-facts boundary.
3. **`Decimal(str(x))` where `x` is already a float is forbidden.** It restores the type but not the
   precision and is therefore misleading. Use `float64` explicitly or carry `int64` fixed-point.
4. **Validation follows the representation.** Validators must exist for the representation being
   validated. Decoding a table into dataclasses purely to validate it is not acceptable on bulk paths.
5. **Metadata travels with data or with a stable key, never by position.** `available_at` and lineage
   must be addressable, not reconstructed by convention.
6. **Lazy by default at I/O.** `scan_parquet` over `read_parquet`; `collect()` at the point where a
   materialized result is genuinely required.

### 4.3 Explicit non-goals

- No migration to pandas anywhere.
- No `pl.Decimal` adoption while it remains marked unstable in Polars.
- No removal of `MarketBar` / `MarketTrade`; they stay as boundary and live-runtime objects (TD-011
  post-S025 note).
- No new DSL surface (owned by Sprint 037).
- No distributed storage or query engine (TD-006 boundary unchanged).
- No change to research **methodology** or fact semantics — only to their carriers.

---

## 5. Canonical Primitive Types

### 5.1 Current state

| Concept | Carriers today | Count |
|---|---|---|
| Price | `Price(Decimal)`, `pa.string()`, `int64` nanos, `float64`, `float` | 5 |
| Volume / size | `Volume(int)`, `int64`, `float64` (in `AnalysisDataView`) | 3 |
| Money / PnL | `Decimal`, `str` (JSON), `pl.Float64` (Parquet) | 3 |
| Timestamp | aware `datetime`, naive `timestamp("us")`, `int64` ns, epoch-ms, ISO `str` | 5 |
| Session date | `datetime.date`, `pa.date32()` | 2 |
| Identity | `Identifier(str)`, plain `str`, canonical JSON `str`, SHA-256 hex | 4 |
| Null / missing | Polars null, `NaN` sentinel, `None`, `_STATUS_OMIT` row removal, `MISSING_TS_RECV_NS = 0` | 5 |

### 5.2 Target primitives

| Concept | Canonical primitive | Permitted encodings | Forbidden |
|---|---|---|---|
| Price — accounting | `Price(Decimal)` | — | `float` in order/fill/position paths |
| Price — storage | `int64` fixed-point, scale documented in the schema | — | `pa.string()` in new schemas |
| Price — analysis | `float64` | — | `Decimal` inside kernels or Polars expressions |
| Volume / size | `int64` | `float64` only inside a numeric kernel | silent truncation without `ROUND_FLOOR` |
| Money / PnL — persisted | `int64` minor units | `str` in JSON | `pl.Float64` for money columns |
| Timestamp — domain | UTC-aware `datetime` | — | naive datetimes anywhere in domain code |
| Timestamp — storage | `pa.timestamp("us", tz="UTC")` | `int64` ns for tick-scale contract data | naive `timestamp("us")` + `.replace(tzinfo=UTC)` |
| Timestamp — kernel | `int64` epoch ns | — | — |
| Session date | `datetime.date` / `pa.date32()` | — | string dates |
| Identity | `Identifier` or canonical sorted-key JSON `str` | SHA-256 hex where a fixed-width id is needed | pipe-joined ad-hoc strings |
| Missing value | Polars null / `None` | `NaN` only inside a float kernel, documented | dropping rows to signal absence |

### 5.3 Null semantics

`OutputSeries` has no null representation and uses `NaN`; Polars uses real nulls. The reconciliation
currently lives in `align.py:118-123`. Under D-REP-01 this disappears, because the carrier gains
native null support. Until then, the NaN sentinel must be documented at every boundary that
produces or consumes `OutputSeries`.

---

## 6. Hot Path Analysis

### 6.1 Measurement status

Two rankings coexist below and must not be confused. §6.2 is the **measured** baseline for the
authoring → analysis → evaluate path. §6.4 is the **structural hypothesis** list from the static
pass, most of which the current harness does not exercise.

Nothing in §8 may ship without a before/after measurement attached to its PR.

### 6.1 Baseline

```bash
uv run python scripts/ops/bench_authoring_analysis_evaluate.py --json --bars N
```

Captured 2026-08-25 at commit `f0a82c5`, one market model (`high_volatility`) and one signal model
(`high_volatility_long_edge`), synthetic 1m bars, no `user_data` I/O. Single run per size on one
machine — variance is not characterized, so treat sub-millisecond differences as noise.

Wall time in milliseconds:

| Phase | 250 bars | 2 000 bars | 10 000 bars | 2k → 10k (5× bars) |
|---|---|---|---|---|
| `p1_compile` | 0.18 | 0.19 | 0.20 | 1.06× — flat |
| `p2_run_analysis` | 7.62 | 16.84 | 61.71 | 3.67× |
| `p3_evaluate` (excl. nested `run_analysis`) | 4.06 | 9.43 | 31.72 | 3.36× |
| ├ `run_analysis.resolve_sessions` | 1.80 | 6.86 | **36.25** | 5.28× |
| ├ `run_analysis.execute` | 1.48 | 6.37 | **23.97** | 3.76× |
| ├ `run_analysis.plan` | 0.74 | 0.66 | 0.71 | flat |
| ├ `run_analysis.assemble_frame` | 0.065 | 0.080 | 0.079 | flat |
| ├ `run_analysis.load_market_view` | 0.059 | 0.085 | 0.057 | flat |
| └ `evaluate_models.build_evaluation_table` | 1.32 | 6.29 | **28.36** | 4.51× |

Peak allocation: `p2` 87 KB → 354 KB → 1.59 MB; `p3` 91 KB → 344 KB → 1.56 MB.

### 6.2 Measured ranking

| # | Path | Share at 10k bars | Finding |
|---|---|---|---|
| M1 | `run_analysis.resolve_sessions` | **59 % of `p2`** | Baseline: four chained eager `with_columns`, `dt.convert_time_zone("America/New_York")`, Utf8 `session_id`. **#279** fused RTH/`session_id` into one pass (**36.25 ms → ~29–31 ms** at 10k); timezone stays a separate pass; `session_id` stays Utf8. Residual M1 is still the D-REP-02 evidence. |
| M2 | `evaluate_models.build_evaluation_table` | **89 % of `p3`** | Still dominant after the #275 vectorization; the remaining cost is frame construction plus the per-node scratch frames in `evaluator` (H5). |
| M3 | `run_analysis.execute` | 39 % of `p2` | Component kernels including the `tuple[float, ...]` ↔ `np.ndarray` crossings (H3). Sublinear — fixed overhead still visible at 10k. |
| M4 | `plan`, `assemble_frame`, `load_market_view`, `p1_compile` | < 2 % combined, flat | Not worth optimizing. `p1_compile` being flat at 0.2 ms confirms the D-S036-02 hypothesis and gives Sprint 037 DSL headroom. |

**M1 is the single largest measured cost and was not ranked in the static pass.** It is also the
clearest available evidence for D-REP-02: four eager `with_columns` on one frame is exactly the
shape a lazy pipeline fuses into a single pass.

### 6.3 Harness coverage after T006 (#278)

Default command still times P1–P3 on a single-timeframe `preloaded_column_batch`. P4–P6 research
loops and P7 Parquet ingest stay untimed.

Opt-in flags (CI smoke `--bars 80`; local sizing `--bars 500`):

| Flag | What it times | Hypothesis |
|---|---|---|
| `--mtf` | P2 adds `trend.ema` period 3 on 5m. Nested `execute.resample.*` and `align.*`. P3 stays on 1m canonical models. | H2, H6 |
| `--parquet` | tempfile dataset (never `user_data/`) loaded via `query_historical_columnar`. Nested `ohlcv.*` and `load_market_view.query_columnar`. | production columnar read; **not** H4 `list[MarketBar]` |

Local N=500 (engineer, recorded in #278):

| Mode | p1 | p2 | p3 |
|------|----|----|-----|
| default | 0.18 ms | 9.9 ms | 5.1 ms |
| `--mtf` | 0.17 ms | 51.6 ms | 4.8 ms |
| `--parquet` | 0.23 ms | 55.9 ms | 4.7 ms |
| `--mtf --parquet` | 0.17 ms | 92.5 ms | 4.9 ms |

Nested (same run):

- `execute.resample` (1m→5m): **24.1 ms** (`--mtf`) — **H2 material** versus default p2 of 9.9 ms.
- `align.last_closed_bar`: **0.57 ms** — **H6 not material** at this scale.
- `load_market_view.query_columnar`: **16.5 ms** (`--parquet`, P3 nested).
- `ohlcv.read_legacy_file`: **1.6 ms**; `ohlcv.build_column_batch`: **13.6 ms** — Parquet file I/O is
  cheap; table→column conversion dominates.

**Still unmeasured:** H1 at research-envelope / CLI dataset scale (full-file `pl.read_parquet` in
`research/datasets/*` has no predicate — converting it is not this step), H4
(`query_historical` → `list[MarketBar]`), H3 with `structure.swing`, H7–H10, P4–P6, P7 ingest.

Nested `run_analysis.*` under `--mtf` includes P2 (MTF) + P3 (1m). Use `execute.resample.*` /
`align.*` for Stage 1 comparisons, not summed `run_analysis.execute`.

### 6.3.1 Stage 2 step 1 — partitioned OHLCV `scan_parquet` (S036-T008)

Hot read path is `ParquetDatasetRepository.query_ohlcv_table`, not research-envelope
`pl.read_parquet`. Before this step the partitioned path opened **every** `session_date` file,
concatenated, then filtered `observed_at` in memory.

Shipped: prune partitions whose `session_date` cannot overlap the query (UTC dates ±1 day for
CME Globex vs UTC calendar), then `pl.scan_parquet` with an `observed_at` predicate. Public
`query_ohlcv_table` / `query_historical_columnar` contracts unchanged. Research-envelope
full-file reads stay eager (no predicate). The lazy `build_analysis_frame` join is §6.3.2.

Local microbench (90 session partitions × 390 1m bars; query two sessions → 780 rows; N=8):

| Path | median `query_ohlcv_table` |
|------|----------------------------|
| Eager read-all + Arrow filter (sprint HEAD `518185e`) | **85.59 ms** |
| Session prune + `scan_parquet` | **2.09 ms** (~41×) |

Single-file 500-bar full-range read (the `--parquet` harness shape) is not the win:
eager **1.03 ms** vs scan **1.34 ms**. `--parquet --bars 500` nested `ohlcv.scan_parquet`
~2.3 ms; `ohlcv.build_column_batch` still dominates (~13.9 ms).

### 6.3.2 Stage 2 step 2 — lazy `build_analysis_frame` (S036-T008)

`build_analysis_frame` joins in-memory envelope tables (`outcomes` × entities × optional
`context`). The public return type stays `pl.DataFrame`. The plan is now a `LazyFrame`:
`collect_schema()` validates dtypes before materialization, then `collect()` + the existing
eager `validate_analysis_frame`.

MARKET_AND_SIGNAL envelope, N=8:

| Rows | eager (sprint HEAD `0af1e26`) | lazy join + collect_schema + collect |
|------|-------------------------------|--------------------------------------|
| 1 000 | 0.75 ms | 0.95 ms |
| 20 000 | 1.89 ms | 1.95 ms |
| 100 000 | 6.38 ms | 6.20 ms |

Wall time is **flat**. The I/O win was step 1; this step is the D-REP-02 pipeline default
(validation adapted for lazy), not a second read-path speedup. Fixture frames stay identical.

### 6.4 Structural hypotheses (static pass)

Ordered by expected impact, to be confirmed or refuted by measurement before any of them justifies a PR.

### 6.2 Ranked candidates

| # | Path | Structural cost | Files | Expected impact | Confirmed by |
|---|---|---|---|---|---|
| H1 | Eager Parquet reads across all research CLIs and dashboard queries | full-file materialization, no pushdown | 65 Polars files, `read_parquet` only | HIGH — **partitioned OHLCV query repaid** (§6.3.1); research-envelope full-file reads remain | bench + partitioned repository timing |
| H2 | `resample_analysis_view` round-trip | per-row `iter_rows` + `Decimal(str())` + `MarketBar.__post_init__` OHLC validation | `market_analysis/data/resample.py:70-102` | HIGH — **confirmed** at 500 1m bars (`execute.resample` ~24 ms vs default p2 ~10 ms; #278) | authoring→analysis bench `--mtf` |
| H3 | `tuple[float, ...]` ↔ `np.ndarray` per component per output | boxed floats, full materialization both ways | `adapters/numpy/result_builder.py`, 4 component modules | HIGH (worst at `swing`: 20 outputs) | bench with swing in the plan |
| H4 | `list[MarketBar]` on bulk paths | one Python object per bar | `query_historical`, `import_external_dataset`, `derive_continuous_ohlcv:366`, dashboards | HIGH — **still unmeasured** (`--parquet` uses `query_historical_columnar`) | TD-011 already accepted as HIGH |
| H5 | per-node scratch frames in `evaluator` | one `pl.DataFrame` allocation per AST node | `model_expression/evaluation/evaluator.py:131,164,179,192,205` | MEDIUM | bench. **Partially addressed**: `build_evaluation_dataframe` itself was vectorized in #275; the per-node `when/then` scratch frames remain |
| H6 | `align.py` two frames per aligned column | frame construction per column on cache miss | `market_analysis/data/align.py:104-123` | MEDIUM — **not material** at 500 1m bars (`align.last_closed_bar` ~0.57 ms; #278) | MTF bench `--mtf` |
| H7 | Monte Carlo over `list[Decimal]` | pure-Python arithmetic, thousands of paths | `robustness/analytics/monte_carlo.py:163` | MEDIUM — deliberate (precision) | robustness bench |
| H8 | Dual JSON + Parquet writes for all analytics | every analytics object serialized twice | `datasets/robustness.py`, `application/signal_research/analytics_parquet.py` | LOW–MEDIUM | I/O timing |
| H9 | `iter_rows` in per-scenario / per-trade loops | row-wise Python | `stress.py:148`, `compile.py:180`, `strategy_dashboard.py:201,223` | LOW–MEDIUM | robustness + dashboard bench |
| H10 | `ParquetTradeDatasetRepository.write_trades` read-merge-write | full partition rewrite per call | `parquet/trade_repository.py` | LOW (import already repaid in S027) | import bench, only if touched |

Reconciliation with §6.2: H5 is confirmed as M2 and H3 is partially confirmed as M3. After #278, H2
is confirmed material and H6 is not at N=500. H4 remains unmeasured (columnar load). H1 partitioned
OHLCV reads are now measured (§6.3.1); research-envelope `read_parquet` is still full-file. H7–H10
and H3-with-swing stay untouched. The measured M1 had no counterpart in this list — the static pass treated
`CmeEsRthSessionResolver` as "already vectorized"; #279 repaid the fused `with_columns` part.

### 6.5 Paths explicitly not re-profiled

Per Sprint 036 §4, the following were repaid in Sprints 026/027 and must not be blindly rewritten:
Signal Research occurrence/outcome materialization (TD-017), robustness shared evaluation (TD-018),
Databento chunk buffers (TD-019), continuous materialize write path (TD-020). They appear above only
where the representation policy touches them.

---

## 7. Decision Register

Entries marked **ADR impact** require an ADR amendment or superseding ADR before implementation, even
where the decision itself is accepted.

---

### D-REP-01 — `MarketFrame(pl.LazyFrame, metadata)` as the canonical bulk representation

**Status:** ACCEPTED 2026-08-25 — ADR-MA-014 · **Type:** representation contract · **ADR impact:** ADR-MA-004, ADR-MA-010

**Reason.** `AnalysisDataView` carries `tuple[float, ...]` columns and a custom `column()` API. Every
tabular operation the engine needs (resample, as-of align, join, aggregate) must therefore leave the
contract, go to Polars, and come back.

**Justification.** This is the repayment direction already registered in TD-015 ("Introduce
`MarketFrame(pl.LazyFrame, metadata)` for batch paths; migrate components incrementally") and TD-011
("Add columnar batch return type (`MarketDataBatch` / `pl.LazyFrame` with metadata)"). It collapses
H2, H3, H4 and H6 into one structural fix rather than four local patches.

**Risk.** ADR-MA-004 froze a backend-neutral view and ADR-MA-010 states that domain protocols do not
import adapter libraries. A `LazyFrame`-typed contract makes Polars part of the public domain contract.
That is a genuine architectural reversal, not a detail. It also touches every component implementation
and its tests. `CURRENT_STATUS.md` §10 lists "Polars boundary creep" as a known risk precisely here.

**Recommendation.** Accept, but only with an explicit superseding ADR that states Polars is now a
committed engine rather than an optional backend, and with `AnalysisDataView` retained as a thin
adapter for the live runtime (where N=1 and object semantics win). Migrate components incrementally
behind the adapter; do not big-bang.

**Alternative if rejected.** Keep the view, adopt D-REP-03 and D-REP-04 only. This removes the worst
redundant conversions but leaves H3 permanently in place.

**Outcome.** Accepted with the recommended shape. Recorded as
[ADR-MA-014](../adr/ADR-MA-014-marketframe-polars-committed-bulk-engine.md): Polars is a committed
engine; `AnalysisDataView` is retained as a thin adapter for the live runtime. Incremental
component migration behind the adapter; no big-bang rewrite. Stage 4 code still requires its own
PRs.

---

### D-REP-02 — Lazy as the default Polars mode

**Status:** ACCEPTED 2026-08-25 — two-step · **Type:** workflow data path · **ADR impact:** none

**Reason.** Zero `LazyFrame` / `scan_parquet` in 65 Polars files.

**Justification.** Predicate and projection pushdown are free wins on every research CLI and dashboard
query, particularly for the four-table join in `research/analytics/frame_builder.py:18-87` and for
partitioned Parquet reads where most partitions are filtered out immediately afterwards.

**Risk.** Schema errors move from construction time to `collect()` time. `research/analytics/schemas.py`
validates dtypes eagerly, so `validate_*` must either move behind `collect()` or switch to
`collect_schema()`. Error messages become less local, which affects debuggability.

**Recommendation.** Accept in two steps: first `scan_parquet` at repository read boundaries only
(low risk, isolated), then lazy pipelines inside `research/analytics` once schema validation is
adapted. Do not convert reporting code — it materializes anyway.

**Outcome.** Accepted as two steps. Step 2 must not start before step 1 has a committed measurement.

---

### D-REP-03 — Eliminate the `MarketBar` / `Decimal` round-trip on bulk paths

**Status:** ACCEPTED 2026-08-25 — Sprint 036 · **Type:** workflow data path · **ADR impact:** none

**Reason.** Three concrete redundancies:
`resample.py:70-102` (Polars → `Decimal(str(float))` → `MarketBar` → `float`),
`derive_continuous_ohlcv.py:366` (Arrow → `MarketBar` solely to validate),
`query_historical.py:106-109` (dataclasses → Arrow → tuples).

**Justification.** In all three the intermediate representation adds no information. In the resample
case, `Decimal(str(float64))` followed by `float()` is an exact identity on IEEE-754 round-trip, so
removing it cannot change results — only cost. This is the cheapest measurable win in the audit and
is independent of D-REP-01.

**Risk.** Low, but not zero: `MarketBar.__post_init__` currently re-validates OHLC consistency after
resampling. Removing the object removes that check, so an equivalent table-level assertion must be
added, otherwise a silent correctness regression is possible. Fixture research facts must be proven
byte-identical before and after.

**Recommendation.** Accept. Ship as Stage 1 (S036-T007). T006 (#278) confirmed H2 material at 500 1m
bars; H4 stays unmeasured on the columnar path. Include a table-level OHLC validator replacing the
object-level one and a fixture equality test.

**Outcome.** Accepted together with D-REP-07 as the full Stage 1, supplying S036-T007. T006 measurements
justify the resample round-trip PR; do not spend Stage 1 on `align.py` (H6).

---

### D-REP-04 — One numeric carrier per layer

**Status:** 04a ACCEPTED 2026-08-25 · 04b DEFERRED · **Type:** boundary contract + persisted schema · **ADR impact:** ADR-0008, ADR-0018, D-S027-08

**Reason.** Price has five carriers and money is persisted as `pl.Float64` in
`simulated_trade_schema()` while being computed in `Decimal`.

**Justification.** TD-012's registered repayment direction is exactly this: "Analytical OHLCV as
float64 or scaled integer at storage boundary; reserve Decimal for execution/accounting." Unifying
storage on `int64` fixed-point also deletes `_price_nanos_to_string_expr` and the string↔float↔string
cycle in `continuous_trades_to_ohlcv_table.py:73-83`.

**Risk.** Highest of all entries. It changes **persisted schemas**, which requires a schema version
bump plus migration or rebuild of existing `user_data/` datasets. D-S027-08 explicitly deferred the
continuous `price_nanos` move to "an explicit ADR amendment + version bump, not a silent rewrite".
Changing `simulated_trade_schema()` invalidates existing research run envelopes.

**Recommendation.** Split and stage:
- **04a** — persist simulation PnL as `int64` minor units instead of `Float64`. Research-facing,
  no market-data migration. Accept if research artifacts may be rebuilt.
- **04b** — unify continuous/bars Parquet on `price_nanos`. Requires ADR-0018 amendment and a
  migration script. Defer unless a measurement shows the string bridge is material.

Do not accept 04b as part of Sprint 036; it is a sprint of its own.

**Outcome.** 04a accepted — research artifacts in `user_data/` may be rebuilt, so the migration cost
is a rebuild, not a compatibility shim. 04b deferred to a dedicated sprint; D-S027-08 and ADR-0018
remain binding until then, and the continuous `price` string schema must not be touched.

---

### D-REP-05 — `available_at` as a first-class column

**Status:** ACCEPTED 2026-08-25 — additive first · **Type:** boundary contract · **ADR impact:** ADR-MA-004, ADR-MA-009

**Reason.** `AnalysisDataView.from_bars` keeps only `observed_at`. `available_at` is reconstructed
downstream from the timeframe — in `resample.py:82` and `adapters/numpy/result_builder.py:44` via
`derive_bar_interval`, and since #275 in `frame_adapter.py:25-27` via
`pl.duration(seconds=evaluation_timeframe.total_seconds)`. Three independent reconstructions of a
value that the source `MarketBar` already carried.

**Justification.** The `observed_at` / `available_at` distinction is the framework's look-ahead-bias
control (ADR-MA-009). Reconstructing it from a timeframe is only equivalent when provider availability
matches the nominal bar interval. If a provider ever reports a different delay, that information is
already lost before the engine sees it, and no downstream code can detect the loss.

**Risk.** Extends the input contract of every component. Increases frame width. May expose existing
fixtures where reconstructed and recorded `available_at` differ — which would be a finding, not a bug
in the change.

**Recommendation.** Accept as a correctness item independent of performance. Implement as an additive
optional column first, assert equality against the reconstructed value on fixtures, then make it
required once parity is demonstrated.

**Outcome.** Accepted. If the parity assertion fails on any fixture, stop and report — that is a
look-ahead-bias finding, not a defect in the change.

---

### D-REP-06 — Timezone-aware Parquet timestamps

**Status:** PROPOSED — open · **Type:** persisted schema · **ADR impact:** ADR-0003, ADR-0008

**Reason.** All Parquet schemas use naive `timestamp("us")`; readers re-attach UTC by convention, and
`ohlcv_columnar.py:30-31` and `materialize_continuous_trades.py:274` use `.replace(tzinfo=UTC)` —
an assumption — instead of the `require_utc_aware` validation mandated by ADR-0003.

**Justification.** Moving the invariant from convention into the type removes a whole class of silent
error and deletes repeated strip/attach code in six writers and readers. `time/utc_datetime_series.py`
(#276) already establishes the target shape in-memory — it validates tz-awareness and emits
`pl.Datetime("us", "UTC")` — so this decision is about extending an existing convention to storage,
not inventing one.

**Risk.** Schema change with the same migration cost profile as D-REP-04b.

**Recommendation.** Defer the schema change; accept the **cheap half** now — replace `.replace(tzinfo=UTC)`
with a validating helper at the three read boundaries. Full tz-aware schemas ride along with D-REP-04b
if and when that happens.

---

### D-REP-07 — Table-level validators

**Status:** ACCEPTED 2026-08-25 — Sprint 036 · **Type:** boundary contract · **ADR impact:** none

**Reason.** `TradeBatchValidator` implements the same invariants three times (domain objects, NumPy
columns, records), and `OhlcvBarValidator` only accepts `Sequence[MarketBar]`, which forces
`derive_continuous_ohlcv.py:366` to decode Arrow purely to validate.

**Justification.** Prerequisite for D-REP-03 and D-REP-01; also removes a triplicated invariant that
is a natural place for the three copies to drift apart.

**Risk.** Low. Requires proving the table-level validator flags exactly the same violations.

**Recommendation.** Accept, bundled with D-REP-03.

---

### D-REP-08 — Single configuration mechanism

**Status:** PROPOSED — open · **Type:** boundary contract · **ADR impact:** none

**Reason.** `FrameworkConfig` is the only Pydantic model in `src/`; `AwsBtcFuturesRuntimeConfig` does
the same job with hand-written parsers.

**Justification.** A dependency used in exactly one place carries its full cost with none of the
standardization benefit, and AGENTS.md forbids dependencies without demonstrated need.

**Risk.** Removing Pydantic means hand-validating TOML, which is a small amount of new code. The
opposite direction adds Pydantic to the Lambda deployment footprint.

**Recommendation.** Accept removal of Pydantic. Low value, low risk, but it should not consume a
Sprint 036 optimization slot — treat as hygiene in Sprint 037 or a standalone `refactor/` PR.

---

### D-REP-09 — Deduplicate `DatasetMetadataReader`

**Status:** PROPOSED — open · **Type:** boundary contract · **ADR impact:** none

**Reason.** The identical `Protocol` is declared in four Parquet repository modules.

**Justification.** Pure hygiene; four copies of one port invite divergence.

**Risk.** None beyond import churn.

**Recommendation.** Accept as an opportunistic cleanup inside whichever PR touches those modules first.

---

### D-REP-10 — Lineage addressability

**Status:** ACCEPTED 2026-08-25 — sidecar variant · **Type:** representation contract · **ADR impact:** ADR-MA-005

**Reason.** `AnalysisFrame.column_lineage` does not survive `build_evaluation_dataframe`. Downstream
of `model_expression`, provenance travels only as a separate manifest.

**Justification.** Without a stable key binding a result column to its producing computation, lineage
correctness depends on column ordering conventions holding across four modules.

**Risk.** Adding lineage columns widens every evaluation frame. A sidecar keyed by column name is
cheaper but relies on name uniqueness, which `AnalysisFrameAssembler` already enforces via
`AliasCollisionError`.

**Recommendation.** Accept the sidecar variant (stable key, not extra columns). Reject the
lineage-as-columns variant on cost grounds unless a research-reproducibility requirement demands it.

---

## 8. Refactoring Plan

Sequenced so that each stage is independently valuable, independently revertible, and gated by a
measurement. Sizes follow the 100–400 LOC target from the sprint git workflow.

### Stage 0 — Gate (no code)

| Item | Output | Status |
|---|---|---|
| Maintainer approves or rejects each D-REP entry | this document moves DRAFT → ACCEPTED | DONE 2026-08-25 |
| Superseding ADR for D-REP-01 (Polars as committed engine; MA-004 / MA-010) | [ADR-MA-014](../adr/ADR-MA-014-marketframe-polars-committed-bulk-engine.md) | DONE 2026-08-25 — blocks Stage 4 until implementation PRs |
| ADR note for D-REP-05 / D-REP-10 (availability + lineage addressability) | ADR-MA-009 / ADR-MA-005 amendments | DONE 2026-08-25 — blocks Stage 3 until implementation PRs |
| Baseline measurement captured | `bench_authoring_analysis_evaluate.py --json` recorded in §6.1 | DONE 2026-08-25 — S036-T004 |

**Nothing below starts before its blocking Stage 0 item completes.** Stage 1 needs only the baseline
measurement; it does not wait for the ADRs.

**Sequencing resolved 2026-08-25.** The baseline showed the largest measured costs (M1, M2) sit
outside Stage 1, so a measured-first stage is inserted ahead of it. Measured work leads; structurally
justified work follows once its paths are covered by a measurement. T006 (#278) now covers those
paths: H2 is material, H6 is not, H4 remains unmeasured on the columnar load.

### Stage 0.5 — Measured hot spot first

Depends on: the §6.1 baseline. No decision from §7 is required — this changes no contract.

**Shipped #279** (`feat/session-resolver-single-pass`, squash `ffe3530`).

| PR | Outcome | Files | Risk |
|---|---|---|---|
| `feat/session-resolver-single-pass` | fuse RTH/`session_id` into the output `select`; holiday masking via `is_in` instead of a join; **resolver signature unchanged** | `time/sessions/cme_es_rth.py` | LOW |

What shipped vs the original row: timezone conversion stayed its own eager pass (a fully nested
one-`select` was slower locally). `session_id` stays **Utf8** — Enum/categorical changed the public
dtype and was slower.

Before/after at 10k bars (`bench_authoring_analysis_evaluate.py --json --bars 10000`):
`run_analysis.resolve_sessions` **36.25 ms → 29.25 / 30.90 ms**; `p2_run_analysis` **61.71 ms →
56.90 / 58.85 ms**. Residual M1 is still D-REP-02 (lazy) work, not a second Stage 0.5 PR.

Acceptance met: identical resolver output on fixtures (columns, dtypes and values); `session_id`
dtype remains Utf8.

### Stage 1 — Redundant conversions (no contract change)

Depends on: D-REP-03, D-REP-07. Harness coverage **#278** (`bench/mtf-and-parquet-coverage`).

| PR | Outcome | Files | Risk |
|---|---|---|---|
| `bench/mtf-and-parquet-coverage` | **DONE #278** — `--mtf` / `--parquet` cover resample, alignment, and columnar Parquet read | `scripts/ops/bench_authoring_analysis_evaluate.py` | LOW |
| `feat/table-level-ohlcv-validator` | OHLC invariants validated on `pa.Table` / Polars | `infrastructure/validation/`, `market/validation/` | LOW |
| `feat/resample-without-marketbar-roundtrip` | `resample_analysis_view` stays columnar end to end — **justified by H2** | `market_analysis/data/resample.py` | LOW |
| `feat/derive-continuous-table-validation` | drop Arrow → `MarketBar` decode before validation | `application/market_data/derive_continuous_ohlcv.py` | LOW |

T006 result: **H2 is material** (resample ~24 ms at 500 1m bars). **H6 is not** (align ~0.6 ms) —
do not spend a Stage 1 PR on `align.py`. **H4 is still unmeasured** because `--parquet` uses
`query_historical_columnar`, not `query_historical` → `list[MarketBar]`. Keep the derive-continuous
validator as a D-REP-03 site, not as an H4 measurement.

Acceptance: fixture research facts byte-identical; before/after timing in each remaining Stage 1 PR.

### Stage 2 — Lazy at I/O (no contract change)

Depends on: D-REP-02 (first step only). Step 2 must not start before step 1 has a committed
measurement — that gate is this section / §6.3.1.

| PR | Outcome | Files | Risk |
|---|---|---|---|
| `feat/scan-parquet-at-repository-boundary` | **DONE #283** — `scan_parquet` + session-date prune on OHLCV repository reads. Research-envelope `pl.read_parquet` is full-file (no predicate) and was left unchanged. | `infrastructure/storage/parquet/*`, `infrastructure/storage/paths.py` | LOW–MEDIUM |
| `feat/lazy-analysis-frame-builder` | **DONE** — lazy join; `collect_schema` then `collect()`; `build_analysis_frame` still returns `pl.DataFrame` | `research/analytics/frame_builder.py`, `schemas.py` | MEDIUM |

Acceptance: identical frames on fixtures; step 1 read-time measurement (§6.3.1); step 2 join
timing recorded even when flat (§6.3.2).

### Stage 3 — Correctness of metadata

Depends on: D-REP-05, D-REP-10.

| PR | Outcome | Files | Risk |
|---|---|---|---|
| `feat/available-at-as-view-column` | additive optional `available_at`, parity assertion on fixtures | `market_analysis/data/view.py`, `assembly/`, `model_expression/evaluation/` | MEDIUM |
| `feat/lineage-sidecar-key` | stable key binding evaluation columns to `OutputRef` | `market_analysis/assembly/`, `model_expression/evaluation/` | MEDIUM |

Acceptance: parity test proving reconstructed and carried `available_at` agree on all fixtures.

### Stage 4 — Representation contract (only if D-REP-01 accepted)

| PR | Outcome | Files | Risk |
|---|---|---|---|
| `docs/adr-marketframe-representation` | **DONE** — [ADR-MA-014](../adr/ADR-MA-014-marketframe-polars-committed-bulk-engine.md) | `docs/adr/` | — |
| `feat/marketframe-contract` | `MarketFrame(pl.LazyFrame, metadata)` + adapter from `AnalysisDataView` | `market_analysis/data/` | HIGH |
| `feat/marketframe-component-migration-1` | migrate `ema`, `true_range` behind the adapter | `market_analysis/components/` | HIGH |
| `feat/marketframe-component-migration-2` | migrate `atr`, `state`, `swing` | `market_analysis/components/` | HIGH |
| `refactor/deprecate-analysis-data-view-bulk` | view retained for live runtime only | `market_analysis/`, `execution/runtime/` | HIGH |

Acceptance per PR: identical `AnalysisResult` values on fixtures; measurement attached.

### Stage 5 — Persisted schemas (separate sprint)

Depends on: D-REP-04b, D-REP-06 full. **Out of scope for Sprint 036.**

| PR | Outcome | Risk |
|---|---|---|
| `docs/adr-0018-amendment-price-nanos` | ADR amendment + version bump + migration note | — |
| `feat/continuous-price-nanos-schema` | unify continuous schema on `int64` | HIGH |
| `feat/tz-aware-parquet-timestamps` | tz-aware timestamps across schemas | HIGH |
| `feat/migrate-user-data-schemas` | migration script + rebuild guidance | HIGH |

### Stage 6 — Hygiene

Depends on: D-REP-08, D-REP-09. Opportunistic; no dedicated sprint slot.

### Sequencing constraints

```text
Stage 0 ──► Stage 0.5 ──► Stage 1 ──► Stage 2 ──► Stage 3 ──► Stage 4 (conditional)
                                                           └─► Stage 5 (separate sprint)
Stage 6 may interleave anywhere.
```

The original two-PR cap on Sprint 036 optimization work was **lifted by the maintainer on 2026-08-25**.
Sprint 036 therefore runs Stage 1 and Stage 2 in full. The binding constraint is no longer PR count
but the measurement gate: every PR carries a before/after number, and any PR without one is rejected.
Stage 4 remains conditional on its ADR; Stage 5 remains a separate sprint.

---

## 9. Relationship to existing debt and decisions

| Existing item | Status | This audit |
|---|---|---|
| TD-011 — historical query returns `list[MarketBar]` | ACCEPTED, HIGH | confirmed; H4; addressed by D-REP-01, D-REP-03 |
| TD-012 — Decimal OHLCV with float64 analysis | ACCEPTED, MEDIUM | confirmed; addressed by D-REP-04 |
| TD-013 — multi-implementation registry | ACCEPTED, MEDIUM | unchanged; out of scope |
| TD-014 — separate store / workspace / cache | ACCEPTED, MEDIUM | unchanged; out of scope |
| TD-015 — view as map-of-arrays | ACCEPTED, HIGH | confirmed; H3; addressed by D-REP-01 |
| TD-016 — dual identity axis | ACCEPTED, LOW | unchanged; out of scope |
| TD-017 / TD-018 / TD-019 / TD-020 | REPAID | not re-profiled; see §6.3 |
| D-S027-08 — keep continuous string `price` | binding, unchanged | D-REP-04b is deferred; this decision stays in force |
| ADR-MA-004 — `AnalysisDataView` | ACCEPTED | to be superseded by D-REP-01; view survives as live-runtime adapter |
| ADR-MA-010 — external libraries as optional backends | ACCEPTED | to be superseded by D-REP-01 (Polars becomes a committed engine) |
| ADR-MA-009 — warmup / causality / availability | ACCEPTED | D-REP-05 strengthens; amendment required |
| ADR-MA-005 — analysis result and output identity | ACCEPTED | D-REP-10 adds lineage addressability; amendment required |
| ADR-0003 — UTC internal time | ACCEPTED | D-REP-06 closes a convention gap |

---

## 10. Resolved questions and remaining open items

### 10.1 Resolved 2026-08-25

| Question | Answer | Consequence |
|---|---|---|
| May `user_data/` research artifacts be rebuilt? | **Yes** — research artifacts may be rebuilt; market data must not be migrated in this work | D-REP-04a is a rebuild, not a compatibility shim |
| Is Polars a committed engine rather than an optional backend? | **Yes** | ADR-MA-010 must be superseded before Stage 4 |
| Does the live runtime keep object semantics after the `MarketFrame` migration? | **Yes** | `AnalysisDataView` survives as a live-runtime adapter; the migration is bulk-path only |

### 10.2 Still open

| Item | Why it is still open |
|---|---|
| Harness coverage for Stage 1 paths | **resolved #278** — `--mtf` measures H2/H6; `--parquet` measures columnar read. H4 (`list[MarketBar]`) remains open. Partitioned H1 is in §6.3.1 |
| D-REP-06 — tz-aware Parquet timestamps | schema migration cost couples it to the deferred D-REP-04b; the cheap half (validating helper instead of `.replace(tzinfo=UTC)`) can be taken independently |
| D-REP-08 — single configuration mechanism | hygiene; no sprint slot allocated |
| D-REP-09 — deduplicate `DatasetMetadataReader` | opportunistic; fold into whichever PR touches those modules |
| Scale of the D-REP-04b migration | needs a count of affected `user_data/` partitions before the dedicated sprint can be sized |

---

## References

- `docs/planning/TECHNICAL_DEBT.md` — TD-011, TD-012, TD-015, TD-020
- `docs/planning/sprints/SPRINT_036.md` — this sprint's scope and acceptance criteria
- `docs/planning/sprints/S027_WAVE0_DECISIONS.md` — D-S027-05 representation guidance, D-S027-08
- `docs/adr/ADR-MA-004-analysis-data-view-and-data-ownership.md`
- `docs/adr/ADR-MA-010-external-analytical-libraries.md`
- `docs/adr/ADR-MA-012-batch-multitimeframe-computation-with-polars.md`
- `docs/adr/ADR-0008-parquet-historical-storage.md`
- `docs/adr/ADR-0018-continuous-futures-materialization.md`
- `docs/reference/MODULE_MAP.md`
