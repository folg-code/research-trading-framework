"""Reference price policies for Signal Research occurrence materialization.

``reference_price`` is a **descriptive research anchor** at signal observation time.
It is not a simulated fill, entry or execution price.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

import polars as pl

from trading_framework.core.exceptions import ValidationError
from trading_framework.market_analysis.assembly.frame import AnalysisFrame
from trading_framework.market_analysis.data.view import AnalysisDataView

_CLOSE_FIELD = "close"


class ReferencePricePolicy(StrEnum):
    """How to derive the descriptive reference price for one occurrence."""

    CLOSE_AT_DETECTED_AT = "close_at_detected_at"


@dataclass(frozen=True, slots=True)
class ReferencePriceLookup:
    """Precomputed timestamp index and close series for one evaluation frame.

    Build once per research run / materialization pass — never per occurrence.
    """

    index_by_timestamp: dict[datetime, int]
    close_values: tuple[float, ...]

    def to_frame(self) -> pl.DataFrame:
        """Return a joinable ``detected_at`` / ``reference_price`` table."""
        return pl.DataFrame(
            {
                "detected_at": list(self.index_by_timestamp.keys()),
                "reference_price": list(self.close_values),
            }
        )


def build_reference_price_lookup(
    frame: AnalysisFrame,
    market_view: AnalysisDataView | None = None,
) -> ReferencePriceLookup:
    """Build O(bars) lookup tables shared across many reference-price resolutions."""
    return ReferencePriceLookup(
        index_by_timestamp={timestamp: index for index, timestamp in enumerate(frame.timestamps)},
        close_values=_close_column(frame, market_view),
    )


def require_close_at_detected_at_policy(policy: ReferencePricePolicy) -> None:
    """Raise when a reference-price policy is not supported for batch resolution."""
    if policy.value != ReferencePricePolicy.CLOSE_AT_DETECTED_AT.value:
        msg = f"unsupported reference price policy: {policy.value}"
        raise ValidationError(msg)


def resolve_reference_price(
    policy: ReferencePricePolicy,
    *,
    detected_at: datetime,
    frame: AnalysisFrame,
    market_view: AnalysisDataView | None = None,
    lookup: ReferencePriceLookup | None = None,
) -> float:
    """Resolve descriptive reference price for one signal occurrence.

    Prefer passing a prebuilt ``lookup`` when resolving many timestamps against the
    same frame. When ``lookup`` is omitted, tables are built for this single call.
    """
    require_close_at_detected_at_policy(policy)

    resolved = lookup or build_reference_price_lookup(frame, market_view)
    index = resolved.index_by_timestamp.get(detected_at)
    if index is None:
        return math.nan
    return resolved.close_values[index]


def _close_column(
    frame: AnalysisFrame,
    market_view: AnalysisDataView | None,
) -> tuple[float, ...]:
    if _CLOSE_FIELD in frame.columns:
        return frame.columns[_CLOSE_FIELD]

    if market_view is None:
        msg = "evaluation frame lacks close column; market_view is required"
        raise ValidationError(msg)

    index_by_timestamp = {
        timestamp: index for index, timestamp in enumerate(market_view.timestamps)
    }
    aligned: list[float] = []
    for timestamp in frame.timestamps:
        source_index = index_by_timestamp.get(timestamp)
        if source_index is None:
            aligned.append(math.nan)
            continue
        aligned.append(market_view.close.values[source_index])
    return tuple(aligned)
