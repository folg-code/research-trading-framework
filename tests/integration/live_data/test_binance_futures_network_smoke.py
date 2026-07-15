"""Opt-in network smoke test for Binance USD-M futures live data."""

import os

import pytest

from trading_framework.infrastructure.providers.binance import (
    BinanceFuturesSmokeConfig,
    run_binance_futures_feed_smoke,
)

RUN_ENV_VAR = "TRADING_FRAMEWORK_RUN_BINANCE_NETWORK_SMOKE"

pytestmark = pytest.mark.binance_network


@pytest.mark.skipif(
    os.getenv(RUN_ENV_VAR) != "1",
    reason=f"set {RUN_ENV_VAR}=1 to run Binance network smoke test",
)
def test_binance_futures_feed_smoke_receives_live_payloads() -> None:
    """Receive at least one normalized BTCUSDT event from public Binance streams."""
    import asyncio

    received: list[dict[str, object]] = []
    config = BinanceFuturesSmokeConfig(
        symbol="BTCUSDT",
        duration_seconds=10.0,
        max_messages=1,
    )

    emitted = asyncio.run(run_binance_futures_feed_smoke(config, writer=received.append))

    assert emitted >= 1
    assert received
    assert received[0]["symbol"] == "BTCUSDT"
    assert received[0]["event"] in {"book_ticker", "closed_kline_1m"}
