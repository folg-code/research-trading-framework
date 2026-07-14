"""Synthetic Databento DBN trades rows and mock store helpers."""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from types import SimpleNamespace

import pandas as pd  # type: ignore[import-untyped]


@dataclass(frozen=True, slots=True)
class SyntheticTradeRowSpec:
    """One synthetic Databento trades row."""

    second: int
    minute: int = 0
    symbol: str = "NQ.FUT"
    side: str = "B"
    price: float = 22860.75
    size: int = 119
    sequence: int | None = None
    trade_id: str | None = None


def synthetic_trades_rows(
    specs: Sequence[SyntheticTradeRowSpec] | None = None,
) -> list[SimpleNamespace]:
    """Build Databento-like trades rows for mapper and reader tests."""
    rows = specs or [
        SyntheticTradeRowSpec(second=0),
        SyntheticTradeRowSpec(second=1, side="A"),
        SyntheticTradeRowSpec(second=2, symbol="ES.FUT"),
    ]
    return [
        SimpleNamespace(
            ts_event=datetime(2025, 7, 13, 22, spec.minute, spec.second, tzinfo=UTC),
            ts_recv=datetime(2025, 7, 13, 22, spec.minute, spec.second, 1000, tzinfo=UTC),
            price=spec.price,
            size=spec.size,
            side=spec.side,
            sequence=spec.sequence if spec.sequence is not None else spec.second,
            trade_id=spec.trade_id if spec.trade_id is not None else f"t-{spec.second}",
            symbol=spec.symbol,
        )
        for spec in rows
    ]


def synthetic_trades_dataframe(
    specs: Sequence[SyntheticTradeRowSpec] | None = None,
) -> pd.DataFrame:
    """Build a pandas DataFrame chunk matching Databento trades decode output."""
    rows = synthetic_trades_rows(specs)
    return pd.DataFrame(
        [
            {
                "ts_event": row.ts_event,
                "ts_recv": row.ts_recv,
                "price": row.price,
                "size": row.size,
                "side": row.side,
                "sequence": row.sequence,
                "trade_id": row.trade_id,
                "symbol": row.symbol,
            }
            for row in rows
        ]
    )


class MockDBNStore:
    """Minimal DBNStore stand-in for Tier 1 adapter tests."""

    def __init__(
        self,
        *,
        chunks: Sequence[pd.DataFrame],
        schema: str = "trades",
        symbols: Sequence[str] = ("NQ.FUT", "ES.FUT"),
        nbytes: int = 128,
        dataset: str = "GLBX.MDP3",
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> None:
        self.schema = schema
        self.symbols = list(symbols)
        self.nbytes = nbytes
        self.dataset = dataset
        self.start = start or datetime(2025, 7, 13, 22, 0, 0, tzinfo=UTC)
        self.end = end or datetime(2025, 7, 13, 22, 0, 2, tzinfo=UTC)
        self._chunks = list(chunks)

    def to_df(self, count: int = 50_000) -> Iterator[pd.DataFrame]:
        del count
        yield from self._chunks


def build_mock_dbn_store(
    *,
    specs: Sequence[SyntheticTradeRowSpec] | None = None,
    chunk_size: int | None = None,
) -> MockDBNStore:
    """Return a mock store with one or more synthetic trades chunks."""
    frame = synthetic_trades_dataframe(specs)
    if chunk_size is None or chunk_size >= len(frame):
        return MockDBNStore(chunks=[frame])
    chunks = [frame.iloc[index : index + chunk_size] for index in range(0, len(frame), chunk_size)]
    return MockDBNStore(chunks=chunks)
