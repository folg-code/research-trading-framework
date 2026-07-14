"""Chunked Databento DBN trades reader."""

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import databento as db

from trading_framework.infrastructure.importers.databento.mapper import map_databento_trades_row
from trading_framework.market.models import MarketTrade

_TRADES_SCHEMA = "trades"
DEFAULT_CHUNK_SIZE = 50_000


def _schema_name(store: db.DBNStore) -> str:
    schema = store.schema
    if schema is None:
        return "unknown"
    return str(schema).removeprefix("Schema.").lower()


class DatabentoDBNTradeReader:
    """Decode Databento DBN trades archives in bounded chunks."""

    def __init__(self, *, chunk_size: int = DEFAULT_CHUNK_SIZE) -> None:
        self._chunk_size = chunk_size

    def iter_raw_chunks(self, path: Path) -> Iterator[Any]:
        """Yield pandas DataFrame chunks from a trades DBN archive."""
        store = db.DBNStore.from_file(path)
        schema_name = _schema_name(store)
        if schema_name != _TRADES_SCHEMA:
            msg = f"unsupported databento schema {schema_name!r}; expected {_TRADES_SCHEMA!r}"
            raise ValueError(msg)
        iterator = store.to_df(count=self._chunk_size)
        if not hasattr(iterator, "__iter__"):
            yield iterator
            return
        yield from iterator

    def iter_trades(
        self,
        path: Path,
        *,
        provider_symbol: str | None = None,
    ) -> Iterator[MarketTrade]:
        """Yield canonical market trades from a trades DBN archive."""
        for chunk in self.iter_raw_chunks(path):
            for row in chunk.itertuples(index=False):
                if provider_symbol is not None:
                    symbol = getattr(row, "symbol", None)
                    if symbol is not None and str(symbol) != provider_symbol:
                        continue
                yield map_databento_trades_row(row)
