"""Load canonical market input for one analysis execution plan."""

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from trading_framework.application.market_data.query_historical import (
    QueryHistoricalRequest,
    query_historical,
)
from trading_framework.core.profiling import optional_phase
from trading_framework.infrastructure.storage.metadata.registry import FileDatasetRegistry
from trading_framework.market.datasets import DatasetRef
from trading_framework.market.models import MarketBar
from trading_framework.market.repositories import DatasetRepository
from trading_framework.market_analysis.data.view import AnalysisDataView
from trading_framework.market_analysis.models.time_range import TimeRange


@dataclass(frozen=True, slots=True)
class LoadAnalysisDataViewRequest:
    """Request to materialize one read-only market view for a plan."""

    dataset_ref: DatasetRef
    computation_range: TimeRange


def load_analysis_data_view(
    request: LoadAnalysisDataViewRequest,
    *,
    storage_root: Path,
    registry: FileDatasetRegistry | None = None,
    repository: DatasetRepository | None = None,
    preloaded_bars: Sequence[MarketBar] | None = None,
) -> AnalysisDataView:
    """Materialize one AnalysisDataView from a published dataset version."""
    if preloaded_bars is not None:
        with optional_phase("load_market_view.from_preloaded"):
            return AnalysisDataView.from_bars(preloaded_bars)
    with optional_phase("load_market_view.query_historical"):
        bars = query_historical(
            QueryHistoricalRequest(
                dataset_ref=request.dataset_ref,
                start_at=request.computation_range.start,
                end_at=request.computation_range.end,
            ),
            storage_root=storage_root,
            registry=registry,
            repository=repository,
        )
    with optional_phase("load_market_view.build_view"):
        return AnalysisDataView.from_bars(bars)
