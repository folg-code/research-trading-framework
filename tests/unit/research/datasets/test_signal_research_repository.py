"""Tests for Signal Research dataset repository."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from trading_framework import __version__ as framework_version
from trading_framework.core.exceptions import ValidationError
from trading_framework.research.datasets import (
    SIGNAL_RESEARCH_SCHEMA_VERSION,
    RunDatasetRef,
    SignalResearchDatasetRepository,
    SignalResearchRunEnvelope,
    SignalResearchRunManifest,
    derive_run_id,
    outcome_definition_fingerprint,
)
from trading_framework.research.outcomes import empty_forward_outcomes_dataframe
from trading_framework.strategy.reference_price import ReferencePricePolicy
from trading_framework.strategy.signal_occurrence import empty_signal_occurrences_dataframe


def _sample_manifest(*, run_id: str) -> SignalResearchRunManifest:
    return SignalResearchRunManifest(
        run_id=run_id,
        schema_version=SIGNAL_RESEARCH_SCHEMA_VERSION,
        framework_version=framework_version,
        created_at_utc=datetime(2024, 1, 1, tzinfo=UTC),
        source_dataset_ref="ES.c.0:ohlcv:1m:csv:fixture@1",
        evaluation_timeframe="1m",
        signal_model_ids=("higher_low_long",),
        horizon_bars_requested=(5, 10),
        reference_price_policy=ReferencePricePolicy.CLOSE_AT_DETECTED_AT,
        outcome_definition_fingerprint=outcome_definition_fingerprint((5, 10)),
    )


def _sample_envelope(*, run_id: str) -> SignalResearchRunEnvelope:
    occurrences = empty_signal_occurrences_dataframe()
    outcomes = empty_forward_outcomes_dataframe()
    return SignalResearchRunEnvelope(
        manifest=_sample_manifest(run_id=run_id),
        occurrences=occurrences,
        outcomes=outcomes,
    )


def test_derive_run_id_is_stable() -> None:
    start = datetime(2024, 1, 1, tzinfo=UTC)
    end = datetime(2024, 1, 2, tzinfo=UTC)
    fingerprint = outcome_definition_fingerprint((5, 10))
    first = derive_run_id(
        source_dataset_ref="dataset@1",
        signal_model_ids=("signal_a",),
        horizons=(5, 10),
        evaluation_timeframe="1m",
        requested_range_start=start,
        requested_range_end=end,
        framework_version=framework_version,
        outcome_definition_fingerprint=fingerprint,
    )
    second = derive_run_id(
        source_dataset_ref="dataset@1",
        signal_model_ids=("signal_a",),
        horizons=(5, 10),
        evaluation_timeframe="1m",
        requested_range_start=start,
        requested_range_end=end,
        framework_version=framework_version,
        outcome_definition_fingerprint=fingerprint,
    )
    assert first == second
    assert len(first) == 16


def test_repository_write_read_round_trip(tmp_path: Path) -> None:
    storage_root = tmp_path / "storage"
    repository = SignalResearchDatasetRepository(storage_root)
    run_id = "abc123def4567890"
    envelope = _sample_envelope(run_id=run_id)

    run_ref = repository.write(envelope)
    loaded = repository.read(run_ref)

    assert run_ref == RunDatasetRef(run_id=run_id)
    assert loaded.manifest.run_id == run_id
    assert loaded.manifest.schema_version == SIGNAL_RESEARCH_SCHEMA_VERSION
    assert loaded.occurrences.columns == envelope.occurrences.columns
    assert loaded.outcomes.columns == envelope.outcomes.columns


def test_repository_refuses_overwrite(tmp_path: Path) -> None:
    storage_root = tmp_path / "storage"
    repository = SignalResearchDatasetRepository(storage_root)
    run_id = "immutable-run-id1"
    envelope = _sample_envelope(run_id=run_id)
    repository.write(envelope)

    with pytest.raises(FileExistsError):
        repository.write(envelope)


def test_repository_rejects_unsupported_schema_version(tmp_path: Path) -> None:
    storage_root = tmp_path / "storage"
    repository = SignalResearchDatasetRepository(storage_root)
    run_id = "bad-schema-run01"
    manifest = _sample_manifest(run_id=run_id)
    bad_manifest = SignalResearchRunManifest(
        run_id=manifest.run_id,
        schema_version="signal_research.v0",
        framework_version=manifest.framework_version,
        created_at_utc=manifest.created_at_utc,
        source_dataset_ref=manifest.source_dataset_ref,
        evaluation_timeframe=manifest.evaluation_timeframe,
        signal_model_ids=manifest.signal_model_ids,
        horizon_bars_requested=manifest.horizon_bars_requested,
        reference_price_policy=manifest.reference_price_policy,
        outcome_definition_fingerprint=manifest.outcome_definition_fingerprint,
    )
    envelope = SignalResearchRunEnvelope(
        manifest=bad_manifest,
        occurrences=empty_signal_occurrences_dataframe(),
        outcomes=empty_forward_outcomes_dataframe(),
    )

    with pytest.raises(ValidationError, match="unsupported schema version"):
        repository.write(envelope)
