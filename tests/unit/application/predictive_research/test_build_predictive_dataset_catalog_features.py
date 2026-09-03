"""Predictive consumption of the Sprint 051 catalog (S051-T010, PRD metric 1, half two).

Proves the second of two consumption paths the sprint promises: a
``PredictiveStudySpec`` can declare Sprint 051's new catalog components as
``FeatureSpec`` entries and ``build_predictive_dataset`` turns them into a
labelled matrix with fold roles, against the SAME synthetic CI fixture
pattern already used throughout Phase 10 (``tests/unit/application/
predictive_research/test_build_predictive_dataset.py``'s ``_synthetic_bars``
-- D-S039-CI-dataset, ADR-0023 SS8). No real data, no network: every bar here
is generated in-process.

Three of the six new components are declared, spanning three distinct
namespaces and two distinct output ids (not just three ``value`` outputs), so
the test also demonstrates non-default parameters and non-"value" outputs
resolve correctly:

- ``momentum.rsi`` (``value``)
- ``volatility.relative_volatility`` (``ratio``, not ``value``)
- ``statistics.return_autocorrelation`` (``value``)

``momentum.macd``/``momentum.stochastic``/``statistics.return_distribution``
are proven by their own component-level tests (S051-T004/T005/T008) and by
T009's rule-based path; repeating all six here would just re-test the shared
``build_predictive_dataset`` machinery, which the pre-existing ``atr``
fixture already covers -- this file's job is proving the NEW components
integrate through the UNMODIFIED pipeline, not re-proving the pipeline.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import polars as pl

from trading_framework.application.market_analysis.run_analysis import (
    RunAnalysisRequest,
    run_analysis,
)
from trading_framework.application.predictive_research import (
    BuildPredictiveDatasetRequest,
    build_predictive_dataset,
)
from trading_framework.core.types import Price, Volume
from trading_framework.market.datasets import DatasetRef
from trading_framework.market.models import MarketBar
from trading_framework.market_analysis.assembly.frame import (
    AnalysisFrameColumnSpec,
    AnalysisFrameRequest,
)
from trading_framework.market_analysis.identity.component import ComponentId
from trading_framework.market_analysis.models.outputs import OutputId
from trading_framework.market_analysis.models.parameters import CanonicalParameters
from trading_framework.market_analysis.models.request import ComponentRequest
from trading_framework.market_analysis.models.time_range import TimeRange
from trading_framework.research.predictive import (
    FeatureMatrixSpec,
    FeatureSpec,
    FoldRole,
    LabelKind,
    LabelSpec,
    PredictiveStudySpec,
    PurgedWalkForwardSplitMode,
    PurgedWalkForwardSplitSpec,
)
from trading_framework.time.models.timeframe import Timeframe

_BAR_COUNT = 180

# Non-default, deliberately small periods so the three components' warm-ups
# (max 20 bars, relative_volatility's baseline_period) fit comfortably inside
# the 180-bar synthetic fixture alongside the label horizon and fold split,
# while still using each component's real parameter schema.
_RSI_PARAMS = CanonicalParameters.from_mapping({"period": 5})
_RELATIVE_VOLATILITY_PARAMS = CanonicalParameters.from_mapping({"period": 5, "baseline_period": 20})
_RETURN_AUTOCORRELATION_PARAMS = CanonicalParameters.from_mapping({"period": 10, "lag": 1})

_RSI_FEATURE = FeatureSpec(
    component_id=ComponentId("momentum.rsi"),
    parameters=_RSI_PARAMS,
    output_id=OutputId("value"),
    alias="rsi_5",
)
_RELATIVE_VOLATILITY_FEATURE = FeatureSpec(
    component_id=ComponentId("volatility.relative_volatility"),
    parameters=_RELATIVE_VOLATILITY_PARAMS,
    output_id=OutputId("ratio"),
    alias="relvol_ratio_5_20",
)
_RETURN_AUTOCORRELATION_FEATURE = FeatureSpec(
    component_id=ComponentId("statistics.return_autocorrelation"),
    parameters=_RETURN_AUTOCORRELATION_PARAMS,
    output_id=OutputId("value"),
    alias="return_autocorr_10_1",
)
_NEW_CATALOG_FEATURES = (
    _RSI_FEATURE,
    _RELATIVE_VOLATILITY_FEATURE,
    _RETURN_AUTOCORRELATION_FEATURE,
)


def _dataset_ref() -> DatasetRef:
    return DatasetRef.parse("ES.c.0|ohlcv|1m|csv|predictive-catalog-fixture@1")


def _timestamps() -> tuple[datetime, ...]:
    start = datetime(2024, 1, 2, 14, 0, tzinfo=UTC)
    return tuple(start + timedelta(minutes=index) for index in range(_BAR_COUNT))


def _synthetic_bars() -> tuple[MarketBar, ...]:
    """In-process synthetic bars -- no file, no network, no real dataset."""
    bars: list[MarketBar] = []
    for index, observed_at in enumerate(_timestamps()):
        # A mild oscillation on top of a drift, so RSI, relative volatility
        # and autocorrelation each see genuine (non-degenerate) variation
        # rather than a perfectly monotonic or perfectly flat series.
        close = 100.0 + (index * 0.03) + (2.0 if index % 7 < 3 else -1.0)
        bars.append(
            MarketBar(
                open=Price(Decimal(str(round(close, 4)))),
                high=Price(Decimal(str(round(close + 0.4, 4)))),
                low=Price(Decimal(str(round(close - 0.4, 4)))),
                close=Price(Decimal(str(round(close, 4)))),
                volume=Volume(1_000),
                observed_at=observed_at,
                available_at=observed_at + timedelta(minutes=1),
            )
        )
    return tuple(bars)


def _study() -> PredictiveStudySpec:
    timestamps = _timestamps()
    return PredictiveStudySpec(
        study_id="catalog_features_forward_return",
        dataset_ref=_dataset_ref(),
        time_range=TimeRange(start=timestamps[0], end=timestamps[-1]),
        features=FeatureMatrixSpec(features=_NEW_CATALOG_FEATURES),
        label=LabelSpec(kind=LabelKind.REGRESSION, horizon=Timeframe("5m")),
        split=PurgedWalkForwardSplitSpec(
            mode=PurgedWalkForwardSplitMode.EXPANDING,
            fold_count=2,
            test_span=Timeframe("30m"),
            embargo_span=Timeframe("5m"),
            min_train_rows=5,
        ),
    )


def _no_feature_available_after_detected(frame: pl.DataFrame) -> bool:
    """True only if every row satisfies the ADR-0023 SS4 leakage guard."""
    if frame.height == 0:
        return False
    return frame.filter(pl.col("available_at") > pl.col("detected_at")).height == 0


def test_predictive_study_declares_new_catalog_components_and_builds_labelled_matrix(
    tmp_path: Path,
) -> None:
    storage_root = tmp_path / "workspace"
    spec = _study()

    result = build_predictive_dataset(
        BuildPredictiveDatasetRequest(
            spec=spec,
            storage_root=storage_root,
            persist=False,
            preloaded_bars=_synthetic_bars(),
        )
    )

    rows = result.envelope.features
    assert rows.height > 0
    for feature in _NEW_CATALOG_FEATURES:
        assert feature.alias in rows.columns
        assert rows.get_column(feature.alias).drop_nulls().len() > 0
    assert "fold_id" in rows.columns
    assert "fold_role" in rows.columns
    roles = set(rows.get_column("fold_role").to_list())
    assert FoldRole.TRAIN.value in roles
    assert FoldRole.TEST.value in roles
    assert result.envelope.manifest.exclusion_counts["labelled_rows"] > 0


def test_new_catalog_feature_aliases_resolve_to_the_new_components_lineage(
    tmp_path: Path,
) -> None:
    """Aliases must trace back to the ACTUAL new ComponentIds, not just to
    columns with matching names -- calls the same ``run_analysis`` step
    ``build_predictive_dataset`` uses internally, independently, and inspects
    the resulting ``AnalysisFrame.column_lineage`` directly."""
    storage_root = tmp_path / "workspace"
    spec = _study()

    analysis = run_analysis(
        RunAnalysisRequest(
            dataset_ref=spec.dataset_ref,
            timeframe=spec.dataset_ref.dataset_id.timeframe,
            requested_range=spec.time_range,
            storage_root=storage_root,
            component_requests=tuple(
                ComponentRequest(component_id=feature.component_id, parameters=feature.parameters)
                for feature in _NEW_CATALOG_FEATURES
            ),
            frame_request=AnalysisFrameRequest(
                market_fields=("open", "high", "low", "close", "volume"),
                analysis_columns=tuple(
                    AnalysisFrameColumnSpec(
                        component_id=feature.component_id,
                        parameters=feature.parameters,
                        output_id=feature.output_id,
                        alias=feature.alias,
                    )
                    for feature in _NEW_CATALOG_FEATURES
                ),
            ),
            evaluation_timeframe=spec.evaluation_timeframe,
            preloaded_bars=_synthetic_bars(),
        )
    )

    assert analysis.frame is not None
    frame = analysis.frame
    for feature in _NEW_CATALOG_FEATURES:
        assert feature.alias in frame.column_lineage, (
            f"alias {feature.alias!r} did not resolve to a lineage entry at all"
        )
        output_ref = frame.column_lineage[feature.alias]
        identity = output_ref.computation_identity
        assert identity.component_id == feature.component_id
        assert identity.parameters == feature.parameters
        assert output_ref.output_id == feature.output_id

    # Same declarations, through the actual application entry point: proves
    # the lineage resolution above is not incidental to calling run_analysis
    # directly -- build_predictive_dataset's own _declared_feature_lineage
    # step (which raises PredictiveDatasetError on an unresolved alias) must
    # also succeed for these three new components.
    result = build_predictive_dataset(
        BuildPredictiveDatasetRequest(
            spec=spec,
            storage_root=storage_root,
            persist=False,
            preloaded_bars=_synthetic_bars(),
        )
    )
    assert result.fingerprint


def test_leakage_guard_holds_for_the_new_catalog_features_specifically(
    tmp_path: Path,
) -> None:
    """ADR-0023 SS4: ``available_at`` must never be later than ``detected_at``
    for any row -- asserted against the ACTUAL built matrix carrying these
    three new features, not trusted because it holds for ``atr`` elsewhere."""
    storage_root = tmp_path / "workspace"
    spec = _study()

    result = build_predictive_dataset(
        BuildPredictiveDatasetRequest(
            spec=spec,
            storage_root=storage_root,
            persist=False,
            preloaded_bars=_synthetic_bars(),
        )
    )

    rows = result.envelope.features
    assert rows.height > 0
    # Every one of these rows carries values for all three new features
    # (feature-null rows are excluded by build_labelled_feature_matrix), so
    # this assertion is specific to the new components, not a generic check
    # that happens to pass on unrelated rows.
    for feature in _NEW_CATALOG_FEATURES:
        assert rows.get_column(feature.alias).null_count() == 0
    assert _no_feature_available_after_detected(rows)
    assert rows.filter(pl.col("available_at") > pl.col("detected_at")).height == 0


def test_predictive_catalog_consumption_test_uses_no_real_data_or_network() -> None:
    """Structural guard (ADR-0023 SS8): this file's own bars come from
    ``_synthetic_bars`` only -- assert no import of a network/file provider."""
    import ast

    source = Path(__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imported.append(node.module)

    assert not any(
        name == root or name.startswith(f"{root}.")
        for name in imported
        for root in (
            "trading_framework.infrastructure.providers",
            "requests",
            "httpx",
            "aiohttp",
            "urllib",
        )
    )
    assert "user_data" + "/" not in source
