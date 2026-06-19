"""Dataset repository contract tests."""

from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from trading_framework.core.identifiers import Identifier
from trading_framework.core.types import Price, Volume
from trading_framework.market.datasets import DatasetId, DatasetRef
from trading_framework.market.models import MarketBar
from trading_framework.market.repositories import DatasetRepository, HistoricalBarQuery
from trading_framework.time.models.timeframe import Timeframe


class _InMemoryDatasetRepository:
    def __init__(self) -> None:
        self._bars: dict[str, list[MarketBar]] = {}

    def write_bars(self, dataset_ref: DatasetRef, bars: Sequence[MarketBar]) -> None:
        self._bars[str(dataset_ref)] = list(bars)

    def query_bars(self, query: HistoricalBarQuery) -> Sequence[MarketBar]:
        bars = self._bars.get(str(query.dataset_ref), [])
        return [bar for bar in bars if query.start_at <= bar.observed_at <= query.end_at]


def _dataset_ref() -> DatasetRef:
    return DatasetRef(
        dataset_id=DatasetId(
            instrument_id=Identifier("ES.c.0"),
            data_type="ohlcv",
            timeframe=Timeframe("1m"),
            provider="csv",
            source_id="sample-file",
        ),
        version=1,
    )


def _sample_bar(minute: int) -> MarketBar:
    observed_at = datetime(2024, 1, 1, 12, minute, tzinfo=UTC)
    return MarketBar(
        open=Price(Decimal("100")),
        high=Price(Decimal("105")),
        low=Price(Decimal("99")),
        close=Price(Decimal("103")),
        volume=Volume(1000),
        observed_at=observed_at,
        available_at=observed_at + timedelta(minutes=1),
    )


def test_dataset_repository_protocol_is_implementable() -> None:
    repository: DatasetRepository = _InMemoryDatasetRepository()
    dataset_ref = _dataset_ref()
    bars = [_sample_bar(0), _sample_bar(1)]
    repository.write_bars(dataset_ref, bars)
    result = repository.query_bars(
        HistoricalBarQuery(
            dataset_ref=dataset_ref,
            start_at=datetime(2024, 1, 1, 12, 0, tzinfo=UTC),
            end_at=datetime(2024, 1, 1, 12, 0, tzinfo=UTC),
        )
    )
    assert len(result) == 1
