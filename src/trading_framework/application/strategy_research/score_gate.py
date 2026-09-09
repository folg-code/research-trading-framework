"""Predictive score gate: evaluate a resolved score condition in-process, under ``available_at``.

Sprint 058 T004 (Phase 16 increment 16C), ADR-0033. Composes strictly AFTER
``build_gated_entry_signals``'s existing market/signal gate -- one further
Polars filter on ``{available_at, direction}``, never a redesign of the
simulator's input contract. The simulator
(``research/simulation/engine.py``) stays opaque to WHY a row survived;
adding this gate cannot and does not touch it.

Runs one additional, narrowly-scoped analysis pass over the promoted
artifact's declared feature columns (decoded from
``PromotedArtifactManifest.feature_output_refs``) -- deliberately NOT
merged into ``evaluate_models``'s shared market/signal analysis pass, to
avoid widening that shared contract (used by every Strategy Research
caller, not only a scored one) for a Phase-16-only feature. ``available_at``
is derived by the identical ``timestamp + evaluation_timeframe`` rule
``model_expression/evaluation/frame_adapter.py::build_evaluation_dataframe``
already uses for the market/signal gate -- the score can never look ahead
of that rule because it is the same rule.

Reads only the promoted artifact's ``manifest.json`` (already resolved by
``resolve_score_condition``, T003) and ``artifact.json`` (the parameter
payload -- a plain-number JSON file, ADR-0029 §1). Never reads
``models/fold_{n}.bin`` (TD-022's safe operating boundary, unchanged) and
never imports ``infrastructure.ml`` (enforced by
``tests/unit/test_architecture_boundaries.py``).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import polars as pl

from trading_framework.application.market_analysis.run_analysis import (
    RunAnalysisRequest,
    run_analysis,
)
from trading_framework.application.strategy_research.resolve_score_condition import (
    ResolvedScoreCondition,
)
from trading_framework.core.exceptions import ValidationError
from trading_framework.infrastructure.storage.paths import promoted_artifact_payload_path
from trading_framework.market.datasets import DatasetRef
from trading_framework.market_analysis.assembly.frame import (
    AnalysisFrame,
    AnalysisFrameColumnSpec,
    AnalysisFrameRequest,
)
from trading_framework.market_analysis.data.columnar import OhlcvColumnBatch
from trading_framework.market_analysis.models.request import ComponentRequest
from trading_framework.market_analysis.models.time_range import TimeRange
from trading_framework.research.predictive.features import FeatureMatrixSpec, FeatureSpec
from trading_framework.research.predictive.promotion.evaluator import load_promoted_artifact
from trading_framework.research.predictive.promotion.parameters import PromotedArtifactParameters
from trading_framework.time.models.timeframe import Timeframe
from trading_framework.time.sessions.protocol import TradingSessionResolver
from trading_framework.time.utc_datetime_series import utc_datetime_series


class ScoreGateError(ValidationError):
    """Raised when the predictive score gate cannot be evaluated."""


def read_promoted_artifact_parameters(
    storage_root: Path,
    artifact_fingerprint: str,
) -> PromotedArtifactParameters:
    """Read ``artifact.json`` -- the plain-number parameter payload, never a fitted blob."""
    payload_path = promoted_artifact_payload_path(storage_root, artifact_fingerprint)
    if not payload_path.is_file():
        msg = f"promoted artifact parameter payload not found: {payload_path}"
        raise ScoreGateError(msg)
    return PromotedArtifactParameters.from_dict(
        json.loads(payload_path.read_text(encoding="utf-8"))
    )


def decode_feature_matrix_spec(resolved: ResolvedScoreCondition) -> FeatureMatrixSpec:
    """Decode the promoted artifact's declared, positionally-ordered features.

    ``feature_output_refs`` are canonical-JSON ``FeatureSpec`` encodings
    (``application/predictive_research/promote_predictive_run.py::_feature_identity``),
    the exact inverse of ``FeatureSpec.to_dict``.
    """
    try:
        features = tuple(
            FeatureSpec.from_dict(json.loads(ref)) for ref in resolved.manifest.feature_output_refs
        )
    except (json.JSONDecodeError, KeyError, ValueError, TypeError) as exc:
        msg = (
            f"promoted artifact {resolved.manifest.artifact_fingerprint!r} has "
            "undecodable feature_output_refs"
        )
        raise ScoreGateError(msg) from exc
    return FeatureMatrixSpec(features=features)


@dataclass(frozen=True, slots=True)
class ScoreTableRequest:
    """Inputs for the scorer's own, narrowly-scoped analysis pass."""

    dataset_ref: DatasetRef
    timeframe: Timeframe
    requested_range: TimeRange
    storage_root: Path
    evaluation_timeframe: Timeframe
    preloaded_column_batch: OhlcvColumnBatch | None = None
    session_resolver: TradingSessionResolver | None = None


