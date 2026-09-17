"""Tests for the causal Structure Level Role Reversal ("SR flip") component."""

from datetime import UTC, datetime
from decimal import Decimal

from trading_framework.core.identifiers import Identifier
from trading_framework.core.types import Price, Volume
from trading_framework.market.datasets import DatasetId, DatasetRef
from trading_framework.market.models import MarketBar
from trading_framework.market_analysis import (
    AnalysisContext,
    ComponentId,
    OutputId,
    TimeRange,
)
from trading_framework.market_analysis.assembly.session_metadata import TradingSessionMetadata
from trading_framework.market_analysis.components.structure import LevelRoleReversalComponent
from trading_framework.market_analysis.data.view import AnalysisDataView
from trading_framework.market_analysis.execution import SequentialBatchExecutor
from trading_framework.market_analysis.models.kind import Causality, ComponentKind
from trading_framework.market_analysis.models.request import ComponentRequest
from trading_framework.market_analysis.models.result import AnalysisResult
from trading_framework.market_analysis.planning import (
    DependencyPlanner,
    PlanningContext,
    PlanningRequest,
)
from trading_framework.market_analysis.registry.builtins import register_mvp_components
from trading_framework.market_analysis.registry.registry import ComponentRegistry
from trading_framework.time.models.timeframe import Timeframe
from trading_framework.time.sessions import CmeEsRthSessionResolver

# pivot_range=1: swing high at p=1 (high=110) confirms at index 2.
# Index 3 breaks resistance (close=111 > 110). Index 4 retests: low touches
# 110 while close (112) holds above it -- role flips to support.
_HOLD_ROWS: tuple[tuple[datetime, float, float, float, float], ...] = (
    (datetime(2024, 6, 3, 13, 30, tzinfo=UTC), 100.0, 100.0, 99.0, 100.0),
    (datetime(2024, 6, 3, 13, 31, tzinfo=UTC), 100.0, 110.0, 100.0, 105.0),
    (datetime(2024, 6, 3, 13, 32, tzinfo=UTC), 105.0, 106.0, 104.0, 105.0),
    (datetime(2024, 6, 3, 13, 33, tzinfo=UTC), 105.0, 112.0, 104.0, 111.0),
    (datetime(2024, 6, 3, 13, 34, tzinfo=UTC), 111.0, 113.0, 110.0, 112.0),
)

# Same break, but the retest bar closes back below the level -- role reversal
# is not confirmed (broke back through instead of holding).
_FAILED_RETEST_ROWS: tuple[tuple[datetime, float, float, float, float], ...] = (
    (datetime(2024, 6, 3, 13, 30, tzinfo=UTC), 100.0, 100.0, 99.0, 100.0),
    (datetime(2024, 6, 3, 13, 31, tzinfo=UTC), 100.0, 110.0, 100.0, 105.0),
    (datetime(2024, 6, 3, 13, 32, tzinfo=UTC), 105.0, 106.0, 104.0, 105.0),
    (datetime(2024, 6, 3, 13, 33, tzinfo=UTC), 105.0, 112.0, 104.0, 111.0),
    (datetime(2024, 6, 3, 13, 34, tzinfo=UTC), 111.0, 111.0, 109.0, 109.0),
)


def _bars(rows: tuple[tuple[datetime, float, float, float, float], ...]) -> list[MarketBar]:
    bars: list[MarketBar] = []
    for observed, open_, high, low, close in rows:
        bars.append(
            MarketBar(
                open=Price(Decimal(str(open_))),
                high=Price(Decimal(str(high))),
                low=Price(Decimal(str(low))),
                close=Price(Decimal(str(close))),
                volume=Volume(1000),
                observed_at=observed,
                available_at=observed.replace(minute=observed.minute + 1)
                if observed.minute < 59
                else observed.replace(hour=observed.hour + 1, minute=0),
            )
        )
    return bars


def _context(*, start: datetime, end: datetime, source_id: str) -> AnalysisContext:
    return AnalysisContext(
        dataset_ref=DatasetRef(
            DatasetId(
                instrument_id=Identifier("ES.c.0"),
                data_type="ohlcv",
                timeframe=Timeframe("1m"),
                provider="csv",
                source_id=source_id,
            ),
            version=1,
        ),
        timeframe=Timeframe("1m"),
        requested_range=TimeRange(start=start, end=end),
        computation_range=TimeRange(start=start, end=end),
        engine_version="0.1.0",
    )


def _run(
    rows: tuple[tuple[datetime, float, float, float, float], ...],
    *,
    source_id: str,
) -> AnalysisResult:
    view = AnalysisDataView.from_bars(_bars(rows))
    resolver = CmeEsRthSessionResolver()
    metadata = TradingSessionMetadata.resolve(view.timestamps, resolver)
    registry = ComponentRegistry()
    register_mvp_components(registry)
    planner = DependencyPlanner(registry)
    parameters = LevelRoleReversalComponent().parameter_schema.canonicalize(
        {"pivot_range": 1, "retest_window": 5}
    )
    request = ComponentRequest(
        component_id=ComponentId("structure.level_role_reversal"),
        parameters=parameters,
    )
    context = _context(start=view.timestamps[0], end=view.timestamps[-1], source_id=source_id)
    plan = planner.build_plan(
        PlanningContext(
            dataset_ref=context.dataset_ref,
            timeframe=Timeframe("1m"),
            requested_range=context.requested_range,
        ),
        (PlanningRequest.from_component_request(request),),
    )
    executed = SequentialBatchExecutor().execute(
        plan,
        market_view=view,
        context=context,
        session_metadata=metadata,
        session_resolver=resolver,
    )
    for result in executed.result_store.results().values():
        if result.computation_identity.component_id.value == "structure.level_role_reversal":
            return result
    raise AssertionError("structure.level_role_reversal not computed")


def test_level_role_reversal_component_declares_shape() -> None:
    component = LevelRoleReversalComponent()
    assert component.component_id.value == "structure.level_role_reversal"
    assert component.kind is ComponentKind.FEATURE
    assert component.causality is Causality.CAUSAL
    output_ids = {field.output_id.value for field in component.output_schema.outputs}
    assert output_ids == {"resistance_to_support_event", "support_to_resistance_event"}


def test_level_role_reversal_confirms_when_retest_holds() -> None:
    result = _run(_HOLD_ROWS, source_id="role-reversal-hold")
    resistance_to_support = result.outputs[OutputId("resistance_to_support_event")].values
    # Bar 3 breaks resistance (111 > 110); bar 4 retests (low 110) and holds (close 112).
    assert resistance_to_support[3] == 0.0
    assert resistance_to_support[4] == 1.0


def test_level_role_reversal_does_not_confirm_when_retest_fails() -> None:
    result = _run(_FAILED_RETEST_ROWS, source_id="role-reversal-fail")
    resistance_to_support = result.outputs[OutputId("resistance_to_support_event")].values
    # Bar 4 closes back below the level (109 < 110) -- broke back through, not held.
    assert list(resistance_to_support) == [0.0] * len(resistance_to_support)
