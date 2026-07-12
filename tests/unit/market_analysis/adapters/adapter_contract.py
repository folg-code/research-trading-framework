"""Shared adapter contract checks (D-033)."""

import math
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from trading_framework.core.identifiers import Identifier
from trading_framework.core.types import Price, Volume
from trading_framework.market.datasets import DatasetId, DatasetRef
from trading_framework.market.models import MarketBar
from trading_framework.market_analysis.identity.component import ComponentId
from trading_framework.market_analysis.models.context import AnalysisContext
from trading_framework.market_analysis.models.parameters import CanonicalParameters
from trading_framework.market_analysis.models.time_range import TimeRange
from trading_framework.market_analysis.protocols.batch_component import BatchAnalysisComponent
from trading_framework.market_analysis.protocols.implementation import ComponentImplementation
from trading_framework.market_analysis.storage.workspace import (
    AnalysisWorkspace,
    AnalysisWorkspaceView,
)
from trading_framework.time.models.timeframe import Timeframe


@dataclass(frozen=True, slots=True)
class AdapterContractCase:
    """One semantic component and implementation pair under contract test."""

    component: BatchAnalysisComponent
    implementation: ComponentImplementation
    parameters: CanonicalParameters
    dependency_keys: tuple[str, ...]
    prepare_workspace: Callable[[AnalysisWorkspace], AnalysisWorkspaceView] | None = None


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
                source_id="adapter-contract",
            ),
            version=1,
        ),
        timeframe=Timeframe("1h"),
        requested_range=TimeRange(start=start, end=end),
        computation_range=TimeRange(start=start, end=end),
        engine_version="0.1.0",
    )


def _workspace_view(
    case: AdapterContractCase,
) -> tuple[AnalysisContext, AnalysisWorkspaceView, int]:
    from trading_framework.market_analysis.data.view import AnalysisDataView

    workspace = AnalysisWorkspace(AnalysisDataView.from_bars(_bars()))
    if case.prepare_workspace is not None:
        workspace_view = case.prepare_workspace(workspace)
    else:
        workspace_view = workspace.view_for(case.dependency_keys)
    return _context(), workspace_view, len(workspace.market_view)


def _series_values_equal(left: tuple[float, ...], right: tuple[float, ...]) -> bool:
    if len(left) != len(right):
        return False
    for left_value, right_value in zip(left, right, strict=True):
        if math.isnan(left_value) and math.isnan(right_value):
            continue
        if left_value != right_value:
            return False
    return True


def assert_adapter_contract(case: AdapterContractCase) -> None:
    """Run shared D-033 checks for one component implementation."""
    context, workspace_view, bar_count = _workspace_view(case)
    original_close = workspace_view.market.close.values

    first = case.implementation.compute(context, workspace_view, case.parameters)
    second = case.implementation.compute(context, workspace_view, case.parameters)

    assert first.outputs.keys() == second.outputs.keys()
    for output_id in first.outputs:
        assert _series_values_equal(
            first.outputs[output_id].values,
            second.outputs[output_id].values,
        )

    assert workspace_view.market.close.values == original_close
    assert first.computation_identity.component_id == case.component.component_id
    assert set(first.outputs) == {field.output_id for field in case.component.output_schema.outputs}

    for _output_id, series in first.outputs.items():
        assert series.length == bar_count

    assert first.validity.valid_from_index >= first.warmup.warmup_bars
    assert first.lineage.component_id == case.component.component_id
    assert first.lineage.implementation_id == case.implementation.implementation_id
    assert first.lineage.engine_version == context.engine_version


def dependency_workspace(
    *,
    component_id: ComponentId,
    parameters: CanonicalParameters,
) -> Callable[[AnalysisWorkspace], AnalysisWorkspaceView]:
    """Build workspace view with one registered dependency result."""

    def _prepare(workspace: AnalysisWorkspace) -> AnalysisWorkspaceView:
        from trading_framework.market_analysis import (
            ComponentRequest,
            SequentialBatchExecutor,
        )
        from trading_framework.market_analysis.planning import (
            DependencyPlanner,
            PlanningContext,
            PlanningRequest,
        )
        from trading_framework.market_analysis.registry.builtins import (
            register_volatility_components,
        )
        from trading_framework.market_analysis.registry.registry import ComponentRegistry

        registry = ComponentRegistry()
        register_volatility_components(registry)
        context = _context()
        request = ComponentRequest(component_id=component_id, parameters=parameters)
        plan = DependencyPlanner(registry).build_plan(
            PlanningContext(
                dataset_ref=context.dataset_ref,
                timeframe=context.timeframe,
                requested_range=context.requested_range,
            ),
            [PlanningRequest.from_component_request(request)],
        )
        populated = SequentialBatchExecutor().execute(
            plan,
            market_view=workspace.market_view,
            context=context,
        )
        dependency_key = next(
            result.computation_identity.canonical_key()
            for result in populated.result_store.results().values()
            if result.computation_identity.component_id == component_id
        )
        for result in populated.result_store.results().values():
            workspace.register(result)
        return workspace.view_for((dependency_key,))

    return _prepare
