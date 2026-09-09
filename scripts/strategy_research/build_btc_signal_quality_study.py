"""Sprint 058 T005 worked example, stage 1: build the SIGNAL_QUALITY dataset.

Builds a real-data ``signal_occurrences`` + ``SIGNAL_QUALITY``
``PredictiveStudySpec`` over BTCUSDT.P, using Sprint 051's real, catalog-
composed RSI / relative-volatility strategy
(``apps/cli/tests/fixtures/strategies/uses_rsi_relative_volatility.py``,
S051-T009) as the Signal Model whose occurrences define the sample
universe -- the "first real SIGNAL_QUALITY task" §13H.3 asks for.

No `signal_model_file` loader exists yet (TD-031, `docs/planning/
TECHNICAL_DEBT.md`), so this script supplies the already-constructed
``SignalModelDefinition`` in-process via ``BuildPredictiveDatasetRequest.
signal_model`` -- the sanctioned seam every test in this sprint already
uses. This is why T005 needs a script rather than a `trading-cli`
config: no CLI command can hand a Python object across the process
boundary.

Feature list, dataset_ref and time_range are reused byte-for-byte from
Sprint 052's proven, already-computable ten-feature list
(`apps/cli/examples/predictive/btc_momentum_regime_study_binary.yaml`) --
known to compute cleanly over this exact dataset. The label is a binary
"did price move favorably shortly after this RSI-oversold signal fired"
target: BINARY, horizon matching the strategy's own bracket-exit timeout
(20 bars), threshold 0.0 on forward_return.

Usage::

    uv run python scripts/strategy_research/build_btc_signal_quality_study.py \
        --storage-root /absolute/path/to/user_data/workspace
"""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
from pathlib import Path

try:  # package import (pytest, or `-m scripts.strategy_research...`)
    from scripts.strategy_research._btc_rsi_relative_volatility import build_signal_model
except ImportError:  # standalone script execution -- own directory is on sys.path
    from _btc_rsi_relative_volatility import (  # type: ignore[no-redef,import-not-found]
        build_signal_model,
    )

from trading_framework.application.predictive_research import (
    BuildPredictiveDatasetRequest,
    build_predictive_dataset,
)
from trading_framework.market.datasets import DatasetRef
from trading_framework.market_analysis.identity.component import ComponentId
from trading_framework.market_analysis.models.outputs import OutputId
from trading_framework.market_analysis.models.parameters import CanonicalParameters
from trading_framework.market_analysis.models.time_range import TimeRange
from trading_framework.research.predictive import (
    FeatureMatrixSpec,
    FeatureSpec,
    LabelKind,
    LabelSpec,
    PredictiveStudySpec,
    PredictiveTask,
    PurgedWalkForwardSplitMode,
    PurgedWalkForwardSplitSpec,
    SampleDirection,
    SampleKind,
    SampleSpec,
)
from trading_framework.signal_model.definitions import SignalModelDefinition
from trading_framework.time.models.timeframe import Timeframe

_DATASET_REF = DatasetRef.parse("BTCUSDT.P|ohlcv|1m|binance|binance-usdm-klines-v1@1")
_TIME_RANGE = TimeRange(
    start=datetime(2024, 1, 1, tzinfo=UTC), end=datetime(2026, 6, 30, 23, 59, tzinfo=UTC)
)

