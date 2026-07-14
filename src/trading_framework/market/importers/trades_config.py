"""Configuration for Databento trades archive imports."""

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from trading_framework.core.identifiers import Identifier
from trading_framework.market.datasets import DatasetId


@dataclass(frozen=True, slots=True)
class SymbolMapping:
    """Map one provider symbol to a framework instrument identity."""

    provider_symbol: str
    instrument_id: Identifier


@dataclass(frozen=True, slots=True)
class DatabentoTradesArchiveImportConfig:
    """Settings for importing a Databento DBN trades archive."""

    path: Path
    dataset_id: DatasetId
    symbol_mapping: SymbolMapping
    schema_version: str
    normalization_version: str
    lineage: Mapping[str, str] | None = None
