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


def test_market_analysis_exports_core_models() -> None:
    for name in (
        "ComponentKind",
        "Causality",
        "ComponentRequest",
        "AnalysisContext",
        "AnalysisResult",
        "OutputRef",
        "Lineage",
    ):
        assert hasattr(market_analysis, name)
