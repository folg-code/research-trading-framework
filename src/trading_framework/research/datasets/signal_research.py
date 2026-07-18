"""Signal Research run envelope — manifest, schema validation, persistence."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, assert_never

import polars as pl

from trading_framework.core.exceptions import ValidationError
from trading_framework.infrastructure.storage.paths import (
    signal_research_analytics_parquet_path,
    signal_research_analytics_summary_path,
    signal_research_run_dir,
)
from trading_framework.research.context.context_fact import (
    empty_context_facts_dataframe,
    validate_context_facts_dataframe,
)
from trading_framework.research.observations.market_model_observation import (
    empty_market_model_observations_dataframe,
    validate_observations_dataframe,
)
from trading_framework.research.outcomes.calculator import empty_forward_outcomes_dataframe
from trading_framework.research.outcomes.definition import ForwardOutcomeDefinition
from trading_framework.research.scope import ResearchScope
from trading_framework.strategy.reference_price import ReferencePricePolicy
from trading_framework.strategy.signal_occurrence import empty_signal_occurrences_dataframe

SIGNAL_RESEARCH_SCHEMA_VERSION = "signal_research.v1"
SIGNAL_RESEARCH_SCHEMA_V2 = "signal_research.v2"
SUPPORTED_READ_SCHEMA_VERSIONS = frozenset(
    {SIGNAL_RESEARCH_SCHEMA_VERSION, SIGNAL_RESEARCH_SCHEMA_V2}
)
SUPPORTED_WRITE_SCHEMA_VERSIONS = frozenset(
    {SIGNAL_RESEARCH_SCHEMA_VERSION, SIGNAL_RESEARCH_SCHEMA_V2}
)


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
    research_scope: ResearchScope | None = None
    market_model_ids: tuple[str, ...] = ()
    research_id: str | None = None
    research_question: str | None = None
    definition_hash: str | None = None
    occurrence_policy: dict[str, Any] | None = None

    def effective_scope(self) -> ResearchScope:
        """Resolve explicit v2 scope or infer ``SIGNAL_MODEL_ONLY`` for legacy v1 runs."""
        if self.research_scope is not None:
            return self.research_scope
        return ResearchScope.SIGNAL_MODEL_ONLY

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
        if self.research_scope is not None:
            payload["research_scope"] = self.research_scope.value
        if self.market_model_ids:
            payload["market_model_ids"] = list(self.market_model_ids)
        if self.research_id is not None:
            payload["research_id"] = self.research_id
        if self.research_question is not None:
            payload["research_question"] = self.research_question
        if self.definition_hash is not None:
            payload["definition_hash"] = self.definition_hash
        if self.occurrence_policy is not None:
            payload["occurrence_policy"] = self.occurrence_policy
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> SignalResearchRunManifest:
        research_scope_raw = payload.get("research_scope")
        research_scope = (
            ResearchScope(str(research_scope_raw)) if research_scope_raw is not None else None
        )
        market_model_ids_raw = payload.get("market_model_ids", [])
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
            research_scope=research_scope,
            market_model_ids=tuple(str(value) for value in market_model_ids_raw),
            research_id=(
                str(payload["research_id"]) if payload.get("research_id") is not None else None
            ),
            research_question=(
                str(payload["research_question"])
                if payload.get("research_question") is not None
                else None
            ),
            definition_hash=(
                str(payload["definition_hash"])
                if payload.get("definition_hash") is not None
                else None
            ),
            occurrence_policy=(
                dict(payload["occurrence_policy"])
                if payload.get("occurrence_policy") is not None
                else None
            ),
        )


@dataclass(frozen=True, slots=True)
class SignalResearchRunEnvelope:
    """In-memory Signal Research run envelope."""

    manifest: SignalResearchRunManifest
    outcomes: pl.DataFrame
    occurrences: pl.DataFrame
    observations: pl.DataFrame
    context: pl.DataFrame


def empty_signal_research_run_envelope(
    *, manifest: SignalResearchRunManifest
) -> SignalResearchRunEnvelope:
    """Build an envelope with empty fact tables for the requested scope."""
    return SignalResearchRunEnvelope(
        manifest=manifest,
        outcomes=empty_forward_outcomes_dataframe(),
        occurrences=empty_signal_occurrences_dataframe(),
        observations=empty_market_model_observations_dataframe(),
        context=empty_context_facts_dataframe(),
    )


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
    """Deterministic run identity for v1 ``SIGNAL_MODEL_ONLY`` runs."""
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


def derive_run_id_v2(
    *,
    research_scope: ResearchScope,
    source_dataset_ref: str,
    market_model_ids: tuple[str, ...],
    signal_model_ids: tuple[str, ...],
    horizons: tuple[int, ...],
    evaluation_timeframe: str,
    requested_range_start: datetime,
    requested_range_end: datetime,
    framework_version: str,
    outcome_definition_fingerprint: str,
) -> str:
    """Deterministic run identity including explicit research scope."""
    payload = "|".join(
        [
            research_scope.value,
            source_dataset_ref,
            ",".join(sorted(market_model_ids)),
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
    """Validate signal occurrence fact table columns against the canonical schema."""
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


def _validate_v2_manifest_scope(manifest: SignalResearchRunManifest) -> ResearchScope:
    if manifest.schema_version != SIGNAL_RESEARCH_SCHEMA_V2:
        msg = "v2 scope validation requires signal_research.v2 schema version"
        raise ValidationError(msg)
    if manifest.research_scope is None:
        msg = "v2 manifest requires explicit research_scope"
        raise ValidationError(msg)
    return manifest.research_scope


class SignalResearchDatasetRepository:
    """Persist and load Signal Research run envelopes."""

    def __init__(self, root: Path) -> None:
        self._root = root

    def write(self, envelope: SignalResearchRunEnvelope) -> RunDatasetRef:
        """Persist one run envelope; refuse overwrite of an existing run."""
        validate_outcomes_dataframe(envelope.outcomes)
        if not envelope.manifest.run_id.strip():
            msg = "manifest run_id must be non-empty"
            raise ValidationError(msg)
        if envelope.manifest.schema_version not in SUPPORTED_WRITE_SCHEMA_VERSIONS:
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
        envelope.outcomes.write_parquet(run_dir / "outcomes.parquet")

        if envelope.manifest.schema_version == SIGNAL_RESEARCH_SCHEMA_VERSION:
            validate_occurrences_dataframe(envelope.occurrences)
            envelope.occurrences.write_parquet(run_dir / "occurrences.parquet")
            return RunDatasetRef(run_id=envelope.manifest.run_id)

        scope = _validate_v2_manifest_scope(envelope.manifest)
        if scope is ResearchScope.SIGNAL_MODEL_ONLY:
            validate_occurrences_dataframe(envelope.occurrences)
            envelope.occurrences.write_parquet(run_dir / "occurrences.parquet")
        elif scope is ResearchScope.MARKET_MODEL_ONLY:
            validate_observations_dataframe(envelope.observations)
            envelope.observations.write_parquet(run_dir / "observations.parquet")
        elif scope is ResearchScope.MARKET_AND_SIGNAL:
            validate_occurrences_dataframe(envelope.occurrences)
            validate_context_facts_dataframe(envelope.context)
            if len(envelope.occurrences) != len(envelope.context):
                msg = "context rows must match occurrence rows for MARKET_AND_SIGNAL"
                raise ValidationError(msg)
            envelope.occurrences.write_parquet(run_dir / "occurrences.parquet")
            envelope.context.write_parquet(run_dir / "context.parquet")
        else:
            assert_never(scope)

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
        if manifest.schema_version not in SUPPORTED_READ_SCHEMA_VERSIONS:
            msg = f"unsupported schema version: {manifest.schema_version}"
            raise ValidationError(msg)

        outcomes = pl.read_parquet(run_dir / "outcomes.parquet")
        validate_outcomes_dataframe(outcomes)

        if manifest.schema_version == SIGNAL_RESEARCH_SCHEMA_VERSION:
            occurrences = pl.read_parquet(run_dir / "occurrences.parquet")
            validate_occurrences_dataframe(occurrences)
            return SignalResearchRunEnvelope(
                manifest=manifest,
                outcomes=outcomes,
                occurrences=occurrences,
                observations=empty_market_model_observations_dataframe(),
                context=empty_context_facts_dataframe(),
            )

        scope = manifest.effective_scope()
        occurrences = empty_signal_occurrences_dataframe()
        observations = empty_market_model_observations_dataframe()
        context = empty_context_facts_dataframe()

        occurrences_path = run_dir / "occurrences.parquet"
        observations_path = run_dir / "observations.parquet"
        context_path = run_dir / "context.parquet"

        if scope in {ResearchScope.SIGNAL_MODEL_ONLY, ResearchScope.MARKET_AND_SIGNAL}:
            if not occurrences_path.exists():
                msg = f"missing occurrences parquet: {occurrences_path}"
                raise FileNotFoundError(msg)
            occurrences = pl.read_parquet(occurrences_path)
            validate_occurrences_dataframe(occurrences)

        if scope is ResearchScope.MARKET_MODEL_ONLY:
            if not observations_path.exists():
                msg = f"missing observations parquet: {observations_path}"
                raise FileNotFoundError(msg)
            observations = pl.read_parquet(observations_path)
            validate_observations_dataframe(observations)

        if scope is ResearchScope.MARKET_AND_SIGNAL:
            if not context_path.exists():
                msg = f"missing context parquet: {context_path}"
                raise FileNotFoundError(msg)
            context = pl.read_parquet(context_path)
            validate_context_facts_dataframe(context)

        return SignalResearchRunEnvelope(
            manifest=manifest,
            outcomes=outcomes,
            occurrences=occurrences,
            observations=observations,
            context=context,
        )

    def write_analytics_summary(self, run_id: str, payload: dict[str, Any]) -> Path:
        """Persist one cached analytics envelope under ``analytics/summary.json``."""
        run_dir = signal_research_run_dir(self._root, run_id)
        if not run_dir.exists():
            msg = f"run directory not found: {run_dir}"
            raise FileNotFoundError(msg)

        summary_path = signal_research_analytics_summary_path(self._root, run_id)
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        summary_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return summary_path

    def write_analytics_parquet_tables(
        self,
        run_id: str,
        tables: dict[str, pl.DataFrame],
    ) -> dict[str, Path]:
        """Dual-write tabular analytics frames as Parquet under ``analytics/``."""
        run_dir = signal_research_run_dir(self._root, run_id)
        if not run_dir.exists():
            msg = f"run directory not found: {run_dir}"
            raise FileNotFoundError(msg)
        if not tables:
            msg = "analytics parquet tables must be non-empty"
            raise ValidationError(msg)

        written: dict[str, Path] = {}
        for table_name, frame in tables.items():
            if not table_name.strip():
                msg = "analytics parquet table name must be non-empty"
                raise ValidationError(msg)
            path = signal_research_analytics_parquet_path(self._root, run_id, table_name)
            path.parent.mkdir(parents=True, exist_ok=True)
            frame.write_parquet(path)
            written[table_name] = path
        return written

    def read_analytics_summary_payload(self, run_id: str) -> dict[str, Any]:
        """Load the raw cached analytics summary mapping."""
        summary_path = signal_research_analytics_summary_path(self._root, run_id)
        if not summary_path.exists():
            msg = f"missing analytics summary: {summary_path}"
            raise FileNotFoundError(msg)
        payload = json.loads(summary_path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            msg = f"analytics summary must be a mapping: {summary_path}"
            raise ValidationError(msg)
        return payload

    def has_analytics_summary(self, run_id: str) -> bool:
        """Return whether a cached analytics summary exists for one run."""
        return signal_research_analytics_summary_path(self._root, run_id).exists()
