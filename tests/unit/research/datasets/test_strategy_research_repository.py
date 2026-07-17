"""Tests for Strategy Research dataset repository."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from trading_framework import __version__ as framework_version
from trading_framework.core.exceptions import ValidationError
from trading_framework.research.datasets.strategy_research import (
    STRATEGY_RESEARCH_SCHEMA_VERSION,
    StrategyResearchDatasetRepository,
    StrategyResearchRunEnvelope,
    StrategyResearchRunManifest,
    StrategyResearchRunRef,
    derive_strategy_run_id,
)
from trading_framework.research.simulation.facts import (
    empty_equity_points_dataframe,
    empty_simulated_trades_dataframe,
)


def _sample_manifest(*, run_id: str) -> StrategyResearchRunManifest:
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


def _sample_envelope(*, run_id: str) -> StrategyResearchRunEnvelope:
    return StrategyResearchRunEnvelope(
        manifest=_sample_manifest(run_id=run_id),
        trades=empty_simulated_trades_dataframe(),
        equity=empty_equity_points_dataframe(),
    )


def test_derive_strategy_run_id_is_stable() -> None:
    start = datetime(2024, 1, 1, tzinfo=UTC)
    end = datetime(2024, 1, 2, tzinfo=UTC)
    first = derive_strategy_run_id(
        strategy_model_id="strategy_a",
        market_model_id="market_a",
        signal_model_id="signal_a",
        exit_model_id="fixed_bars",
        exit_after_bars=10,
        risk_model_id="fixed_quantity",
        position_quantity="1",
        source_dataset_ref="dataset@1",
        evaluation_timeframe="1m",
        requested_range_start=start,
        requested_range_end=end,
        framework_version=framework_version,
        simulation_assumptions_fingerprint="1aa6ee647c5cc636",
    )
    second = derive_strategy_run_id(
        strategy_model_id="strategy_a",
        market_model_id="market_a",
        signal_model_id="signal_a",
        exit_model_id="fixed_bars",
        exit_after_bars=10,
        risk_model_id="fixed_quantity",
        position_quantity="1",
        source_dataset_ref="dataset@1",
        evaluation_timeframe="1m",
        requested_range_start=start,
        requested_range_end=end,
        framework_version=framework_version,
        simulation_assumptions_fingerprint="1aa6ee647c5cc636",
    )
    assert first == second


def test_strategy_research_repository_round_trip(tmp_path: Path) -> None:
    repository = StrategyResearchDatasetRepository(tmp_path)
    run_id = "abc123strategyrun"
    envelope = _sample_envelope(run_id=run_id)

    written = repository.write(envelope)
    loaded = repository.read(written)

    assert loaded.manifest.run_id == run_id
    assert loaded.trades.equals(envelope.trades)
    assert loaded.equity.equals(envelope.equity)


def test_strategy_research_repository_refuses_overwrite(tmp_path: Path) -> None:
    repository = StrategyResearchDatasetRepository(tmp_path)
    run_id = "duplicate-run"
    repository.write(_sample_envelope(run_id=run_id))

    with pytest.raises(FileExistsError):
        repository.write(_sample_envelope(run_id=run_id))


def test_strategy_research_repository_read_validates_manifest(tmp_path: Path) -> None:
    run_id = "broken-manifest"
    run_dir = tmp_path / "research" / "strategy_research" / "runs" / run_id
    run_dir.mkdir(parents=True)
    (run_dir / "manifest.json").write_text(
        json.dumps(
            {
                "run_id": run_id,
                "schema_version": "strategy_research.v0",
                "framework_version": framework_version,
                "created_at_utc": datetime(2024, 1, 1, tzinfo=UTC).isoformat(),
                "source_dataset_ref": "dataset@1",
                "evaluation_timeframe": "1m",
                "strategy_model_id": "s",
                "market_model_id": "m",
                "signal_model_id": "sig",
                "exit_model_id": "fixed_bars",
                "risk_model_id": "fixed_quantity",
                "simulation_assumptions_fingerprint": "abc",
            }
        ),
        encoding="utf-8",
    )
    empty_simulated_trades_dataframe().write_parquet(run_dir / "trades.parquet")
    empty_equity_points_dataframe().write_parquet(run_dir / "equity.parquet")

    repository = StrategyResearchDatasetRepository(tmp_path)
    with pytest.raises(ValidationError, match="unsupported schema version"):
        repository.read(StrategyResearchRunRef(run_id=run_id))
