"""Shared helpers for the Databento DBN OHLCV spike (S012-T001)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import databento as db

from trading_framework.market.importers import compute_source_checksum_sha256

OHLCV_1M_SCHEMA = "ohlcv-1m"
DEFAULT_CHUNK_SIZE = 50_000


@dataclass(frozen=True, slots=True)
class DbnOhlcvInspection:
    """Summary of an OHLCV DBN archive before framework import."""

    path: Path
    source_checksum_sha256: str
    nbytes: int
    databento_schema: str
    dataset: str | None
    symbols: tuple[str, ...]
    start: datetime | None
    end: datetime | None


@dataclass(frozen=True, slots=True)
class MappedBarSample:
    """Prototype MarketBar field mapping from one OHLCV DBN row."""

    observed_at: datetime
    available_at: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int
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


def inspect_ohlcv_dbn(path: Path) -> DbnOhlcvInspection:
    """Load DBN metadata without decoding the full archive."""
    store = db.DBNStore.from_file(path)
    schema_name = _schema_name(store)
    if schema_name != OHLCV_1M_SCHEMA:
        msg = f"expected databento schema {OHLCV_1M_SCHEMA!r}, got {schema_name!r}"
        raise ValueError(msg)

    return DbnOhlcvInspection(
        path=path,
        source_checksum_sha256=compute_source_checksum_sha256(path),
        nbytes=int(store.nbytes),
        databento_schema=schema_name,
        dataset=str(store.dataset) if store.dataset is not None else None,
        symbols=tuple(store.symbols or ()),
        start=_as_utc_datetime(store.start),
        end=_as_utc_datetime(store.end),
    )


def map_ohlcv_row(row: Any) -> MappedBarSample:
    """Map one Databento OHLCV DataFrame row to prototype bar fields."""
    observed_at = _as_utc_datetime(getattr(row, "ts_event", None))
    if observed_at is None:
        msg = "ohlcv row missing ts_event"
        raise ValueError(msg)

    symbol = getattr(row, "symbol", None)
    symbol_text = str(symbol) if symbol is not None else None

    return MappedBarSample(
        observed_at=observed_at,
        available_at=observed_at + timedelta(minutes=1),
        open=float(row.open),
        high=float(row.high),
        low=float(row.low),
        close=float(row.close),
        volume=int(row.volume),
        symbol=symbol_text,
    )


def sample_ohlcv_rows(path: Path, *, max_rows: int = 5) -> list[MappedBarSample]:
    """Decode up to ``max_rows`` OHLCV rows for spike validation."""
    store = db.DBNStore.from_file(path)
    schema_name = _schema_name(store)
    if schema_name != OHLCV_1M_SCHEMA:
        msg = f"expected databento schema {OHLCV_1M_SCHEMA!r}, got {schema_name!r}"
        raise ValueError(msg)

    frame = store.to_df(count=max_rows)
    if hasattr(frame, "__iter__") and not hasattr(frame, "itertuples"):
        frame = next(iter(frame))

    samples: list[MappedBarSample] = []
    for row in frame.itertuples(index=False):
        samples.append(map_ohlcv_row(row))
        if len(samples) >= max_rows:
            break
    return samples
