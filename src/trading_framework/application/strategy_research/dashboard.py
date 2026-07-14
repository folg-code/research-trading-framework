"""Build Strategy Research dashboard view models from persisted runs."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from trading_framework.application.market_data.query_historical import (
    QueryHistoricalRequest,
    query_historical,
)
from trading_framework.market.datasets import DatasetRef
from trading_framework.market.models import MarketBar
from trading_framework.research.analytics.strategy_dashboard import (
    StrategyDashboardMetadata,
    StrategyDashboardViewModel,
    effective_equity_range,
    equity_dataframe_to_rows,
    market_bars_to_rows,
    trades_dataframe_to_rows,
)
from trading_framework.research.analytics.strategy_dashboard_metrics import (
    compute_strategy_dashboard_analytics,
)
from trading_framework.research.datasets.strategy_research import (
    StrategyResearchDatasetRepository,
    StrategyResearchRunRef,
)


@dataclass(frozen=True, slots=True)
class BuildStrategyDashboardRequest:
    """Input for building one Strategy Research dashboard view model."""

    run_ref: StrategyResearchRunRef
    storage_root: Path


def build_strategy_dashboard_view_model(
    request: BuildStrategyDashboardRequest,
    *,
    repository: StrategyResearchDatasetRepository | None = None,
) -> StrategyDashboardViewModel:
    """Load one persisted run and assemble a read-only dashboard view model."""
    repo = repository or StrategyResearchDatasetRepository(request.storage_root)
    envelope = repo.read(request.run_ref)
    manifest = envelope.manifest

    trades = trades_dataframe_to_rows(envelope.trades)
    equity = equity_dataframe_to_rows(envelope.equity)
    analytics = compute_strategy_dashboard_analytics(
        trades=envelope.trades,
        equity=envelope.equity,
        evaluation_timeframe=manifest.evaluation_timeframe,
        recent_trade_rows=trades,
    )
    effective_from, effective_to = effective_equity_range(envelope.equity)
    bars = _load_source_bars(
        source_dataset_ref=manifest.source_dataset_ref,
        storage_root=request.storage_root,
        start_at=effective_from,
        end_at=effective_to,
    )
    bar_rows = market_bars_to_rows(bars)
    metadata = StrategyDashboardMetadata(
        evaluation_timeframe=manifest.evaluation_timeframe,
        bar_count=len(bar_rows),
        effective_from_utc=effective_from,
        effective_to_utc=effective_to,
    )

    return StrategyDashboardViewModel(
        run_id=manifest.run_id,
        source_dataset_ref=manifest.source_dataset_ref,
        strategy_model_id=manifest.strategy_model_id,
        market_model_id=manifest.market_model_id,
        signal_model_id=manifest.signal_model_id,
        exit_model_id=manifest.exit_model_id,
        risk_model_id=manifest.risk_model_id,
        simulation_assumptions_fingerprint=manifest.simulation_assumptions_fingerprint,
        overview=analytics.overview,
        performance=analytics.performance,
        metric_context=analytics.metric_context,
        trades=trades,
        equity=equity,
        bars=bar_rows,
        metadata=metadata,
    )


def _load_source_bars(
    *,
    source_dataset_ref: str,
    storage_root: Path,
    start_at: datetime | None,
    end_at: datetime | None,
) -> list[MarketBar]:
    if start_at is None or end_at is None:
        return []
    dataset_ref = DatasetRef.parse(source_dataset_ref)
    return query_historical(
        QueryHistoricalRequest(
            dataset_ref=dataset_ref,
            start_at=start_at,
            end_at=end_at,
        ),
        storage_root=storage_root,
    )
