"""Dataset identity value objects."""

from dataclasses import dataclass

from trading_framework.core.exceptions import ValidationError
from trading_framework.core.identifiers import Identifier
from trading_framework.market.models.instrument import AssetClass
from trading_framework.time.models.timeframe import Timeframe

_DATASET_REF_SEPARATOR = "@"
_DATASET_ID_SEPARATOR = "|"
_LEGACY_IDENTITY_FIELD_COUNT = 5
_IDENTITY_FIELD_COUNT_WITH_ASSET_CLASS = 6


@dataclass(frozen=True, slots=True)
class DatasetId:
    """Stable logical dataset identity.

    ``asset_class`` is optional for backward compatibility only:
    identities parsed from a legacy 5-field canonical string (written before
    the market-data directory layout simplification) carry ``None`` and
    resolve through the legacy flat storage layout. Every NEWLY constructed
    identity must set ``asset_class`` explicitly -- there is no inferred or
    defaulted classification, specifically so a CFD instrument can never
    silently fall back to ``FUTURES`` (or any other class) by omission.
    """

    instrument_id: Identifier
    data_type: str
    timeframe: Timeframe
    provider: str
    source_id: str
    asset_class: AssetClass | None = None

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
        """Return the stable canonical identity string.

        Legacy shape (``asset_class`` unset): 5 ``|``-separated fields, byte
        identical to every canonical string ever persisted before the
        directory-layout simplification -- old ``DatasetRef`` values must
        keep resolving (``parse()`` below). New identities append
        ``asset_class`` as a 6th field.
        """
        fields = [
            self.instrument_id.value,
            self.data_type,
            self.timeframe.value,
            self.provider,
            self.source_id,
        ]
        if self.asset_class is not None:
            fields.append(self.asset_class.value)
        return _DATASET_ID_SEPARATOR.join(fields)


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
        """Parse a canonical ``DatasetRef`` string.

        Accepts both the legacy 5-field identity (no ``asset_class`` --
        every reference persisted before the directory-layout
        simplification) and the current 6-field identity (``asset_class``
        appended). This is the one place old ``DatasetRef`` values must
        keep resolving; do not tighten this back to 5-only.
        """
        if _DATASET_REF_SEPARATOR not in value:
            msg = f"invalid dataset reference: {value!r}"
            raise ValidationError(msg)
        identity, version_text = value.rsplit(_DATASET_REF_SEPARATOR, maxsplit=1)
        parts = identity.split(_DATASET_ID_SEPARATOR)
        if len(parts) == _LEGACY_IDENTITY_FIELD_COUNT:
            instrument_id, data_type, timeframe_value, provider, source_id = parts
            asset_class: AssetClass | None = None
        elif len(parts) == _IDENTITY_FIELD_COUNT_WITH_ASSET_CLASS:
            instrument_id, data_type, timeframe_value, provider, source_id, asset_class_value = (
                parts
            )
            try:
                asset_class = AssetClass(asset_class_value)
            except ValueError as exc:
                msg = f"invalid dataset reference asset_class: {value!r}"
                raise ValidationError(msg) from exc
        else:
            msg = f"invalid dataset reference: {value!r}"
            raise ValidationError(msg)
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
                asset_class=asset_class,
            ),
            version=version,
        )
