"""Unit tests for run_strategy_research orchestration."""

from __future__ import annotations

from datetime import UTC
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

import pytest

from trading_framework.application.model_evaluation.canonical_examples import (
    build_canonical_market_model_high_volatility,
    build_canonical_signal_higher_low_on_event,
)
from trading_framework.application.strategy_research import (
    RunStrategyResearchRequest,
    run_strategy_research,
)
from trading_framework.application.strategy_research.run_strategy_research import (
    StrategyResearchError,
    _dispatch_exit_model,
    _exit_model_parameters,
)
from trading_framework.core.identifiers import Identifier
from trading_framework.infrastructure.storage.metadata.registry import FileDatasetRegistry
from trading_framework.market.datasets import DatasetId, DatasetLifecycleState, DatasetRef
from trading_framework.market_analysis import TimeRange
from trading_framework.research.simulation import SimulationAssumptions
from trading_framework.strategy import (
    FixedQuantityRiskModel,
    StrategyModelDefinition,
    build_canonical_strategy_model,
)
from trading_framework.strategy.exit_model import BracketExitModel, FixedBarsExitModel
from trading_framework.time.models.timeframe import Timeframe
from trading_framework.time.sessions import CmeEsRthSessionResolver


def _write_published_dataset(storage_root: Path, *, csv_path: Path) -> DatasetRef:
    from trading_framework.application.market_data import (
        ImportExternalDatasetRequest,
        finalize_dataset,
        import_external_dataset,
        publish_dataset,
    )
    from trading_framework.market.normalization import OhlcvColumnMapping, OhlcvImportConfig
    from trading_framework.market.temporal import BarTimestampSemantics

    dataset_id = DatasetId(
        instrument_id=Identifier("ES.c.0"),
        data_type="ohlcv",
        timeframe=Timeframe("1m"),
        provider="csv",
        source_id="unit-run-strategy-research",
    )
    result = import_external_dataset(
        ImportExternalDatasetRequest(
            path=csv_path,
            dataset_id=dataset_id,
            import_config=OhlcvImportConfig(
                column_mapping=OhlcvColumnMapping(
                    timestamp="timestamp",
                    open="open",
                    high="high",
                    low="low",
                    close="close",
                    volume="volume",
                ),
                timeframe=Timeframe("1m"),
                timestamp_semantics=BarTimestampSemantics.INTERVAL_START,
                source_timezone=UTC,
            ),
            schema_version="ohlcv.v1",
            normalization_version="utc-interval-start.v1",
        ),
        storage_root=storage_root,
    )
    finalize_dataset(result.dataset_ref, storage_root=storage_root)
    publish_dataset(result.dataset_ref, storage_root=storage_root)
    metadata = FileDatasetRegistry(storage_root).get(result.dataset_ref)
    assert metadata.lifecycle_status is DatasetLifecycleState.PUBLISHED
    return result.dataset_ref


def test_run_strategy_research_queries_historical_bars_once(
    tmp_path: Path,
    ohlcv_sample_1m_path: Path,
) -> None:
    from trading_framework.application.market_data.query_historical import (
        query_historical_columnar as real_query_historical_columnar,
    )

    storage_root = tmp_path / "storage"
    dataset_ref = _write_published_dataset(storage_root, csv_path=ohlcv_sample_1m_path)
    metadata = FileDatasetRegistry(storage_root).get(dataset_ref)
    strategy_model = build_canonical_strategy_model()
    query_count = 0

    def counting_query_historical_columnar(*args, **kwargs):
        nonlocal query_count
        query_count += 1
        return real_query_historical_columnar(*args, **kwargs)

    with (
        patch(
            "trading_framework.application.strategy_research.run_strategy_research.query_historical_columnar",
            side_effect=counting_query_historical_columnar,
        ),
        patch(
            "trading_framework.application.market_analysis.load_data_view.query_historical_columnar",
            side_effect=counting_query_historical_columnar,
        ),
    ):
        result = run_strategy_research(
            RunStrategyResearchRequest(
                dataset_ref=dataset_ref,
                timeframe=Timeframe("1m"),
                requested_range=TimeRange(start=metadata.start_at, end=metadata.end_at),
                storage_root=storage_root,
                strategy_model=strategy_model,
                assumptions=SimulationAssumptions(),
                evaluation_timeframe=Timeframe("1m"),
                session_resolver=CmeEsRthSessionResolver(),
                persist=False,
            )
        )

    assert query_count == 1
    assert len(result.equity) > 0


