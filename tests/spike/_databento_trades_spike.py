"""Shared helpers for the Databento DBN trades spike (S011-T001)."""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import databento as db

from trading_framework.market.importers import compute_source_checksum_sha256

TRADES_SCHEMA = "trades"
DEFAULT_CHUNK_SIZE = 50_000


@dataclass(frozen=True, slots=True)
class DbnTradesInspection:
    """Summary of a trades DBN archive before framework import."""

    path: Path
    source_checksum_sha256: str
    nbytes: int
    databento_schema: str
    dataset: str | None
    symbols: tuple[str, ...]
    start: datetime | None
    end: datetime | None
    symbology_instrument_ids: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class MappedTradeSample:
    """Prototype MarketTrade field mapping from one DBN trades row."""

    event_at: datetime
    received_at: datetime | None
    price: float
    size: int
    side_raw: str | None
    sequence: int | None
    instrument_id_raw: int | None
    symbol: str | None


def _schema_name(store: db.DBNStore) -> str:
    schema = store.schema
    if schema is None:
        return "unknown"
    return str(schema).removeprefix("Schema.").lower()


def _as_utc_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)
    return None


def inspect_trades_dbn(path: Path) -> DbnTradesInspection:
    """Load DBN metadata without decoding the full archive."""
    store = db.DBNStore.from_file(path)
    schema_name = _schema_name(store)
    if schema_name != TRADES_SCHEMA:
        msg = f"expected databento schema {TRADES_SCHEMA!r}, got {schema_name!r}"
        raise ValueError(msg)

    symbols = tuple(store.symbols or ())
    symbology = store.symbology or {}
    instrument_ids: list[int] = []
    for entry in symbology.values():
        if not isinstance(entry, list):
            continue
        for mapping in entry:
            if not isinstance(mapping, Mapping):
                continue
            raw_id = mapping.get("instrument_id")
            if isinstance(raw_id, int):
                instrument_ids.append(raw_id)

    return DbnTradesInspection(
        path=path,
        source_checksum_sha256=compute_source_checksum_sha256(path),
        nbytes=int(store.nbytes),
        databento_schema=schema_name,
        dataset=str(store.dataset) if store.dataset is not None else None,
        symbols=symbols,
        start=_as_utc_datetime(store.start),
        end=_as_utc_datetime(store.end),
        symbology_instrument_ids=tuple(sorted(set(instrument_ids))),
    )


def _side_raw(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value)
    if text in {"", "None", "nan"}:
        return None
    return text


def map_trades_row(row: Any) -> MappedTradeSample:
    """Map one Databento trades DataFrame row to prototype MarketTrade fields."""
    event_at = _as_utc_datetime(getattr(row, "ts_event", None))
    if event_at is None:
        msg = "trades row missing ts_event"
        raise ValueError(msg)

    received_at = _as_utc_datetime(getattr(row, "ts_recv", None))
    price = float(row.price)
    size = int(row.size)
    sequence_value = getattr(row, "sequence", None)
    sequence = int(sequence_value) if sequence_value is not None else None
    instrument_id_raw = getattr(row, "instrument_id", None)
    instrument_id = int(instrument_id_raw) if instrument_id_raw is not None else None
    symbol = getattr(row, "symbol", None)
    symbol_text = str(symbol) if symbol is not None else None

    return MappedTradeSample(
        event_at=event_at,
        received_at=received_at,
        price=price,
        size=size,
        side_raw=_side_raw(getattr(row, "side", None)),
        sequence=sequence,
        instrument_id_raw=instrument_id,
        symbol=symbol_text,
    )


def iter_trades_chunks(
    path: Path,
    *,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
) -> Iterator[Any]:
    """Yield pandas DataFrame chunks from a trades DBN archive."""
    store = db.DBNStore.from_file(path)
    schema_name = _schema_name(store)
    if schema_name != TRADES_SCHEMA:
        msg = f"expected databento schema {TRADES_SCHEMA!r}, got {schema_name!r}"
        raise ValueError(msg)
    iterator = store.to_df(count=chunk_size)
    if not hasattr(iterator, "__iter__"):
        yield iterator
        return
    yield from iterator


def day_partition_counts(
    path: Path,
    *,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    max_rows: int | None = None,
) -> dict[date, int]:
    """Count rows per UTC calendar day of ts_event."""
    counts: dict[date, int] = {}
    seen = 0
    for chunk in iter_trades_chunks(path, chunk_size=chunk_size):
        for row in chunk.itertuples(index=False):
            if max_rows is not None and seen >= max_rows:
                return counts
            sample = map_trades_row(row)
            day = sample.event_at.date()
            counts[day] = counts.get(day, 0) + 1
            seen += 1
    return counts


def side_value_counts(
    path: Path,
    *,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    max_rows: int = 10_000,
) -> dict[str | None, int]:
    """Summarize raw Databento side values in the first N rows."""
    counts: dict[str | None, int] = {}
    seen = 0
    for chunk in iter_trades_chunks(path, chunk_size=chunk_size):
        for row in chunk.itertuples(index=False):
            if seen >= max_rows:
                return counts
            sample = map_trades_row(row)
            counts[sample.side_raw] = counts.get(sample.side_raw, 0) + 1
            seen += 1
    return counts
