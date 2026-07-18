"""Parse canonical dataset-ref strings into storage paths (dashboard-local).

Format mirrors the trading-framework DatasetRef canonical string without importing
that package:

``instrument|data_type|timeframe|provider|source_id@version``
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

_REF_SEPARATOR = "@"
_ID_SEPARATOR = "|"


@dataclass(frozen=True, slots=True)
class DatasetLocator:
    """Resolved identity pieces for one published dataset version."""

    instrument_id: str
    data_type: str
    timeframe: str
    provider: str
    source_id: str
    version: int

    @classmethod
    def parse(cls, value: str) -> DatasetLocator:
        """Parse a canonical dataset reference string."""
        text = value.strip()
        if _REF_SEPARATOR not in text:
            msg = f"invalid dataset reference: {value!r}"
            raise ValueError(msg)
        identity, version_text = text.rsplit(_REF_SEPARATOR, maxsplit=1)
        parts = identity.split(_ID_SEPARATOR)
        if len(parts) != 5:
            msg = f"invalid dataset reference: {value!r}"
            raise ValueError(msg)
        instrument_id, data_type, timeframe, provider, source_id = parts
        try:
            version = int(version_text)
        except ValueError as exc:
            msg = f"invalid dataset reference version: {value!r}"
            raise ValueError(msg) from exc
        if version < 1:
            msg = f"dataset version must be >= 1: {value!r}"
            raise ValueError(msg)
        if not all(part.strip() for part in parts):
            msg = f"invalid dataset reference: {value!r}"
            raise ValueError(msg)
        return cls(
            instrument_id=instrument_id.strip(),
            data_type=data_type.strip().lower(),
            timeframe=timeframe.strip(),
            provider=provider.strip(),
            source_id=source_id.strip(),
            version=version,
        )

    def ohlcv_partitions_dir(self, storage_root: Path) -> Path:
        """Return hive partition root for this OHLCV dataset version."""
        return (
            storage_root
            / "market_data"
            / "normalized"
            / self.instrument_id
            / self.data_type
            / self.timeframe
            / self.provider
            / self.source_id
            / f"v{self.version}"
            / "partitions"
        )

    def ohlcv_glob(self, storage_root: Path) -> str:
        """Return DuckDB ``read_parquet`` glob for session partitions."""
        partitions = self.ohlcv_partitions_dir(storage_root)
        # Forward slashes keep DuckDB globs portable on Windows.
        return (partitions / "session_date=*" / "bars.parquet").as_posix()
