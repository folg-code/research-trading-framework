"""Databento DBN inspector tests with mocked DBNStore."""

from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

import pytest

from tests.fixtures.databento import build_mock_dbn_store
from trading_framework.infrastructure.importers.databento.inspector import DatabentoDBNInspector
from trading_framework.market.importers import ArchiveSourceFormat


def test_databento_inspector_reads_trades_metadata(tmp_path: Path) -> None:
    archive_path = tmp_path / "sample.dbn.zst"
    archive_path.write_bytes(b"fake-dbn")
    mock_store = build_mock_dbn_store()

    with patch(
        "trading_framework.infrastructure.importers.databento.inspector.db.DBNStore.from_file",
        return_value=mock_store,
    ):
        result = DatabentoDBNInspector().inspect(archive_path)

    assert result.source_format is ArchiveSourceFormat.DATABENTO_DBN
    assert result.vendor_schema == "trades"
    assert result.symbols == ("NQ.FUT", "ES.FUT")
    assert result.dataset == "GLBX.MDP3"
    assert result.start_at == datetime(2025, 7, 13, 22, 0, 0, tzinfo=UTC)


def test_databento_inspector_rejects_unsupported_schema(tmp_path: Path) -> None:
    archive_path = tmp_path / "sample.dbn.zst"
    archive_path.write_bytes(b"fake-dbn")
    mock_store = build_mock_dbn_store()
    mock_store.schema = "ohlcv-1s"

    with (
        patch(
            "trading_framework.infrastructure.importers.databento.inspector.db.DBNStore.from_file",
            return_value=mock_store,
        ),
        pytest.raises(ValueError, match="unsupported databento schema"),
    ):
        DatabentoDBNInspector().inspect(archive_path)


def test_databento_inspector_reads_ohlcv_metadata(tmp_path: Path) -> None:
    archive_path = tmp_path / "sample.dbn.zst"
    archive_path.write_bytes(b"fake-dbn")
    mock_store = build_mock_dbn_store()
    mock_store.schema = "ohlcv-1m"

    with patch(
        "trading_framework.infrastructure.importers.databento.inspector.db.DBNStore.from_file",
        return_value=mock_store,
    ):
        result = DatabentoDBNInspector().inspect(archive_path)

    assert result.source_format is ArchiveSourceFormat.DATABENTO_DBN
    assert result.vendor_schema == "ohlcv-1m"
    assert result.symbols == ("NQ.FUT", "ES.FUT")
    assert result.dataset == "GLBX.MDP3"


def test_databento_inspector_with_checksum(tmp_path: Path) -> None:
    archive_path = tmp_path / "sample.dbn.zst"
    archive_path.write_bytes(b"checksum-bytes")
    mock_store = build_mock_dbn_store()

    with patch(
        "trading_framework.infrastructure.importers.databento.inspector.db.DBNStore.from_file",
        return_value=mock_store,
    ):
        result, checksum = DatabentoDBNInspector().inspect_with_checksum(archive_path)

    assert result.vendor_schema == "trades"
    assert len(checksum) == 64
