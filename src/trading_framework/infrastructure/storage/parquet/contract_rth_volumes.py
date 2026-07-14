"""Aggregate RTH session volumes from contract trade Arrow tables."""

from __future__ import annotations

from collections import defaultdict
from datetime import date

import polars as pl
import pyarrow as pa

from trading_framework.time.sessions import CmeEsRthSessionResolver


def rth_session_volume_from_trade_table(
    table: pa.Table,
    *,
    session_date: date,
    resolver: CmeEsRthSessionResolver | None = None,
) -> int:
    """Sum RTH trade size for one session partition table."""
    if table.num_rows == 0:
        return 0

    session_resolver = resolver or CmeEsRthSessionResolver()
    frame = pl.from_arrow(table)
    if not isinstance(frame, pl.DataFrame) or frame.is_empty():
        return 0

    timestamps = pl.from_epoch(
        frame.get_column("ts_event_ns"), time_unit="ns"
    ).dt.replace_time_zone("UTC")
    resolved = session_resolver.resolve(timestamps)
    total = (
        frame.with_columns(is_rth=resolved.get_column("is_rth"))
        .filter(pl.col("is_rth"))
        .select(pl.col("size").sum())
        .item()
    )
    if total is None:
        return 0
    return int(total)


def aggregate_rth_session_volumes_from_partition_tables(
    *,
    tables_by_contract: dict[str, list[tuple[date, pa.Table]]],
    resolver: CmeEsRthSessionResolver | None = None,
) -> dict[date, dict[str, int]]:
    """Sum RTH trade size by session date and contract from partition tables."""
    session_resolver = resolver or CmeEsRthSessionResolver()
    volumes: dict[date, dict[str, int]] = defaultdict(dict)

    for contract_code, session_tables in tables_by_contract.items():
        for session_date, table in session_tables:
            volume = rth_session_volume_from_trade_table(
                table,
                session_date=session_date,
                resolver=session_resolver,
            )
            if volume > 0:
                volumes[session_date][contract_code] = volume

    return {
        session_date: dict(contract_volumes)
        for session_date, contract_volumes in volumes.items()
        if contract_volumes
    }
