"""Unit tests for run_strategy_research orchestration."""

from __future__ import annotations

import json
from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any
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
    ScoreConditionSpec,
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


def _write_promoted_ridge_artifact(
    storage_root: Path,
    *,
    fingerprint: str,
    coefficients: tuple[float, ...] = (1.0,),
    intercept: float = 0.0,
) -> None:
    """A real, evaluable sklearn.ridge artifact scoring the canonical
    strategy's own market model's ATR component (period=2) -- the same
    component ``build_canonical_market_model_high_volatility`` already
    requires, so no new Market Analysis dependency enters the fixture.
    """
    from trading_framework.market_analysis.identity.component import ComponentId
    from trading_framework.market_analysis.models.outputs import OutputId
    from trading_framework.market_analysis.models.parameters import CanonicalParameters
    from trading_framework.research.datasets.promoted_artifact import (
        PROMOTED_ARTIFACT_SCHEMA_VERSION,
        PromotedArtifactManifest,
        PromotedArtifactRepository,
    )
    from trading_framework.research.predictive.features import FeatureSpec

    feature = FeatureSpec(
        component_id=ComponentId("volatility.atr"),
        parameters=CanonicalParameters.from_mapping({"period": 2}),
        output_id=OutputId("value"),
        alias="atr",
    )
    manifest = PromotedArtifactManifest(
        schema_version=PROMOTED_ARTIFACT_SCHEMA_VERSION,
        artifact_fingerprint=fingerprint,
        run_fingerprint="c" * 64,
        dataset_fingerprint="d" * 64,
        fold_id=3,
        feature_output_refs=(json.dumps(feature.to_dict(), sort_keys=True, separators=(",", ":")),),
        model_family="sklearn.ridge",
        format="numpy_parameter_file",
        format_version="v1",
        preprocessing_spec={"steps": ["IMPUTE_MEDIAN", "STANDARDIZE"]},
        estimator_spec={"family": "sklearn.ridge", "hyperparameters": {}, "seed": 7},
        training_library="scikit-learn",
        training_library_version="1.5.0",
        created_at_utc=datetime(2024, 7, 2, 9, 0, tzinfo=UTC),
    )
    PromotedArtifactRepository(storage_root).write(
        manifest,
        artifact_payload={
            "coefficients": list(coefficients),
            "intercept": intercept,
            "impute_median": [0.0],
            "standardize_mean": [0.0],
            "standardize_scale": [1.0],
        },
    )


def test_run_strategy_research_wires_the_score_gate_into_entry_filtering(
    tmp_path: Path,
    ohlcv_sample_1m_path: Path,
) -> None:
    """Proves genuine wiring, not a decorative no-op.

    ``apply_score_gate`` (the real function, not a stand-in) is called
    exactly once, with the declared threshold, filtering the SAME
    ``entry_signals`` ``build_gated_entry_signals`` already produced --
    never widening it (``output_height <= input_height``, matching
    ``apply_score_gate``'s own inner-join-and-filter contract, proven
    directly by ``test_score_gate.py``'s unit tests). This is more robust
    than a trade-count comparison: the canonical strategy fires zero
    entries on this small sample fixture regardless of scoring (confirmed
    directly), so a height-based before/after comparison would prove
    nothing about THIS wiring -- a call-count and argument assertion does.
    """
    storage_root = tmp_path / "storage"
    dataset_ref = _write_published_dataset(storage_root, csv_path=ohlcv_sample_1m_path)
    metadata = FileDatasetRegistry(storage_root).get(dataset_ref)
    _write_promoted_ridge_artifact(storage_root, fingerprint="f" * 64)
    strategy_model = replace(
        build_canonical_strategy_model(),
        score_condition=ScoreConditionSpec(artifact_fingerprint="f" * 64, threshold=0.0),
    )
    from trading_framework.application.strategy_research.score_gate import (
        apply_score_gate as real_apply_score_gate,
    )

    captured: dict[str, Any] = {"call_count": 0}

    def spy_apply_score_gate(entry_signals, score_table, *, threshold):
        result = real_apply_score_gate(entry_signals, score_table, threshold=threshold)
        captured["call_count"] = int(captured["call_count"]) + 1
        captured["threshold"] = threshold
        captured["input_height"] = entry_signals.height
        captured["output_height"] = result.height
        return result

    with patch(
        "trading_framework.application.strategy_research.run_strategy_research.apply_score_gate",
        side_effect=spy_apply_score_gate,
    ):
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

    assert captured["call_count"] == 1
    assert captured["threshold"] == 0.0
    assert captured["output_height"] <= captured["input_height"]


def test_run_strategy_research_does_not_call_the_score_gate_when_undeclared(
    tmp_path: Path,
    ohlcv_sample_1m_path: Path,
) -> None:
    """No ``score_condition`` -> no call at all, not a call with a
    permissive threshold -- the additive gate must be entirely absent from
    the path for every existing strategy that never declares one.
    """
    storage_root = tmp_path / "storage"
    dataset_ref = _write_published_dataset(storage_root, csv_path=ohlcv_sample_1m_path)
    metadata = FileDatasetRegistry(storage_root).get(dataset_ref)
    strategy_model = build_canonical_strategy_model()

    with patch(
        "trading_framework.application.strategy_research.run_strategy_research.apply_score_gate"
    ) as mock_apply_score_gate:
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

    mock_apply_score_gate.assert_not_called()


