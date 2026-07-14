"""Configuration for Databento OHLCV archive imports."""

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from trading_framework.market.datasets import DatasetId
from trading_framework.market.importers.trades_config import SymbolMapping


@dataclass(frozen=True, slots=True)
class DatabentoOhlcvArchiveImportConfig:
    """Settings for importing a Databento DBN OHLCV archive."""

    path: Path
    dataset_id: DatasetId
    symbol_mapping: SymbolMapping
    schema_version: str
    normalization_version: str
    lineage: Mapping[str, str] | None = None
