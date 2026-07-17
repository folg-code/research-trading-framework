"""Workspace layout path helper tests."""

from pathlib import Path

from trading_framework.core.identifiers import Identifier
from trading_framework.infrastructure.storage.paths import (
    dataset_bars_path,
    dataset_metadata_path,
    market_data_raw_root,
    market_data_root,
    robustness_experiment_dir,
    roll_schedules_base_dir,
    signal_research_family_experiment_dir,
    signal_research_run_dir,
    strategy_research_run_dir,
)
from trading_framework.market.datasets import DatasetId, DatasetRef
from trading_framework.time.models.timeframe import Timeframe


def _ohlcv_ref() -> DatasetRef:
    return DatasetRef(
        dataset_id=DatasetId(
            instrument_id=Identifier("NQ.c.0"),
            data_type="ohlcv",
            timeframe=Timeframe("1m"),
            provider="databento",
            source_id="nq_continuous_1m",
        ),
        version=1,
    )


def test_workspace_market_and_research_namespaces(tmp_path: Path) -> None:
    workspace = tmp_path / "user_data"
    assert market_data_root(workspace) == workspace / "market_data"
    assert market_data_raw_root(workspace) == workspace / "market_data" / "raw"
    assert signal_research_run_dir(workspace, "abc123") == (
        workspace / "research" / "market_research" / "runs" / "abc123"
    )
    assert signal_research_family_experiment_dir(workspace, "fam-1") == (
        workspace / "research" / "market_research" / "experiments" / "fam-1"
    )
    assert strategy_research_run_dir(workspace, "strat-1") == (
        workspace / "research" / "strategy_research" / "runs" / "strat-1"
    )
    assert robustness_experiment_dir(workspace, "rob-1") == (
        workspace / "research" / "strategy_robustness" / "experiments" / "rob-1"
    )
    assert roll_schedules_base_dir(workspace, product="NQ", policy_slug="volume-rth-close") == (
        workspace / "market_data" / "continuous" / "schedules" / "NQ" / "volume-rth-close"
    )


def test_dataset_paths_live_under_market_data(tmp_path: Path) -> None:
    workspace = tmp_path / "user_data"
    dataset_ref = _ohlcv_ref()
    assert dataset_metadata_path(workspace, dataset_ref) == (
        workspace
        / "market_data"
        / "metadata"
        / "NQ.c.0"
        / "ohlcv"
        / "1m"
        / "databento"
        / "nq_continuous_1m"
        / "v1.json"
    )
    assert dataset_bars_path(workspace, dataset_ref) == (
        workspace
        / "market_data"
        / "normalized"
        / "NQ.c.0"
        / "ohlcv"
        / "1m"
        / "databento"
        / "nq_continuous_1m"
        / "v1"
        / "bars.parquet"
    )
