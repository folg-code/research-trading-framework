"""Signal Research run envelope — manifest, schema validation, persistence."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import polars as pl

from trading_framework.core.exceptions import ValidationError
from trading_framework.infrastructure.storage.paths import signal_research_run_dir
from trading_framework.research.outcomes.calculator import empty_forward_outcomes_dataframe
from trading_framework.research.outcomes.definition import ForwardOutcomeDefinition
from trading_framework.strategy.reference_price import ReferencePricePolicy
from trading_framework.strategy.signal_occurrence import empty_signal_occurrences_dataframe

SIGNAL_RESEARCH_SCHEMA_VERSION = "signal_research.v1"


@dataclass(frozen=True, slots=True)
class RunDatasetRef:
    """Logical reference to one persisted Signal Research run."""

    run_id: str

    def __post_init__(self) -> None:
        normalized = self.run_id.strip()
        if not normalized:
            msg = "run_id must be non-empty"
            raise ValidationError(msg)


@dataclass(frozen=True, slots=True)
class SignalResearchRunManifest:
    """Run-level metadata for one Signal Research envelope."""

    run_id: str
    schema_version: str
    framework_version: str
    created_at_utc: datetime
    source_dataset_ref: str
    evaluation_timeframe: str
    signal_model_ids: tuple[str, ...]
    horizon_bars_requested: tuple[int, ...]
    reference_price_policy: ReferencePricePolicy
    outcome_definition_fingerprint: str
    experiment_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "run_id": self.run_id,
            "schema_version": self.schema_version,
            "framework_version": self.framework_version,
            "created_at_utc": self.created_at_utc.isoformat(),
            "source_dataset_ref": self.source_dataset_ref,
            "evaluation_timeframe": self.evaluation_timeframe,
            "signal_model_ids": list(self.signal_model_ids),
            "horizon_bars_requested": list(self.horizon_bars_requested),
            "reference_price_policy": self.reference_price_policy.value,
            "outcome_definition_fingerprint": self.outcome_definition_fingerprint,
        }
        if self.experiment_id is not None:
            payload["experiment_id"] = self.experiment_id
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> SignalResearchRunManifest:
        return cls(
            run_id=str(payload["run_id"]),
            schema_version=str(payload["schema_version"]),
            framework_version=str(payload["framework_version"]),
            created_at_utc=datetime.fromisoformat(str(payload["created_at_utc"])),
            source_dataset_ref=str(payload["source_dataset_ref"]),
            evaluation_timeframe=str(payload["evaluation_timeframe"]),
            signal_model_ids=tuple(str(value) for value in payload["signal_model_ids"]),
            horizon_bars_requested=tuple(int(value) for value in payload["horizon_bars_requested"]),
            reference_price_policy=ReferencePricePolicy(str(payload["reference_price_policy"])),
            outcome_definition_fingerprint=str(payload["outcome_definition_fingerprint"]),
            experiment_id=(
                str(payload["experiment_id"]) if payload.get("experiment_id") is not None else None
            ),
        )


@dataclass(frozen=True, slots=True)
class SignalResearchRunEnvelope:
    """In-memory Signal Research run envelope."""

    manifest: SignalResearchRunManifest
    occurrences: pl.DataFrame
    outcomes: pl.DataFrame


def outcome_definition_fingerprint(
    horizons: tuple[int, ...],
    definition: ForwardOutcomeDefinition | None = None,
) -> str:
    """Stable fingerprint for outcome semantics included in run identity."""
    base = definition or ForwardOutcomeDefinition(horizon_bars=horizons[0])
    payload = "|".join(
        [
            ",".join(str(horizon) for horizon in sorted(horizons)),
            base.reference_price_policy.value,
            base.terminal_price_field.value,
            base.excursion_high_field.value,
            base.excursion_low_field.value,
            base.incomplete_horizon_policy.value,
        ]
    )
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


def derive_run_id(
    *,
    source_dataset_ref: str,
    signal_model_ids: tuple[str, ...],
    horizons: tuple[int, ...],
    evaluation_timeframe: str,
    requested_range_start: datetime,
    requested_range_end: datetime,
    framework_version: str,
    outcome_definition_fingerprint: str,
) -> str:
    """Deterministic run identity from material inputs."""
    payload = "|".join(
        [
            source_dataset_ref,
            ",".join(sorted(signal_model_ids)),
            ",".join(str(horizon) for horizon in sorted(horizons)),
            evaluation_timeframe,
            requested_range_start.isoformat(),
            requested_range_end.isoformat(),
            framework_version,
            outcome_definition_fingerprint,
        ]
    )
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


def validate_occurrences_dataframe(frame: pl.DataFrame) -> None:
    """Validate occurrence fact table columns against the canonical schema."""
    expected = empty_signal_occurrences_dataframe()
    if frame.columns != expected.columns:
        msg = f"occurrences columns mismatch: {frame.columns} != {expected.columns}"
        raise ValidationError(msg)


def validate_outcomes_dataframe(frame: pl.DataFrame) -> None:
    """Validate outcome fact table columns against the canonical schema."""
    expected = empty_forward_outcomes_dataframe()
    if frame.columns != expected.columns:
        msg = f"outcomes columns mismatch: {frame.columns} != {expected.columns}"
        raise ValidationError(msg)


class SignalResearchDatasetRepository:
    """Persist and load Signal Research run envelopes."""

    def __init__(self, root: Path) -> None:
        self._root = root

    def write(self, envelope: SignalResearchRunEnvelope) -> RunDatasetRef:
        """Persist one run envelope; refuse overwrite of an existing run."""
        validate_occurrences_dataframe(envelope.occurrences)
        validate_outcomes_dataframe(envelope.outcomes)
        if not envelope.manifest.run_id.strip():
            msg = "manifest run_id must be non-empty"
            raise ValidationError(msg)
        if envelope.manifest.schema_version != SIGNAL_RESEARCH_SCHEMA_VERSION:
            msg = f"unsupported schema version: {envelope.manifest.schema_version}"
            raise ValidationError(msg)

        run_dir = signal_research_run_dir(self._root, envelope.manifest.run_id)
        if run_dir.exists():
            msg = f"run directory already exists: {run_dir}"
            raise FileExistsError(msg)

        run_dir.mkdir(parents=True, exist_ok=False)
        manifest_path = run_dir / "manifest.json"
        manifest_path.write_text(
            json.dumps(envelope.manifest.to_dict(), indent=2),
            encoding="utf-8",
        )
        envelope.occurrences.write_parquet(run_dir / "occurrences.parquet")
        envelope.outcomes.write_parquet(run_dir / "outcomes.parquet")
        return RunDatasetRef(run_id=envelope.manifest.run_id)

    def read(self, ref: RunDatasetRef) -> SignalResearchRunEnvelope:
        """Load one run envelope and validate schema version."""
        run_dir = signal_research_run_dir(self._root, ref.run_id)
        manifest_path = run_dir / "manifest.json"
        if not manifest_path.exists():
            msg = f"missing manifest: {manifest_path}"
            raise FileNotFoundError(msg)

        manifest = SignalResearchRunManifest.from_dict(
            json.loads(manifest_path.read_text(encoding="utf-8"))
        )
        if manifest.schema_version != SIGNAL_RESEARCH_SCHEMA_VERSION:
            msg = f"unsupported schema version: {manifest.schema_version}"
            raise ValidationError(msg)

        occurrences = pl.read_parquet(run_dir / "occurrences.parquet")
        outcomes = pl.read_parquet(run_dir / "outcomes.parquet")
        validate_occurrences_dataframe(occurrences)
        validate_outcomes_dataframe(outcomes)
        return SignalResearchRunEnvelope(
            manifest=manifest,
            occurrences=occurrences,
            outcomes=outcomes,
        )
