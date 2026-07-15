"""CLI tests for the Binance futures live feed smoke command."""

from unittest.mock import patch

import pytest
from scripts.live_data import run_binance_futures_smoke

from trading_framework.infrastructure.providers.binance import BinanceFuturesSmokeConfig


def test_binance_futures_smoke_cli_runs_with_bounded_arguments(
    capsys: pytest.CaptureFixture[str],
) -> None:
    async def fake_run(config: BinanceFuturesSmokeConfig, writer: object) -> int:
        assert config.symbol == "BTCUSDT"
        assert config.duration_seconds == 1.5
        assert config.max_messages == 2
        return 2

    with patch.object(run_binance_futures_smoke, "run_binance_futures_feed_smoke", fake_run):
        exit_code = run_binance_futures_smoke.main(
            [
                "--symbol",
                "btcusdt",
                "--duration-seconds",
                "1.5",
                "--max-messages",
                "2",
            ]
        )

    output = capsys.readouterr().out
    assert exit_code == 0
    assert '"event": "summary"' in output
    assert '"emitted": 2' in output


def test_binance_futures_smoke_cli_rejects_invalid_duration(
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = run_binance_futures_smoke.main(["--duration-seconds", "0"])

    error = capsys.readouterr().err
    assert exit_code == 1
    assert "duration_seconds" in error
