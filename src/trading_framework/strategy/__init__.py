"""Strategy domain package."""

from trading_framework.strategy.canonical_examples import (
    CANONICAL_EXIT_AFTER_BARS,
    CANONICAL_POSITION_QUANTITY,
    CANONICAL_STRATEGY_MODEL_ID,
    build_canonical_strategy_model,
)
from trading_framework.strategy.exit_model import ExitModel, ExitReason, FixedBarsExitModel
from trading_framework.strategy.reference_price import ReferencePricePolicy, resolve_reference_price
from trading_framework.strategy.risk_model import FixedQuantityRiskModel, RiskModel
from trading_framework.strategy.signal_occurrence import (
    OccurrenceMaterializationContext,
    derive_occurrence_id,
    empty_signal_occurrences_dataframe,
    materialize_signal_occurrences,
)
from trading_framework.strategy.strategy_model import (
    StrategyModelDefinition,
    StrategyModelDefinitionError,
    validate_strategy_model_definition,
)

__all__ = [
    "CANONICAL_EXIT_AFTER_BARS",
    "CANONICAL_POSITION_QUANTITY",
    "CANONICAL_STRATEGY_MODEL_ID",
    "ExitModel",
    "ExitReason",
    "FixedBarsExitModel",
    "FixedQuantityRiskModel",
    "OccurrenceMaterializationContext",
    "ReferencePricePolicy",
    "RiskModel",
    "StrategyModelDefinition",
    "StrategyModelDefinitionError",
    "build_canonical_strategy_model",
    "derive_occurrence_id",
    "empty_signal_occurrences_dataframe",
    "materialize_signal_occurrences",
    "resolve_reference_price",
    "validate_strategy_model_definition",
]
