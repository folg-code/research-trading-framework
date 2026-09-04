"""Predictive study specification, definition hash, and YAML/JSON loading."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from trading_framework.core.exceptions import ValidationError
from trading_framework.market.datasets import DatasetRef
from trading_framework.market_analysis.models.time_range import TimeRange
from trading_framework.research.predictive.errors import PredictiveSpecError
from trading_framework.research.predictive.features import FeatureMatrixSpec
from trading_framework.research.predictive.labels import LabelSpec
from trading_framework.research.predictive.sample import (
    PredictiveTask,
    SampleKind,
    SampleSpec,
    parse_predictive_task,
    validate_sample_task_compatibility,
)
from trading_framework.research.predictive.splitting import PurgedWalkForwardSplitSpec
from trading_framework.time.models.timeframe import Timeframe


@dataclass(frozen=True, slots=True)
class PredictiveStudySpec:
    """Declarative learning-problem contract for one Predictive Research dataset.

    Mirrors ``SignalResearchDefinitionSpec``: identity, published ``DatasetRef``,
    analysis window, declared features, one label horizon, and a purged
    walk-forward split policy. ``definition_hash`` fingerprints those declared
    fields via canonical JSON. Feature lineage is hashed later when a matrix
    is built (D-S039-11); this type never hashes DataFrames.
    """

    study_id: str
    dataset_ref: DatasetRef
    time_range: TimeRange
    features: FeatureMatrixSpec
    label: LabelSpec
    split: PurgedWalkForwardSplitSpec
    evaluation_timeframe: Timeframe = field(default_factory=lambda: Timeframe("1m"))
    sample: SampleSpec = field(default_factory=lambda: SampleSpec(kind=SampleKind.EVERY_BAR))
    task: PredictiveTask = PredictiveTask.FORWARD_RETURN
    definition_hash: str | None = None

    def __post_init__(self) -> None:
        normalized_id = self.study_id.strip()
        if not normalized_id:
            msg = "study_id must be non-empty"
            raise PredictiveSpecError(msg)
        object.__setattr__(self, "study_id", normalized_id)
        if self.evaluation_timeframe.is_event_level:
            msg = "evaluation_timeframe must be a bar duration"
            raise PredictiveSpecError(msg)
        validate_sample_task_compatibility(self.sample, self.task)
        self.label_horizon_bars()
        if self.definition_hash is None:
            object.__setattr__(self, "definition_hash", compute_definition_hash(self))

    def label_horizon_bars(self) -> int:
        """Bar count of the declared label horizon on ``evaluation_timeframe``.

        Same conversion as Signal Research ``horizon_to_bars``: the YAML horizon
        stays a ``Timeframe`` so it composes with ``ForwardOutcomeDefinition``
        once the builder supplies ``horizon_bars``.
        """
        horizon = self.label.horizon
        base = self.evaluation_timeframe
        if horizon.total_seconds % base.total_seconds != 0:
            msg = (
                f"label horizon {horizon.value!r} is not an integer multiple of "
                f"evaluation timeframe {base.value!r}"
            )
            raise PredictiveSpecError(msg)
        bars = horizon.total_seconds // base.total_seconds
        if bars < 1:
            msg = f"label horizon {horizon.value!r} must span at least one evaluation bar"
            raise PredictiveSpecError(msg)
        return bars

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "study_id": self.study_id,
            "dataset_ref": {
                "dataset_id": self.dataset_ref.dataset_id.canonical(),
                "version": self.dataset_ref.version,
            },
            "time_range": {
                "start": self.time_range.start.isoformat(),
                "end": self.time_range.end.isoformat(),
            },
            "evaluation_timeframe": self.evaluation_timeframe.value,
            "features": self.features.to_dict(),
            "label": self.label.to_dict(),
            "split": self.split.to_dict(),
        }
        # Default elision (ADR-0031 Decision 2, D-S056-04): an explicitly
        # declared default hashes identically to an omitted one. `sample` is
        # omitted only for `every_bar` and `task` only for `FORWARD_RETURN`,
        # which is what keeps every existing spec's definition_hash unchanged.
        if self.sample.kind is not SampleKind.EVERY_BAR:
            payload["sample"] = self.sample.to_dict()
        if self.task is not PredictiveTask.FORWARD_RETURN:
            payload["task"] = self.task.value
        if self.definition_hash is not None:
            payload["definition_hash"] = self.definition_hash
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> PredictiveStudySpec:
        normalized = _normalize_study_payload(payload)
        raw_id = normalized.get("study_id", normalized.get("research_id", normalized.get("id")))
        if raw_id is None:
            msg = "study spec missing field: study_id"
            raise PredictiveSpecError(msg)
        study_id = str(raw_id)
        try:
            dataset_ref = _parse_dataset_ref(normalized["dataset_ref"])
            time_payload = normalized["time_range"]
            features_payload = normalized["features"]
            label_payload = normalized["label"]
            split_payload = normalized["split"]
        except KeyError as exc:
            msg = f"study spec missing field: {exc.args[0]}"
            raise PredictiveSpecError(msg) from exc

        if not isinstance(time_payload, dict):
            msg = "time_range must be a mapping"
            raise PredictiveSpecError(msg)
        if not isinstance(label_payload, dict):
            msg = "label must be a mapping"
            raise PredictiveSpecError(msg)
        if not isinstance(split_payload, dict):
            msg = "split must be a mapping"
            raise PredictiveSpecError(msg)

        try:
            time_range = TimeRange(
                start=_parse_datetime(time_payload["start"]),
                end=_parse_datetime(time_payload["end"], end_of_day=True),
            )
            evaluation_timeframe = Timeframe(str(normalized.get("evaluation_timeframe", "1m")))
        except KeyError as exc:
            msg = f"time_range missing field: {exc.args[0]}"
            raise PredictiveSpecError(msg) from exc
        except ValidationError as exc:
            if isinstance(exc, PredictiveSpecError):
                raise
            raise PredictiveSpecError(str(exc)) from exc

        sample_payload = normalized.get("sample")
        if sample_payload is None:
            sample = SampleSpec(kind=SampleKind.EVERY_BAR)
        elif isinstance(sample_payload, dict):
            sample = SampleSpec.from_dict(sample_payload)
        else:
            msg = "sample must be a mapping"
            raise PredictiveSpecError(msg)

        task_payload = normalized.get("task")
        task = (
            PredictiveTask.FORWARD_RETURN
            if task_payload is None
            else parse_predictive_task(str(task_payload))
        )

        return cls(
            study_id=study_id,
            dataset_ref=dataset_ref,
            time_range=time_range,
            features=FeatureMatrixSpec.from_dict(features_payload),
            label=LabelSpec.from_dict({str(key): value for key, value in label_payload.items()}),
            split=PurgedWalkForwardSplitSpec.from_dict(
                {str(key): value for key, value in split_payload.items()}
            ),
            evaluation_timeframe=evaluation_timeframe,
            sample=sample,
            task=task,
        )


def compute_definition_hash(spec: PredictiveStudySpec) -> str:
    """Fingerprint the declared study independent of run identity and frame bytes."""
    payload = spec.to_dict()
    payload.pop("definition_hash", None)
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def load_predictive_study_spec_from_dict(payload: dict[str, Any]) -> PredictiveStudySpec:
    """Parse a study mapping into a validated spec."""
    return PredictiveStudySpec.from_dict(payload)


def load_predictive_study_spec(path: Path | str) -> PredictiveStudySpec:
    """Load a study from a ``.yaml``, ``.yml`` or ``.json`` file."""
    file_path = Path(path)
    if not file_path.is_file():
        msg = f"study file not found: {file_path}"
        raise PredictiveSpecError(msg)

    suffix = file_path.suffix.lower()
    text = file_path.read_text(encoding="utf-8")
    if suffix == ".json":
        payload = _load_json(text, source_path=file_path)
    elif suffix in {".yaml", ".yml"}:
        payload = _load_yaml(text, source_path=file_path)
    else:
        msg = f"unsupported study file extension: {suffix!r}"
        raise PredictiveSpecError(msg)

    if not isinstance(payload, dict):
        msg = "study root must be a mapping"
        raise PredictiveSpecError(msg)
    return load_predictive_study_spec_from_dict(payload)


def _normalize_study_payload(payload: dict[str, Any]) -> dict[str, Any]:
    study_payload = payload.get("study")
    if isinstance(study_payload, dict):
        return study_payload
    return payload


def _parse_dataset_ref(dataset_payload: object) -> DatasetRef:
    try:
        if isinstance(dataset_payload, dict):
            return DatasetRef.parse(f"{dataset_payload['dataset_id']}@{dataset_payload['version']}")
        return DatasetRef.parse(str(dataset_payload))
    except KeyError as exc:
        msg = f"dataset_ref missing field: {exc.args[0]}"
        raise PredictiveSpecError(msg) from exc
    except ValidationError as exc:
        raise PredictiveSpecError(str(exc)) from exc


def _parse_datetime(value: object, *, end_of_day: bool = False) -> datetime:
    text = str(value).strip()
    if len(text) == 10 and text[4] == "-" and text[7] == "-":
        year, month, day = (int(part) for part in text.split("-"))
        if end_of_day:
            return datetime(year, month, day, 23, 59, 59, tzinfo=UTC)
        return datetime(year, month, day, tzinfo=UTC)
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _load_json(text: str, *, source_path: Path) -> object:
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        msg = f"invalid JSON study file: {source_path}"
        raise PredictiveSpecError(msg) from exc


def _load_yaml(text: str, *, source_path: Path) -> dict[str, Any]:
    try:
        import yaml  # type: ignore[import-untyped]
    except ImportError as exc:
        msg = (
            f"PyYAML is required to load YAML studies; install pyyaml or use JSON for {source_path}"
        )
        raise PredictiveSpecError(msg) from exc

    loaded = yaml.safe_load(text)
    if not isinstance(loaded, dict):
        msg = f"YAML study must deserialize to a mapping: {source_path}"
        raise PredictiveSpecError(msg)
    return loaded
