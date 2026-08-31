"""Tests for `trading-cli data fetch databento` (S046-T009).

Tier 1, network-free: fakes ``import_databento_trades_archive`` (the same
pattern as tests/unit/application/market_data's own coverage of that
workflow, which already exercises the real DBN decode path). This module
proves the CLI seam: config -> `DatabentoTradesArchiveImportConfig` ->
printed result, plus the "import, not network fetch" naming caveat (a real
local file must exist) and the `data fetch binance` Wave-3 placeholder.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from unittest.mock import patch

import pytest

from trading_cli.cli import main
from trading_cli.commands import data as data_cmd
from trading_cli.errors import EXIT_CONFIG_ERROR, EXIT_SUCCESS, EXIT_WORKFLOW_FAILURE


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


def test_data_fetch_binance_is_not_implemented_yet(tmp_path: Path) -> None:
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
            "    mode: ohlcv\n"
            "    symbol: BTCUSDT\n"
            "    instrument_id: BTCUSDT.P\n"
            "    interval: 1m\n"
            "    start: 2025-01-01T00:00:00Z\n"
            "    end: 2025-01-02T00:00:00Z\n"
        ),
    )

    exit_code = main(["data", "fetch", "--config", str(config_path)])

    assert exit_code == EXIT_WORKFLOW_FAILURE
