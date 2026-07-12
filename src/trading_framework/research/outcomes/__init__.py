"""Forward outcome definitions and calculators (Research domain)."""

from trading_framework.research.outcomes.calculator import (
    compute_forward_outcomes,
    compute_forward_outcomes_for_horizons,
    empty_forward_outcomes_dataframe,
)
from trading_framework.research.outcomes.definition import (
    ForwardOutcomeDefinition,
    IncompleteHorizonPolicy,
    OutcomeStatus,
)
from trading_framework.research.outcomes.ohlcv import align_ohlcv_to_evaluation_frame

__all__ = [
    "ForwardOutcomeDefinition",
    "IncompleteHorizonPolicy",
    "OutcomeStatus",
    "align_ohlcv_to_evaluation_frame",
    "compute_forward_outcomes",
    "compute_forward_outcomes_for_horizons",
    "empty_forward_outcomes_dataframe",
]
