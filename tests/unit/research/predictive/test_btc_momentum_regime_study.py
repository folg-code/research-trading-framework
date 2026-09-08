"""Network-free, extra-free parse test for the committed real-data BTC study.

Sprint 052 (Phase 15B, S052-T002): the study is a declared configuration, not
a runnable fixture -- this test only proves the committed files load through
their own loaders (`load_predictive_study_spec`, `EstimatorSpec.from_dict`)
with no code change, and that D-S052-05's frozen ten-feature list and
D-S052-03's frozen fold plan match `S052_WAVE0_DECISIONS.md` exactly. It does
not build a dataset or fit an estimator (S052-T003, maintainer-executed with
the `ml` extra); nothing here reads real data, `user_data/`, or the network
(SPRINT_052.md Sec5).
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml  # type: ignore[import-untyped]

from trading_framework.research.predictive.estimators import EstimatorSpec, TaskType
from trading_framework.research.predictive.labels import LabelKind
from trading_framework.research.predictive.spec import load_predictive_study_spec

_EXAMPLES_DIR = Path(__file__).resolve().parents[4] / "apps" / "cli" / "examples" / "predictive"

_REGRESSION_STUDY = _EXAMPLES_DIR / "btc_momentum_regime_study_regression.yaml"
_BINARY_STUDY = _EXAMPLES_DIR / "btc_momentum_regime_study_binary.yaml"
_RIDGE_ESTIMATOR = _EXAMPLES_DIR / "btc_momentum_regime_ridge.yaml"
_LOGISTIC_ESTIMATOR = _EXAMPLES_DIR / "btc_momentum_regime_logistic.yaml"

# D-S052-05's frozen ten-component feature list (S052_WAVE0_DECISIONS.md),
# in the order it is declared in both committed study specs. This list is
# reviewable as a diff against the committed spec (SPRINT_052.md acceptance
# criterion 8) -- it must never be edited to match a study result.
_FROZEN_COMPONENT_IDS = (
    "momentum.rsi",
    "momentum.macd",
    "momentum.stochastic",
    "volatility.relative_volatility",
    "statistics.return_autocorrelation",
    "statistics.return_distribution",
    "volatility.atr",
    "trend.slope",
    "candle.wick",
    "volatility.range_expansion",
)


def _load_estimator_spec(path: Path) -> EstimatorSpec:
    """Mirror `trading_cli.commands.research._load_estimator_spec`'s file I/O.

    `EstimatorSpec.from_dict` is the spec's own validating constructor
    (D-S046-07); this helper only reads the file, exactly like the CLI's.
    """
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return EstimatorSpec.from_dict(payload)


@pytest.mark.parametrize(
    ("path", "label_kind", "study_id"),
    [
        (_REGRESSION_STUDY, LabelKind.REGRESSION, "btc_momentum_regime_study_regression"),
        (_BINARY_STUDY, LabelKind.BINARY, "btc_momentum_regime_study_binary"),
    ],
)
def test_btc_study_spec_parses(path: Path, label_kind: LabelKind, study_id: str) -> None:
    loaded = load_predictive_study_spec(path)

    assert loaded.study_id == study_id
    assert loaded.dataset_ref.dataset_id.canonical() == (
        "BTCUSDT.P|ohlcv|1m|binance|binance-usdm-klines-v1"
    )
    assert loaded.dataset_ref.version == 1
    assert loaded.evaluation_timeframe.value == "1m"
    assert loaded.label.kind is label_kind
    assert loaded.label.horizon.value == "1h"


@pytest.mark.parametrize("path", [_REGRESSION_STUDY, _BINARY_STUDY])
def test_btc_study_spec_declares_the_frozen_feature_list_exactly(path: Path) -> None:
    loaded = load_predictive_study_spec(path)

    component_ids = tuple(feature.component_id.value for feature in loaded.features.features)
    assert component_ids == _FROZEN_COMPONENT_IDS


@pytest.mark.parametrize("path", [_REGRESSION_STUDY, _BINARY_STUDY])
def test_btc_study_spec_declares_the_locked_fold_plan(path: Path) -> None:
    """D-S052-03's frozen fold plan: EXPANDING, F=6, T=30d, E=1d, M=2000."""
    loaded = load_predictive_study_spec(path)
    split = loaded.split

    assert split.mode.value == "EXPANDING"
    assert split.fold_count == 6
    assert split.test_span.value == "30d"
    assert split.embargo_span.value == "1d"
    assert split.min_train_rows == 2000


@pytest.mark.parametrize("path", [_REGRESSION_STUDY, _BINARY_STUDY])
def test_btc_study_spec_header_hash_matches_the_loaded_spec(path: Path) -> None:
    """The header comment's `definition_hash` must be the value the loader
    itself computes -- reviewable by inspection, not by trust."""
    text = path.read_text(encoding="utf-8")
    header_line = next(line for line in text.splitlines() if "definition_hash:" in line)
    header_hash = header_line.split("definition_hash:", 1)[1].strip()

    loaded = load_predictive_study_spec(path)

    assert loaded.definition_hash == header_hash


@pytest.mark.parametrize(
    ("path", "family", "task_type"),
    [
        (_RIDGE_ESTIMATOR, "sklearn.ridge", TaskType.REGRESSION),
        (_LOGISTIC_ESTIMATOR, "sklearn.logistic", TaskType.CLASSIFICATION),
    ],
)
def test_btc_estimator_spec_parses(path: Path, family: str, task_type: TaskType) -> None:
    loaded = _load_estimator_spec(path)

    assert loaded.family == family
    assert loaded.task_type is task_type
    assert loaded.seed == 42


def test_btc_estimator_specs_share_the_same_seed() -> None:
    """D-S052-06: Pass 1's regression and classification runs share one seed."""
    ridge = _load_estimator_spec(_RIDGE_ESTIMATOR)
    logistic = _load_estimator_spec(_LOGISTIC_ESTIMATOR)

    assert ridge.seed == logistic.seed