def test_run_strategy_research_records_subphase_timings_when_timer_active(
    tmp_path: Path,
    ohlcv_sample_1m_path: Path,
) -> None:
    from io import StringIO

    from trading_framework.infrastructure.observability.phase_timer import PhaseTimer
    from trading_framework.infrastructure.observability.profile_context import phase_timer_context

    storage_root = tmp_path / "storage"
    dataset_ref = _write_published_dataset(storage_root, csv_path=ohlcv_sample_1m_path)
    metadata = FileDatasetRegistry(storage_root).get(dataset_ref)
    strategy_model = build_canonical_strategy_model()
    timer = PhaseTimer(enabled=True, log_stream=StringIO())

    with phase_timer_context(timer):
        timer.begin_session()
        run_strategy_research(
            RunStrategyResearchRequest(
                dataset_ref=dataset_ref,
                timeframe=Timeframe("1m"),
                requested_range=TimeRange(start=metadata.start_at, end=metadata.end_at),
                storage_root=storage_root,
                strategy_model=strategy_model,
                assumptions=SimulationAssumptions(),
                evaluation_timeframe=Timeframe("1m"),
                session_resolver=CmeEsRthSessionResolver(),
                persist=False,
            )
        )

    assert "strategy_research.evaluate_models" in timer._stats
    assert "strategy_research.load_ohlcv" in timer._stats
    assert "strategy_research.simulate" in timer._stats
    assert "evaluate_models.run_analysis" in timer._stats
    assert "run_analysis.assemble_frame" in timer._stats
    assert "ohlcv.query_columnar" in timer._stats
    assert "evaluate_models.build_evaluation_table" in timer._stats
    assert timer._stats["strategy_research.evaluate_models"].call_count == 1


def _bracket_strategy_model() -> StrategyModelDefinition:
    return StrategyModelDefinition(
        strategy_model_id="test_bracket_strategy",
        market_model=build_canonical_market_model_high_volatility(market_model_id="m1"),
        signal_model=build_canonical_signal_higher_low_on_event(signal_model_id="s1"),
        exit_model=BracketExitModel(
            stop_loss_bps=50,
            take_profit_bps=120,
            max_bars=40,
        ),
        risk_model=FixedQuantityRiskModel(quantity=Decimal("1")),
    )


def test_dispatch_exit_model_accepts_bracket_exit_model() -> None:
    """S048-T008: the application-layer dispatch no longer refuses a bracket exit."""
    strategy_model = _bracket_strategy_model()

    dispatched = _dispatch_exit_model(strategy_model)

    assert dispatched is strategy_model.exit_model


def test_dispatch_exit_model_still_rejects_unknown_exit_model() -> None:
    strategy_model = build_canonical_strategy_model()
    object.__setattr__(strategy_model, "exit_model", object())

    with pytest.raises(StrategyResearchError) as exc_info:
        _dispatch_exit_model(strategy_model)
    assert str(exc_info.value) == (
        "run_strategy_research supports FixedBarsExitModel or a "
        "PriceBracketExit-conformant exit model only"
    )


def test_exit_model_parameters_encodes_bracket_fields_by_name() -> None:
    bracket = BracketExitModel(stop_loss_bps=50, take_profit_bps=120, max_bars=40)

    payload = _exit_model_parameters(bracket)

    assert payload == "stop_loss_bps=50,take_profit_bps=120,max_bars=40"


def test_exit_model_parameters_cannot_collide_fixed_bars_vs_bracket() -> None:
    fixed_bars_payload = _exit_model_parameters(FixedBarsExitModel(exit_after_bars=40))
    bracket_payload = _exit_model_parameters(
        BracketExitModel(stop_loss_bps=50, take_profit_bps=120, max_bars=40)
    )

    assert fixed_bars_payload != bracket_payload
