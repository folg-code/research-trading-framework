"""Inspect Databento DBN archives."""

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import databento as db

from trading_framework.market.importers import (
    ArchiveInspectionResult,
    ArchiveSourceFormat,
    compute_source_checksum_sha256,
)

_TRADES_SCHEMA = "trades"


def _schema_name(store: db.DBNStore) -> str:
    schema = store.schema
    if schema is None:
        return "unknown"
    return str(schema).removeprefix("Schema.").lower()


def _as_utc_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    if not isinstance(value, datetime):
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


class DatabentoDBNInspector:
    """Inspect a Databento DBN archive without full decode."""

    def inspect(self, path: Path) -> ArchiveInspectionResult:
        """Return archive metadata for supported Databento schemas."""
        store = db.DBNStore.from_file(path)
        schema_name = _schema_name(store)
        if schema_name != _TRADES_SCHEMA:
            msg = f"unsupported databento schema {schema_name!r}; expected {_TRADES_SCHEMA!r}"
            raise ValueError(msg)

        symbols = tuple(store.symbols or ())
        return ArchiveInspectionResult(
            path=path,
            source_format=ArchiveSourceFormat.DATABENTO_DBN,
            vendor_schema=schema_name,
            nbytes=int(store.nbytes),
            dataset=str(store.dataset) if store.dataset is not None else None,
            symbols=symbols,
            start_at=_as_utc_datetime(store.start),
            end_at=_as_utc_datetime(store.end),
            row_estimate=None,
        )

    def inspect_with_checksum(self, path: Path) -> tuple[ArchiveInspectionResult, str]:
        """Inspect and return the source checksum in one pass-friendly helper."""
        result = self.inspect(path)
        checksum = compute_source_checksum_sha256(path)
        return result, checksum
