"""Regression tests for execution cache dedup, identity and input immutability."""

from datetime import UTC, datetime
from decimal import Decimal

from trading_framework.core.identifiers import Identifier
from trading_framework.core.types import Price, Volume
from trading_framework.market.datasets import DatasetId, DatasetRef
from trading_framework.market.models import MarketBar
from trading_framework.market_analysis import (
    AnalysisContext,
    AnalysisResult,
    ComponentId,
    ComponentRequest,
    TimeRange,
)
from trading_framework.market_analysis.components.volatility import (
    AtrComponent,
    NumpyAtrImplementation,
    NumpyTrueRangeImplementation,
    NumpyVolatilityStateImplementation,
    TrueRangeComponent,
    VolatilityStateComponent,
)
from trading_framework.market_analysis.data.view import AnalysisDataView
from trading_framework.market_analysis.execution import SequentialBatchExecutor
from trading_framework.market_analysis.planning import (
    DependencyPlanner,
    PlanningContext,
    PlanningRequest,
)
from trading_framework.market_analysis.registry.builtins import register_mvp_components
from trading_framework.market_analysis.registry.registry import ComponentRegistry
from trading_framework.market_analysis.storage.workspace import AnalysisWorkspaceView
from trading_framework.time.models.timeframe import Timeframe


def _bars() -> list[MarketBar]:
    base = datetime(2024, 1, 1, tzinfo=UTC)
    specs = [
        (100, 105, 95, 102),
        (102, 108, 101, 107),
        (107, 110, 104, 105),
        (105, 106, 100, 101),
        (101, 103, 99, 102),
    ]
    bars: list[MarketBar] = []
    for index, (open_, high, low, close) in enumerate(specs):
        observed = base.replace(hour=index)
        bars.append(
            MarketBar(
                open=Price(Decimal(str(open_))),
                high=Price(Decimal(str(high))),
                low=Price(Decimal(str(low))),
                close=Price(Decimal(str(close))),
                volume=Volume(1000),
                observed_at=observed,
                available_at=observed.replace(minute=1),
            )
        )
    return bars


def _context() -> AnalysisContext:
    start = datetime(2024, 1, 1, tzinfo=UTC)
    end = datetime(2024, 1, 1, 4, tzinfo=UTC)
    return AnalysisContext(
        dataset_ref=DatasetRef(
            DatasetId(
                instrument_id=Identifier("NQ.c.0"),
                data_type="ohlcv",
                timeframe=Timeframe("1h"),
                provider="csv",
                source_id="test",
            ),
            version=1,
        ),
        timeframe=Timeframe("1h"),
        requested_range=TimeRange(start=start, end=end),
        computation_range=TimeRange(start=start, end=end),
        engine_version="0.1.0",
    )


def _planning_context() -> PlanningContext:
    start = datetime(2024, 1, 1, tzinfo=UTC)
    end = datetime(2024, 1, 1, 4, tzinfo=UTC)
    return PlanningContext(
        dataset_ref=DatasetRef(
            DatasetId(
                instrument_id=Identifier("NQ.c.0"),
                data_type="ohlcv",
                timeframe=Timeframe("1h"),
                provider="csv",
                source_id="test",
            ),
            version=1,
        ),
        timeframe=Timeframe("1h"),
        requested_range=TimeRange(start=start, end=end),
    )


def test_planner_deduplicates_duplicate_atr_requests() -> None:
    registry = ComponentRegistry()
    register_mvp_components(registry)
    atr_params = AtrComponent().parameter_schema.canonicalize({"period": 14})
    atr_request = ComponentRequest(
        component_id=ComponentId("volatility.atr"),
        parameters=atr_params,
    )
    planner = DependencyPlanner(registry)
    plan = planner.build_plan(
        _planning_context(),
        [
            PlanningRequest.from_component_request(atr_request),
            PlanningRequest.from_component_request(atr_request),
        ],
    )
    atr_nodes = [
        node for node in plan.nodes if node.request.component_id == ComponentId("volatility.atr")
    ]
    assert len(atr_nodes) == 1
    assert len(plan.nodes) == 2


