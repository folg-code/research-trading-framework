"""Tests for trading session metadata enrichment on analysis paths."""

from datetime import UTC, datetime
from decimal import Decimal

from trading_framework.core.types import Price, Volume
from trading_framework.market.models import MarketBar
from trading_framework.market_analysis import (
    AnalysisFrameAssembler,
    AnalysisFrameRequest,
    AnalysisWorkspace,
    TimeRange,
    TradingSessionMetadata,
)
from trading_framework.market_analysis.data.view import AnalysisDataView
from trading_framework.time.sessions import ES_RTH_SESSION_ID, CmeEsRthSessionResolver


def _bar(observed_at: datetime, close: float) -> MarketBar:
    price = Price(Decimal(str(close)))
    return MarketBar(
        open=price,
        high=price,
        low=price,
        close=price,
        volume=Volume(1000),
        observed_at=observed_at,
        available_at=observed_at.replace(minute=observed_at.minute + 1)
        if observed_at.minute < 59
        else observed_at.replace(hour=observed_at.hour + 1, minute=0),
    )


def test_trading_session_metadata_resolve_aligns_to_timestamps() -> None:
    timestamps = (
        datetime(2024, 6, 3, 13, 29, tzinfo=UTC),
        datetime(2024, 6, 3, 13, 30, tzinfo=UTC),
    )
    metadata = TradingSessionMetadata.resolve(timestamps, CmeEsRthSessionResolver())
    assert len(metadata) == 2
    assert metadata.is_rth == (False, True)
    assert metadata.session_ids[1] == ES_RTH_SESSION_ID


def test_frame_assembler_includes_session_metadata_from_workspace() -> None:
    bars = [
        _bar(datetime(2024, 6, 3, 13, 29, tzinfo=UTC), 100.0),
        _bar(datetime(2024, 6, 3, 13, 30, tzinfo=UTC), 101.0),
    ]
    view = AnalysisDataView.from_bars(bars)
    metadata = TradingSessionMetadata.resolve(view.timestamps, CmeEsRthSessionResolver())
    workspace = AnalysisWorkspace(view, session_metadata=metadata)
    frame = AnalysisFrameAssembler().assemble(
        workspace,
        AnalysisFrameRequest(market_fields=("close",)),
        evaluation_range=TimeRange(start=view.timestamps[0], end=view.timestamps[-1]),
    )
    assert frame.session_metadata is metadata
    assert frame.session_metadata is not None
    assert frame.session_metadata.is_rth == (False, True)


def test_workspace_without_session_metadata_yields_none_on_frame() -> None:
    bars = [_bar(datetime(2024, 6, 3, 13, 30, tzinfo=UTC), 100.0)]
    view = AnalysisDataView.from_bars(bars)
    workspace = AnalysisWorkspace(view)
    frame = AnalysisFrameAssembler().assemble(
        workspace,
        AnalysisFrameRequest(market_fields=("close",)),
        evaluation_range=TimeRange(start=view.timestamps[0], end=view.timestamps[-1]),
    )
    assert frame.session_metadata is None
