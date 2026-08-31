"""Opt-in network smoke test for Binance USD-M historical OHLCV import.

Mirrors ``test_binance_futures_network_smoke.py``'s marker/env-var convention
(D-S045-12): excluded from the standard, network-free CI run by default.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from trading_framework.application.market_data import (
    ImportBinanceFuturesOhlcvRequest,
    import_binance_futures_ohlcv,
)
from trading_framework.core.identifiers import Identifier

RUN_ENV_VAR = "TRADING_FRAMEWORK_RUN_BINANCE_NETWORK_SMOKE"

pytestmark = pytest.mark.binance_network


@pytest.mark.skipif(
    os.getenv(RUN_ENV_VAR) != "1",
    reason=f"set {RUN_ENV_VAR}=1 to run Binance historical OHLCV network smoke test",
)
def test_import_binance_historical_ohlcv_smoke_short_range(tmp_path: Path) -> None:
    """A one-hour BTCUSDT 1m range imports and publishes against the real Binance API."""
    end_at = datetime.now(tz=UTC).replace(second=0, microsecond=0) - timedelta(minutes=5)
    start_at = end_at - timedelta(hours=1)

    request = ImportBinanceFuturesOhlcvRequest(
        instrument_id=Identifier("BTCUSDT.P"),
        symbol="BTCUSDT",
        interval="1m",
        start_at=start_at,
        end_at=end_at,
        schema_version="market-bar-v1",
        normalization_version="binance-usdm-klines-v1",
    )

    result = import_binance_futures_ohlcv(request, storage_root=tmp_path)

    assert result.validation_result.is_valid is True
    assert result.manifest.rows_decoded > 0
