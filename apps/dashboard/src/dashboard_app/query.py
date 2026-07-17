"""DuckDB-backed read queries over mounted Parquet artifacts."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import duckdb
import pyarrow as pa

from dashboard_app.contracts import PRESENTATION_SCHEMA_VERSION, ChartWindow
from dashboard_app.dataset_locator import DatasetLocator

DEFAULT_MAX_BARS = 5_000
_OHLCV_COLUMNS = ("observed_at", "open", "high", "low", "close", "volume")


@dataclass(frozen=True, slots=True)
class OhlcvBarRow:
    """One OHLCV bar returned by the query service."""

    schema_version: str
    observed_at_utc: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int


@dataclass(frozen=True, slots=True)
class OhlcvWindowResult:
    """Windowed OHLCV read result with truncation metadata."""

    bars: tuple[OhlcvBarRow, ...]
    truncated: bool
    dataset_ref: str
    partitions_dir: str


class DashboardQueryService:
    """Read-only query facade over storage_root (DuckDB + Parquet)."""

    def __init__(self, storage_root: Path, *, max_bars: int = DEFAULT_MAX_BARS) -> None:
        if max_bars < 1:
            msg = "max_bars must be >= 1"
            raise ValueError(msg)
        self._storage_root = storage_root.expanduser().resolve()
        self._max_bars = max_bars

    @property
    def storage_root(self) -> Path:
        """Resolved workspace root."""
        return self._storage_root

    def read_ohlcv_window(
        self,
        *,
        dataset_ref: str,
        window: ChartWindow,
    ) -> OhlcvWindowResult:
        """Load OHLCV bars for ``window`` from partitioned market_data Parquet.

        Never loads the full multi-year history: filters by ``observed_at`` and
        applies ``LIMIT`` (``window.max_bars`` or the service default).
        """
        if window.end_at_utc < window.start_at_utc:
            msg = "ChartWindow.end_at_utc must be >= start_at_utc"
            raise ValueError(msg)

        locator = DatasetLocator.parse(dataset_ref)
        partitions_dir = locator.ohlcv_partitions_dir(self._storage_root)
        limit = window.max_bars if window.max_bars is not None else self._max_bars
        if limit < 1:
            msg = "max_bars must be >= 1"
            raise ValueError(msg)
        # Fetch one extra row to detect truncation without a second count query.
        fetch_limit = limit + 1

        if not partitions_dir.is_dir():
            return OhlcvWindowResult(
                bars=(),
                truncated=False,
                dataset_ref=dataset_ref,
                partitions_dir=str(partitions_dir),
            )

        glob = locator.ohlcv_glob(self._storage_root)
        start = _as_naive_utc(window.start_at_utc)
        end = _as_naive_utc(window.end_at_utc)
        columns_sql = ", ".join(_quote_ident(col) for col in _OHLCV_COLUMNS)
        sql = f"""
            SELECT {columns_sql}
            FROM read_parquet(?, hive_partitioning = true)
            WHERE observed_at >= ? AND observed_at <= ?
            ORDER BY observed_at
            LIMIT ?
        """
        with duckdb.connect(database=":memory:") as conn:
            table = conn.execute(sql, [glob, start, end, fetch_limit]).to_arrow_table()

        bars = tuple(_row_from_arrow(table, index) for index in range(table.num_rows))
        truncated = len(bars) > limit
        if truncated:
            bars = bars[:limit]
        return OhlcvWindowResult(
            bars=bars,
            truncated=truncated,
            dataset_ref=dataset_ref,
            partitions_dir=str(partitions_dir),
        )

    def read_parquet_columns(
        self,
        relative_or_absolute: Path | str,
        *,
        columns: Sequence[str] | None = None,
        limit: int | None = None,
    ) -> pa.Table:
        """Read a Parquet file with optional column projection and row limit."""
        path = Path(relative_or_absolute)
        if not path.is_absolute():
            path = self._storage_root / path
        path = path.resolve()
        if not path.is_file():
            empty_schema = (
                pa.schema([(name, pa.null()) for name in columns]) if columns else pa.schema([])
            )
            return pa.table({field.name: [] for field in empty_schema}, schema=empty_schema)

        selected = ", ".join(_quote_ident(col) for col in columns) if columns else "*"
        sql = f"SELECT {selected} FROM read_parquet(?)"
        params: list[Any] = [path.as_posix()]
        if limit is not None:
            if limit < 1:
                msg = "limit must be >= 1"
                raise ValueError(msg)
            sql += " LIMIT ?"
            params.append(limit)
        with duckdb.connect(database=":memory:") as conn:
            return conn.execute(sql, params).to_arrow_table()

    def read_strategy_trades(self, run_dir: Path | str, *, limit: int | None = None) -> pa.Table:
        """Read ``trades.parquet`` from a strategy research run directory."""
        return self.read_parquet_columns(Path(run_dir) / "trades.parquet", limit=limit)

    def read_strategy_equity(self, run_dir: Path | str, *, limit: int | None = None) -> pa.Table:
        """Read ``equity.parquet`` from a strategy research run directory."""
        return self.read_parquet_columns(Path(run_dir) / "equity.parquet", limit=limit)


def _as_naive_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value
    return value.astimezone(UTC).replace(tzinfo=None)


def _quote_ident(name: str) -> str:
    if not name or any(ch in name for ch in '"\\'):
        msg = f"invalid column name: {name!r}"
        raise ValueError(msg)
    return f'"{name}"'


def _row_from_arrow(table: pa.Table, index: int) -> OhlcvBarRow:
    observed = table.column("observed_at")[index].as_py()
    if isinstance(observed, datetime) and observed.tzinfo is None:
        observed = observed.replace(tzinfo=UTC)
    elif isinstance(observed, datetime):
        observed = observed.astimezone(UTC)
    else:
        msg = f"unexpected observed_at type: {type(observed)!r}"
        raise TypeError(msg)
    return OhlcvBarRow(
        schema_version=PRESENTATION_SCHEMA_VERSION,
        observed_at_utc=observed,
        open=float(table.column("open")[index].as_py()),
        high=float(table.column("high")[index].as_py()),
        low=float(table.column("low")[index].as_py()),
        close=float(table.column("close")[index].as_py()),
        volume=int(table.column("volume")[index].as_py()),
    )
