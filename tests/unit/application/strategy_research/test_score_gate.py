"""Unit tests for the predictive score gate (Sprint 058 T004, ADR-0033)."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import polars as pl
import pytest

from trading_framework.application.strategy_research import (
    ResolvedScoreCondition,
    ScoreGateError,
    apply_score_gate,
    decode_feature_matrix_spec,
    read_promoted_artifact_parameters,
)
from trading_framework.infrastructure.storage.paths import promoted_artifact_payload_path
from trading_framework.market_analysis.identity.component import ComponentId
from trading_framework.market_analysis.models.outputs import OutputId
from trading_framework.market_analysis.models.parameters import CanonicalParameters
from trading_framework.research.datasets.promoted_artifact import (
    PROMOTED_ARTIFACT_SCHEMA_VERSION,
    PromotedArtifactManifest,
)
from trading_framework.research.predictive.features import FeatureSpec
from trading_framework.strategy import ScoreConditionSpec

_UTC_US = pl.Datetime(time_unit="us", time_zone="UTC")


def _atr_feature() -> FeatureSpec:
    return FeatureSpec(
        component_id=ComponentId("volatility.atr"),
        parameters=CanonicalParameters.from_mapping({"period": 2}),
        output_id=OutputId("value"),
        alias="atr",
    )


def _manifest(*, fingerprint: str) -> PromotedArtifactManifest:
    return PromotedArtifactManifest(
        schema_version=PROMOTED_ARTIFACT_SCHEMA_VERSION,
        artifact_fingerprint=fingerprint,
        run_fingerprint="c" * 64,
        dataset_fingerprint="d" * 64,
        fold_id=3,
        feature_output_refs=(
            json.dumps(_atr_feature().to_dict(), sort_keys=True, separators=(",", ":")),
        ),
        model_family="sklearn.ridge",
        format="numpy_parameter_file",
        format_version="v1",
        preprocessing_spec={"steps": ["IMPUTE_MEDIAN", "STANDARDIZE"]},
        estimator_spec={"family": "sklearn.ridge", "hyperparameters": {}, "seed": 7},
        training_library="scikit-learn",
        training_library_version="1.5.0",
        created_at_utc=datetime(2024, 7, 2, 9, 0, tzinfo=UTC),
    )


def test_decode_feature_matrix_spec_round_trips_feature_output_refs() -> None:
    manifest = _manifest(fingerprint="a" * 64)
    resolved = ResolvedScoreCondition(
        spec=ScoreConditionSpec(artifact_fingerprint="a" * 64, threshold=0.5),
        manifest=manifest,
    )

    spec = decode_feature_matrix_spec(resolved)

    assert len(spec.features) == 1
    assert spec.features[0].alias == "atr"
    assert spec.features[0].component_id == ComponentId("volatility.atr")


def test_decode_feature_matrix_spec_refuses_undecodable_refs() -> None:
    manifest_dict = _manifest(fingerprint="a" * 64).to_dict()
    manifest_dict["features"] = ["not-json"]
    manifest = PromotedArtifactManifest.from_dict(manifest_dict)
    resolved = ResolvedScoreCondition(
        spec=ScoreConditionSpec(artifact_fingerprint="a" * 64, threshold=0.5),
        manifest=manifest,
    )

    with pytest.raises(ScoreGateError, match="undecodable"):
        decode_feature_matrix_spec(resolved)


def test_read_promoted_artifact_parameters_missing_file_is_named_error(tmp_path: Path) -> None:
    with pytest.raises(ScoreGateError, match="not found"):
        read_promoted_artifact_parameters(tmp_path, "a" * 64)


def test_read_promoted_artifact_parameters_reads_the_payload(tmp_path: Path) -> None:
    payload_path = promoted_artifact_payload_path(tmp_path, "a" * 64)
    payload_path.parent.mkdir(parents=True, exist_ok=True)
    payload_path.write_text(json.dumps({"coefficients": [1.0], "intercept": 0.0}), encoding="utf-8")

    parameters = read_promoted_artifact_parameters(tmp_path, "a" * 64)

    assert parameters.coefficients == (1.0,)
    assert parameters.intercept == 0.0


def _available_at_series(start: datetime, count: int) -> list[datetime]:
    return [start + timedelta(minutes=index) for index in range(count)]


def _entry_signals(available_at: list[datetime]) -> pl.DataFrame:
    return pl.DataFrame(
        {
            "available_at": available_at,
            "direction": ["long"] * len(available_at),
        },
        schema={"available_at": _UTC_US, "direction": pl.String()},
    )


def _score_table(available_at: list[datetime], scores: list[float]) -> pl.DataFrame:
    return pl.DataFrame(
        {"available_at": available_at, "score": scores},
        schema={"available_at": _UTC_US, "score": pl.Float64()},
    )


def test_apply_score_gate_keeps_only_rows_clearing_threshold() -> None:
    start = datetime(2024, 1, 1, tzinfo=UTC)
    available_at = _available_at_series(start, 4)
    entries = _entry_signals(available_at)
    scores = _score_table(available_at, [0.1, 0.9, 0.5, 0.4])

    gated = apply_score_gate(entries, scores, threshold=0.5)

    assert gated.get_column("available_at").to_list() == [available_at[1], available_at[2]]


def test_apply_score_gate_decision_depends_only_on_the_row_s_own_score() -> None:
    """No-look-ahead / no-cross-row-leakage: changing another row's score
    must not change this row's gate decision -- the join key is
    ``available_at`` alone, one row in, one decision out.
    """
    start = datetime(2024, 1, 1, tzinfo=UTC)
    available_at = _available_at_series(start, 3)
    entries = _entry_signals(available_at)
    baseline_scores = _score_table(available_at, [0.9, 0.1, 0.9])
    mutated_scores = _score_table(available_at, [0.9, 0.1, 0.0])  # only row 2 changed

    baseline_gated = apply_score_gate(entries, baseline_scores, threshold=0.5)
    mutated_gated = apply_score_gate(entries, mutated_scores, threshold=0.5)

    assert available_at[0] in baseline_gated.get_column("available_at").to_list()
    assert available_at[0] in mutated_gated.get_column("available_at").to_list()
    assert available_at[1] not in baseline_gated.get_column("available_at").to_list()
    assert available_at[1] not in mutated_gated.get_column("available_at").to_list()


def test_apply_score_gate_drops_occurrences_with_no_matching_score() -> None:
    start = datetime(2024, 1, 1, tzinfo=UTC)
    available_at = _available_at_series(start, 3)
    entries = _entry_signals(available_at)
    scores = _score_table(available_at[:2], [0.9, 0.9])  # row 2 has no score at all

    gated = apply_score_gate(entries, scores, threshold=0.5)

    assert available_at[2] not in gated.get_column("available_at").to_list()
    assert gated.height == 2
