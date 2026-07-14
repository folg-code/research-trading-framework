"""Decode outright contract trades from Databento DBN archives."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterator
from pathlib import Path

from trading_framework.infrastructure.importers.databento.mapper import map_databento_trades_row
from trading_framework.infrastructure.importers.databento.reader import DatabentoDBNTradeReader
from trading_framework.market.contracts.identity import parse_outright_contract_symbol
from trading_framework.market.models import MarketTrade


class DatabentoDBNContractTradeReader:
    """Decode Databento trades rows grouped by outright contract symbol."""

    def __init__(self, *, chunk_size: int | None = None) -> None:
        if chunk_size is None:
            self._reader = DatabentoDBNTradeReader()
        else:
            self._reader = DatabentoDBNTradeReader(chunk_size=chunk_size)

    def decode_contract_trades(
        self,
        path: Path,
        *,
        product: str,
    ) -> tuple[dict[str, list[MarketTrade]], int]:
        """Decode outright contract trades and count rejected spread/non-outright rows."""
        trades_by_contract: dict[str, list[MarketTrade]] = defaultdict(list)
        rejected_row_count = 0
        for chunk in self._reader.iter_raw_chunks(path):
            for row in chunk.itertuples(index=False):
                symbol = str(getattr(row, "symbol", ""))
                contract_code = parse_outright_contract_symbol(symbol, product=product)
                if contract_code is None:
                    rejected_row_count += 1
                    continue
                trades_by_contract[contract_code].append(map_databento_trades_row(row))
        return dict(trades_by_contract), rejected_row_count

    def iter_contract_trades(
        self,
        path: Path,
        *,
        product: str,
    ) -> Iterator[tuple[str, MarketTrade]]:
        """Yield ``(contract_code, MarketTrade)`` for outright ``product`` symbols."""
        trades_by_contract, _ = self.decode_contract_trades(path, product=product)
        for contract_code in sorted(trades_by_contract):
            for trade in trades_by_contract[contract_code]:
                yield contract_code, trade
