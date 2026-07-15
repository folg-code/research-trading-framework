"""View models for Signal Research HTML reports."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

import polars as pl

from trading_framework.core.exceptions import ValidationError
from trading_framework.research.analytics.metadata import AnalyticsResultMetadata
from trading_framework.research.analytics.quality_flags import SignalResearchQualityWarning
from trading_framework.research.reporting.signal_research.contracts import (
    SignalResearchReportSource,
)
from trading_framework.research.scope import ResearchScope


@dataclass(frozen=True, slots=True)
class SignalResearchKpiCard:
    """One headline KPI with sample-size context."""

    label: str
    value: str
    sample_note: str


@dataclass(frozen=True, slots=True)
class SignalResearchReportViewModel:
    """Presentation-ready analytics snapshot for one Signal Research run."""

    source_run_id: str
    generated_at_utc: datetime
    metadata: AnalyticsResultMetadata
    primary_horizon_bars: int
    run_summaries: pl.DataFrame
    grouped_summaries: pl.DataFrame | None
    conditional_comparison: pl.DataFrame | None
    distribution_summaries: pl.DataFrame
    join_diagnostics: pl.DataFrame
    metric_histograms: pl.DataFrame
    quality_warnings: tuple[SignalResearchQualityWarning, ...]
    kpi_cards: tuple[SignalResearchKpiCard, ...]


def build_signal_research_report_view_model(
    result: SignalResearchReportSource,
    *,
    generated_at_utc: datetime | None = None,
) -> SignalResearchReportViewModel:
    """Map a finished analytics result to a report view model."""
    if result.run_summaries.height == 0:
        msg = "run_summaries must contain at least one row"
        raise ValidationError(msg)

    primary_row = result.run_summaries.sort("horizon_bars").row(0, named=True)
    primary_horizon = int(str(primary_row["horizon_bars"]))
    histograms = result.metric_histograms
    if histograms is None:
        from trading_framework.research.analytics.schemas import empty_metric_histograms

        histograms = empty_metric_histograms()

    return SignalResearchReportViewModel(
        source_run_id=result.source_run_id,
        generated_at_utc=generated_at_utc or datetime.now(tz=UTC),
        metadata=result.metadata,
        primary_horizon_bars=primary_horizon,
        run_summaries=result.run_summaries,
        grouped_summaries=result.grouped_summaries,
        conditional_comparison=result.conditional_comparison,
        distribution_summaries=result.distribution_summaries,
        join_diagnostics=result.join_diagnostics,
        metric_histograms=histograms,
        quality_warnings=result.quality_warnings,
        kpi_cards=_build_kpi_cards(result, primary_row=primary_row),
    )


def _build_kpi_cards(
    result: SignalResearchReportSource,
    *,
    primary_row: dict[str, object],
) -> tuple[SignalResearchKpiCard, ...]:
    from trading_framework.research.reporting.signal_research.formatting import (
        format_count,
        format_hit_rate,
        format_return,
        format_share,
    )

    sample_complete = int(str(primary_row["sample_size_complete"]))
    sample_total = int(str(primary_row["sample_size_total"]))
    sample_note = f"n={format_count(sample_complete)} complete / {format_count(sample_total)} total"
    eligible = bool(primary_row["metrics_eligible"])

    def metric_value(key: str, *, hit_rate: bool = False) -> str:
        if not eligible:
            return "—"
        raw = primary_row.get(key)
        if raw is None:
            return "—"
        return format_hit_rate(float(str(raw))) if hit_rate else format_return(float(str(raw)))

    cards: list[SignalResearchKpiCard] = [
        SignalResearchKpiCard("Sample size", format_count(sample_complete), sample_note),
        SignalResearchKpiCard("Mean return", metric_value("forward_return_mean"), sample_note),
        SignalResearchKpiCard(
            "Median return",
            metric_value("forward_return_median"),
            sample_note,
        ),
        SignalResearchKpiCard(
            "Hit rate",
            metric_value("hit_rate", hit_rate=True),
            sample_note,
        ),
        SignalResearchKpiCard("Median MFE", metric_value("mfe_median"), sample_note),
        SignalResearchKpiCard("Median MAE", metric_value("mae_median"), sample_note),
    ]

    scope = ResearchScope(result.metadata.research_scope)
    if scope is ResearchScope.MARKET_AND_SIGNAL and result.conditional_comparison is not None:
        conditional = result.conditional_comparison.filter(
            pl.col("horizon_bars") == int(str(primary_row["horizon_bars"]))
        )
        if conditional.height > 0:
            row = conditional.row(0, named=True)
            true_count = int(str(row["context_true_sample_size"]))
            retention = true_count / sample_complete if sample_complete else 0.0
            retention_note = (
                f"{format_count(true_count)} conditioned / {format_count(sample_complete)} signal"
            )
            cards.append(
                SignalResearchKpiCard(
                    "Sample retention",
                    format_share(retention),
                    retention_note,
                )
            )
    return tuple(cards)
