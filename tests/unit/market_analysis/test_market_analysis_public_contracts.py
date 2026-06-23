"""Public Market Analysis contract export tests."""

import trading_framework.market_analysis as market_analysis


def test_market_analysis_exports_identity_contracts() -> None:
    for name in (
        "ComponentId",
        "ComponentVersion",
        "ImplementationId",
        "ImplementationVersion",
        "ComputationIdentity",
    ):
        assert hasattr(market_analysis, name)


def test_market_analysis_exports_classification_contracts() -> None:
    for name in (
        "ComponentKind",
        "Causality",
        "HistoryRequirement",
        "WarmUpMetadata",
    ):
        assert hasattr(market_analysis, name)


def test_market_analysis_exports_parameter_contracts() -> None:
    for name in (
        "ParameterSchema",
        "CanonicalParameters",
        "ComponentRequest",
    ):
        assert hasattr(market_analysis, name)


def test_market_analysis_exports_execution_context_contracts() -> None:
    for name in (
        "AnalysisContext",
        "TimeRange",
    ):
        assert hasattr(market_analysis, name)


def test_market_analysis_exports_result_contracts() -> None:
    for name in (
        "AnalysisResult",
        "OutputRef",
        "Lineage",
        "OutputSchema",
        "AvailabilityMetadata",
    ):
        assert hasattr(market_analysis, name)