def test_executor_runs_deduplicated_atr_once() -> None:
    atr_calls = {"count": 0}

    class CountingAtrImplementation(NumpyAtrImplementation):
        def compute(
            self,
            context: AnalysisContext,
            workspace: AnalysisWorkspaceView,
            parameters: object,
        ) -> AnalysisResult:
            atr_calls["count"] += 1
            return super().compute(context, workspace, parameters)  # type: ignore[arg-type]

    registry = ComponentRegistry()
    registry.register(TrueRangeComponent(), NumpyTrueRangeImplementation(), default=True)
    registry.register(AtrComponent(), CountingAtrImplementation(), default=True)
    registry.register(
        VolatilityStateComponent(), NumpyVolatilityStateImplementation(), default=True
    )
    atr_params = AtrComponent().parameter_schema.canonicalize({"period": 3})
    atr_request = ComponentRequest(
        component_id=ComponentId("volatility.atr"),
        parameters=atr_params,
    )
    state_request = ComponentRequest(
        component_id=ComponentId("volatility.state"),
        parameters=VolatilityStateComponent().parameter_schema.canonicalize(
            {"period": 3, "threshold": 5.0}
        ),
    )
    planner = DependencyPlanner(registry)
    plan = planner.build_plan(
        _planning_context(),
        [
            PlanningRequest.from_component_request(atr_request),
            PlanningRequest.from_component_request(state_request),
        ],
    )
    SequentialBatchExecutor().execute(
        plan,
        market_view=AnalysisDataView.from_bars(_bars()),
        context=_context(),
    )
    assert atr_calls["count"] == 1


def test_execution_leaves_market_view_unchanged() -> None:
    registry = ComponentRegistry()
    register_mvp_components(registry)
    market_view = AnalysisDataView.from_bars(_bars())
    original_high = market_view.high.values
    original_close = market_view.close.values
    request = ComponentRequest(
        component_id=ComponentId("volatility.state"),
        parameters=VolatilityStateComponent().parameter_schema.canonicalize(
            {"period": 3, "threshold": 5.0}
        ),
    )
    plan = DependencyPlanner(registry).build_plan(
        _planning_context(),
        [PlanningRequest.from_component_request(request)],
    )
    SequentialBatchExecutor().execute(
        plan,
        market_view=market_view,
        context=_context(),
    )
    assert market_view.high.values == original_high
    assert market_view.close.values == original_close


def test_identical_requests_resolve_to_same_computation_identity() -> None:
    registry = ComponentRegistry()
    register_mvp_components(registry)
    atr_params = AtrComponent().parameter_schema.canonicalize({"period": 14})
    request = ComponentRequest(
        component_id=ComponentId("volatility.atr"),
        parameters=atr_params,
    )
    planner = DependencyPlanner(registry)
    first = planner.build_plan(
        _planning_context(),
        [PlanningRequest.from_component_request(request)],
    )
    second = planner.build_plan(
        _planning_context(),
        [PlanningRequest.from_component_request(request)],
    )
    atr_nodes_first = [
        node for node in first.nodes if node.request.component_id == ComponentId("volatility.atr")
    ]
    atr_nodes_second = [
        node for node in second.nodes if node.request.component_id == ComponentId("volatility.atr")
    ]
    assert len(atr_nodes_first) == 1
    assert len(atr_nodes_second) == 1
    assert (
        atr_nodes_first[0].computation_identity.canonical_key()
        == atr_nodes_second[0].computation_identity.canonical_key()
    )


def test_different_parameters_yield_different_computation_identities() -> None:
    registry = ComponentRegistry()
    register_mvp_components(registry)
    planner = DependencyPlanner(registry)
    context = _planning_context()
    plan_14 = planner.build_plan(
        context,
        [
            PlanningRequest.from_component_request(
                ComponentRequest(
                    component_id=ComponentId("volatility.atr"),
                    parameters=AtrComponent().parameter_schema.canonicalize({"period": 14}),
                )
            )
        ],
    )
    plan_21 = planner.build_plan(
        context,
        [
            PlanningRequest.from_component_request(
                ComponentRequest(
                    component_id=ComponentId("volatility.atr"),
                    parameters=AtrComponent().parameter_schema.canonicalize({"period": 21}),
                )
            )
        ],
    )
    key_14 = next(
        node.computation_identity.canonical_key()
        for node in plan_14.nodes
        if node.request.component_id == ComponentId("volatility.atr")
    )
    key_21 = next(
        node.computation_identity.canonical_key()
        for node in plan_21.nodes
        if node.request.component_id == ComponentId("volatility.atr")
    )
    assert key_14 != key_21
