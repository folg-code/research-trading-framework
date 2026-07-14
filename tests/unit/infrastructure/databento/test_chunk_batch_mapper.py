"""Batch chunk mapper tests."""

from datetime import UTC, datetime

import pandas as pd  # type: ignore[import-untyped]

from trading_framework.infrastructure.importers.databento.chunk_batch_mapper import (
    map_trades_chunk_to_contract_columns,
)
from trading_framework.infrastructure.importers.databento.contract_chunk_columns import (
    ContractChunkColumns,
)
from trading_framework.infrastructure.importers.databento.instrument_cache import (
    InstrumentIdentityCache,
)
from trading_framework.market.contracts.storage_codec import utc_ns_from_datetime


def test_map_trades_chunk_groups_outright_contracts() -> None:
    event_ns = utc_ns_from_datetime(datetime(2025, 7, 13, 22, 0, 1, tzinfo=UTC))
    recv_ns = utc_ns_from_datetime(datetime(2025, 7, 13, 22, 0, 1, 1000, tzinfo=UTC))
    chunk = pd.DataFrame(
        [
            {
                "ts_event": event_ns,
                "ts_recv": recv_ns,
                "price": 22_860_750_000_000,
                "size": 119,
                "side": "B",
                "sequence": 1,
                "symbol": "NQU5",
                "instrument_id": 101,
                "publisher_id": 1,
            },
            {
                "ts_event": event_ns + 1,
                "ts_recv": recv_ns + 1,
                "price": 22_860_750_000_000,
                "size": 10,
                "side": "A",
                "sequence": 2,
                "symbol": "NQ-spread",
                "instrument_id": 202,
                "publisher_id": 1,
            },
        ]
    )
    buffers: dict[str, ContractChunkColumns] = {}
    rejected = map_trades_chunk_to_contract_columns(
        chunk,
        identity_cache=InstrumentIdentityCache(product="NQ"),
        contract_buffers=buffers,
    )

    assert rejected == 1
    assert set(buffers) == {"NQU5"}
    columns = buffers["NQU5"]
    assert len(columns) == 1
    assert columns.ts_event_ns == [event_ns]
    assert columns.ts_recv_ns == [recv_ns]
    assert columns.price_nanos == [22_860_750_000_000]
    assert columns.instrument_id == [101]
    assert columns.side == ["buy"]
