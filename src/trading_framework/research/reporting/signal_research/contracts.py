"""Finished-result contract for Signal Research HTML reporting."""

from __future__ import annotations

from typing import Protocol

import polars as pl

from trading_framework.research.analytics.metadata import AnalyticsResultMetadata
from trading_framework.research.analytics.quality_flags import SignalResearchQualityWarning


class SignalResearchReportSource(Protocol):
    """Minimal finished-result contract for presentation adapters."""

    @property
    def source_run_id(self) -> str: ...

    @property
    def run_summaries(self) -> pl.DataFrame: ...

    @property
    def grouped_summaries(self) -> pl.DataFrame | None: ...

    @property
    def conditional_comparison(self) -> pl.DataFrame | None: ...

    @property
    def distribution_summaries(self) -> pl.DataFrame: ...

    @property
    def join_diagnostics(self) -> pl.DataFrame: ...

    @property
    def metadata(self) -> AnalyticsResultMetadata: ...

    @property
    def quality_warnings(self) -> tuple[SignalResearchQualityWarning, ...]: ...

    @property
    def metric_histograms(self) -> pl.DataFrame | None: ...
