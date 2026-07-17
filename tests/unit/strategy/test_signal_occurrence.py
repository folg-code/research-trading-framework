"""Tests for SignalOccurrence materialization and reference price policy."""

from __future__ import annotations

import math
from collections.abc import Callable
from datetime import UTC, datetime

import polars as pl
import pytest

from trading_framework.core.exceptions import ValidationError
from trading_framework.market_analysis.assembly.frame import AnalysisFrame
from trading_framework.market_analysis.data.view import AnalysisDataView, DataColumn
from trading_framework.strategy import (
    OccurrenceMaterializationContext,
    ReferencePricePolicy,
    derive_occurrence_id,
    materialize_signal_occurrences,
    resolve_reference_price,
)
from trading_framework.time.models.timeframe import Timeframe


def _context(**overrides: object) -> OccurrenceMaterializationContext:
    defaults = {
        "signal_model_id": "higher_low_long",
        "instrument": "ES.c.0",
        "evaluation_timeframe": Timeframe("1m"),
        "source_dataset_ref": "ES.c.0:ohlcv:1m:csv:fixture@1",
    }
    defaults.update(overrides)
    return OccurrenceMaterializationContext(**defaults)  # type: ignore[arg-type]


def test_derive_occurrence_id_is_stable() -> None:
    detected_at = datetime(2024, 1, 1, 12, 0, tzinfo=UTC)
    first = derive_occurrence_id(
        signal_model_id="signal_a",
        detected_at=detected_at,
        direction="long",
    )
    second = derive_occurrence_id(
        signal_model_id="signal_a",
        detected_at=detected_at,
        direction="long",
    )
    assert first == second
    assert len(first) == 16


def test_materialize_empty_emissions_returns_canonical_schema() -> None:
    frame = AnalysisFrame(
        timestamps=(datetime(2024, 1, 1, tzinfo=UTC),),
        columns={"close": (100.0,)},
        column_lineage={},
    )
    result = materialize_signal_occurrences(
        pl.DataFrame(),
        frame=frame,
        context=_context(),
    )
    assert result.columns == [
        "occurrence_id",
        "signal_model_id",
        "detected_at",
        "available_at",
        "direction",
        "reference_price",
        "instrument",
        "evaluation_timeframe",
        "source_dataset_ref",
    ]
    assert len(result) == 0


def test_reference_price_is_close_at_detected_at(
    build_test_frame: Callable[..., AnalysisFrame],
) -> None:
    frame = build_test_frame(columns={"close": (100.0, 101.0, 102.0)})
    timestamps = frame.timestamps
    emissions = pl.DataFrame(
        {
            "detected_at": [timestamps[1]],
            "available_at": [timestamps[1]],
            "direction": ["long"],
        }
    )
    result = materialize_signal_occurrences(
        emissions,
        frame=frame,
        context=_context(),
    )
    assert result["reference_price"].to_list() == [101.0]
    assert result["occurrence_id"].n_unique() == 1


def test_reference_price_uses_market_view_when_frame_lacks_ohlcv() -> None:
    timestamps = (
        datetime(2024, 1, 1, 12, 0, tzinfo=UTC),
        datetime(2024, 1, 1, 12, 1, tzinfo=UTC),
    )
    frame = AnalysisFrame(
        timestamps=timestamps,
        columns={"vol_state": (0.0, 1.0)},
        column_lineage={},
    )
    market_view = AnalysisDataView(
        timestamps=timestamps,
        open=DataColumn((100.0, 101.0)),
        high=DataColumn((100.5, 101.5)),
        low=DataColumn((99.5, 100.5)),
        close=DataColumn((100.0, 101.0)),
        volume=DataColumn((1.0, 1.0)),
    )
    emissions = pl.DataFrame(
        {
            "detected_at": [timestamps[1]],
            "available_at": [timestamps[1]],
            "direction": ["long"],
        }
    )
    result = materialize_signal_occurrences(
        emissions,
        frame=frame,
        context=_context(),
        market_view=market_view,
    )
    assert result["reference_price"].to_list() == [101.0]


