"""Dataset identity value objects."""

from dataclasses import dataclass

from trading_framework.core.exceptions import ValidationError
from trading_framework.core.identifiers import Identifier
from trading_framework.time.models.timeframe import Timeframe

_DATASET_REF_SEPARATOR = "@"
_DATASET_ID_SEPARATOR = "|"


@dataclass(frozen=True, slots=True)
class DatasetId:
    """Stable logical dataset identity."""

    instrument_id: Identifier
    data_type: str
    timeframe: Timeframe
    provider: str
    source_id: str

    def __post_init__(self) -> None:
        normalized_data_type = self.data_type.strip().lower()
        normalized_provider = self.provider.strip()
        normalized_source_id = self.source_id.strip()
        if not normalized_data_type:
            msg = "data_type must be non-empty"
            raise ValidationError(msg)
        if not normalized_provider:
            msg = "provider must be non-empty"
            raise ValidationError(msg)
        if not normalized_source_id:
            msg = "source_id must be non-empty"
            raise ValidationError(msg)
        if normalized_data_type != self.data_type:
            object.__setattr__(self, "data_type", normalized_data_type)
        if normalized_provider != self.provider:
            object.__setattr__(self, "provider", normalized_provider)
        if normalized_source_id != self.source_id:
            object.__setattr__(self, "source_id", normalized_source_id)

    def canonical(self) -> str:
        """Return the stable canonical identity string."""
        return _DATASET_ID_SEPARATOR.join(
            [
                self.instrument_id.value,
                self.data_type,
                self.timeframe.value,
                self.provider,
                self.source_id,
            ]
        )


@dataclass(frozen=True, slots=True)
class DatasetRef:
    """Published or in-progress reference to a specific dataset version."""

    dataset_id: DatasetId
    version: int

    def __post_init__(self) -> None:
        if self.version < 1:
            msg = "dataset version must be >= 1"
            raise ValidationError(msg)

    def __str__(self) -> str:
        return f"{self.dataset_id.canonical()}{_DATASET_REF_SEPARATOR}{self.version}"

    @classmethod
    def parse(cls, value: str) -> "DatasetRef":
        """Parse a canonical ``DatasetRef`` string."""
        if _DATASET_REF_SEPARATOR not in value:
            msg = f"invalid dataset reference: {value!r}"
            raise ValidationError(msg)
        identity, version_text = value.rsplit(_DATASET_REF_SEPARATOR, maxsplit=1)
        parts = identity.split(_DATASET_ID_SEPARATOR)
        if len(parts) != 5:
            msg = f"invalid dataset reference: {value!r}"
            raise ValidationError(msg)
        instrument_id, data_type, timeframe_value, provider, source_id = parts
        try:
            version = int(version_text)
        except ValueError as exc:
            msg = f"invalid dataset reference version: {value!r}"
            raise ValidationError(msg) from exc
        return cls(
            dataset_id=DatasetId(
                instrument_id=Identifier(instrument_id),
                data_type=data_type,
                timeframe=Timeframe(timeframe_value),
                provider=provider,
                source_id=source_id,
            ),
            version=version,
        )
