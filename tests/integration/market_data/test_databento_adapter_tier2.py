"""Tier 2 Databento adapter integration tests."""

from pathlib import Path

import pytest

from trading_framework.infrastructure.importers.databento import (
    DatabentoDBNInspector,
    DatabentoDBNTradeReader,
)

_DEFAULT_DBN = Path(
    "user_data/market_data/NQ/databento/GLBX-20260712-DU3ML8YKBH/glbx-mdp3-20250713.trades.dbn.zst"
)


@pytest.mark.tier2_databento
@pytest.mark.skipif(not _DEFAULT_DBN.exists(), reason="local trades DBN not available")
def test_databento_inspector_reads_local_trades_archive() -> None:
    result = DatabentoDBNInspector().inspect(_DEFAULT_DBN)
    assert result.vendor_schema == "trades"
    assert result.nbytes > 0


@pytest.mark.tier2_databento
@pytest.mark.skipif(not _DEFAULT_DBN.exists(), reason="local trades DBN not available")
def test_databento_reader_decodes_local_trades_archive() -> None:
    reader = DatabentoDBNTradeReader(chunk_size=1_000)
    trades = list(reader.iter_trades(_DEFAULT_DBN))
    assert len(trades) > 0
    assert trades[0].size.value > 0
