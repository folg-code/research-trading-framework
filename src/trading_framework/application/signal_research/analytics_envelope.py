"""Serialize and deserialize Signal Research analytics results for sidecar storage."""

from __future__ import annotations

from typing import Any

import polars as pl

from trading_framework.application.signal_research.analyze_signal_research import (
    AnalyzeSignalResearchResult,
)
from trading_framework.core.exceptions import ValidationError
from trading_framework.research.analytics.dimensions import AnalyticsTimestampBasis
from trading_framework.research.analytics.filters import OutcomeAnalyticsFilter
from trading_framework.research.analytics.metadata import AnalyticsResultMetadata
from trading_framework.research.analytics.quality_flags import (
    SignalResearchQualityFlag,
    SignalResearchQualityWarning,
)
from trading_framework.research.analytics.schemas import (
    empty_conditional_comparison,
    empty_distribution_summaries,
    empty_grouped_summaries,
    empty_join_diagnostics,
    empty_metric_histograms,
    empty_run_summaries,
    validate_conditional_comparison,
    validate_distribution_summaries,
    validate_grouped_summaries,
    validate_join_diagnostics,
    validate_metric_histograms,
    validate_run_summaries,
)
from trading_framework.research.outcomes.definition import OutcomeStatus
from trading_framework.strategy.reference_price import ReferencePricePolicy

SIGNAL_RESEARCH_ANALYTICS_SCHEMA_VERSION = "signal_research_analytics.v1"


class SignalResearchAnalyticsEnvelopeError(ValidationError):
    """Raised when a cached analytics envelope cannot be parsed."""


def signal_research_analytics_to_dict(result: AnalyzeSignalResearchResult) -> dict[str, Any]:
    """Convert one analytics result to a JSON-serializable mapping."""
    return {
        "schema_version": SIGNAL_RESEARCH_ANALYTICS_SCHEMA_VERSION,
        "source_run_id": result.source_run_id,
        "metadata": _metadata_to_dict(result.metadata),
        "quality_warnings": [
            _quality_warning_to_dict(warning) for warning in result.quality_warnings
        ],
        "run_summaries": result.run_summaries.to_dicts(),
        "grouped_summaries": (
            result.grouped_summaries.to_dicts() if result.grouped_summaries is not None else None
        ),
        "conditional_comparison": (
            result.conditional_comparison.to_dicts()
            if result.conditional_comparison is not None
            else None
        ),
        "distribution_summaries": result.distribution_summaries.to_dicts(),
        "join_diagnostics": result.join_diagnostics.to_dicts(),
        "metric_histograms": (
            result.metric_histograms.to_dicts() if result.metric_histograms is not None else None
        ),
    }


def signal_research_analytics_from_dict(payload: dict[str, Any]) -> AnalyzeSignalResearchResult:
    """Restore one analytics result from a cached JSON mapping."""
    schema_version = str(payload.get("schema_version"))
    if schema_version != SIGNAL_RESEARCH_ANALYTICS_SCHEMA_VERSION:
        msg = f"unsupported analytics schema version: {schema_version!r}"
        raise SignalResearchAnalyticsEnvelopeError(msg)

    run_summaries = _dataframe_from_rows(
        payload["run_summaries"],
        schema=empty_run_summaries().schema,
        label="run summaries",
        validator=validate_run_summaries,
    )
    grouped_rows = payload.get("grouped_summaries")
    grouped_summaries = None
    if grouped_rows is not None:
        grouped_summaries = _dataframe_from_rows(
            grouped_rows,
            schema=empty_grouped_summaries().schema,
            label="grouped summaries",
            validator=validate_grouped_summaries,
        )

    conditional_rows = payload.get("conditional_comparison")
    conditional_comparison = None
    if conditional_rows is not None:
        conditional_comparison = _dataframe_from_rows(
            conditional_rows,
            schema=empty_conditional_comparison().schema,
            label="conditional comparison",
            validator=validate_conditional_comparison,
        )

    distribution_summaries = _dataframe_from_rows(
        payload["distribution_summaries"],
        schema=empty_distribution_summaries().schema,
        label="distribution summaries",
        validator=validate_distribution_summaries,
    )
    join_diagnostics = _dataframe_from_rows(
        payload["join_diagnostics"],
        schema=empty_join_diagnostics().schema,
        label="join diagnostics",
        validator=validate_join_diagnostics,
    )

    histogram_rows = payload.get("metric_histograms")
    metric_histograms = None
    if histogram_rows is not None:
        metric_histograms = _dataframe_from_rows(
            histogram_rows,
            schema=empty_metric_histograms().schema,
            label="metric histograms",
            validator=validate_metric_histograms,
        )

    warnings_raw = payload.get("quality_warnings", [])
    quality_warnings = tuple(
        _quality_warning_from_dict(item) for item in warnings_raw if isinstance(item, dict)
    )

    return AnalyzeSignalResearchResult(
        source_run_id=str(payload["source_run_id"]),
        run_summaries=run_summaries,
        grouped_summaries=grouped_summaries,
        conditional_comparison=conditional_comparison,
        distribution_summaries=distribution_summaries,
        join_diagnostics=join_diagnostics,
        metadata=_metadata_from_dict(payload["metadata"]),
        quality_warnings=quality_warnings,
        metric_histograms=metric_histograms,
    )


