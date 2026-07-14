"""Databento DBN trade reader tests with mocked DBNStore."""

from pathlib import Path
from unittest.mock import patch

import pytest

from tests.fixtures.databento import SyntheticTradeRowSpec, build_mock_dbn_store
from trading_framework.infrastructure.importers.databento.reader import DatabentoDBNTradeReader
from trading_framework.market.models import TradeSide


def test_databento_reader_decodes_synthetic_trades(tmp_path: Path) -> None:
    archive_path = tmp_path / "sample.dbn.zst"
    archive_path.write_bytes(b"fake-dbn")
    mock_store = build_mock_dbn_store()

    with patch(
        "trading_framework.infrastructure.importers.databento.reader.db.DBNStore.from_file",
        return_value=mock_store,
    ):
        trades = list(DatabentoDBNTradeReader(chunk_size=10).iter_trades(archive_path))

    assert len(trades) == 3
    assert trades[0].side is TradeSide.BUY
    assert trades[1].side is TradeSide.SELL


def test_databento_reader_filters_by_provider_symbol(tmp_path: Path) -> None:
    archive_path = tmp_path / "sample.dbn.zst"
    archive_path.write_bytes(b"fake-dbn")
    specs = [
        SyntheticTradeRowSpec(second=0, symbol="NQ.FUT"),
        SyntheticTradeRowSpec(second=1, symbol="ES.FUT"),
    ]
    mock_store = build_mock_dbn_store(specs=specs)

    with patch(
        "trading_framework.infrastructure.importers.databento.reader.db.DBNStore.from_file",
        return_value=mock_store,
    ):
        trades = list(DatabentoDBNTradeReader().iter_trades(archive_path, provider_symbol="NQ.FUT"))

    assert len(trades) == 1


def test_databento_reader_rejects_unsupported_schema(tmp_path: Path) -> None:
    archive_path = tmp_path / "sample.dbn.zst"
    archive_path.write_bytes(b"fake-dbn")
    mock_store = build_mock_dbn_store()
    mock_store.schema = "mbp-1"

    with (
        patch(
            "trading_framework.infrastructure.importers.databento.reader.db.DBNStore.from_file",
            return_value=mock_store,
        ),
        pytest.raises(ValueError, match="unsupported databento schema"),
    ):
        list(DatabentoDBNTradeReader().iter_trades(archive_path))
