"""Roll schedule volume aggregation from contract trade records."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping
from datetime import date

import polars as pl

from trading_framework.market.contracts.trade_record import ContractTradeRecord
from trading_framework.time.sessions import CmeEsRthSessionResolver


def aggregate_rth_session_volumes(
    records_by_contract: Mapping[str, Iterable[ContractTradeRecord]],
    *,
    resolver: CmeEsRthSessionResolver | None = None,
) -> dict[date, dict[str, int]]:
    """Sum RTH trade size by session date and contract code."""
    session_resolver = resolver or CmeEsRthSessionResolver()
    volumes: dict[date, dict[str, int]] = defaultdict(lambda: defaultdict(int))

    for contract_code, records in records_by_contract.items():
        record_list = list(records)
        if not record_list:
            continue
        resolved = session_resolver.resolve(
            pl.Series([record.event_at() for record in record_list])
        )
        is_rth_flags = resolved.get_column("is_rth").to_list()
        for record, is_rth in zip(record_list, is_rth_flags, strict=True):
            if not is_rth:
                continue
            volumes[record.session_date][contract_code] += record.size

    return {
        session: dict(contract_volumes)
        for session, contract_volumes in volumes.items()
        if contract_volumes
    }