# Byte-for-byte the Sprint 052 D-S052-05 ten-feature list -- proven to
# compute cleanly over this exact dataset (docs/reference/BTC_PREDICTIVE_STUDY.md).
_FEATURES = FeatureMatrixSpec(
    features=(
        FeatureSpec(
            component_id=ComponentId("momentum.rsi"),
            parameters=CanonicalParameters.from_mapping({"period": 210}),
            output_id=OutputId("value"),
            alias="momentum_rsi_210",
        ),
        FeatureSpec(
            component_id=ComponentId("momentum.macd"),
            parameters=CanonicalParameters.from_mapping(
                {"fast_period": 180, "slow_period": 390, "signal_period": 135}
            ),
            output_id=OutputId("histogram"),
            alias="momentum_macd_histogram",
        ),
        FeatureSpec(
            component_id=ComponentId("momentum.stochastic"),
            parameters=CanonicalParameters.from_mapping({"period": 210, "smoothing_period": 45}),
            output_id=OutputId("k"),
            alias="momentum_stochastic_k",
        ),
        FeatureSpec(
            component_id=ComponentId("volatility.relative_volatility"),
            parameters=CanonicalParameters.from_mapping({"period": 300, "baseline_period": 1500}),
            output_id=OutputId("ratio"),
            alias="volatility_relative_volatility_ratio",
        ),
        FeatureSpec(
            component_id=ComponentId("statistics.return_autocorrelation"),
            parameters=CanonicalParameters.from_mapping({"period": 900, "lag": 15}),
            output_id=OutputId("value"),
            alias="statistics_return_autocorrelation",
        ),
        FeatureSpec(
            component_id=ComponentId("statistics.return_distribution"),
            parameters=CanonicalParameters.from_mapping({"period": 900}),
            output_id=OutputId("skew"),
            alias="statistics_return_distribution_skew",
        ),
        FeatureSpec(
            component_id=ComponentId("volatility.atr"),
            parameters=CanonicalParameters.from_mapping({"period": 210}),
            output_id=OutputId("value"),
            alias="volatility_atr_210",
        ),
        FeatureSpec(
            component_id=ComponentId("trend.slope"),
            parameters=CanonicalParameters.from_mapping({"period": 300}),
            output_id=OutputId("value"),
            alias="trend_slope_300",
        ),
        FeatureSpec(
            component_id=ComponentId("candle.wick"),
            parameters=CanonicalParameters.from_mapping({}),
            output_id=OutputId("upper_wick_ratio"),
            alias="candle_wick_upper_ratio",
        ),
        FeatureSpec(
            component_id=ComponentId("volatility.range_expansion"),
            parameters=CanonicalParameters.from_mapping({"period": 210}),
            output_id=OutputId("ratio"),
            alias="volatility_range_expansion_ratio",
        ),
    )
)


def build_study_spec() -> tuple[PredictiveStudySpec, SignalModelDefinition]:
    """Return the SIGNAL_QUALITY study spec and the in-process Signal Model."""
    signal_model = build_signal_model()

    spec = PredictiveStudySpec(
        study_id="btc_rsi_relative_volatility_signal_quality",
        dataset_ref=_DATASET_REF,
        time_range=_TIME_RANGE,
        features=_FEATURES,
        label=LabelSpec(kind=LabelKind.BINARY, horizon=Timeframe("20m"), threshold=0.0),
        split=PurgedWalkForwardSplitSpec(
            mode=PurgedWalkForwardSplitMode.EXPANDING,
            fold_count=4,
            test_span=Timeframe("60d"),
            embargo_span=Timeframe("1d"),
            min_train_rows=50,
        ),
        sample=SampleSpec(
            kind=SampleKind.SIGNAL_OCCURRENCES,
            signal_model_file="user_data/components/strategies/rsi_relative_volatility_regime.py",
            signal_model_id=signal_model.signal_model_id,
            direction=SampleDirection.ANY,
        ),
        task=PredictiveTask.SIGNAL_QUALITY,
    )
    return spec, signal_model


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--storage-root", required=True, type=Path)
    parser.add_argument("--no-persist", action="store_true")
    args = parser.parse_args(argv)

    spec, signal_model = build_study_spec()
    result = build_predictive_dataset(
        BuildPredictiveDatasetRequest(
            spec=spec,
            storage_root=args.storage_root,
            persist=not args.no_persist,
            signal_model=signal_model,
        )
    )

    provenance = result.envelope.manifest.sample_provenance
    print(f"dataset_id: {result.dataset_id}")
    print(f"fingerprint: {result.fingerprint}")
    print(f"persisted: {result.persisted}")
    print(f"candidate_rows (occurrences): {provenance.universe_row_count if provenance else '?'}")
    print(f"labelled_rows: {provenance.resolved_row_count if provenance else '?'}")
    print(f"drop_counts: {provenance.drop_counts if provenance else '?'}")
    print(f"fold_summary: {result.envelope.manifest.fold_summary}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
