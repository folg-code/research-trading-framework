"""Tests for trading session metadata enrichment on analysis paths."""

from datetime import UTC, date, datetime
from decimal import Decimal

import polars as pl
import pytest

from trading_framework.core.exceptions import ValidationError
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
from trading_framework.time.sessions import (
    ES_RTH_SESSION_ID,
    OUTSIDE_RTH_SESSION_ID,
    CmeEsRthSessionResolver,
)


class _MismatchedLengthResolver:
    def resolve(self, timestamps: pl.Series) -> pl.DataFrame:
        truncated = timestamps.head(max(timestamps.len() - 1, 0))
        return pl.DataFrame(
            {
                "timestamp": truncated,
                "trading_day": [date(2024, 6, 3)] * truncated.len(),
                "session_id": ["ES_RTH"] * truncated.len(),
                "is_rth": [True] * truncated.len(),
            }
        )


class _RecordingResolver:
    def __init__(self) -> None:
        self.call_count = 0
        self._inner = CmeEsRthSessionResolver()

    def resolve(self, timestamps: pl.Series) -> pl.DataFrame:
        self.call_count += 1
        return self._inner.resolve(timestamps)


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


def test_trading_session_metadata_rejects_empty_timestamps() -> None:
    with pytest.raises(ValidationError, match="non-empty"):
        TradingSessionMetadata.resolve((), CmeEsRthSessionResolver())


def test_trading_session_metadata_maps_rth_fixture_window() -> None:
    """Bars from 13:30 UTC on 2024-06-03 align to NY RTH open and same trading day."""
    timestamps = tuple(
        datetime(2024, 6, 3, 13, 30, tzinfo=UTC).replace(minute=30 + offset) for offset in range(5)
    )
    metadata = TradingSessionMetadata.resolve(timestamps, CmeEsRthSessionResolver())
    assert all(metadata.is_rth)
    assert all(session_id == ES_RTH_SESSION_ID for session_id in metadata.session_ids)
    assert all(trading_day == date(2024, 6, 3) for trading_day in metadata.trading_days)


def test_resolve_length_matches_timestamps_without_reading_columns() -> None:
    timestamps = tuple(
        datetime(2024, 6, 3, 13, 30, tzinfo=UTC).replace(minute=30 + offset) for offset in range(8)
    )
    metadata = TradingSessionMetadata.resolve(timestamps, CmeEsRthSessionResolver())
    assert len(metadata) == len(timestamps)


def test_resolve_rejects_resolver_output_length_mismatch() -> None:
    timestamps = (
        datetime(2024, 6, 3, 13, 29, tzinfo=UTC),
        datetime(2024, 6, 3, 13, 30, tzinfo=UTC),
    )
    with pytest.raises(ValidationError, match="resolver output length"):
        TradingSessionMetadata.resolve(timestamps, _MismatchedLengthResolver())


def test_resolve_invokes_resolver_without_materializing_tuples(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    timestamps = (
        datetime(2024, 6, 3, 13, 29, tzinfo=UTC),
        datetime(2024, 6, 3, 13, 30, tzinfo=UTC),
    )
    resolver = _RecordingResolver()
    materialized_columns: list[str] = []
    original_to_list = pl.Series.to_list

    def tracked_to_list(self: pl.Series) -> list[object]:
        if self.name in {"trading_day", "session_id", "is_rth"}:
            materialized_columns.append(self.name)
        return original_to_list(self)

    monkeypatch.setattr(pl.Series, "to_list", tracked_to_list)
    metadata = TradingSessionMetadata.resolve(timestamps, resolver)
    assert resolver.call_count == 1
    assert len(metadata) == len(timestamps)
    assert materialized_columns == []
    assert metadata.is_rth == (False, True)
    assert metadata.session_ids == (OUTSIDE_RTH_SESSION_ID, ES_RTH_SESSION_ID)
    assert metadata.trading_days == (date(2024, 6, 3), date(2024, 6, 3))


def test_from_dataframe_rejects_missing_resolver_columns() -> None:
    frame = pl.DataFrame(
        {
            "timestamp": [datetime(2024, 6, 3, 13, 30, tzinfo=UTC)],
            "trading_day": [date(2024, 6, 3)],
            "session_id": [ES_RTH_SESSION_ID],
        }
    )
    with pytest.raises(ValidationError, match="missing columns"):
        TradingSessionMetadata.from_dataframe(frame)


def test_from_dataframe_defers_python_tuple_materialization(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    timestamps = (
        datetime(2024, 6, 3, 13, 29, tzinfo=UTC),
        datetime(2024, 6, 3, 13, 30, tzinfo=UTC),
    )
    frame = CmeEsRthSessionResolver().resolve(pl.Series("timestamp", timestamps))
    materialized_columns: list[str] = []
    original_to_list = pl.Series.to_list

    def tracked_to_list(self: pl.Series) -> list[object]:
        if self.name in {"trading_day", "session_id", "is_rth"}:
            materialized_columns.append(self.name)
        return original_to_list(self)

    monkeypatch.setattr(pl.Series, "to_list", tracked_to_list)
    metadata = TradingSessionMetadata.from_dataframe(frame)
    assert len(metadata) == frame.height
    assert materialized_columns == []
    assert metadata.is_rth == (False, True)
    assert materialized_columns == ["is_rth"]
    assert metadata.session_ids[1] == ES_RTH_SESSION_ID
    assert metadata.trading_days == (date(2024, 6, 3), date(2024, 6, 3))
    assert materialized_columns == ["is_rth", "session_id", "trading_day"]
