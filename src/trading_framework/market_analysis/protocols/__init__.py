"""Market Analysis component protocols."""

from trading_framework.market_analysis.protocols.batch_component import BatchAnalysisComponent
from trading_framework.market_analysis.protocols.implementation import ComponentImplementation

__all__ = [
    "BatchAnalysisComponent",
    "ComponentImplementation",
]