def build_score_table(
    request: ScoreTableRequest,
    *,
    resolved: ResolvedScoreCondition,
    parameters: PromotedArtifactParameters,
) -> pl.DataFrame:
    """Evaluate the promoted artifact over its own declared feature columns.

    Returns ``{available_at, score}``, one row per bar, on the SAME
    evaluation-timeframe grid every other gate uses.
    """
    features = decode_feature_matrix_spec(resolved)
    analysis = run_analysis(
        RunAnalysisRequest(
            dataset_ref=request.dataset_ref,
            timeframe=request.timeframe,
            requested_range=request.requested_range,
            storage_root=request.storage_root,
            component_requests=_score_component_requests(features),
            frame_request=AnalysisFrameRequest(
                analysis_columns=_score_frame_column_specs(features)
            ),
            evaluation_timeframe=request.evaluation_timeframe,
            session_resolver=request.session_resolver,
            preloaded_column_batch=request.preloaded_column_batch,
        )
    )
    frame = analysis.frame
    if frame is None:
        msg = "score gate requires an assembled AnalysisFrame"
        raise ScoreGateError(msg)

    predictor = load_promoted_artifact(resolved.manifest, parameters)
    feature_matrix = _feature_matrix(frame, features)
    scores = np.asarray(predictor.predict(feature_matrix), dtype=np.float64).reshape(-1)
    if scores.shape[0] != len(frame.timestamps):
        msg = (
            f"score gate predictor returned {scores.shape[0]} scores for "
            f"{len(frame.timestamps)} rows"
        )
        raise ScoreGateError(msg)

    return (
        pl.DataFrame({"timestamp": utc_datetime_series(frame.timestamps)})
        .with_columns(
            (
                pl.col("timestamp")
                + pl.duration(seconds=request.evaluation_timeframe.total_seconds)
            ).alias("available_at")
        )
        .with_columns(pl.Series("score", scores))
        .select("available_at", "score")
    )


def apply_score_gate(
    entry_signals: pl.DataFrame,
    score_table: pl.DataFrame,
    *,
    threshold: float,
) -> pl.DataFrame:
    """Filter already-gated entries to those whose score clears ``threshold``.

    A further Polars filter on ``{available_at, direction}`` -- composes
    AFTER ``build_gated_entry_signals``, never before and never in its
    place. An occurrence with no matching ``available_at`` in
    ``score_table`` (inner join) is dropped, not defaulted to pass or fail
    -- an occurrence the scorer cannot score is not gate-eligible.
    """
    return (
        entry_signals.join(score_table, on="available_at", how="inner")
        .filter(pl.col("score") >= threshold)
        .select("available_at", "direction")
    )


def _score_component_requests(features: FeatureMatrixSpec) -> tuple[ComponentRequest, ...]:
    """Mirrors ``application/predictive_research/build_predictive_dataset.py``'s
    ``_component_requests`` -- deliberately duplicated, not imported. That
    function is private to Predictive Research's dataset builder; this is
    the same accepted-duplication pattern already used elsewhere in this
    increment (``MODEL_FAMILY_ALLOWLIST``'s two copies, ADR-0029 §9) rather
    than widening a module boundary for a ten-line mapping.
    """
    requests: list[ComponentRequest] = []
    seen: set[tuple[str, str]] = set()
    for feature in features.features:
        key = (feature.component_id.value, feature.parameters.fingerprint())
        if key in seen:
            continue
        seen.add(key)
        requests.append(
            ComponentRequest(component_id=feature.component_id, parameters=feature.parameters)
        )
    return tuple(requests)


def _score_frame_column_specs(features: FeatureMatrixSpec) -> tuple[AnalysisFrameColumnSpec, ...]:
    return tuple(
        AnalysisFrameColumnSpec(
            component_id=feature.component_id,
            parameters=feature.parameters,
            output_id=feature.output_id,
            alias=feature.alias,
        )
        for feature in features.features
    )


def _feature_matrix(frame: AnalysisFrame, features: FeatureMatrixSpec) -> np.ndarray:
    columns: list[np.ndarray] = []
    for feature in features.features:
        if feature.alias not in frame.columns:
            msg = f"assembled frame missing scorer feature column: {feature.alias!r}"
            raise ScoreGateError(msg)
        columns.append(np.asarray(frame.columns[feature.alias], dtype=np.float64))
    return np.column_stack(columns)
