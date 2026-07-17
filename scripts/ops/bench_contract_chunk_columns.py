"""Synthetic microbench for contract import column-buffer hot path.

Times ``extend_masked``, ``take``, and Arrow table build without Databento archives.
Useful for Sprint 027 Wave A/C notes; not a CI gate.

Example::

    uv run python scripts/ops/bench_contract_chunk_columns.py
    uv run python scripts/ops/bench_contract_chunk_columns.py --rows 500000 --chunks 20
"""

from __future__ import annotations

import argparse
import time
from datetime import date

import numpy as np

from trading_framework.infrastructure.importers.databento.contract_chunk_columns import (
    ContractChunkColumns,
)
from trading_framework.infrastructure.storage.parquet.contract_trade_writer import (
    contract_trade_columns_to_table,
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Microbench NumPy contract chunk column buffers (no DBN I/O).",
    )
    parser.add_argument("--rows", type=int, default=200_000, help="Rows per synthetic chunk")
    parser.add_argument("--chunks", type=int, default=10, help="Number of chunks to append")
    parser.add_argument(
        "--take-fraction",
        type=float,
        default=0.25,
        help="Fraction of rows selected by take() after append",
    )
    return parser


def _synthetic_chunk(rows: int, *, seed: int) -> dict[str, np.ndarray]:
    rng = np.random.default_rng(seed)
    ts_event_ns = np.arange(rows, dtype=np.int64) * 1_000_000_000 + seed
    return {
        "ts_event_ns": ts_event_ns,
        "ts_recv_ns": ts_event_ns + 1_000,
        "price_nanos": rng.integers(20_000_000_000_000, 25_000_000_000_000, size=rows),
        "size": rng.integers(1, 50, size=rows, dtype=np.int64),
        "instrument_id": np.full(rows, 101, dtype=np.int64),
        "sequence": np.arange(rows, dtype=np.int64),
        "publisher_id": np.ones(rows, dtype=np.int64),
        "side": np.asarray(["buy", "sell"], dtype=object)[rng.integers(0, 2, size=rows)],
    }


def main(argv: list[str] | None = None) -> int:
    """Run the synthetic column-buffer microbench and print phase timings."""
    args = _build_parser().parse_args(argv)
    if args.rows < 1 or args.chunks < 1:
        print("rows and chunks must be >= 1")
        return 1
    if not 0.0 < args.take_fraction <= 1.0:
        print("take-fraction must be in (0, 1]")
        return 1

    columns = ContractChunkColumns.empty()
    extend_started = time.perf_counter()
    for chunk_index in range(args.chunks):
        chunk = _synthetic_chunk(args.rows, seed=chunk_index)
        mask = np.ones(args.rows, dtype=bool)
        columns.extend_masked(
            mask,
            ts_event_ns=chunk["ts_event_ns"],
            ts_recv_ns=chunk["ts_recv_ns"],
            price_nanos=chunk["price_nanos"],
            size=chunk["size"],
            instrument_id=chunk["instrument_id"],
            sequence=chunk["sequence"],
            publisher_id=chunk["publisher_id"],
            side=chunk["side"],
        )
    extend_seconds = time.perf_counter() - extend_started

    take_count = max(1, int(len(columns) * args.take_fraction))
    indices = np.arange(0, len(columns), max(1, len(columns) // take_count), dtype=np.int64)[
        :take_count
    ]
    take_started = time.perf_counter()
    subset = columns.take(indices)
    take_seconds = time.perf_counter() - take_started

    table_started = time.perf_counter()
    table = contract_trade_columns_to_table(
        subset,
        product="NQ",
        contract_code="NQZ5",
        session_date=date(2025, 7, 14),
        source_file="bench",
    )
    table_seconds = time.perf_counter() - table_started

    total_rows = len(columns)
    print(
        "bench_contract_chunk_columns: "
        f"chunks={args.chunks} rows_per_chunk={args.rows} total_rows={total_rows} "
        f"take_rows={len(subset)} table_rows={table.num_rows}"
    )
    print(f"extend_masked_s={extend_seconds:.4f}")
    print(f"take_s={take_seconds:.4f}")
    print(f"columns_to_table_s={table_seconds:.4f}")
    print(f"total_s={extend_seconds + take_seconds + table_seconds:.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