def test_missing_detected_at_timestamp_yields_nan_reference_price(
    build_test_frame: Callable[..., AnalysisFrame],
) -> None:
    frame = build_test_frame(columns={"close": (100.0, 101.0)})
    emissions = pl.DataFrame(
        {
            "detected_at": [datetime(2099, 1, 1, tzinfo=UTC)],
            "available_at": [datetime(2099, 1, 1, tzinfo=UTC)],
            "direction": ["long"],
        }
    )
    result = materialize_signal_occurrences(
        emissions,
        frame=frame,
        context=_context(),
    )
    assert math.isnan(result["reference_price"][0])


def test_resolve_reference_price_requires_market_view_without_close_column() -> None:
    frame = AnalysisFrame(
        timestamps=(datetime(2024, 1, 1, tzinfo=UTC),),
        columns={"vol_state": (1.0,)},
        column_lineage={},
    )
    with pytest.raises(ValidationError, match="market_view is required"):
        resolve_reference_price(
            ReferencePricePolicy.CLOSE_AT_DETECTED_AT,
            detected_at=frame.timestamps[0],
            frame=frame,
        )


def test_materialize_builds_reference_price_lookup_once(
    build_test_frame: Callable[..., AnalysisFrame],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from trading_framework.strategy import signal_occurrence as occurrence_module
    from trading_framework.strategy.reference_price import (
        ReferencePriceLookup,
    )
    from trading_framework.strategy.reference_price import (
        build_reference_price_lookup as real_build,
    )

    frame = build_test_frame(columns={"close": (100.0, 101.0, 102.0, 103.0)})
    timestamps = frame.timestamps
    emissions = pl.DataFrame(
        {
            "detected_at": list(timestamps),
            "available_at": list(timestamps),
            "direction": ["long"] * len(timestamps),
        }
    )
    call_count = 0

    def counting_build(
        evaluation_frame: AnalysisFrame,
        market_view: AnalysisDataView | None = None,
    ) -> ReferencePriceLookup:
        nonlocal call_count
        call_count += 1
        return real_build(evaluation_frame, market_view)

    monkeypatch.setattr(occurrence_module, "build_reference_price_lookup", counting_build)

    result = materialize_signal_occurrences(
        emissions,
        frame=frame,
        context=_context(),
    )

    assert call_count == 1
    assert result["reference_price"].to_list() == [100.0, 101.0, 102.0, 103.0]


def test_resolve_reference_price_reuses_prebuilt_lookup(
    build_test_frame: Callable[..., AnalysisFrame],
) -> None:
    from trading_framework.strategy.reference_price import build_reference_price_lookup

    frame = build_test_frame(columns={"close": (100.0, 101.0, 102.0)})
    lookup = build_reference_price_lookup(frame)
    prices = [
        resolve_reference_price(
            ReferencePricePolicy.CLOSE_AT_DETECTED_AT,
            detected_at=timestamp,
            frame=frame,
            lookup=lookup,
        )
        for timestamp in frame.timestamps
    ]
    assert prices == [100.0, 101.0, 102.0]


def test_occurrence_preserves_detected_and_available_at(
    build_test_frame: Callable[..., AnalysisFrame],
) -> None:
    frame = build_test_frame(columns={"close": (100.0, 101.0, 102.0)})
    timestamps = frame.timestamps
    emissions = pl.DataFrame(
        {
            "detected_at": [timestamps[0]],
            "available_at": [timestamps[1]],
            "direction": ["long"],
        }
    )
    result = materialize_signal_occurrences(
        emissions,
        frame=frame,
        context=_context(),
    )
    assert result["detected_at"].to_list() == [timestamps[0]]
    assert result["available_at"].to_list() == [timestamps[1]]