def _dataframe_from_rows(
    rows: object,
    *,
    schema: dict[str, pl.DataType],
    label: str,
    validator: object,
) -> pl.DataFrame:
    if not isinstance(rows, list):
        msg = f"{label} must be a list"
        raise SignalResearchAnalyticsEnvelopeError(msg)
    frame = pl.DataFrame(rows, schema=schema) if rows else pl.DataFrame(schema=schema)
    validator(frame)  # type: ignore[operator]
    return frame


def _metadata_to_dict(metadata: AnalyticsResultMetadata) -> dict[str, Any]:
    return {
        "source_run_id": metadata.source_run_id,
        "research_scope": metadata.research_scope,
        "timestamp_basis": metadata.timestamp_basis.value,
        "outcome_filter": _outcome_filter_to_dict(metadata.outcome_filter),
        "evaluation_timeframe": metadata.evaluation_timeframe,
        "reference_price_policy": metadata.reference_price_policy.value,
        "market_model_ids": list(metadata.market_model_ids),
        "signal_model_ids": list(metadata.signal_model_ids),
        "min_sample_size": metadata.min_sample_size,
        "interpretation_min_sample_size": metadata.interpretation_min_sample_size,
        "source_dataset_ref": metadata.source_dataset_ref,
        "research_id": metadata.research_id,
        "research_question": metadata.research_question,
        "definition_hash": metadata.definition_hash,
        "time_of_day_timezone": metadata.time_of_day_timezone,
        "time_of_day_bucket_minutes": metadata.time_of_day_bucket_minutes,
    }


def _metadata_from_dict(payload: dict[str, Any]) -> AnalyticsResultMetadata:
    return AnalyticsResultMetadata(
        source_run_id=str(payload["source_run_id"]),
        research_scope=str(payload["research_scope"]),
        timestamp_basis=AnalyticsTimestampBasis(str(payload["timestamp_basis"])),
        outcome_filter=_outcome_filter_from_dict(payload["outcome_filter"]),
        evaluation_timeframe=str(payload["evaluation_timeframe"]),
        reference_price_policy=ReferencePricePolicy(str(payload["reference_price_policy"])),
        market_model_ids=tuple(str(value) for value in payload.get("market_model_ids", [])),
        signal_model_ids=tuple(str(value) for value in payload.get("signal_model_ids", [])),
        min_sample_size=int(payload["min_sample_size"]),
        interpretation_min_sample_size=int(payload["interpretation_min_sample_size"]),
        source_dataset_ref=(
            str(payload["source_dataset_ref"])
            if payload.get("source_dataset_ref") is not None
            else None
        ),
        research_id=str(payload["research_id"]) if payload.get("research_id") is not None else None,
        research_question=(
            str(payload["research_question"])
            if payload.get("research_question") is not None
            else None
        ),
        definition_hash=(
            str(payload["definition_hash"]) if payload.get("definition_hash") is not None else None
        ),
        time_of_day_timezone=str(payload.get("time_of_day_timezone", "America/New_York")),
        time_of_day_bucket_minutes=int(payload.get("time_of_day_bucket_minutes", 60)),
    )


def _outcome_filter_to_dict(outcome_filter: OutcomeAnalyticsFilter) -> dict[str, Any]:
    return {
        "aggregate_statuses": [status.value for status in outcome_filter.aggregate_statuses],
    }


def _outcome_filter_from_dict(payload: dict[str, Any]) -> OutcomeAnalyticsFilter:
    statuses = frozenset(
        OutcomeStatus(str(value)) for value in payload.get("aggregate_statuses", [])
    )
    return OutcomeAnalyticsFilter(aggregate_statuses=statuses)


def _quality_warning_to_dict(warning: SignalResearchQualityWarning) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "code": warning.code.value,
        "message": warning.message,
    }
    if warning.horizon_bars is not None:
        payload["horizon_bars"] = warning.horizon_bars
    return payload


def _quality_warning_from_dict(payload: dict[str, Any]) -> SignalResearchQualityWarning:
    horizon = payload.get("horizon_bars")
    return SignalResearchQualityWarning(
        code=SignalResearchQualityFlag(str(payload["code"])),
        message=str(payload["message"]),
        horizon_bars=int(horizon) if horizon is not None else None,
    )
