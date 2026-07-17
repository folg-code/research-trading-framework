"""Batch map Databento trades chunks to contract column buffers."""

from __future__ import annotations

import numpy as np
import pandas as pd  # type: ignore[import-untyped]

from trading_framework.infrastructure.importers.databento.contract_chunk_columns import (
    ContractChunkColumns,
)
from trading_framework.infrastructure.importers.databento.instrument_cache import (
    InstrumentIdentityCache,
)
from trading_framework.infrastructure.importers.databento.storage_normalizer import (
    normalize_optional_int_series,
    normalize_price_series,
    normalize_side_series,
    normalize_ts_recv_series,
    normalize_ts_series,
)


def map_trades_chunk_to_contract_columns(
    chunk: pd.DataFrame,
    *,
    identity_cache: InstrumentIdentityCache,
    contract_buffers: dict[str, ContractChunkColumns],
) -> int:
    """Append one decoded DBN chunk to per-contract column buffers."""
    if chunk.empty:
        return 0

    instrument_ids = normalize_optional_int_series(_optional_column(chunk, "instrument_id"))
    symbols = chunk["symbol"].astype(str).to_numpy()
    ts_event_ns = normalize_ts_series(chunk["ts_event"])
    ts_recv_ns = normalize_ts_recv_series(_optional_column(chunk, "ts_recv"))
    price_nanos = normalize_price_series(chunk["price"])
    size = normalize_optional_int_series(chunk["size"])
    sequence = normalize_optional_int_series(_optional_column(chunk, "sequence"))
    publisher_id = normalize_optional_int_series(_optional_column(chunk, "publisher_id"))
    side = normalize_side_series(_optional_column(chunk, "side"))

    rejected_row_count = 0
    unique_instrument_ids = set(instrument_ids.tolist())
    for instrument_id in unique_instrument_ids:
        mask = instrument_ids == instrument_id
        symbol_index = int(mask.argmax())
        symbol = str(symbols[symbol_index])
        identity = identity_cache.resolve(
            symbol=symbol,
            instrument_id=int(instrument_id) if instrument_id != 0 else None,
        )
        if identity is None:
            rejected_row_count += int(mask.sum())
            continue
        buffer = contract_buffers.setdefault(identity.contract_code, ContractChunkColumns.empty())
        buffer.extend_masked(
            mask,
            ts_event_ns=ts_event_ns,
            ts_recv_ns=ts_recv_ns,
            price_nanos=price_nanos,
            size=size,
            instrument_id=instrument_ids,
            sequence=sequence,
            publisher_id=publisher_id,
            side=side,
        )
    return rejected_row_count


def _optional_column(chunk: pd.DataFrame, name: str) -> pd.Series:
    if name in chunk.columns:
        return chunk[name]
    return pd.Series(np.full(len(chunk), np.nan), index=chunk.index)
