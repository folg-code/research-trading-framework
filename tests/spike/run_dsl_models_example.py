"""Demonstrate the user-facing model authoring DSL from S006.

Run:

    uv run python tests/spike/run_dsl_models_example.py
"""

from __future__ import annotations

from trading_framework.model_authoring import (
    LONG,
    VolatilityState,
    market_model,
    price,
    signal_model,
    structure,
    trend,
    volatility,
)

high_volatility = market_model(
    "high_volatility",
    when=(volatility.state(period=14, threshold=2.0) == VolatilityState.HIGH),
)

bullish_context = market_model(
    "bullish_context",
    when=(
        (price.close > trend.ema(period=20))
        & (volatility.state(period=14, threshold=2.0) == VolatilityState.HIGH)
    ),
)

higher_low_long = signal_model(
    "higher_low_long",
    direction=LONG,
    when=structure.higher_low_event(pivot_range=15, timeframe="5m"),
)

combined_signal = signal_model(
    "high_vol_and_higher_low",
    direction=LONG,
    when=(
        (volatility.state(period=14, threshold=2.0) == VolatilityState.HIGH)
        & structure.higher_low_event(pivot_range=15, timeframe="5m")
    ),
)


def main() -> int:
    for authored in (high_volatility, bullish_context, higher_low_long, combined_signal):
        print(authored.describe())
        print(f"  dependencies: {len(authored.dependencies().component_requests)} components")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
