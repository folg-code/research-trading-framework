"""Configuration for multi-contract Databento trades archive imports."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from trading_framework.core.exceptions import ValidationError
from trading_framework.market.contracts.identity import validate_product_code


@dataclass(frozen=True, slots=True)
class DatabentoContractTradesArchiveImportConfig:
    """Settings for importing outright contracts from one Databento DBN archive."""

    path: Path
    product: str
    source_id: str
    schema_version: str
    normalization_version: str
    lineage: Mapping[str, str] | None = None

    def __post_init__(self) -> None:
        normalized_product = validate_product_code(self.product)
        if normalized_product != self.product:
            object.__setattr__(self, "product", normalized_product)
        normalized_source = self.source_id.strip()
        if not normalized_source:
            msg = "source_id must be non-empty"
            raise ValidationError(msg)
        if normalized_source != self.source_id:
            object.__setattr__(self, "source_id", normalized_source)
