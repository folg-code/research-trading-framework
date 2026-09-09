"""Sprint 051's real, catalog-composed RSI / relative-volatility strategy
(S051-T009), reproduced here for Sprint 058 T005's worked example.

The operator-authored original
(``user_data/components/strategies/rsi_relative_volatility_regime.py``) is
gitignored (ADR-0002); its committed framework-side stand-in
(``apps/cli/tests/fixtures/strategies/uses_rsi_relative_volatility.py``)
lives in a separate project (``apps/cli/pyproject.toml``) not importable
from these scripts' own venv. Duplicating the ~15-line DSL composition is
simpler and more robust than a cross-project ``sys.path`` hack, and
matches this increment's own precedent (``score_gate.py``'s deliberately
duplicated component-request helpers).

Same Market/Signal condition, same exit/risk parameters as the original --
only the ``strategy_model_id`` differs (unprefixed here; this is neither
the operator's original nor the CLI test fixture, it is T005's own worked
example).
"""

from __future__ import annotations

from decimal import Decimal

from trading_framework.market_model.definitions import MarketModelDefinition
from trading_framework.model_authoring import (
    LONG,
    ON_TRUE_EDGE,
    market_model,
    momentum,
    signal_model,
    volatility,
)
from trading_framework.signal_model.definitions import SignalModelDefinition
from trading_framework.strategy import (
    BracketExitModel,
    EquityPercentRiskModel,
    ScoreConditionSpec,
    StrategyModelDefinition,
)

STRATEGY_MODEL_ID = "s058_t005_rsi_relative_volatility"

RSI_PERIOD = 14
RSI_OVERSOLD_THRESHOLD = 30.0
RELATIVE_VOLATILITY_PERIOD = 20
RELATIVE_VOLATILITY_BASELINE_PERIOD = 100
RELATIVE_VOLATILITY_RATIO_THRESHOLD = 1.0
STOP_LOSS_BPS = 20.0
TAKE_PROFIT_BPS = 20.0
MAX_BARS = 20
ACCOUNT_EQUITY = Decimal(100_000)
RISK_PERCENT = Decimal("0.01")
STOP_DISTANCE = Decimal("2")


def build_market_model() -> MarketModelDefinition:
    return market_model(
        "s058_t005_rsi_relative_volatility_market",
        when=(
            volatility.relative_volatility_ratio(
                period=RELATIVE_VOLATILITY_PERIOD,
                baseline_period=RELATIVE_VOLATILITY_BASELINE_PERIOD,
            )
            > RELATIVE_VOLATILITY_RATIO_THRESHOLD
        ),
    ).definition


def build_signal_model() -> SignalModelDefinition:
    return signal_model(
        "s058_t005_rsi_relative_volatility_signal",
        direction=LONG,
        when=(momentum.rsi(period=RSI_PERIOD) < RSI_OVERSOLD_THRESHOLD),
        firing=ON_TRUE_EDGE,
    ).definition


def build_strategy(*, score_condition: ScoreConditionSpec | None = None) -> StrategyModelDefinition:
    strategy_model_id = (
        STRATEGY_MODEL_ID if score_condition is None else f"{STRATEGY_MODEL_ID}_scored"
    )
    return StrategyModelDefinition(
        strategy_model_id=strategy_model_id,
        market_model=build_market_model(),
        signal_model=build_signal_model(),
        exit_model=BracketExitModel(
            stop_loss_bps=STOP_LOSS_BPS,
            take_profit_bps=TAKE_PROFIT_BPS,
            max_bars=MAX_BARS,
        ),
        risk_model=EquityPercentRiskModel(
            account_equity=ACCOUNT_EQUITY,
            risk_percent=RISK_PERCENT,
            stop_distance=STOP_DISTANCE,
        ),
        score_condition=score_condition,
    )
