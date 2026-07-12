"""Strategy domain package."""

from trading_framework.strategy.reference_price import ReferencePricePolicy, resolve_reference_price
from trading_framework.strategy.signal_occurrence import (
    OccurrenceMaterializationContext,
    derive_occurrence_id,
    empty_signal_occurrences_dataframe,
    materialize_signal_occurrences,
)

__all__ = [
    "OccurrenceMaterializationContext",
    "ReferencePricePolicy",
    "derive_occurrence_id",
    "empty_signal_occurrences_dataframe",
    "materialize_signal_occurrences",
    "resolve_reference_price",
]
