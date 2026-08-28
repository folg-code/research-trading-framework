"""Versioned presentation contracts for the research dashboard.

These DTOs are intentionally independent of ``trading_framework.research`` so the
app (and a future dry-run datasource) can share schema without importing
workflow engines.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any

PRESENTATION_SCHEMA_VERSION = "dashboard.presentation.v1"


class WorkflowKind(StrEnum):
    """Top-level catalog workflow kinds shown in the dashboard."""

    MARKET = "market"
    SIGNAL = "signal"
    STRATEGY = "strategy"
    ROBUSTNESS = "robustness"
    LIVE_PAPER = "live_paper"
    PREDICTIVE = "predictive"


@dataclass(frozen=True, slots=True)
class RunSummary:
    """One catalog row for a research run or robustness experiment."""

    schema_version: str
    workflow: WorkflowKind
    run_id: str
    created_at_utc: datetime | None
    title: str
    storage_path: str
    source_dataset_ref: str | None = None
    evaluation_timeframe: str | None = None
    framework_version: str | None = None
    artifact_schema_version: str | None = None
    research_scope: str | None = None
    experiment_id: str | None = None


@dataclass(frozen=True, slots=True)
class RunManifest:
    """Presentation envelope: summary plus selected raw identity fields."""

    schema_version: str
    summary: RunSummary
    identity: Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class PredictiveDatasetSummary:
    """One catalog row for a Predictive Research dataset envelope."""

    schema_version: str
    dataset_id: str
    dataset_fingerprint: str
    created_at_utc: datetime | None
    source_dataset_ref: str | None
    label_kind: str | None
    horizon: str | None
    storage_path: str
    run_count: int = 0


@dataclass(frozen=True, slots=True)
class PredictiveQualityFlagView:
    """One dashboard-local quality warning for a predictive run row."""

    code: str
    message: str


@dataclass(frozen=True, slots=True)
class PredictiveRunSummary:
    """One catalog row for a Predictive Research run, grouped by dataset fingerprint."""

    schema_version: str
    run_id: str
    dataset_id: str
    dataset_fingerprint: str
    created_at_utc: datetime | None
    family: str | None
    task_type: str | None
    primary_metric_name: str | None
    primary_metric_value: float | None
    baseline_delta: float | None
    quality_flags: tuple[PredictiveQualityFlagView, ...]
    storage_path: str
    has_metrics: bool


@dataclass(frozen=True, slots=True)
class ChartWindow:
    """Bounded market-chart request (windowed OHLCV; never full history)."""

    schema_version: str
    start_at_utc: datetime
    end_at_utc: datetime
    timeframe: str
    instrument_id: str | None = None
    max_bars: int | None = None


@dataclass(frozen=True, slots=True)
class TradeView:
    """One trade row for strategy inspection overlays and tables."""

    schema_version: str
    trade_id: str
    side: str
    entry_at_utc: datetime
    exit_at_utc: datetime | None = None
    entry_price: float | None = None
    exit_price: float | None = None
    quantity: float | None = None
    pnl: float | None = None
    bars_held: int | None = None
