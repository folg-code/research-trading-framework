"""End-to-end proof: a SIGNAL_QUALITY study over signal_occurrences runs
through the unmodified Phase 10 pipeline -- Sprint 058 T001.

Sprint 056 shipped signal_occurrences sample resolution and the
SIGNAL_QUALITY PredictiveTask as a compatible (sample, task) pair, proven
only at the dataset-construction level
(``tests/unit/application/predictive_research/test_build_predictive_dataset.py``).
This is the first test that carries a signal_occurrences + SIGNAL_QUALITY
``PredictiveStudySpec`` all the way through ``run_predictive_research`` --
the "first real SIGNAL_QUALITY task"
(``docs/planning/roadmap/PHASE_16_QUANT_WORKBENCH.md`` SS13H.3) 16C needs as
its foundation.

No new production code is required: ``PredictiveTask`` has no effect
downstream of sample/task compatibility (``build_predictive_dataset.py``,
``run_predictive_research.py`` never branch on it). Proving that the fit /
fold / metrics path is genuinely task-agnostic below the dataset-manifest
level is itself the finding this test locks in.

The estimator family is ``sklearn.ridge`` -- a promotable family (Phase 16
SS13H.12 Q6, Option B) -- since 16C's later tasks (T003/T004) build the
Strategy Research scorer-reference path on top of a promotable-family
result; nothing here should establish a precedent of using a non-promotable
family for anything that could later gate a strategy.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from trading_framework.application.predictive_research import (
    BuildPredictiveDatasetRequest,
    PredictiveDatasetError,
    RunPredictiveResearchRequest,
    build_predictive_dataset,
    run_predictive_research,
)
from trading_framework.core.types import Price, Volume
from trading_framework.market.datasets import DatasetRef
from trading_framework.market.models import MarketBar
from trading_framework.market_analysis.identity.component import ComponentId
from trading_framework.market_analysis.models.outputs import OutputId
from trading_framework.market_analysis.models.parameters import CanonicalParameters
from trading_framework.market_analysis.models.time_range import TimeRange
from trading_framework.model_expression import (
    CompareExpression,
    ComparisonOperator,
    MarketField,
    MarketFieldReference,
)
from trading_framework.research.datasets.predictive_run import PredictiveRunRepository
from trading_framework.research.predictive import (
    EstimatorSpec,
    FeatureMatrixSpec,
    FeatureSpec,
    LabelKind,
    LabelSpec,
    PredictiveStudySpec,
    PredictiveTask,
    PreprocessingSpec,
    PreprocessingStep,
    PurgedWalkForwardSplitMode,
    PurgedWalkForwardSplitSpec,
    SampleDirection,
    SampleKind,
    SampleSpec,
    TaskType,
)
from trading_framework.signal_model.definitions import (
    SignalDirection,
    SignalFiringPolicy,
    SignalModelDefinition,
)
from trading_framework.time.clocks.fixed import FixedClock
from trading_framework.time.models.timeframe import Timeframe

pytest.importorskip("sklearn")

pytestmark = pytest.mark.ml

_BAR_COUNT = 180
_ATR_PERIOD = 2
_BREAKOUT_THRESHOLD = 108.0


def _dataset_ref() -> DatasetRef:
    return DatasetRef.parse("ES.c.0|ohlcv|1m|csv|signal-quality-e2e-fixture@1")


def _timestamps() -> tuple[datetime, ...]:
    start = datetime(2024, 1, 2, 14, 0, tzinfo=UTC)
    return tuple(start + timedelta(minutes=index) for index in range(_BAR_COUNT))


def _synthetic_bars() -> tuple[MarketBar, ...]:
    """A monotonic close ramp, identical in shape to the Sprint 056 fixture
    (``test_build_predictive_dataset.py::_synthetic_bars``) so the breakout
    signal model below fires on the same known idx range (161..179).
    """
    bars: list[MarketBar] = []
    for index, observed_at in enumerate(_timestamps()):
        close = 100.0 + (index * 0.05)
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


def _breakout_signal_model() -> SignalModelDefinition:
    """Fires ON_EVENT once close crosses ``_BREAKOUT_THRESHOLD``.

    Against ``_synthetic_bars()``'s ramp this fires for idx 161..179 (19
    bars); a 5-bar horizon leaves idx 161..174 (14 rows) COMPLETE -- the
    same fixture shape as the Sprint 056 dataset-construction test, kept
    identical here so this test's row/fold counts trace to a known
    precedent instead of being re-derived.
    """
    return SignalModelDefinition(
        signal_model_id="breakout_v1",
        expression=CompareExpression(
            operand=MarketFieldReference(field=MarketField.CLOSE),
            operator=ComparisonOperator.GT,
            value=_BREAKOUT_THRESHOLD,
        ),
        direction=SignalDirection.LONG,
        firing_policy=SignalFiringPolicy.ON_EVENT,
    )


def _signal_quality_study() -> PredictiveStudySpec:
    timestamps = _timestamps()
    return PredictiveStudySpec(
        study_id="breakout_signal_quality_e2e",
        dataset_ref=_dataset_ref(),
        time_range=TimeRange(start=timestamps[0], end=timestamps[-1]),
        features=FeatureMatrixSpec(
            features=(
                FeatureSpec(
                    component_id=ComponentId("volatility.atr"),
                    parameters=CanonicalParameters.from_mapping({"period": _ATR_PERIOD}),
                    output_id=OutputId("value"),
                    alias="atr",
                ),
            )
        ),
        label=LabelSpec(kind=LabelKind.REGRESSION, horizon=Timeframe("5m")),
        split=PurgedWalkForwardSplitSpec(
            mode=PurgedWalkForwardSplitMode.EXPANDING,
            fold_count=1,
            test_span=Timeframe("3m"),
            embargo_span=Timeframe("1m"),
            min_train_rows=2,
        ),
        sample=SampleSpec(
            kind=SampleKind.SIGNAL_OCCURRENCES,
            signal_model_file="models/breakout.yaml",
            signal_model_id="breakout_v1",
            direction=SampleDirection.ANY,
        ),
        task=PredictiveTask.SIGNAL_QUALITY,
    )


def test_signal_quality_study_runs_through_unmodified_phase10_pipeline(
    tmp_path: Path,
) -> None:
    """Build -> persist -> fit/fold/metrics, with no code path other than
    the one FORWARD_RETURN studies already use.
    """
    storage_root = tmp_path / "workspace"
    spec = _signal_quality_study()
    signal_model = _breakout_signal_model()

    dataset_result = build_predictive_dataset(
        BuildPredictiveDatasetRequest(
            spec=spec,
            storage_root=storage_root,
            persist=True,
            preloaded_bars=_synthetic_bars(),
            signal_model=signal_model,
            clock=FixedClock(datetime(2024, 6, 1, 12, 0, tzinfo=UTC)),
        )
    )

    assert dataset_result.persisted is True
    provenance = dataset_result.envelope.manifest.sample_provenance
    assert provenance is not None
    assert provenance.kind is SampleKind.SIGNAL_OCCURRENCES
    assert provenance.task is PredictiveTask.SIGNAL_QUALITY
    assert provenance.resolved_row_count > 0
    # task is only serialized when it differs from the FORWARD_RETURN
    # default (ADR-0031 Decision 2) -- confirm it actually round-trips.
    assert dataset_result.envelope.manifest.study_spec["task"] == "SIGNAL_QUALITY"

    run_result = run_predictive_research(
        RunPredictiveResearchRequest(
            dataset_ref=dataset_result.dataset_ref,
            estimator=EstimatorSpec(
                family="sklearn.ridge",
                hyperparameters={"alpha": 1.0},
                seed=7,
                task_type=TaskType.REGRESSION,
            ),
            storage_root=storage_root,
            preprocessing=PreprocessingSpec(
                steps=(PreprocessingStep.IMPUTE_MEDIAN, PreprocessingStep.STANDARDIZE)
            ),
            persist=True,
            clock=FixedClock(datetime(2024, 6, 1, 13, 0, tzinfo=UTC)),
        )
    )

    assert run_result.persisted is True
    assert run_result.envelope.predictions.height > 0
    assert run_result.metrics.fold_primary

    loaded_run = PredictiveRunRepository(storage_root).read(run_result.run_ref)
    assert loaded_run.manifest.run_id == run_result.run_id
    assert loaded_run.manifest.dataset_id == dataset_result.dataset_id
    assert loaded_run.manifest.estimator_spec["family"] == "sklearn.ridge"


def test_signal_quality_study_still_rejects_missing_signal_model(
    tmp_path: Path,
) -> None:
    """Regression guard: the TD-031-sanctioned in-process seam is required,
    unchanged by this sprint -- a signal_occurrences build still refuses
    rather than silently falling back to every_bar.
    """
    storage_root = tmp_path / "workspace"
    spec = _signal_quality_study()

    with pytest.raises(PredictiveDatasetError, match=r"requires request\.signal_model"):
        build_predictive_dataset(
            BuildPredictiveDatasetRequest(
                spec=spec,
                storage_root=storage_root,
                persist=False,
                preloaded_bars=_synthetic_bars(),
            )
        )
