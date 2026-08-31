"""Import a Binance USD-M historical OHLCV range into a published dataset version.

Mirrors the Databento archive-import shape (ADR-0014/ADR-0015) for a
network/REST source instead of a file archive (ADR-0025): fetch -> validate ->
write bars -> register WORKING -> write ``import_manifest.json`` -> finalize
-> publish, all behind a single call so the maintainer gets back a published
``DatasetRef`` in one step (Sprint 045 goal, ADR-0025 §2).

Provider boundary (SPRINT_045.md §4, binding): this module owns lifecycle,
validation and manifest content. It never imports ``urllib`` or touches
Binance JSON directly -- ``fetch_historical_klines`` (infrastructure layer)
already returns decoded ``MarketBar`` objects and fetch statistics.

Mode selector (D-S045-09): v1 accepts only ``mode="ohlcv"``. ``mode="trades"``
is reserved for a future increment (fetch aggregate trades, then
``derive_ohlcv_from_trades``) and is rejected here with an explicit
"not supported in v1" error -- nothing in this module is built "for" that
mode ahead of time.

Gap / validator interaction (D-S045-10, decided in S045-T006):
``OhlcvBarValidator`` checks required fields, non-negative volume, duplicate
``observed_at`` timestamps and non-decreasing ordering -- it does **not**
check that consecutive bars are exactly one interval apart. A range with a
genuine Binance gap (a page that legitimately returned zero rows) therefore
**passes validation**; the gap is recorded in ``import_manifest.json``
(``gaps``) by this workflow, never filled or silently dropped. This is the
"validation passes with the gap recorded" branch of D-S045-10, chosen because
it is the validator's actual behaviour, not a guess.

Idempotency (acceptance criterion 5): re-importing an identical ``[start,
end)`` range must not create a second ``PUBLISHED`` version. Before
allocating a new dataset version this workflow looks up the latest persisted
version for the same dataset identity via
``infrastructure.storage.metadata.discovery.latest_dataset_ref`` (the same
"reuse if content is unchanged" mechanism ``materialize_continuous_trades``
already uses for continuous datasets) and compares its checksum against the
checksum of the freshly fetched bars. A match returns the existing
``PUBLISHED`` ``dataset_ref`` unchanged (``reused=True``) instead of writing
a new version, respecting the ADR-0007 immutability of published data.
"""

from __future__ import annotations

import json
import random
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any

from trading_framework.application.market_data.checksum import compute_dataset_checksum
from trading_framework.application.market_data.finalize_dataset import finalize_dataset
from trading_framework.application.market_data.publish_dataset import publish_dataset
from trading_framework.core.exceptions import ValidationError
from trading_framework.core.identifiers import Identifier
from trading_framework.infrastructure.storage.metadata.discovery import latest_dataset_ref
from trading_framework.infrastructure.storage.metadata.registry import FileDatasetRegistry
from trading_framework.infrastructure.storage.parquet.repository import ParquetDatasetRepository
from trading_framework.infrastructure.storage.paths import dataset_bars_path
from trading_framework.infrastructure.validation.ohlcv_validator import OhlcvBarValidator
from trading_framework.market.datasets import (
    DatasetId,
    DatasetLifecycleState,
    DatasetMetadata,
    DatasetRef,
    ValidationStatus,
)
from trading_framework.market.models import MarketBar
from trading_framework.market.repositories import DatasetRepository
from trading_framework.market.validation import OhlcvValidator, ValidationResult
from trading_framework.time.clocks.protocol import Clock
from trading_framework.time.clocks.system import SystemClock
from trading_framework.time.models.timeframe import Timeframe
from trading_framework.time.models.utc_instant import require_utc_aware

if TYPE_CHECKING:
    # Deferred to a function-local import at call time (see
    # ``import_binance_futures_ohlcv``): ``futures_mapper`` (imported by
    # ``futures_klines_history``) transitively imports
    # ``application.market_data`` through the execution/strategy layers, so a
    # module-level import here would create an import cycle whenever
    # ``infrastructure.providers.binance`` is imported before this module.
    from trading_framework.infrastructure.providers.binance.futures_klines_history import (
        HistoricalKlinesFetchStats,
    )

#: v1 accepts only direct klines; ``trades`` is reserved (D-S045-09).
SUPPORTED_IMPORT_MODES = ("ohlcv",)
_RESERVED_IMPORT_MODES = ("trades",)
_MANIFEST_FILENAME = "import_manifest.json"


