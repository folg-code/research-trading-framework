"""Workspace layout path helper tests."""

from datetime import UTC, date, datetime
from pathlib import Path

from trading_framework.core.identifiers import Identifier
from trading_framework.infrastructure.storage.paths import (
    dataset_bars_path,
    dataset_metadata_path,
    market_data_raw_root,
    market_data_root,
    ohlcv_session_dates_overlapping_range,
    predictive_research_dataset_dir,
    predictive_research_run_dir,
    predictive_research_run_learning_curves_path,
    predictive_research_run_metrics_path,
    predictive_research_run_model_path,
    predictive_research_run_report_path,
    predictive_research_run_window_accounting_path,
    robustness_experiment_dir,
    roll_schedules_base_dir,
    signal_research_family_experiment_dir,
    signal_research_run_dir,
    strategy_research_run_dir,
)
from trading_framework.market.datasets import DatasetId, DatasetRef
from trading_framework.market.models.instrument import AssetClass
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
    assert predictive_research_dataset_dir(workspace, "abc123def4567890") == (
        workspace / "research" / "predictive_research" / "datasets" / "abc123def4567890"
    )
    assert predictive_research_run_dir(workspace, "fedcba9876543210") == (
        workspace / "research" / "predictive_research" / "runs" / "fedcba9876543210"
    )
    assert predictive_research_run_model_path(workspace, "fedcba9876543210", 3) == (
        workspace
        / "research"
        / "predictive_research"
        / "runs"
        / "fedcba9876543210"
        / "models"
        / "fold_3.bin"
    )
    assert predictive_research_run_metrics_path(workspace, "fedcba9876543210") == (
        workspace
        / "research"
        / "predictive_research"
        / "runs"
        / "fedcba9876543210"
        / "metrics.json"
    )
    assert predictive_research_run_report_path(workspace, "fedcba9876543210") == (
        workspace / "research" / "predictive_research" / "runs" / "fedcba9876543210" / "report.html"
    )
    assert predictive_research_run_learning_curves_path(workspace, "fedcba9876543210") == (
        workspace
        / "research"
        / "predictive_research"
        / "runs"
        / "fedcba9876543210"
        / "learning_curves.json"
    )
    assert predictive_research_run_window_accounting_path(workspace, "fedcba9876543210") == (
        workspace
        / "research"
        / "predictive_research"
        / "runs"
        / "fedcba9876543210"
        / "window_accounting.json"
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


# ---------------------------------------------------------------------------
# Market-data directory layout simplification (ADR-0008 update): a NEW
# identity (asset_class set) resolves through the simplified
# {asset_class}/{provider}/{instrument}/{timeframe}/ layout with no
# ohlcv/source-id/version directories between instrument and file; a LEGACY
# identity (asset_class unset, produced by DatasetRef.parse() on an old
# 5-field canonical string) keeps resolving through the old layout unchanged.
# ---------------------------------------------------------------------------


def _new_layout_ref(*, source_id: str = "binance-usdm-klines-v1") -> DatasetRef:
    return DatasetRef(
        dataset_id=DatasetId(
            instrument_id=Identifier("BTCUSDT.P"),
            data_type="ohlcv",
            timeframe=Timeframe("1m"),
            provider="binance",
            source_id=source_id,
            asset_class=AssetClass.CRYPTO,
        ),
        version=1,
    )


def test_new_layout_dataset_paths_use_asset_class_provider_instrument_timeframe(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "user_data"
    dataset_ref = _new_layout_ref()

    assert dataset_metadata_path(workspace, dataset_ref) == (
        workspace
        / "market_data"
        / "metadata"
        / "crypto"
        / "binance"
        / "BTCUSDT.P"
        / "1m"
        / "ohlcv.binance-usdm-klines-v1.v1.json"
    )
    assert dataset_bars_path(workspace, dataset_ref) == (
        workspace
        / "market_data"
        / "normalized"
        / "crypto"
        / "binance"
        / "BTCUSDT.P"
        / "1m"
        / "ohlcv.binance-usdm-klines-v1.v1.parquet"
    )


def test_legacy_five_field_dataset_ref_still_resolves_the_old_layout(tmp_path: Path) -> None:
    """Acceptance criterion: reads through an existing DatasetRef keep working."""
    workspace = tmp_path / "user_data"
    legacy_ref = DatasetRef.parse("ES.c.0|ohlcv|1m|csv|sample-file@1")

    assert legacy_ref.dataset_id.asset_class is None
    assert dataset_metadata_path(workspace, legacy_ref) == (
        workspace
        / "market_data"
        / "metadata"
        / "ES.c.0"
        / "ohlcv"
        / "1m"
        / "csv"
        / "sample-file"
        / "v1.json"
    )


def test_dataset_ref_round_trips_through_str_and_parse_for_both_layouts() -> None:
    legacy = DatasetRef.parse("ES.c.0|ohlcv|1m|csv|sample-file@1")
    assert DatasetRef.parse(str(legacy)) == legacy

    new_layout = _new_layout_ref()
    assert str(new_layout) == "BTCUSDT.P|ohlcv|1m|binance|binance-usdm-klines-v1|crypto@1"
    assert DatasetRef.parse(str(new_layout)) == new_layout


def test_two_source_series_same_instrument_timeframe_do_not_collide(tmp_path: Path) -> None:
    """Acceptance criterion: two source series for one instrument/timeframe
    coexist in one directory without a path collision."""
    workspace = tmp_path / "user_data"
    series_a = _new_layout_ref(source_id="binance-usdm-klines-v1")
    series_b = _new_layout_ref(source_id="binance-usdm-klines-v2-backfill")

    path_a = dataset_bars_path(workspace, series_a)
    path_b = dataset_bars_path(workspace, series_b)

    assert path_a != path_b
    assert path_a.parent == path_b.parent  # same instrument/timeframe directory
    assert path_a.name == "ohlcv.binance-usdm-klines-v1.v1.parquet"
    assert path_b.name == "ohlcv.binance-usdm-klines-v2-backfill.v1.parquet"


def test_ohlcv_session_dates_overlapping_range_keeps_adjacent_utc_days() -> None:
    session_dates = [date(2024, 1, day) for day in range(1, 11)]
    selected = ohlcv_session_dates_overlapping_range(
        session_dates,
        datetime(2024, 1, 5, 10, 0, tzinfo=UTC),
        datetime(2024, 1, 5, 16, 0, tzinfo=UTC),
    )
    assert selected == [date(2024, 1, 4), date(2024, 1, 5), date(2024, 1, 6)]