def test_run_strategy_research_refuses_score_condition_with_shared_evaluation(
    tmp_path: Path,
    ohlcv_sample_1m_path: Path,
) -> None:
    storage_root = tmp_path / "storage"
    dataset_ref = _write_published_dataset(storage_root, csv_path=ohlcv_sample_1m_path)
    metadata = FileDatasetRegistry(storage_root).get(dataset_ref)
    _write_promoted_ridge_artifact(storage_root, fingerprint="f" * 64)
    strategy_model = replace(
        build_canonical_strategy_model(),
        score_condition=ScoreConditionSpec(artifact_fingerprint="f" * 64, threshold=0.0),
    )
    fake_shared_evaluation = object()

    with pytest.raises(StrategyResearchError, match="shared_evaluation"):
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
                shared_evaluation=fake_shared_evaluation,  # type: ignore[arg-type]
            )
        )


def test_resolve_evaluation_inputs_widens_warmup_for_score_condition_features(
    tmp_path: Path,
    ohlcv_sample_1m_path: Path,
) -> None:
    """Regression test for a review finding on this increment: a scorer
    feature needing MORE lookback than the strategy's own market/signal
    components used to get silently starved -- the preloaded OHLCV batch
    was sized only for market/signal warm-up, and
    ``load_analysis_data_view`` uses a supplied preloaded batch verbatim,
    ignoring any ``computation_range`` computed after the fact.

    Asserted at the ``resolve_analysis_computation_range`` level (the
    warm-up PLANNING step), not the final preloaded batch: the sample
    fixture's history starts exactly at the requested range, so a
    storage-clamped fetch cannot show a widened plan reaching further back
    than data actually exists -- the planning step is what
    ``extra_component_requests`` must reach, and is where this bug lived.
    """
    from trading_framework.application.market_analysis.run_analysis import (
        RunAnalysisRequest,
        resolve_analysis_computation_range,
    )
    from trading_framework.market_analysis.identity.component import ComponentId
    from trading_framework.market_analysis.models.parameters import CanonicalParameters
    from trading_framework.market_analysis.models.request import ComponentRequest
    from trading_framework.model_expression.planning import (
        build_analysis_frame_request,
        collect_model_dependencies,
    )

    storage_root = tmp_path / "storage"
    dataset_ref = _write_published_dataset(storage_root, csv_path=ohlcv_sample_1m_path)
    metadata = FileDatasetRegistry(storage_root).get(dataset_ref)
    strategy_model = build_canonical_strategy_model()
    requested_range = TimeRange(start=metadata.start_at, end=metadata.end_at)
    dependencies = collect_model_dependencies(
        market_models=(strategy_model.market_model,),
        signal_models=(strategy_model.signal_model,),
    )
    frame_request = build_analysis_frame_request(dependencies)
    wide_lookback_request = ComponentRequest(
        component_id=ComponentId("volatility.atr"),
        parameters=CanonicalParameters.from_mapping({"period": 200}),
    )

    baseline_range = resolve_analysis_computation_range(
        RunAnalysisRequest(
            dataset_ref=dataset_ref,
            timeframe=Timeframe("1m"),
            requested_range=requested_range,
            storage_root=storage_root,
            component_requests=dependencies.component_requests,
            frame_request=frame_request,
            evaluation_timeframe=Timeframe("1m"),
        )
    )
    widened_range = resolve_analysis_computation_range(
        RunAnalysisRequest(
            dataset_ref=dataset_ref,
            timeframe=Timeframe("1m"),
            requested_range=requested_range,
            storage_root=storage_root,
            component_requests=(*dependencies.component_requests, wide_lookback_request),
            frame_request=frame_request,
            evaluation_timeframe=Timeframe("1m"),
        )
    )

    assert widened_range.start < baseline_range.start

    request = RunStrategyResearchRequest(
        dataset_ref=dataset_ref,
        timeframe=Timeframe("1m"),
        requested_range=requested_range,
        storage_root=storage_root,
        strategy_model=strategy_model,
        assumptions=SimulationAssumptions(),
        evaluation_timeframe=Timeframe("1m"),
        session_resolver=CmeEsRthSessionResolver(),
        persist=False,
    )
    # And confirm run_strategy_research's own wiring reaches this planning
    # step at all -- extra_component_requests is not merely accepted but
    # actually used, by patching the planner to capture what it was called
    # with when a score_condition is declared.
    captured_component_requests: list[tuple[object, ...]] = []
    _write_promoted_ridge_artifact(storage_root, fingerprint="a" * 64)
    scored_strategy_model = replace(
        strategy_model,
        score_condition=ScoreConditionSpec(artifact_fingerprint="a" * 64, threshold=-1e9),
    )
    scored_request = replace(request, strategy_model=scored_strategy_model)

    real_resolve_range = resolve_analysis_computation_range

    def spy_resolve_range(analysis_request, **kwargs):
        captured_component_requests.append(analysis_request.component_requests)
        return real_resolve_range(analysis_request, **kwargs)

    with patch(
        "trading_framework.application.strategy_research.run_strategy_research"
        ".resolve_analysis_computation_range",
        side_effect=spy_resolve_range,
    ):
        run_strategy_research(scored_request)

    assert len(captured_component_requests) == 1
    assert len(captured_component_requests[0]) > len(dependencies.component_requests)
