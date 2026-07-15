"""Configurable quality diagnostic flags for Signal Research analytics."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

import polars as pl

from trading_framework.research.analytics.conditional import ConditionalComparisonStatus
from trading_framework.research.analytics.dimensions import GroupDimension
from trading_framework.research.analytics.filters import OutcomeAnalyticsFilter
from trading_framework.research.scope import ResearchScope
from trading_framework.research.signal_research.definition import SignalResearchQualityRules

_SAMPLE_RETENTION_WARNING_THRESHOLD = 0.50
_OUTLIER_TRIM_FRACTION = 0.10
_MIN_DIRECTION_SAMPLES = 10
_MIN_OUTLIER_SAMPLE = 10


class SignalResearchQualityFlag(StrEnum):
    """Diagnostic warning codes — not validation verdicts."""

    LOW_SAMPLE_SIZE = "LOW_SAMPLE_SIZE"
    HIGH_PERIOD_CONCENTRATION = "HIGH_PERIOD_CONCENTRATION"
    UNSTABLE_DIRECTION = "UNSTABLE_DIRECTION"
    WEAK_BASELINE_IMPROVEMENT = "WEAK_BASELINE_IMPROVEMENT"
    HIGH_SAMPLE_LOSS = "HIGH_SAMPLE_LOSS"
    OUTLIER_DEPENDENT = "OUTLIER_DEPENDENT"
    INCOMPLETE_OUTCOMES = "INCOMPLETE_OUTCOMES"


@dataclass(frozen=True, slots=True)
class SignalResearchQualityWarning:
    """One read-only quality diagnostic for a run or horizon."""

    code: SignalResearchQualityFlag
    message: str
    horizon_bars: int | None = None


def compute_signal_research_quality_warnings(
    *,
    run_summaries: pl.DataFrame,
    grouped_summaries: pl.DataFrame | None,
    conditional_comparison: pl.DataFrame | None,
    frame: pl.DataFrame,
    research_scope: ResearchScope,
    rules: SignalResearchQualityRules | None = None,
    outcome_filter: OutcomeAnalyticsFilter | None = None,
) -> tuple[SignalResearchQualityWarning, ...]:
    """Evaluate configured rules and return ordered diagnostic warnings."""
    quality_rules = rules or SignalResearchQualityRules()
    aggregate_filter = outcome_filter or OutcomeAnalyticsFilter.complete_only()
    warnings: list[SignalResearchQualityWarning] = []

    if run_summaries.height == 0:
        return ()

    for row in run_summaries.to_dicts():
        horizon = int(row["horizon_bars"])
        warnings.extend(
            _warnings_for_horizon_summary(
                row,
                horizon_bars=horizon,
                rules=quality_rules,
            )
        )
        warnings.extend(
            _warnings_for_period_concentration(
                grouped_summaries,
                horizon_bars=horizon,
                rules=quality_rules,
            )
        )
        warnings.extend(
            _warnings_for_direction_stability(
                frame,
                horizon_bars=horizon,
                rules=quality_rules,
                outcome_filter=aggregate_filter,
            )
        )
        warnings.extend(
            _warnings_for_outlier_dependence(
                frame,
                horizon_bars=horizon,
                outcome_filter=aggregate_filter,
            )
        )

    warnings.extend(
        _warnings_for_conditional_comparison(
            conditional_comparison,
            research_scope=research_scope,
            rules=quality_rules,
        )
    )
    return tuple(_deduplicate_warnings(warnings))


def _warnings_for_horizon_summary(
    row: dict[str, object],
    *,
    horizon_bars: int,
    rules: SignalResearchQualityRules,
) -> list[SignalResearchQualityWarning]:
    warnings: list[SignalResearchQualityWarning] = []
    sample_complete = int(str(row["sample_size_complete"]))
    sample_total = int(str(row["sample_size_total"]))
    sample_incomplete = int(str(row["sample_size_incomplete"]))

    if sample_complete < rules.minimum_sample_size:
        warnings.append(
            SignalResearchQualityWarning(
                code=SignalResearchQualityFlag.LOW_SAMPLE_SIZE,
                horizon_bars=horizon_bars,
                message=(
                    f"Complete sample size {sample_complete} is below the configured "
                    f"minimum of {rules.minimum_sample_size}."
                ),
            )
        )

    if sample_total > 0:
        incomplete_share = sample_incomplete / sample_total
        if incomplete_share > rules.maximum_incomplete_outcome_share:
            warnings.append(
                SignalResearchQualityWarning(
                    code=SignalResearchQualityFlag.INCOMPLETE_OUTCOMES,
                    horizon_bars=horizon_bars,
                    message=(
                        f"Incomplete outcomes are {incomplete_share:.1%} of rows "
                        f"(maximum allowed {rules.maximum_incomplete_outcome_share:.1%})."
                    ),
                )
            )
    return warnings


def _warnings_for_period_concentration(
    grouped_summaries: pl.DataFrame | None,
    *,
    horizon_bars: int,
    rules: SignalResearchQualityRules,
) -> list[SignalResearchQualityWarning]:
    if grouped_summaries is None or grouped_summaries.height == 0:
        return []

    month_rows = grouped_summaries.filter(
        (pl.col("horizon_bars") == horizon_bars)
        & (pl.col("group_dimension") == GroupDimension.CALENDAR_MONTH.value)
        & pl.col("metrics_eligible")
    )
    if month_rows.height == 0:
        return []

    warnings: list[SignalResearchQualityWarning] = []
    samples = month_rows["sample_size_complete"].to_list()
    total = sum(samples)
    if total <= 0:
        return warnings

    max_share = max(sample / total for sample in samples)
    if max_share > rules.maximum_single_period_contribution:
        warnings.append(
            SignalResearchQualityWarning(
                code=SignalResearchQualityFlag.HIGH_PERIOD_CONCENTRATION,
                horizon_bars=horizon_bars,
                message=(
                    f"Largest calendar month contributes {max_share:.1%} of complete "
                    f"observations (maximum allowed "
                    f"{rules.maximum_single_period_contribution:.1%})."
                ),
            )
        )

    positive_periods = month_rows.filter(pl.col("forward_return_mean") > 0).height
    positive_share = positive_periods / month_rows.height
    if positive_share < rules.minimum_positive_period_share:
        warnings.append(
            SignalResearchQualityWarning(
                code=SignalResearchQualityFlag.UNSTABLE_DIRECTION,
                horizon_bars=horizon_bars,
                message=(
                    f"Only {positive_share:.1%} of eligible months show positive mean "
                    f"return (minimum desired "
                    f"{rules.minimum_positive_period_share:.1%})."
                ),
            )
        )
    return warnings


def _warnings_for_direction_stability(
    frame: pl.DataFrame,
    *,
    horizon_bars: int,
    rules: SignalResearchQualityRules,
    outcome_filter: OutcomeAnalyticsFilter,
) -> list[SignalResearchQualityWarning]:
    if "direction" not in frame.columns:
        return []

    complete = outcome_filter.filter_for_aggregates(
        frame.filter(pl.col("horizon_bars") == horizon_bars)
    )
    if complete.height == 0:
        return []

    grouped = (
        complete.group_by("direction")
        .agg(
            pl.len().alias("sample_size"),
            pl.col("forward_return").mean().alias("mean_return"),
        )
        .filter(pl.col("sample_size") >= rules.minimum_sample_size)
    )
    if grouped.height < 2:
        return []

    means = grouped["mean_return"].to_list()
    if any(value > 0 for value in means) and any(value < 0 for value in means):
        return [
            SignalResearchQualityWarning(
                code=SignalResearchQualityFlag.UNSTABLE_DIRECTION,
                horizon_bars=horizon_bars,
                message=(
                    "Signal directions show opposing mean forward returns on eligible "
                    "samples — interpret direction-specific behaviour carefully."
                ),
            )
        ]
    return []


def _warnings_for_outlier_dependence(
    frame: pl.DataFrame,
    *,
    horizon_bars: int,
    outcome_filter: OutcomeAnalyticsFilter,
) -> list[SignalResearchQualityWarning]:
    complete = outcome_filter.filter_for_aggregates(
        frame.filter(pl.col("horizon_bars") == horizon_bars)
    )
    if complete.height < _MIN_OUTLIER_SAMPLE:
        return []

    returns = complete.sort(pl.col("forward_return").abs(), descending=True)
    trim_count = max(1, int(complete.height * _OUTLIER_TRIM_FRACTION))
    trimmed = returns.slice(trim_count, complete.height - trim_count)
    if trimmed.height < _MIN_DIRECTION_SAMPLES:
        return []

    full_mean_value = returns["forward_return"].mean()
    trimmed_mean_value = trimmed["forward_return"].mean()
    if full_mean_value is None or trimmed_mean_value is None:
        return []
    if not isinstance(full_mean_value, (int, float)) or not isinstance(
        trimmed_mean_value, (int, float)
    ):
        return []
    full_mean = float(full_mean_value)
    trimmed_mean = float(trimmed_mean_value)
    if full_mean > 0 and trimmed_mean <= 0:
        return [
            SignalResearchQualityWarning(
                code=SignalResearchQualityFlag.OUTLIER_DEPENDENT,
                horizon_bars=horizon_bars,
                message=(
                    "Mean forward return turns non-positive after removing the largest "
                    f"{_OUTLIER_TRIM_FRACTION:.0%} absolute outcomes."
                ),
            )
        ]
    return []


def _warnings_for_conditional_comparison(
    conditional_comparison: pl.DataFrame | None,
    *,
    research_scope: ResearchScope,
    rules: SignalResearchQualityRules,
) -> list[SignalResearchQualityWarning]:
    if research_scope is not ResearchScope.MARKET_AND_SIGNAL:
        return []
    if conditional_comparison is None or conditional_comparison.height == 0:
        return []

    warnings: list[SignalResearchQualityWarning] = []
    for row in conditional_comparison.to_dicts():
        horizon = int(row["horizon_bars"])
        status = str(row["comparison_status"])
        true_count = int(row["context_true_sample_size"])
        false_count = int(row["context_false_sample_size"])
        total = true_count + false_count
        if total > 0:
            retention = true_count / total
            if retention < _SAMPLE_RETENTION_WARNING_THRESHOLD:
                warnings.append(
                    SignalResearchQualityWarning(
                        code=SignalResearchQualityFlag.HIGH_SAMPLE_LOSS,
                        horizon_bars=horizon,
                        message=(
                            f"Only {retention:.1%} of comparable complete outcomes remain "
                            f"when Market Model context is true "
                            f"(threshold {_SAMPLE_RETENTION_WARNING_THRESHOLD:.0%})."
                        ),
                    )
                )

        if status != ConditionalComparisonStatus.AVAILABLE.value:
            continue

        mean_delta = row["forward_return_mean_delta"]
        hit_delta = row["hit_rate_delta"]
        if (
            mean_delta is not None
            and hit_delta is not None
            and float(mean_delta) <= 0
            and float(hit_delta) <= 0
        ):
            warnings.append(
                SignalResearchQualityWarning(
                    code=SignalResearchQualityFlag.WEAK_BASELINE_IMPROVEMENT,
                    horizon_bars=horizon,
                    message=(
                        "Conditioned signal does not improve mean return or hit rate "
                        "versus the explicit false-context arm."
                    ),
                )
            )
    return warnings


def _deduplicate_warnings(
    warnings: list[SignalResearchQualityWarning],
) -> list[SignalResearchQualityWarning]:
    seen: set[tuple[str, int | None, str]] = set()
    unique: list[SignalResearchQualityWarning] = []
    for warning in warnings:
        key = (warning.code.value, warning.horizon_bars, warning.message)
        if key in seen:
            continue
        seen.add(key)
        unique.append(warning)
    return unique
