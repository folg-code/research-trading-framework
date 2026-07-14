"""CLI tests for Databento scripts."""

from pathlib import Path
from unittest.mock import patch

import pytest
from scripts.databento import import_trades, inspect_dbn

from tests.fixtures.databento import build_mock_dbn_store


def test_inspect_dbn_cli_prints_json(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    archive_path = tmp_path / "sample.dbn.zst"
    archive_path.write_bytes(b"fake-dbn")
    mock_store = build_mock_dbn_store()

    with patch(
        "trading_framework.infrastructure.importers.databento.inspector.db.DBNStore.from_file",
        return_value=mock_store,
    ):
        exit_code = inspect_dbn.main(["--path", str(archive_path), "--json"])

    output = capsys.readouterr().out
    assert exit_code == 0
    assert '"vendor_schema": "trades"' in output
    assert '"source_checksum_sha256"' in output


def test_import_trades_cli_registers_dataset(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    archive_path = tmp_path / "sample.dbn.zst"
    archive_path.write_bytes(b"fake-dbn")
    storage_root = tmp_path / "data"
    mock_store = build_mock_dbn_store()

    with (
        patch(
            "trading_framework.infrastructure.importers.databento.inspector.db.DBNStore.from_file",
            return_value=mock_store,
        ),
        patch(
            "trading_framework.infrastructure.importers.databento.reader.db.DBNStore.from_file",
            return_value=mock_store,
        ),
    ):
        exit_code = import_trades.main(
            [
                "--path",
                str(archive_path),
                "--storage-root",
                str(storage_root),
                "--instrument-id",
                "nq",
                "--source-id",
                "cli-trades",
                "--provider-symbol",
                "NQ.FUT",
                "--json",
            ]
        )

    output = capsys.readouterr().out
    assert exit_code == 0
    assert '"validation_passed": true' in output
    assert '"decode_row_count": 2' in output
