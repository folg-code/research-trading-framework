"""Import Binance USD-M historical OHLCV workflow tests (network-free, Tier 1)."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from trading_framework.application.market_data.import_binance_futures_ohlcv import (
    ImportBinanceFuturesOhlcvRequest,
    import_binance_futures_ohlcv,
    read_binance_import_manifest,
)
from trading_framework.application.market_data.query_historical import (
    QueryHistoricalRequest,
    query_historical,
)
from trading_framework.core.exceptions import ValidationError
from trading_framework.core.identifiers import Identifier
from trading_framework.infrastructure.storage.metadata.registry import FileDatasetRegistry
from trading_framework.infrastructure.storage.parquet.repository import ParquetDatasetRepository
from trading_framework.market.datasets import DatasetLifecycleState
from trading_framework.time.clocks.fixed import FixedClock

_INTERVAL_MS = 60_000
_SECRET_API_KEY = "do-not-leak-me-98765"
_BASE_MS = int(datetime(2024, 1, 1, tzinfo=UTC).timestamp() * 1000)


class _FakeHeaders:
    def __init__(self, values: dict[str, str] | None = None) -> None:
        self._values = values or {}

    def get(self, name: str, default: str | None = None) -> str | None:
        return self._values.get(name, default)


class _FakeResponse:
    def __init__(self, rows: list[list[Any]]) -> None:
        self._body = json.dumps(rows).encode("utf-8")
        self.headers = _FakeHeaders({"X-MBX-USED-WEIGHT-1M": "100"})

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, *args: object) -> None:
        return None


def _row(open_ms: int, close: str) -> list[Any]:
    return [
        open_ms,
        close,
        close,
        close,
        close,
        "1.0",
        open_ms + _INTERVAL_MS - 1,
        "0",
        0,
        "0",
        "0",
        "0",
    ]


def _paged_urlopen(pages: list[list[list[Any]]]) -> Any:
    remaining = list(pages)

    def fake_urlopen(request: Any, timeout: float | None = None) -> _FakeResponse:
        return _FakeResponse(remaining.pop(0))

    return fake_urlopen


def _request(
    *,
    start_at: datetime,
    end_at: datetime,
    api_key: str | None = None,
    mode: str = "ohlcv",
) -> ImportBinanceFuturesOhlcvRequest:
    return ImportBinanceFuturesOhlcvRequest(
        instrument_id=Identifier("BTCUSDT.P"),
        symbol="BTCUSDT",
        interval="1m",
        start_at=start_at,
        end_at=end_at,
        schema_version="market-bar-v1",
        normalization_version="binance-usdm-klines-v1",
        api_key=api_key,
        mode=mode,
    )


def test_import_binance_futures_ohlcv_multi_page_round_trip(tmp_path: Path) -> None:
    """A multi-page import registers, finalizes, publishes and round-trips via query_historical."""
    storage_root = tmp_path / "data"
    start_at = datetime(2024, 1, 1, tzinfo=UTC)
    end_at = datetime(2024, 1, 1, 0, 4, tzinfo=UTC)
    page_one = [_row(_BASE_MS + 0, "100"), _row(_BASE_MS + 60_000, "101")]
    page_two = [_row(_BASE_MS + 120_000, "102"), _row(_BASE_MS + 180_000, "103")]

    result = import_binance_futures_ohlcv(
        _request(start_at=start_at, end_at=end_at),
        storage_root=storage_root,
        urlopen=_paged_urlopen([page_one, page_two]),
        page_limit=2,
        clock=FixedClock(end_at),
    )

    registry = FileDatasetRegistry(storage_root)
    metadata = registry.get(result.dataset_ref)
    assert metadata.lifecycle_status is DatasetLifecycleState.PUBLISHED
    assert metadata.provider == "binance"
    assert metadata.row_count == 4
    assert result.reused is False

    bars = query_historical(
        QueryHistoricalRequest(
            dataset_ref=result.dataset_ref,
            start_at=metadata.start_at,
            end_at=metadata.end_at,
        ),
        storage_root=storage_root,
    )
    assert [float(bar.close.value) for bar in bars] == [100.0, 101.0, 102.0, 103.0]


def test_import_binance_futures_ohlcv_rejects_trades_mode(tmp_path: Path) -> None:
    """mode='trades' is rejected explicitly, before any network access."""

    def _unexpected_urlopen(request: Any, timeout: float | None = None) -> _FakeResponse:
        raise AssertionError("urlopen must not be called for a rejected mode")

    with pytest.raises(ValidationError, match="not supported in v1"):
        import_binance_futures_ohlcv(
            _request(
                start_at=datetime(2024, 1, 1, tzinfo=UTC),
                end_at=datetime(2024, 1, 1, 0, 1, tzinfo=UTC),
                mode="trades",
            ),
            storage_root=tmp_path / "data",
            urlopen=_unexpected_urlopen,
        )


def test_import_binance_futures_ohlcv_rejects_unknown_mode(tmp_path: Path) -> None:
    with pytest.raises(ValidationError, match="unsupported Binance import mode"):
        import_binance_futures_ohlcv(
            _request(
                start_at=datetime(2024, 1, 1, tzinfo=UTC),
                end_at=datetime(2024, 1, 1, 0, 1, tzinfo=UTC),
                mode="bogus",
            ),
            storage_root=tmp_path / "data",
        )


def test_import_binance_futures_ohlcv_manifest_fields_and_no_key_leak(tmp_path: Path) -> None:
    storage_root = tmp_path / "data"
    start_at = datetime(2024, 1, 1, tzinfo=UTC)
    end_at = datetime(2024, 1, 1, 0, 1, tzinfo=UTC)
    page = [_row(_BASE_MS + 0, "100")]

    result = import_binance_futures_ohlcv(
        _request(start_at=start_at, end_at=end_at, api_key=_SECRET_API_KEY),
        storage_root=storage_root,
        urlopen=_paged_urlopen([page]),
        clock=FixedClock(end_at),
    )

    manifest = read_binance_import_manifest(storage_root, result.dataset_ref)
    expected_fields = {
        "provider",
        "mode",
        "symbol",
        "instrument_id",
        "interval",
        "requested_start",
        "requested_end",
        "first_bar_open_time",
        "last_bar_close_time",
        "page_count",
        "request_count",
        "retry_count",
        "rows_decoded",
        "rows_rejected",
        "gaps",
        "normalization_version",
        "schema_version",
        "api_key_used",
    }
    assert expected_fields.issubset(manifest.keys())
    assert manifest["provider"] == "binance"
    assert manifest["mode"] == "ohlcv"
    assert manifest["symbol"] == "BTCUSDT"
    assert manifest["api_key_used"] is True
    assert manifest["rows_decoded"] == 1

    raw_text = json.dumps(manifest)
    assert _SECRET_API_KEY not in raw_text


def test_import_binance_futures_ohlcv_gap_passes_validation_and_is_recorded(
    tmp_path: Path,
) -> None:
    """A real Binance gap (empty page inside the range) passes ``OhlcvBarValidator`` (T006)."""
    storage_root = tmp_path / "data"
    start_at = datetime(2024, 1, 1, tzinfo=UTC)
    end_at = datetime(2024, 1, 1, 0, 3, tzinfo=UTC)
    # Page 1 is empty (a gap); page 2 resumes with a later bar.
    page_one: list[list[Any]] = []
    page_two = [_row(_BASE_MS + 120_000, "102")]

    result = import_binance_futures_ohlcv(
        _request(start_at=start_at, end_at=end_at),
        storage_root=storage_root,
        urlopen=_paged_urlopen([page_one, page_two]),
        page_limit=2,
        clock=FixedClock(end_at),
    )

    assert result.validation_result.is_valid is True
    assert result.reused is False
    manifest = read_binance_import_manifest(storage_root, result.dataset_ref)
    assert len(manifest["gaps"]) == 1


def test_import_binance_futures_ohlcv_reimport_is_idempotent(tmp_path: Path) -> None:
    """Re-importing an identical range reuses the published version (no second publish)."""
    storage_root = tmp_path / "data"
    start_at = datetime(2024, 1, 1, tzinfo=UTC)
    end_at = datetime(2024, 1, 1, 0, 2, tzinfo=UTC)
    page = [_row(_BASE_MS + 0, "100"), _row(_BASE_MS + 60_000, "101")]

    registry = FileDatasetRegistry(storage_root)
    repository = ParquetDatasetRepository(storage_root)

    first = import_binance_futures_ohlcv(
        _request(start_at=start_at, end_at=end_at),
        storage_root=storage_root,
        urlopen=_paged_urlopen([list(page)]),
        registry=registry,
        repository=repository,
        clock=FixedClock(end_at),
    )
    second = import_binance_futures_ohlcv(
        _request(start_at=start_at, end_at=end_at),
        storage_root=storage_root,
        urlopen=_paged_urlopen([list(page)]),
        registry=registry,
        repository=repository,
        clock=FixedClock(end_at),
    )

    assert first.reused is False
    assert second.reused is True
    assert second.dataset_ref == first.dataset_ref

    first_metadata = registry.get(first.dataset_ref)
    assert first_metadata.dataset_ref.version == 1

    bars = query_historical(
        QueryHistoricalRequest(
            dataset_ref=first.dataset_ref,
            start_at=first_metadata.start_at,
            end_at=first_metadata.end_at,
        ),
        storage_root=storage_root,
    )
    assert len(bars) == 2
