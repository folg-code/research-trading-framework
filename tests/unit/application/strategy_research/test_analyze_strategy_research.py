"""Tests for analyze_strategy_research_run application orchestration."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import polars as pl

from trading_framework import __version__ as framework_version
from trading_framework.application.strategy_research import (
    AnalyzeStrategyResearchRequest,
    analyze_strategy_research_run,
)
from trading_framework.research.datasets.strategy_research import (
    STRATEGY_RESEARCH_SCHEMA_VERSION,
    StrategyResearchDatasetRepository,
    StrategyResearchRunEnvelope,
    StrategyResearchRunManifest,
    StrategyResearchRunRef,
)
from trading_framework.research.simulation.facts import (
    empty_equity_points_dataframe,
    equity_point_schema,
    simulated_trade_schema,
)
from trading_framework.strategy.exit_model import ExitReason


def _manifest(*, run_id: str) -> StrategyResearchRunManifest:
    return StrategyResearchRunManifest(
        run_id=run_id,
        schema_version=STRATEGY_RESEARCH_SCHEMA_VERSION,
        framework_version=framework_version,
        created_at_utc=datetime(2024, 1, 1, tzinfo=UTC),
        source_dataset_ref="ES.c.0:ohlcv:1m:csv:fixture@1",
        evaluation_timeframe="1m",
        strategy_model_id="high_vol_higher_low_fixed_exit",
        market_model_id="high_volatility",
        signal_model_id="higher_low_long",
        exit_model_id="fixed_bars",
        risk_model_id="fixed_quantity",
        simulation_assumptions_fingerprint="1aa6ee647c5cc636",
    )


def test_analyze_strategy_research_run_summarizes_persisted_run(tmp_path: Path) -> None:
    run_id = "analyze-strategy-run"
    entry_at = datetime(2024, 1, 1, 12, 1, tzinfo=UTC)
    exit_at = datetime(2024, 1, 1, 12, 4, tzinfo=UTC)
    trades = pl.DataFrame(
        {
            "trade_id": ["trade-1"],
            "strategy_model_id": ["high_vol_higher_low_fixed_exit"],
            "instrument": ["ES.c.0"],
            "direction": ["long"],
            "entry_signal_at": [datetime(2024, 1, 1, 12, 0, tzinfo=UTC)],
            "entry_fill_at": [entry_at],
            "entry_fill_price": [100.0],
            "exit_signal_at": [datetime(2024, 1, 1, 12, 3, tzinfo=UTC)],
            "exit_fill_at": [exit_at],
            "exit_fill_price": [103.0],
            "quantity": [1.0],
            "gross_pnl": [3.0],
            "commission_paid": [2.0],
            "net_pnl": [1.0],
            "bars_held": [3],
            "exit_reason": [ExitReason.FIXED_BARS.value],
            "source_dataset_ref": ["dataset@1"],
        },
        schema=simulated_trade_schema(),
    )
    equity = pl.DataFrame(
        {
            "observed_at": [
                datetime(2024, 1, 1, 12, 0, tzinfo=UTC),
                datetime(2024, 1, 1, 12, 4, tzinfo=UTC),
            ],
            "equity": [1000.0, 1001.0],
            "drawdown": [0.0, 0.0],
            "open_position_count": [0, 0],
        },
        schema=equity_point_schema(),
    )
    envelope = StrategyResearchRunEnvelope(
        manifest=_manifest(run_id=run_id),
        trades=trades,
        equity=equity,
    )
    repository = StrategyResearchDatasetRepository(tmp_path)
    run_ref = repository.write(envelope)

    result = analyze_strategy_research_run(
        AnalyzeStrategyResearchRequest(run_ref=run_ref, storage_root=tmp_path)
    )

    assert result.source_run_id == run_id
    assert result.summary.trade_count == 1
    assert result.summary.win_count == 1
    assert result.summary.loss_count == 0
    assert result.summary.win_rate == 1.0
    assert result.summary.net_pnl == Decimal("1")
    assert result.summary.final_equity == Decimal("1001")


def test_analyze_strategy_research_run_handles_empty_trades(tmp_path: Path) -> None:
    run_id = "empty-trades-run"
    envelope = StrategyResearchRunEnvelope(
        manifest=_manifest(run_id=run_id),
        trades=pl.DataFrame(schema=simulated_trade_schema()),
        equity=empty_equity_points_dataframe(),
    )
    repository = StrategyResearchDatasetRepository(tmp_path)
    run_ref = repository.write(envelope)

    result = analyze_strategy_research_run(
        AnalyzeStrategyResearchRequest(
            run_ref=StrategyResearchRunRef(run_id=run_ref.run_id),
            storage_root=tmp_path,
        )
    )

    assert result.summary.trade_count == 0
    assert result.summary.win_rate is None
