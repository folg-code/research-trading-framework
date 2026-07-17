"""Strategy domain package."""

from trading_framework.strategy.btc_futures_demo import (
    BTC_FUTURES_DEMO_DISCLOSURE,
    BTC_FUTURES_DEMO_MARKET_MODEL_ID,
    BTC_FUTURES_DEMO_SIGNAL_MODEL_ID,
    BTC_FUTURES_DEMO_STRATEGY_MODEL_ID,
    BtcFuturesDemoStrategyConfig,
    build_btc_futures_demo_strategy_model,
)
from trading_framework.strategy.canonical_examples import (
    CANONICAL_EXIT_AFTER_BARS,
    CANONICAL_POSITION_QUANTITY,
    CANONICAL_STRATEGY_MODEL_ID,
    build_canonical_strategy_model,
)
from trading_framework.strategy.exit_model import ExitModel, ExitReason, FixedBarsExitModel
from trading_framework.strategy.reference_price import (
    ReferencePriceLookup,
    ReferencePricePolicy,
    build_reference_price_lookup,
    resolve_reference_price,
)
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
    "BTC_FUTURES_DEMO_DISCLOSURE",
    "BTC_FUTURES_DEMO_MARKET_MODEL_ID",
    "BTC_FUTURES_DEMO_SIGNAL_MODEL_ID",
    "BTC_FUTURES_DEMO_STRATEGY_MODEL_ID",
    "CANONICAL_EXIT_AFTER_BARS",
    "CANONICAL_POSITION_QUANTITY",
    "CANONICAL_STRATEGY_MODEL_ID",
    "BtcFuturesDemoStrategyConfig",
    "ExitModel",
    "ExitReason",
    "FixedBarsExitModel",
    "FixedQuantityRiskModel",
    "OccurrenceMaterializationContext",
    "ReferencePriceLookup",
    "ReferencePricePolicy",
    "RiskModel",
    "StrategyModelDefinition",
    "StrategyModelDefinitionError",
    "build_btc_futures_demo_strategy_model",
    "build_canonical_strategy_model",
    "build_reference_price_lookup",
    "derive_occurrence_id",
    "empty_signal_occurrences_dataframe",
    "materialize_signal_occurrences",
    "resolve_reference_price",
    "validate_strategy_model_definition",
]
