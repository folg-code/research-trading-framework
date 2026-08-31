"""CLI tests for scripts/market_data/import_binance_ohlcv.py (Tier 1, network-free)."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from scripts.market_data import import_binance_ohlcv

from trading_framework.application.market_data.query_historical import (
    QueryHistoricalRequest,
    query_historical,
)
from trading_framework.infrastructure.storage.metadata.registry import FileDatasetRegistry
from trading_framework.market.datasets import DatasetLifecycleState, DatasetRef

_INTERVAL_MS = 60_000
_BASE_MS = int(datetime(2024, 1, 1, tzinfo=UTC).timestamp() * 1000)
_PATCH_TARGET = (
    "trading_framework.infrastructure.providers.binance."
    "futures_klines_history.urllib.request.urlopen"
)


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


def test_import_binance_ohlcv_cli_end_to_end_round_trip(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A multi-page CLI import publishes a dataset that round-trips via query_historical."""
    storage_root = tmp_path / "data"
    page_one = [_row(_BASE_MS + 0, "100"), _row(_BASE_MS + 60_000, "101")]
    page_two = [_row(_BASE_MS + 120_000, "102"), _row(_BASE_MS + 180_000, "103")]

    with patch(_PATCH_TARGET, side_effect=_paged_urlopen([page_one, page_two])):
        exit_code = import_binance_ohlcv.main(
            [
                "--storage-root",
                str(storage_root),
                "--instrument-id",
                "BTCUSDT.P",
                "--symbol",
                "BTCUSDT",
                "--interval",
                "1m",
                "--start",
                "2024-01-01T00:00:00Z",
                "--end",
                "2024-01-01T00:04:00Z",
                "--json",
            ]
        )

    output = capsys.readouterr().out
    assert exit_code == 0
    payload = json.loads(output)
    assert payload["reused"] is False
    assert payload["validation_passed"] is True
    assert payload["manifest"]["rows_decoded"] == 4
    assert payload["manifest"]["api_key_used"] is False

    dataset_ref = DatasetRef.parse(payload["dataset_ref"])
    registry = FileDatasetRegistry(storage_root)
    metadata = registry.get(dataset_ref)
    assert metadata.lifecycle_status is DatasetLifecycleState.PUBLISHED
    assert metadata.provider == "binance"

    bars = query_historical(
        QueryHistoricalRequest(
            dataset_ref=dataset_ref,
            start_at=metadata.start_at,
            end_at=metadata.end_at,
        ),
        storage_root=storage_root,
    )
    assert [float(bar.close.value) for bar in bars] == [100.0, 101.0, 102.0, 103.0]


def test_import_binance_ohlcv_cli_human_readable_output(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    storage_root = tmp_path / "data"
    page = [_row(_BASE_MS + 0, "100")]

    with patch(_PATCH_TARGET, side_effect=_paged_urlopen([page])):
        exit_code = import_binance_ohlcv.main(
            [
                "--storage-root",
                str(storage_root),
                "--instrument-id",
                "BTCUSDT.P",
                "--symbol",
                "BTCUSDT",
                "--start",
                "2024-01-01T00:00:00Z",
                "--end",
                "2024-01-01T00:01:00Z",
            ]
        )

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "dataset_ref:" in output
    assert "rows_decoded: 1" in output


def test_import_binance_ohlcv_cli_rejects_trades_mode_with_exit_code_one(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A rejected mode is a handled error: exit code 1, no traceback, no network call."""

    def _unexpected_urlopen(request: Any, timeout: float | None = None) -> _FakeResponse:
        raise AssertionError("urlopen must not be called for a rejected mode")

    with patch(_PATCH_TARGET, side_effect=_unexpected_urlopen):
        exit_code = import_binance_ohlcv.main(
            [
                "--storage-root",
                str(tmp_path / "data"),
                "--instrument-id",
                "BTCUSDT.P",
                "--symbol",
                "BTCUSDT",
                "--start",
                "2024-01-01T00:00:00Z",
                "--end",
                "2024-01-01T00:01:00Z",
                "--mode",
                "trades",
            ]
        )

    assert exit_code == 1
    error_output = capsys.readouterr().err
    assert "not supported in v1" in error_output


def test_import_binance_ohlcv_cli_rejects_naive_start_with_exit_code_one(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A naive (non-UTC) --start is a handled validation error, not a traceback."""
    exit_code = import_binance_ohlcv.main(
        [
            "--storage-root",
            str(tmp_path / "data"),
            "--instrument-id",
            "BTCUSDT.P",
            "--symbol",
            "BTCUSDT",
            "--start",
            "2024-01-01T00:00:00",
            "--end",
            "2024-01-01T00:01:00Z",
        ]
    )

    assert exit_code == 1
    assert "timezone-aware" in capsys.readouterr().err


def test_import_binance_ohlcv_cli_help_lists_every_option(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as exc_info:
        import_binance_ohlcv.main(["--help"])

    assert exc_info.value.code == 0
    help_text = capsys.readouterr().out
    for option in (
        "--storage-root",
        "--instrument-id",
        "--symbol",
        "--interval",
        "--start",
        "--end",
        "--mode",
        "--provider",
        "--source-id",
        "--schema-version",
        "--normalization-version",
        "--api-key",
        "--json",
    ):
        assert option in help_text
