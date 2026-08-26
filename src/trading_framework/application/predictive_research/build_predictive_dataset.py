"""Build a fingerprinted Predictive Research dataset from a study spec."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from trading_framework import __version__ as framework_version
from trading_framework.application.market_analysis.run_analysis import (
    RunAnalysisRequest,
    run_analysis,
)
from trading_framework.core.exceptions import ValidationError
from trading_framework.market.models import MarketBar
from trading_framework.market_analysis.assembly.frame import (
    AnalysisFrame,
    AnalysisFrameColumnSpec,
    AnalysisFrameRequest,
)
from trading_framework.market_analysis.data.columnar import OhlcvColumnBatch
from trading_framework.market_analysis.data.view import AnalysisDataView
from trading_framework.market_analysis.models.output_ref import OutputRef
from trading_framework.market_analysis.models.request import ComponentRequest
from trading_framework.research.datasets.predictive import (
    PREDICTIVE_DATASET_SCHEMA_VERSION,
    PredictiveDatasetEnvelope,
    PredictiveDatasetManifest,
    PredictiveDatasetRef,
    PredictiveDatasetRepository,
    compute_dataset_fingerprint,
    derive_dataset_id,
    exclusion_counts_to_dict,
    fold_summary_from_features,
    resolve_fold_boundaries,
)
from trading_framework.research.predictive.features import FeatureMatrixSpec, FeatureSpec
from trading_framework.research.predictive.matrix import build_labelled_feature_matrix
from trading_framework.research.predictive.spec import PredictiveStudySpec
from trading_framework.research.predictive.splitting import assign_purged_walk_forward_folds
from trading_framework.time.clocks.protocol import Clock
from trading_framework.time.clocks.system import SystemClock
from trading_framework.time.sessions.protocol import TradingSessionResolver

_REQUIRED_OHLCV = ("high", "low", "close")
_OPTIONAL_OHLCV = ("open", "volume")


class PredictiveDatasetError(ValidationError):
    """Raised when Predictive Research dataset orchestration fails."""


@dataclass(frozen=True, slots=True)
class BuildPredictiveDatasetRequest:
    """Input for one Predictive Research dataset build."""

    spec: PredictiveStudySpec
    storage_root: Path
    persist: bool = True
    session_resolver: TradingSessionResolver | None = None
    preloaded_bars: tuple[MarketBar, ...] | None = None
    preloaded_column_batch: OhlcvColumnBatch | None = None
    preloaded_view: AnalysisDataView | None = None
    clock: Clock | None = None
    repository: PredictiveDatasetRepository | None = None


@dataclass(frozen=True, slots=True)
class BuildPredictiveDatasetResult:
    """Outcome of one Predictive Research dataset build."""

    dataset_id: str
    dataset_ref: PredictiveDatasetRef
    fingerprint: str
    envelope: PredictiveDatasetEnvelope
    persisted: bool


def build_predictive_dataset(
    request: BuildPredictiveDatasetRequest,
) -> BuildPredictiveDatasetResult:
    """Assemble features, assign folds, fingerprint, and optionally persist."""
    spec = request.spec
    definition_hash = spec.definition_hash
    if definition_hash is None:
        msg = "study spec is missing definition_hash"
        raise PredictiveDatasetError(msg)

    analysis = run_analysis(
        RunAnalysisRequest(
            dataset_ref=spec.dataset_ref,
            timeframe=spec.dataset_ref.dataset_id.timeframe,
            requested_range=spec.time_range,
            storage_root=request.storage_root,
            component_requests=_component_requests(spec.features),
            frame_request=AnalysisFrameRequest(
                market_fields=("open", "high", "low", "close", "volume"),
                analysis_columns=_frame_column_specs(spec.features),
            ),
            evaluation_timeframe=spec.evaluation_timeframe,
            session_resolver=request.session_resolver,
            preloaded_bars=request.preloaded_bars,
            preloaded_column_batch=request.preloaded_column_batch,
            preloaded_view=request.preloaded_view,
        )
    )
    if analysis.frame is None:
        msg = "analysis run did not assemble a consumer frame"
        raise PredictiveDatasetError(msg)

    frame = analysis.frame
    lineage = _declared_feature_lineage(frame, spec.features)
    labelled = build_labelled_feature_matrix(
        frame=frame,
        ohlcv=_ohlcv_from_frame(frame),
        features=spec.features,
        label=spec.label,
        horizon_bars=spec.label_horizon_bars(),
    )
    assigned = assign_purged_walk_forward_folds(labelled.rows, spec.split)
    fingerprint = compute_dataset_fingerprint(
        definition_hash=definition_hash,
        feature_lineage=lineage,
        dataset_ref=spec.dataset_ref,
        time_range=spec.time_range,
    )
    dataset_id = derive_dataset_id(fingerprint)
    clock = request.clock or SystemClock()
    envelope = PredictiveDatasetEnvelope(
        manifest=PredictiveDatasetManifest(
            schema_version=PREDICTIVE_DATASET_SCHEMA_VERSION,
            dataset_id=dataset_id,
            study_spec=spec.to_dict(),
            definition_hash=definition_hash,
            dataset_fingerprint=fingerprint,
            source_dataset_ref=str(spec.dataset_ref),
            time_range_start=spec.time_range.start,
            time_range_end=spec.time_range.end,
            exclusion_counts=exclusion_counts_to_dict(labelled.exclusions),
            fold_summary=fold_summary_from_features(assigned),
            framework_version=framework_version,
            created_at_utc=clock.now(),
        ),
        features=assigned,
        folds=resolve_fold_boundaries(assigned),
    )
    dataset_ref = PredictiveDatasetRef(dataset_id=dataset_id)
    persisted = False
    if request.persist:
        repository = request.repository or PredictiveDatasetRepository(request.storage_root)
        dataset_ref = repository.write(envelope)
        persisted = True
    return BuildPredictiveDatasetResult(
        dataset_id=dataset_id,
        dataset_ref=dataset_ref,
        fingerprint=fingerprint,
        envelope=envelope,
        persisted=persisted,
    )


def _frame_column_specs(features: FeatureMatrixSpec) -> tuple[AnalysisFrameColumnSpec, ...]:
    return tuple(
        AnalysisFrameColumnSpec(
            component_id=feature.component_id,
            parameters=feature.parameters,
            output_id=feature.output_id,
            alias=feature.alias,
        )
        for feature in features.features
    )


def _component_requests(features: FeatureMatrixSpec) -> tuple[ComponentRequest, ...]:
    requests: list[ComponentRequest] = []
    seen: set[tuple[str, str]] = set()
    for feature in features.features:
        key = (feature.component_id.value, feature.parameters.fingerprint())
        if key in seen:
            continue
        seen.add(key)
        requests.append(
            ComponentRequest(
                component_id=feature.component_id,
                parameters=feature.parameters,
            )
        )
    return tuple(requests)


def _declared_feature_lineage(
    frame: AnalysisFrame,
    features: FeatureMatrixSpec,
) -> dict[str, OutputRef]:
    lineage: dict[str, OutputRef] = {}
    for feature in features.features:
        output_ref = _lineage_for_feature(frame, feature)
        if output_ref is None:
            msg = f"assembled frame missing lineage for feature alias: {feature.alias!r}"
            raise PredictiveDatasetError(msg)
        lineage[feature.alias] = output_ref
    return lineage


def _lineage_for_feature(frame: AnalysisFrame, feature: FeatureSpec) -> OutputRef | None:
    if feature.alias in frame.column_lineage:
        return frame.column_lineage[feature.alias]
    for output_ref in frame.column_lineage.values():
        identity = output_ref.computation_identity
        if (
            output_ref.output_id == feature.output_id
            and identity.component_id == feature.component_id
            and identity.parameters == feature.parameters
        ):
            return output_ref
    return None


def _ohlcv_from_frame(frame: AnalysisFrame) -> dict[str, tuple[float, ...]]:
    missing = [name for name in _REQUIRED_OHLCV if name not in frame.columns]
    if missing:
        msg = f"assembled frame missing OHLCV column: {missing[0]}"
        raise PredictiveDatasetError(msg)
    ohlcv: dict[str, tuple[float, ...]] = {name: frame.columns[name] for name in _REQUIRED_OHLCV}
    for name in _OPTIONAL_OHLCV:
        if name in frame.columns:
            ohlcv[name] = frame.columns[name]
    return ohlcv
