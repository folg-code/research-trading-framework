"""Component protocol contract tests."""

from datetime import UTC, datetime

from trading_framework.core.identifiers import Identifier
from trading_framework.market.datasets import DatasetId, DatasetRef
from trading_framework.market_analysis import (
    AnalysisContext,
    AnalysisResult,
    AvailabilityMetadata,
    AvailabilityPolicy,
    BatchAnalysisComponent,
    CanonicalParameters,
    Causality,
    ComponentDependency,
    ComponentId,
    ComponentImplementation,
    ComponentKind,
    ComponentOutputRef,
    ComponentVersion,
    ComputationIdentity,
    DataFieldDependency,
    HistoryRequirement,
    ImplementationId,
    ImplementationVersion,
    Lineage,
    OutputFieldSpec,
    OutputId,
    OutputSchema,
    OutputSeries,
    ParameterFieldSpec,
    ParameterSchema,
    ParameterType,
    TimeRange,
    ValidityMetadata,
    WarmUpMetadata,
)
from trading_framework.market_analysis.data.view import AnalysisDataView, DataColumn
from trading_framework.market_analysis.storage.workspace import AnalysisWorkspaceView
from trading_framework.time.models.timeframe import Timeframe


def _workspace_view() -> AnalysisWorkspaceView:
    timestamps = (datetime(2024, 1, 1, tzinfo=UTC),)
    column = DataColumn((1.0,))
    market = AnalysisDataView(
        timestamps=timestamps,
        open=column,
        high=column,
        low=column,
        close=column,
        volume=column,
    )
    return AnalysisWorkspaceView(market=market, dependency_results={})


class _StubComponent:
    component_id = ComponentId("volatility.atr")
    component_version = ComponentVersion("1.0.0")
    kind = ComponentKind.FEATURE
    causality = Causality.CAUSAL
    parameter_schema = ParameterSchema(
        fields=(ParameterFieldSpec("period", ParameterType.INT, default=14),)
    )
    output_schema = OutputSchema(
        outputs=(OutputFieldSpec(OutputId("value"), "float64"),),
    )

    def history_requirement(self, parameters: CanonicalParameters) -> HistoryRequirement:
        period = int(parameters.get("period"))
        return HistoryRequirement(bars_before=period)

    def data_dependencies(
        self,
        parameters: CanonicalParameters,
    ) -> tuple[DataFieldDependency, ...]:
        return (DataFieldDependency("close"),)

    def component_dependencies(
        self,
        parameters: CanonicalParameters,
    ) -> tuple[ComponentDependency, ...]:
        period = int(parameters.get("period"))
        child_params = ParameterSchema(
            fields=(ParameterFieldSpec("period", ParameterType.INT, default=period),)
        ).canonicalize({"period": period})
        return (
            ComponentDependency(
                output_ref=ComponentOutputRef(
                    component_id=ComponentId("volatility.true_range"),
                    parameters=child_params,
                    output_id=OutputId("value"),
                )
            ),
        )


class _StubImplementation:
    implementation_id = ImplementationId("numpy.atr")
    implementation_version = ImplementationVersion("1.0.0")

    def compute(
        self,
        context: AnalysisContext,
        workspace: AnalysisWorkspaceView,
        parameters: CanonicalParameters,
    ) -> AnalysisResult:
        dataset_ref = context.dataset_ref
        identity = ComputationIdentity(
            component_id=ComponentId("volatility.atr"),
            component_version=ComponentVersion("1.0.0"),
            implementation_id=ImplementationId("numpy.atr"),
            implementation_version=ImplementationVersion("1.0.0"),
            parameters=parameters,
            dataset_ref=dataset_ref,
            computation_timeframe=context.timeframe,
            requested_range=context.requested_range,
            dependency_keys=(),
        )
        output_id = OutputId("value")
        schema = OutputSchema(outputs=(OutputFieldSpec(output_id, "float64"),))
        lineage = Lineage(
            dataset_ref=dataset_ref,
            component_id=ComponentId("volatility.atr"),
            component_version=ComponentVersion("1.0.0"),
            implementation_id=ImplementationId("numpy.atr"),
            implementation_version=ImplementationVersion("1.0.0"),
            parameters=parameters,
            dependency_keys=(),
            engine_version=context.engine_version,
            executed_at=datetime(2024, 1, 1, tzinfo=UTC),
        )
        return AnalysisResult(
            computation_identity=identity,
            output_schema=schema,
            outputs={output_id: OutputSeries(values=(1.0,))},
            lineage=lineage,
            validity=ValidityMetadata(valid_from_index=0, valid_to_index=0),
            warmup=WarmUpMetadata(warmup_bars=0, valid_from_index=0, valid_to_index=0),
            availability=AvailabilityMetadata(policy=AvailabilityPolicy.SAME_BAR),
            diagnostics={},
        )


def test_stub_component_satisfies_batch_protocol() -> None:
    component: BatchAnalysisComponent = _StubComponent()
    params = component.parameter_schema.canonicalize({"period": 21})
    assert component.history_requirement(params).bars_before == 21
    assert len(component.component_dependencies(params)) == 1


def test_stub_implementation_satisfies_protocol() -> None:
    implementation: ComponentImplementation = _StubImplementation()
    context = AnalysisContext(
        dataset_ref=DatasetRef(
            DatasetId(
                instrument_id=Identifier("NQ.c.0"),
                data_type="ohlcv",
                timeframe=Timeframe("1m"),
                provider="csv",
                source_id="sample",
            ),
            version=1,
        ),
        timeframe=Timeframe("1m"),
        requested_range=TimeRange(
            start=datetime(2024, 1, 1, tzinfo=UTC),
            end=datetime(2024, 1, 2, tzinfo=UTC),
        ),
        computation_range=TimeRange(
            start=datetime(2024, 1, 1, tzinfo=UTC),
            end=datetime(2024, 1, 2, tzinfo=UTC),
        ),
        engine_version="0.1.0",
    )
    result = implementation.compute(
        context,
        _workspace_view(),
        ParameterSchema(
            fields=(ParameterFieldSpec("period", ParameterType.INT, default=14),)
        ).canonicalize({}),
    )
    assert result.outputs[OutputId("value")].length == 1
