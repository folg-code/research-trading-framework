"""Tests for analyze_signal_research_run application orchestration."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import polars as pl
import pytest

from trading_framework import __version__ as framework_version
from trading_framework.application.signal_research import (
    AnalyzeSignalResearchError,
    AnalyzeSignalResearchRequest,
    analyze_signal_research_run,
)
from trading_framework.research.analytics.dimensions import AnalyticsTimestampBasis
from trading_framework.research.analytics.schemas import validate_run_summaries
from trading_framework.research.context.context_fact import empty_context_facts_dataframe
from trading_framework.research.datasets import (
    SIGNAL_RESEARCH_SCHEMA_VERSION,
    RunDatasetRef,
    SignalResearchDatasetRepository,
    SignalResearchRunEnvelope,
    SignalResearchRunManifest,
    outcome_definition_fingerprint,
)
from trading_framework.research.observations import empty_market_model_observations_dataframe
from trading_framework.research.outcomes.definition import OutcomeStatus
from trading_framework.strategy.reference_price import ReferencePricePolicy


def _manifest(*, run_id: str) -> SignalResearchRunManifest:
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


def test_analyze_signal_research_run_reads_persisted_run(tmp_path: Path) -> None:
    run_id = "analyze-run"
    detected_at = datetime(2024, 1, 1, 12, 0, tzinfo=UTC)
    occurrences = pl.DataFrame(
        {
            "occurrence_id": ["occ-1"],
            "signal_model_id": ["higher_low_long"],
            "detected_at": [detected_at],
            "available_at": [detected_at],
            "direction": ["long"],
            "reference_price": [100.0],
            "instrument": ["TEST"],
            "evaluation_timeframe": ["1m"],
            "source_dataset_ref": ["test@1"],
        }
    )
    outcomes = pl.DataFrame(
        {
            "occurrence_id": ["occ-1", "occ-1"],
            "horizon_bars": [5, 10],
            "outcome_status": [OutcomeStatus.COMPLETE.value, OutcomeStatus.COMPLETE.value],
            "terminal_price": [101.0, 102.0],
            "forward_return": [0.01, 0.02],
            "mfe": [0.02, 0.03],
            "mae": [-0.005, -0.01],
        }
    )
    envelope = SignalResearchRunEnvelope(
        manifest=_manifest(run_id=run_id),
        occurrences=occurrences,
        observations=empty_market_model_observations_dataframe(),
        outcomes=outcomes,
        context=empty_context_facts_dataframe(),
    )
    repository = SignalResearchDatasetRepository(tmp_path)
    repository.write(envelope)

    result = analyze_signal_research_run(
        AnalyzeSignalResearchRequest(
            run_ref=RunDatasetRef(run_id=run_id),
            storage_root=tmp_path,
        )
    )

    assert result.source_run_id == run_id
    assert result.run_summaries.height == 2
    assert result.grouped_summaries is None
    assert result.conditional_comparison is None
    assert result.metadata.timestamp_basis is AnalyticsTimestampBasis.AVAILABLE_AT
    validate_run_summaries(result.run_summaries)


def test_analyze_signal_research_request_rejects_invalid_min_sample_size() -> None:
    with pytest.raises(AnalyzeSignalResearchError, match="min_sample_size"):
        AnalyzeSignalResearchRequest(
            run_ref=RunDatasetRef(run_id="run"),
            storage_root=Path("."),
            min_sample_size=0,
        )
