"""Dataset metadata model."""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any, final

from trading_framework.core.exceptions import ValidationError
from trading_framework.core.identifiers import Identifier
from trading_framework.market.datasets.identity import DatasetRef
from trading_framework.market.datasets.lifecycle import DatasetLifecycleState
from trading_framework.time.models.timeframe import Timeframe
from trading_framework.time.models.utc_instant import require_utc_aware

_MAX_LINEAGE_ITEMS = 16


class ValidationStatus(StrEnum):
    """Validation outcome for a dataset version."""

    PENDING = "pending"
    PASSED = "passed"
    FAILED = "failed"


def _serialize_datetime(value: datetime) -> str:
    return require_utc_aware(value).isoformat()


def _parse_datetime(value: str) -> datetime:
    return require_utc_aware(datetime.fromisoformat(value))


@final
@dataclass(frozen=True, slots=True)
class DatasetMetadata:
    """Versioned dataset metadata for MVP market data workflows."""

    dataset_ref: DatasetRef
    instrument_id: Identifier
    timeframe: Timeframe
    provider: str
    source_id: str
    data_type: str
    start_at: datetime
    end_at: datetime
    schema_version: str
    normalization_version: str
    validation_status: ValidationStatus
    lifecycle_status: DatasetLifecycleState
    row_count: int
    checksum: str
    created_at: datetime
    published_at: datetime | None = None
    lineage: Mapping[str, str] | None = None

    def __post_init__(self) -> None:
        if self.row_count < 0:
            msg = "row_count must be non-negative"
            raise ValidationError(msg)
        if not self.schema_version.strip():
            msg = "schema_version must be non-empty"
            raise ValidationError(msg)
        if not self.normalization_version.strip():
            msg = "normalization_version must be non-empty"
            raise ValidationError(msg)
        if not self.checksum.strip():
            msg = "checksum must be non-empty"
            raise ValidationError(msg)
        if self.start_at > self.end_at:
            msg = "start_at must be <= end_at"
            raise ValidationError(msg)
        if self.lineage is not None and len(self.lineage) > _MAX_LINEAGE_ITEMS:
            msg = f"lineage must contain at most {_MAX_LINEAGE_ITEMS} items"
            raise ValidationError(msg)

    def to_dict(self) -> dict[str, Any]:
        """Serialize metadata to a JSON-compatible dictionary."""
        return {
            "dataset_ref": str(self.dataset_ref),
            "instrument_id": self.instrument_id.value,
            "timeframe": self.timeframe.value,
            "provider": self.provider,
            "source_id": self.source_id,
            "data_type": self.data_type,
            "start_at": _serialize_datetime(self.start_at),
            "end_at": _serialize_datetime(self.end_at),
            "schema_version": self.schema_version,
            "normalization_version": self.normalization_version,
            "validation_status": self.validation_status.value,
            "lifecycle_status": self.lifecycle_status.value,
            "row_count": self.row_count,
            "checksum": self.checksum,
            "created_at": _serialize_datetime(self.created_at),
            "published_at": (
                None if self.published_at is None else _serialize_datetime(self.published_at)
            ),
            "lineage": None if self.lineage is None else dict(self.lineage),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DatasetMetadata":
        """Deserialize metadata from a JSON-compatible dictionary."""
        published_at_raw = data.get("published_at")
        lineage_raw = data.get("lineage")
        return cls(
            dataset_ref=DatasetRef.parse(str(data["dataset_ref"])),
            instrument_id=Identifier(str(data["instrument_id"])),
            timeframe=Timeframe(str(data["timeframe"])),
            provider=str(data["provider"]),
            source_id=str(data["source_id"]),
            data_type=str(data["data_type"]),
            start_at=_parse_datetime(str(data["start_at"])),
            end_at=_parse_datetime(str(data["end_at"])),
            schema_version=str(data["schema_version"]),
            normalization_version=str(data["normalization_version"]),
            validation_status=ValidationStatus(str(data["validation_status"])),
            lifecycle_status=DatasetLifecycleState(str(data["lifecycle_status"])),
            row_count=int(data["row_count"]),
            checksum=str(data["checksum"]),
            created_at=_parse_datetime(str(data["created_at"])),
            published_at=(
                None if published_at_raw is None else _parse_datetime(str(published_at_raw))
            ),
            lineage=None
            if lineage_raw is None
            else {str(k): str(v) for k, v in lineage_raw.items()},
        )
