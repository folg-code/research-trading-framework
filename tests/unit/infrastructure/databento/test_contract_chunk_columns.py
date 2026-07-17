"""Unit tests for NumPy-backed contract chunk column buffers."""

from __future__ import annotations

import numpy as np

from trading_framework.infrastructure.importers.databento.contract_chunk_columns import (
    ContractChunkColumns,
)


def _sample_arrays(*, offset: int = 0, rows: int = 3) -> dict[str, object]:
    index = np.arange(rows, dtype=np.int64) + offset
    return {
        "ts_event_ns": index,
        "ts_recv_ns": index + 1,
        "price_nanos": (index + 2) * 1_000,
        "size": index + 3,
        "instrument_id": np.full(rows, 101, dtype=np.int64),
        "sequence": index,
        "publisher_id": np.full(rows, 1, dtype=np.int64),
        "side": np.asarray(["buy", "sell", "unknown"][:rows], dtype=object),
    }


def test_extend_masked_keeps_numpy_columns_without_python_lists() -> None:
    columns = ContractChunkColumns.empty()
    values = _sample_arrays()
    mask = np.array([True, False, True])
    columns.extend_masked(
        mask,
        ts_event_ns=values["ts_event_ns"],  # type: ignore[arg-type]
        ts_recv_ns=values["ts_recv_ns"],  # type: ignore[arg-type]
        price_nanos=values["price_nanos"],  # type: ignore[arg-type]
        size=values["size"],  # type: ignore[arg-type]
        instrument_id=values["instrument_id"],  # type: ignore[arg-type]
        sequence=values["sequence"],  # type: ignore[arg-type]
        publisher_id=values["publisher_id"],  # type: ignore[arg-type]
        side=values["side"],  # type: ignore[arg-type]
    )

    assert len(columns) == 2
    assert isinstance(columns.ts_event_ns, np.ndarray)
    assert columns.ts_event_ns.dtype == np.int64
    assert columns.ts_event_ns.tolist() == [0, 2]
    assert columns.side.tolist() == ["buy", "unknown"]


def test_take_and_merge_preserve_row_order() -> None:
    first = ContractChunkColumns.empty()
    first_values = _sample_arrays(offset=0, rows=2)
    first.extend_masked(
        np.array([True, True]),
        ts_event_ns=first_values["ts_event_ns"],  # type: ignore[arg-type]
        ts_recv_ns=first_values["ts_recv_ns"],  # type: ignore[arg-type]
        price_nanos=first_values["price_nanos"],  # type: ignore[arg-type]
        size=first_values["size"],  # type: ignore[arg-type]
        instrument_id=first_values["instrument_id"],  # type: ignore[arg-type]
        sequence=first_values["sequence"],  # type: ignore[arg-type]
        publisher_id=first_values["publisher_id"],  # type: ignore[arg-type]
        side=first_values["side"],  # type: ignore[arg-type]
    )
    second_values = _sample_arrays(offset=10, rows=2)
    second = ContractChunkColumns.from_arrays(
        ts_event_ns=second_values["ts_event_ns"],  # type: ignore[arg-type]
        ts_recv_ns=second_values["ts_recv_ns"],  # type: ignore[arg-type]
        price_nanos=second_values["price_nanos"],  # type: ignore[arg-type]
        size=second_values["size"],  # type: ignore[arg-type]
        instrument_id=second_values["instrument_id"],  # type: ignore[arg-type]
        sequence=second_values["sequence"],  # type: ignore[arg-type]
        publisher_id=second_values["publisher_id"],  # type: ignore[arg-type]
        side=second_values["side"],  # type: ignore[arg-type]
    )
    first.merge(second)
    subset = first.take([1, 3])

    assert len(first) == 4
    assert first.ts_event_ns.tolist() == [0, 1, 10, 11]
    assert subset.ts_event_ns.tolist() == [1, 11]
    assert subset.side.tolist() == ["sell", "sell"]
