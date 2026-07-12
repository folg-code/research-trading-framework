"""Plan Market Analysis inputs required to evaluate declarative models."""

from trading_framework.market_analysis.assembly.frame import AnalysisFrameRequest
from trading_framework.market_model.definitions import MarketModelDefinition
from trading_framework.model_expression.dependencies import (
    ExpressionDependencies,
    ExpressionDependencyExtractor,
    merge_expression_dependencies,
)
from trading_framework.model_expression.expressions import Expression
from trading_framework.signal_model.definitions import SignalModelDefinition


def collect_model_dependencies(
    *,
    market_models: tuple[MarketModelDefinition, ...],
    signal_models: tuple[SignalModelDefinition, ...],
) -> ExpressionDependencies:
    """Collect deduplicated analysis dependencies for one model bundle."""
    extractor = ExpressionDependencyExtractor()
    parts = [extractor.extract(model.expression) for model in market_models]
    parts.extend(extractor.extract(model.expression) for model in signal_models)
    if not parts:
        return ExpressionDependencies((), (), ())
    return merge_expression_dependencies(*parts)


def collect_expression_dependencies(
    expressions: tuple[Expression, ...],
) -> ExpressionDependencies:
    """Collect deduplicated analysis dependencies for raw expressions."""
    extractor = ExpressionDependencyExtractor()
    parts = [extractor.extract(expression) for expression in expressions]
    if not parts:
        return ExpressionDependencies((), (), ())
    return merge_expression_dependencies(*parts)


def build_analysis_frame_request(dependencies: ExpressionDependencies) -> AnalysisFrameRequest:
    """Build one frame request covering all model operand columns."""
    return AnalysisFrameRequest(
        market_fields=tuple(field.value for field in dependencies.market_fields),
        analysis_columns=tuple(
            reference.to_frame_column_spec()
            for reference in dependencies.component_output_references
        ),
    )
