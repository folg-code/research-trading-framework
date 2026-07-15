"""Metadata captured alongside ephemeral analytics results."""

from __future__ import annotations

from dataclasses import dataclass

from trading_framework.research.analytics.dimensions import AnalyticsTimestampBasis
from trading_framework.research.analytics.filters import OutcomeAnalyticsFilter
from trading_framework.research.datasets.signal_research import SignalResearchRunManifest
from trading_framework.strategy.reference_price import ReferencePricePolicy

CME_ES_TIME_OF_DAY_TIMEZONE = "America/New_York"
DEFAULT_TIME_OF_DAY_BUCKET_MINUTES = 60
DEFAULT_INTERPRETATION_MIN_SAMPLE_SIZE = 30


@dataclass(frozen=True, slots=True)
class AnalyticsResultMetadata:
    """Records analytical choices applied to one run interpretation."""

    source_run_id: str
    research_scope: str
    timestamp_basis: AnalyticsTimestampBasis
    outcome_filter: OutcomeAnalyticsFilter
    evaluation_timeframe: str
    reference_price_policy: ReferencePricePolicy
    market_model_ids: tuple[str, ...]
    signal_model_ids: tuple[str, ...]
    min_sample_size: int
    interpretation_min_sample_size: int
    source_dataset_ref: str | None = None
    research_id: str | None = None
    research_question: str | None = None
    definition_hash: str | None = None
    time_of_day_timezone: str = CME_ES_TIME_OF_DAY_TIMEZONE
    time_of_day_bucket_minutes: int = DEFAULT_TIME_OF_DAY_BUCKET_MINUTES


def build_analytics_result_metadata(
    *,
    manifest: SignalResearchRunManifest,
    timestamp_basis: AnalyticsTimestampBasis,
    outcome_filter: OutcomeAnalyticsFilter,
    min_sample_size: int,
    interpretation_min_sample_size: int,
) -> AnalyticsResultMetadata:
    """Build metadata from one persisted run manifest and request choices."""
    return AnalyticsResultMetadata(
        source_run_id=manifest.run_id,
        research_scope=manifest.effective_scope().value,
        timestamp_basis=timestamp_basis,
        outcome_filter=outcome_filter,
        evaluation_timeframe=manifest.evaluation_timeframe,
        reference_price_policy=manifest.reference_price_policy,
        market_model_ids=manifest.market_model_ids,
        signal_model_ids=manifest.signal_model_ids,
        min_sample_size=min_sample_size,
        interpretation_min_sample_size=interpretation_min_sample_size,
        source_dataset_ref=manifest.source_dataset_ref,
        research_id=manifest.research_id,
        research_question=manifest.research_question,
        definition_hash=manifest.definition_hash,
    )


def describe_return_semantics(metadata: AnalyticsResultMetadata) -> str:
    """Return human-readable outcome semantics for reports."""
    return (
        "Direction-adjusted forward return: favourable outcomes are positive for the "
        "signal direction (long and short supported). "
        f"Reference price policy: {metadata.reference_price_policy.value}. "
        "Outcome window spans forward evaluation bars from the bar after "
        f"{metadata.timestamp_basis.value}. "
        "MFE and MAE use intrawindow high/low versus the reference price. "
        "Hit rate is the share of complete outcomes with positive direction-adjusted "
        "forward return."
    )


def describe_horizon_label(*, horizon_bars: int, metadata: AnalyticsResultMetadata) -> str:
    """Return a human-readable horizon label including evaluation timeframe."""
    return f"{horizon_bars} evaluation bars ({metadata.evaluation_timeframe} each)"
