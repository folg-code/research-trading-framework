"""Tests for `trading-cli data fetch` (S046-T009 databento, S046-T010 binance).

Tier 1, network-free: fakes ``import_databento_trades_archive`` and
``import_binance_futures_ohlcv`` (the same pattern as
tests/unit/application/market_data's own coverage of those workflows, which
already exercises the real decode paths). This module proves the CLI seam:
config -> typed request -> printed result, plus the "import, not network
fetch" naming caveat for databento (a real local file must exist) and the
TD-023 eager interval validation for binance.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from unittest.mock import patch

import pytest

from trading_cli.cli import main
from trading_cli.commands import data as data_cmd
from trading_cli.errors import EXIT_CONFIG_ERROR, EXIT_SUCCESS


def _write_config(tmp_path: Path, *, storage_root: Path, text: str) -> Path:
    path = tmp_path / "config.yaml"
    path.write_text(text.format(storage_root=storage_root.as_posix()), encoding="utf-8")
    return path


@dataclass(frozen=True, slots=True)
class _FakeValidationResult:
    is_valid: bool


@dataclass(frozen=True, slots=True)
class _FakeManifest:
    decode_row_count: int
    rejected_row_count: int


@dataclass(frozen=True, slots=True)
class _FakeImportResult:
    dataset_ref: str
    validation_result: _FakeValidationResult
    manifest: _FakeManifest


def test_data_fetch_databento_imports_local_archive(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    storage_root = tmp_path / "workspace"
    archive = tmp_path / "sample.dbn.zst"
    archive.write_bytes(b"not-a-real-archive")
    config_path = _write_config(
        tmp_path,
        storage_root=storage_root,
        text=(
            "version: 1\n"
            "storage_root: {storage_root}\n\n"
            "data:\n"
            "  provider: databento\n"
            "  databento:\n"
            f"    archive: {archive.as_posix()}\n"
            "    instrument_id: NQ.c.0\n"
        ),
    )
    captured: dict[str, object] = {}

    def fake_import(config: object, *, storage_root: Path) -> _FakeImportResult:
        captured["path"] = config.path  # type: ignore[attr-defined]
        captured["instrument_id"] = config.dataset_id.instrument_id.value  # type: ignore[attr-defined]
        captured["provider_symbol"] = config.symbol_mapping.provider_symbol  # type: ignore[attr-defined]
        return _FakeImportResult(
            dataset_ref="NQ.c.0|trades|tick|databento|NQ.c.0@1",
            validation_result=_FakeValidationResult(is_valid=True),
            manifest=_FakeManifest(decode_row_count=10, rejected_row_count=0),
        )

    with patch.object(data_cmd, "import_databento_trades_archive", fake_import):
        exit_code = main(["data", "fetch", "--config", str(config_path), "--json"])

    assert exit_code == EXIT_SUCCESS
    assert captured["path"] == archive
    assert captured["instrument_id"] == "NQ.c.0"
    # naming caveat: with no source_id/provider_symbol in the config
    # (D-S046-07 locks the schema to archive + instrument_id), both default
    # to instrument_id
    assert captured["provider_symbol"] == "NQ.c.0"
    payload = json.loads(capsys.readouterr().out)
    assert payload["result"]["dataset_ref"] == "NQ.c.0|trades|tick|databento|NQ.c.0@1"


def test_data_fetch_databento_missing_archive_is_config_error(tmp_path: Path) -> None:
    storage_root = tmp_path / "workspace"
    config_path = _write_config(
        tmp_path,
        storage_root=storage_root,
        text=(
            "version: 1\n"
            "storage_root: {storage_root}\n\n"
            "data:\n"
            "  provider: databento\n"
            "  databento:\n"
            f"    archive: {(tmp_path / 'does-not-exist.dbn.zst').as_posix()}\n"
            "    instrument_id: NQ.c.0\n"
        ),
    )

    exit_code = main(["data", "fetch", "--config", str(config_path)])

    assert exit_code == EXIT_CONFIG_ERROR


def test_data_fetch_missing_instrument_id_is_config_error(tmp_path: Path) -> None:
    storage_root = tmp_path / "workspace"
    archive = tmp_path / "sample.dbn.zst"
    archive.write_bytes(b"not-a-real-archive")
    config_path = _write_config(
        tmp_path,
        storage_root=storage_root,
        text=(
            "version: 1\n"
            "storage_root: {storage_root}\n\n"
            "data:\n"
            "  provider: databento\n"
            "  databento:\n"
            f"    archive: {archive.as_posix()}\n"
        ),
    )

    exit_code = main(["data", "fetch", "--config", str(config_path)])

    assert exit_code == EXIT_CONFIG_ERROR


@dataclass(frozen=True, slots=True)
class _FakeBinanceManifest:
    page_count: int
    rows_decoded: int
    rows_rejected: int
    api_key_used: bool
    gaps: tuple[object, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "page_count": self.page_count,
            "rows_decoded": self.rows_decoded,
            "rows_rejected": self.rows_rejected,
            "api_key_used": self.api_key_used,
        }


@dataclass(frozen=True, slots=True)
class _FakeBinanceResult:
    dataset_ref: str
    validation_result: _FakeValidationResult
    manifest: _FakeBinanceManifest
    reused: bool


def _binance_config_text(*, interval: str = "1m", extra: str = "") -> str:
    return (
        "version: 1\n"
        "storage_root: {storage_root}\n\n"
        "data:\n"
        "  provider: binance\n"
        "  binance:\n"
        "    mode: ohlcv\n"
        "    symbol: BTCUSDT\n"
        "    instrument_id: BTCUSDT.P\n"
        f"    interval: {interval}\n"
        "    start: 2025-01-01T00:00:00Z\n"
        "    end: 2025-01-02T00:00:00Z\n"
        f"{extra}"
    )


def test_data_fetch_binance_imports_range(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    storage_root = tmp_path / "workspace"
    config_path = _write_config(tmp_path, storage_root=storage_root, text=_binance_config_text())
    captured: dict[str, object] = {}

    def fake_import(request: object, *, storage_root: Path) -> _FakeBinanceResult:
        captured["symbol"] = request.symbol  # type: ignore[attr-defined]
        captured["interval"] = request.interval  # type: ignore[attr-defined]
        captured["api_key"] = request.api_key  # type: ignore[attr-defined]
        captured["start_at"] = request.start_at  # type: ignore[attr-defined]
        return _FakeBinanceResult(
            dataset_ref="BTCUSDT.P|ohlcv|1m|binance|binance-usdm-klines-v1@1",
            validation_result=_FakeValidationResult(is_valid=True),
            manifest=_FakeBinanceManifest(
                page_count=1, rows_decoded=1440, rows_rejected=0, api_key_used=False
            ),
            reused=False,
        )

    with patch.object(data_cmd, "import_binance_futures_ohlcv", fake_import):
        exit_code = main(["data", "fetch", "--config", str(config_path), "--json"])

    assert exit_code == EXIT_SUCCESS
    assert captured["symbol"] == "BTCUSDT"
    assert captured["interval"] == "1m"
    # the CLI never reads or forwards an API key (D-S046-08) -- the fetch
    # layer resolves TRADING_FRAMEWORK_BINANCE_API_KEY from the environment.
    assert captured["api_key"] is None
    assert captured["start_at"].tzinfo is not None
    payload = json.loads(capsys.readouterr().out)
    assert payload["result"]["dataset_ref"] == "BTCUSDT.P|ohlcv|1m|binance|binance-usdm-klines-v1@1"


def test_data_fetch_binance_non_1m_interval_is_config_error_before_side_effect(
    tmp_path: Path,
) -> None:
    storage_root = tmp_path / "workspace"
    config_path = _write_config(
        tmp_path, storage_root=storage_root, text=_binance_config_text(interval="5m")
    )

    def fail_if_called(*args: object, **kwargs: object) -> None:
        raise AssertionError("import_binance_futures_ohlcv must not be called for TD-023")

    with patch.object(data_cmd, "import_binance_futures_ohlcv", fail_if_called):
        exit_code = main(["data", "fetch", "--config", str(config_path)])

    assert exit_code == EXIT_CONFIG_ERROR


def test_data_fetch_binance_publish_false_is_config_error(tmp_path: Path) -> None:
    storage_root = tmp_path / "workspace"
    config_path = _write_config(
        tmp_path,
        storage_root=storage_root,
        text=_binance_config_text(extra="    publish: false\n"),
    )

    exit_code = main(["data", "fetch", "--config", str(config_path)])

    assert exit_code == EXIT_CONFIG_ERROR


def test_data_fetch_binance_missing_start_is_config_error(tmp_path: Path) -> None:
    storage_root = tmp_path / "workspace"
    config_path = _write_config(
        tmp_path,
        storage_root=storage_root,
        text=(
            "version: 1\n"
            "storage_root: {storage_root}\n\n"
            "data:\n"
            "  provider: binance\n"
            "  binance:\n"
            "    symbol: BTCUSDT\n"
            "    instrument_id: BTCUSDT.P\n"
            "    interval: 1m\n"
            "    end: 2025-01-02T00:00:00Z\n"
        ),
    )

    exit_code = main(["data", "fetch", "--config", str(config_path)])

    assert exit_code == EXIT_CONFIG_ERROR


def test_data_fetch_binance_dry_run_touches_nothing(tmp_path: Path) -> None:
    storage_root = tmp_path / "workspace"
    config_path = _write_config(tmp_path, storage_root=storage_root, text=_binance_config_text())

    def fail_if_called(*args: object, **kwargs: object) -> None:
        raise AssertionError("--dry-run must not call the workflow")

    with patch.object(data_cmd, "import_binance_futures_ohlcv", fail_if_called):
        exit_code = main(["data", "fetch", "--config", str(config_path), "--dry-run"])

    assert exit_code == EXIT_SUCCESS
    assert not storage_root.exists()