@dataclass(frozen=True, slots=True)
class ImportBinanceFuturesOhlcvRequest:
    """Input for importing a Binance USD-M historical OHLCV range."""

    instrument_id: Identifier
    symbol: str
    interval: str
    start_at: datetime
    end_at: datetime
    schema_version: str
    normalization_version: str
    mode: str = "ohlcv"
    provider: str = "binance"
    source_id: str = "binance-usdm-klines-v1"
    api_key: str | None = None
    lineage: Mapping[str, str] | None = None

    def __post_init__(self) -> None:
        require_utc_aware(self.start_at)
        require_utc_aware(self.end_at)
        if self.end_at <= self.start_at:
            msg = "end_at must be greater than start_at"
            raise ValidationError(msg)


@dataclass(frozen=True, slots=True)
class BinanceImportGap:
    """A recorded half-open ``[start, end)`` UTC range with no returned bars."""

    start: datetime
    end: datetime


@dataclass(frozen=True, slots=True)
class BinanceImportManifest:
    """``import_manifest.json`` contents for a Binance historical import (D-S045-11)."""

    provider: str
    mode: str
    symbol: str
    instrument_id: str
    interval: str
    requested_start: datetime
    requested_end: datetime
    first_bar_open_time: datetime | None
    last_bar_close_time: datetime | None
    page_count: int
    request_count: int
    retry_count: int
    rows_decoded: int
    rows_rejected: int
    gaps: tuple[BinanceImportGap, ...]
    normalization_version: str
    schema_version: str
    api_key_used: bool

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-serializable representation (never the API key value)."""
        return {
            "provider": self.provider,
            "mode": self.mode,
            "symbol": self.symbol,
            "instrument_id": self.instrument_id,
            "interval": self.interval,
            "requested_start": self.requested_start.isoformat(),
            "requested_end": self.requested_end.isoformat(),
            "first_bar_open_time": (
                self.first_bar_open_time.isoformat() if self.first_bar_open_time else None
            ),
            "last_bar_close_time": (
                self.last_bar_close_time.isoformat() if self.last_bar_close_time else None
            ),
            "page_count": self.page_count,
            "request_count": self.request_count,
            "retry_count": self.retry_count,
            "rows_decoded": self.rows_decoded,
            "rows_rejected": self.rows_rejected,
            "gaps": [
                {"start": gap.start.isoformat(), "end": gap.end.isoformat()} for gap in self.gaps
            ],
            "normalization_version": self.normalization_version,
            "schema_version": self.schema_version,
            "api_key_used": self.api_key_used,
        }


@dataclass(frozen=True, slots=True)
class ImportBinanceFuturesOhlcvResult:
    """Outcome of a Binance USD-M historical OHLCV import."""

    dataset_ref: DatasetRef
    validation_result: ValidationResult
    manifest: BinanceImportManifest
    reused: bool


def _reject_unsupported_mode(mode: str) -> None:
    if mode in SUPPORTED_IMPORT_MODES:
        return
    if mode in _RESERVED_IMPORT_MODES:
        msg = (
            f"Binance import mode {mode!r} is not supported in v1 (reserved for a future increment)"
        )
        raise ValidationError(msg)
    msg = f"unsupported Binance import mode: {mode!r}"
    raise ValidationError(msg)


def _to_ms(value: datetime) -> int:
    return int(value.timestamp() * 1000)


def _from_ms(value_ms: int) -> datetime:
    return datetime.fromtimestamp(value_ms / 1000, tz=UTC)


def _bar_range(
    bars: Sequence[MarketBar],
    *,
    fallback: datetime,
) -> tuple[datetime, datetime]:
    if not bars:
        return fallback, fallback
    return bars[0].observed_at, bars[-1].observed_at


def _manifest_path(storage_root: Path, dataset_ref: DatasetRef) -> Path:
    return dataset_bars_path(storage_root, dataset_ref).parent / _MANIFEST_FILENAME


def _build_manifest(
    request: ImportBinanceFuturesOhlcvRequest,
    bars: Sequence[MarketBar],
    stats: HistoricalKlinesFetchStats,
) -> BinanceImportManifest:
    first_bar_open_time = bars[0].observed_at if bars else None
    last_bar_close_time = bars[-1].available_at - timedelta(milliseconds=1) if bars else None
    gaps = tuple(
        BinanceImportGap(start=_from_ms(gap.start_ms), end=_from_ms(gap.end_ms))
        for gap in stats.gaps
    )
    return BinanceImportManifest(
        provider=request.provider,
        mode=request.mode,
        symbol=request.symbol,
        instrument_id=request.instrument_id.value,
        interval=request.interval,
        requested_start=request.start_at,
        requested_end=request.end_at,
        first_bar_open_time=first_bar_open_time,
        last_bar_close_time=last_bar_close_time,
        page_count=stats.page_count,
        request_count=stats.request_count,
        retry_count=stats.retry_count,
        rows_decoded=stats.rows_decoded,
        rows_rejected=stats.rows_rejected,
        gaps=gaps,
        normalization_version=request.normalization_version,
        schema_version=request.schema_version,
        api_key_used=stats.api_key_used,
    )


def _write_manifest(
    storage_root: Path,
    dataset_ref: DatasetRef,
    manifest: BinanceImportManifest,
) -> Path:
    path = _manifest_path(storage_root, dataset_ref)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest.to_dict(), indent=2), encoding="utf-8")
    return path


def read_binance_import_manifest(storage_root: Path, dataset_ref: DatasetRef) -> dict[str, Any]:
    """Load the persisted ``import_manifest.json`` for a dataset version as a dict."""
    path = _manifest_path(storage_root, dataset_ref)
    payload: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return payload


def import_binance_futures_ohlcv(
    request: ImportBinanceFuturesOhlcvRequest,
    *,
    storage_root: Path,
    urlopen: Any = None,
    sleep: Any = None,
    rng: random.Random | None = None,
    page_limit: int | None = None,
    validator: OhlcvValidator | None = None,
    repository: DatasetRepository | None = None,
    registry: FileDatasetRegistry | None = None,
    clock: Clock | None = None,
) -> ImportBinanceFuturesOhlcvResult:
    """Fetch, validate, write, register, finalize and publish a Binance OHLCV range.

    ``urlopen``, ``sleep``, ``rng`` and ``page_limit`` are forwarded to
    :func:`fetch_historical_klines` unchanged (network-free test seams); see
    that function's docstring for their contract.
    """
    _reject_unsupported_mode(request.mode)

    # Deferred import: see the ``TYPE_CHECKING`` note above this function.
    from trading_framework.infrastructure.providers.binance.futures_klines_history import (
        fetch_historical_klines,
    )

    bar_validator = validator or OhlcvBarValidator()
    bar_repository = repository or ParquetDatasetRepository(storage_root)
    dataset_registry = registry or FileDatasetRegistry(storage_root)
    utc_clock = clock or SystemClock()

    dataset_id = DatasetId(
        instrument_id=request.instrument_id,
        data_type="ohlcv",
        timeframe=Timeframe(request.interval),
        provider=request.provider,
        source_id=request.source_id,
    )

    fetch_kwargs: dict[str, Any] = {}
    if page_limit is not None:
        fetch_kwargs["page_limit"] = page_limit
    fetch_result = fetch_historical_klines(
        symbol=request.symbol,
        interval=request.interval,
        start_ms=_to_ms(request.start_at),
        end_ms=_to_ms(request.end_at),
        urlopen=urlopen,
        sleep=sleep,
        api_key=request.api_key,
        rng=rng,
        **fetch_kwargs,
    )
    bars = list(fetch_result.bars)
    stats = fetch_result.stats

    validation_result = bar_validator.validate(bars)
    validation_status = (
        ValidationStatus.PASSED if validation_result.is_valid else ValidationStatus.FAILED
    )
    manifest = _build_manifest(request, bars, stats)
    checksum = compute_dataset_checksum(bars)

    existing_ref = latest_dataset_ref(storage_root, dataset_id)
    if existing_ref is not None:
        existing_metadata = dataset_registry.get(existing_ref)
        if (
            existing_metadata.lifecycle_status is DatasetLifecycleState.PUBLISHED
            and existing_metadata.checksum == checksum
        ):
            return ImportBinanceFuturesOhlcvResult(
                dataset_ref=existing_ref,
                validation_result=validation_result,
                manifest=manifest,
                reused=True,
            )

    created_at = utc_clock.now()
    dataset_ref = dataset_registry.allocate_ref(dataset_id)

    if validation_result.is_valid:
        bar_repository.write_bars(dataset_ref, bars)

    start_at, end_at = _bar_range(bars, fallback=created_at)
    metadata = DatasetMetadata(
        dataset_ref=dataset_ref,
        instrument_id=dataset_id.instrument_id,
        timeframe=dataset_id.timeframe,
        provider=dataset_id.provider,
        source_id=dataset_id.source_id,
        data_type=dataset_id.data_type,
        start_at=start_at,
        end_at=end_at,
        schema_version=request.schema_version,
        normalization_version=request.normalization_version,
        validation_status=validation_status,
        lifecycle_status=DatasetLifecycleState.WORKING,
        row_count=len(bars),
        checksum="pending",
        created_at=created_at,
        lineage=request.lineage,
    )
    dataset_registry.register(metadata)
    _write_manifest(storage_root, dataset_ref, manifest)

    finalize_dataset(
        dataset_ref,
        storage_root=storage_root,
        registry=dataset_registry,
        repository=bar_repository,
    )
    publish_dataset(
        dataset_ref,
        storage_root=storage_root,
        registry=dataset_registry,
        clock=utc_clock,
    )

    return ImportBinanceFuturesOhlcvResult(
        dataset_ref=dataset_ref,
        validation_result=validation_result,
        manifest=manifest,
        reused=False,
    )
