"""Built-in Market Analysis component registration."""

from trading_framework.market_analysis.components.candle import (
    CandleWickComponent,
    NumpyCandleWickImplementation,
)
from trading_framework.market_analysis.components.momentum import (
    MacdComponent,
    NumpyMacdImplementation,
    NumpyRsiImplementation,
    NumpyStochasticImplementation,
    RsiComponent,
    StochasticComponent,
)
from trading_framework.market_analysis.components.session import (
    CurrentPeriodExtremeComponent,
    NumpyCurrentPeriodExtremeImplementation,
    NumpyOverlapWindowImplementation,
    NumpyPreviousPeriodExtremeImplementation,
    OverlapWindowComponent,
    PreviousPeriodExtremeComponent,
)
from trading_framework.market_analysis.components.statistics import (
    NumpyReturnAutocorrelationImplementation,
    NumpyReturnDistributionImplementation,
    ReturnAutocorrelationComponent,
    ReturnDistributionComponent,
)
from trading_framework.market_analysis.components.structure import (
    CloseReversalLevelComponent,
    ImpulseFollowThroughComponent,
    ImpulseOriginRangeComponent,
    LevelDistanceComponent,
    LevelRoleReversalComponent,
    LevelSweepRejectionComponent,
    MatchedExtremePairComponent,
    NumpyCloseReversalLevelImplementation,
    NumpyImpulseFollowThroughImplementation,
    NumpyImpulseOriginRangeImplementation,
    NumpyLevelDistanceImplementation,
    NumpyLevelRoleReversalImplementation,
    NumpyLevelSweepRejectionImplementation,
    NumpyMatchedExtremePairImplementation,
    NumpyOpeningGapImplementation,
    NumpyRangeDiscontinuityImplementation,
    NumpySessionRangeImplementation,
    NumpySwingStructureImplementation,
    OpeningGapComponent,
    RangeDiscontinuityComponent,
    SessionRangeComponent,
    SwingStructureComponent,
)
from trading_framework.market_analysis.components.trend import (
    EmaComponent,
    EmaDistanceComponent,
    NumpyEmaDistanceImplementation,
    NumpyEmaImplementation,
    NumpySlopeImplementation,
    SlopeComponent,
)
from trading_framework.market_analysis.components.volatility import (
    AccelerationComponent,
    AtrComponent,
    DirectionalAsymmetryComponent,
    NumpyAccelerationImplementation,
    NumpyAtrImplementation,
    NumpyDirectionalAsymmetryImplementation,
    NumpyRangeBasedVarianceImplementation,
    NumpyRangeExpansionImplementation,
    NumpyRelativeVolatilityImplementation,
    NumpyTrueRangeImplementation,
    NumpyVolatilityStateImplementation,
    RangeBasedVarianceComponent,
    RangeExpansionComponent,
    RelativeVolatilityComponent,
    TrueRangeComponent,
    VolatilityStateComponent,
)
from trading_framework.market_analysis.registry.registry import ComponentRegistry


def register_volatility_components(registry: ComponentRegistry) -> None:
    """Register volatility feature and state components."""
    registry.register(TrueRangeComponent(), NumpyTrueRangeImplementation(), default=True)
    registry.register(AtrComponent(), NumpyAtrImplementation(), default=True)
    registry.register(
        VolatilityStateComponent(), NumpyVolatilityStateImplementation(), default=True
    )


def register_range_expansion_component(registry: ComponentRegistry) -> None:
    """Register the Range Expansion feature component."""
    registry.register(
        RangeExpansionComponent(),
        NumpyRangeExpansionImplementation(),
        default=True,
    )


def register_relative_volatility_component(registry: ComponentRegistry) -> None:
    """Register the Relative Volatility feature component."""
    registry.register(
        RelativeVolatilityComponent(),
        NumpyRelativeVolatilityImplementation(),
        default=True,
    )


def register_ema_component(registry: ComponentRegistry) -> None:
    """Register the reusable EMA feature component."""
    registry.register(EmaComponent(), NumpyEmaImplementation(), default=True)


def register_slope_component(registry: ComponentRegistry) -> None:
    """Register the reusable OLS slope feature component."""
    registry.register(SlopeComponent(), NumpySlopeImplementation(), default=True)


def register_ema_distance_component(registry: ComponentRegistry) -> None:
    """Register the EMA Distance feature component."""
    registry.register(
        EmaDistanceComponent(),
        NumpyEmaDistanceImplementation(),
        default=True,
    )


def register_swing_structure_component(registry: ComponentRegistry) -> None:
    """Register the Swing Structure component."""
    registry.register(
        SwingStructureComponent(),
        NumpySwingStructureImplementation(),
        default=True,
    )


def register_session_range_component(registry: ComponentRegistry) -> None:
    """Register the Session Range structure component."""
    registry.register(
        SessionRangeComponent(),
        NumpySessionRangeImplementation(),
        default=True,
    )


def register_candle_wick_component(registry: ComponentRegistry) -> None:
    """Register the Candle Wick feature component."""
    registry.register(CandleWickComponent(), NumpyCandleWickImplementation(), default=True)


def register_level_distance_component(registry: ComponentRegistry) -> None:
    """Register the Level Distance structure component."""
    registry.register(
        LevelDistanceComponent(),
        NumpyLevelDistanceImplementation(),
        default=True,
    )


def register_momentum_rsi_component(registry: ComponentRegistry) -> None:
    """Register the Wilder RSI momentum feature component."""
    registry.register(RsiComponent(), NumpyRsiImplementation(), default=True)


def register_momentum_macd_component(registry: ComponentRegistry) -> None:
    """Register the MACD momentum feature component."""
    registry.register(MacdComponent(), NumpyMacdImplementation(), default=True)


def register_momentum_stochastic_component(registry: ComponentRegistry) -> None:
    """Register the Stochastic Oscillator momentum feature component."""
    registry.register(StochasticComponent(), NumpyStochasticImplementation(), default=True)


def register_statistics_return_autocorrelation_component(registry: ComponentRegistry) -> None:
    """Register the Return Autocorrelation statistics feature component."""
    registry.register(
        ReturnAutocorrelationComponent(),
        NumpyReturnAutocorrelationImplementation(),
        default=True,
    )


def register_statistics_return_distribution_component(registry: ComponentRegistry) -> None:
    """Register the Return Distribution statistics feature component."""
    registry.register(
        ReturnDistributionComponent(),
        NumpyReturnDistributionImplementation(),
        default=True,
    )


def register_opening_gap_component(registry: ComponentRegistry) -> None:
    """Register the Opening Gap component."""
    registry.register(OpeningGapComponent(), NumpyOpeningGapImplementation(), default=True)


def register_overlap_window_component(registry: ComponentRegistry) -> None:
    """Register the Overlap Window component."""
    registry.register(OverlapWindowComponent(), NumpyOverlapWindowImplementation(), default=True)


def register_current_period_extreme_component(registry: ComponentRegistry) -> None:
    """Register the Current Period Extreme component."""
    registry.register(
        CurrentPeriodExtremeComponent(),
        NumpyCurrentPeriodExtremeImplementation(),
        default=True,
    )


def register_previous_period_extreme_component(registry: ComponentRegistry) -> None:
    """Register the Previous Period Extreme component."""
    registry.register(
        PreviousPeriodExtremeComponent(),
        NumpyPreviousPeriodExtremeImplementation(),
        default=True,
    )


def register_impulse_origin_range_component(registry: ComponentRegistry) -> None:
    """Register the Impulse Origin Range component."""
    registry.register(
        ImpulseOriginRangeComponent(),
        NumpyImpulseOriginRangeImplementation(),
        default=True,
    )


def register_range_discontinuity_component(registry: ComponentRegistry) -> None:
    """Register the Range Discontinuity component."""
    registry.register(
        RangeDiscontinuityComponent(),
        NumpyRangeDiscontinuityImplementation(),
        default=True,
    )


def register_impulse_follow_through_component(registry: ComponentRegistry) -> None:
    """Register the Impulse Follow Through component."""
    registry.register(
        ImpulseFollowThroughComponent(),
        NumpyImpulseFollowThroughImplementation(),
        default=True,
    )


def register_matched_extreme_pair_component(registry: ComponentRegistry) -> None:
    """Register the Matched Extreme Pair component."""
    registry.register(
        MatchedExtremePairComponent(),
        NumpyMatchedExtremePairImplementation(),
        default=True,
    )


def register_close_reversal_level_component(registry: ComponentRegistry) -> None:
    """Register the Close Reversal Level component."""
    registry.register(
        CloseReversalLevelComponent(),
        NumpyCloseReversalLevelImplementation(),
        default=True,
    )


def register_level_sweep_rejection_component(registry: ComponentRegistry) -> None:
    """Register the Level Sweep Rejection component."""
    registry.register(
        LevelSweepRejectionComponent(),
        NumpyLevelSweepRejectionImplementation(),
        default=True,
    )


def register_level_role_reversal_component(registry: ComponentRegistry) -> None:
    """Register the Level Role Reversal component."""
    registry.register(
        LevelRoleReversalComponent(),
        NumpyLevelRoleReversalImplementation(),
        default=True,
    )


def register_range_based_variance_component(registry: ComponentRegistry) -> None:
    """Register the Range Based Variance component."""
    registry.register(
        RangeBasedVarianceComponent(),
        NumpyRangeBasedVarianceImplementation(),
        default=True,
    )


def register_directional_asymmetry_component(registry: ComponentRegistry) -> None:
    """Register the Directional Asymmetry component."""
    registry.register(
        DirectionalAsymmetryComponent(),
        NumpyDirectionalAsymmetryImplementation(),
        default=True,
    )


def register_acceleration_component(registry: ComponentRegistry) -> None:
    """Register the Acceleration component."""
    registry.register(AccelerationComponent(), NumpyAccelerationImplementation(), default=True)


def register_mvp_components(registry: ComponentRegistry) -> None:
    """Register Sprint 003 MVP feature and state components."""
    register_volatility_components(registry)
    register_range_expansion_component(registry)
    register_relative_volatility_component(registry)
    register_ema_component(registry)
    register_ema_distance_component(registry)
    register_slope_component(registry)
    register_swing_structure_component(registry)
    register_session_range_component(registry)
    register_candle_wick_component(registry)
    register_level_distance_component(registry)
    register_momentum_rsi_component(registry)
    register_momentum_macd_component(registry)
    register_momentum_stochastic_component(registry)
    register_statistics_return_autocorrelation_component(registry)
    register_statistics_return_distribution_component(registry)
    register_opening_gap_component(registry)
    register_overlap_window_component(registry)
    register_current_period_extreme_component(registry)
    register_previous_period_extreme_component(registry)
    register_impulse_origin_range_component(registry)
    register_range_discontinuity_component(registry)
    register_impulse_follow_through_component(registry)
    register_matched_extreme_pair_component(registry)
    register_close_reversal_level_component(registry)
    register_level_sweep_rejection_component(registry)
    register_level_role_reversal_component(registry)
    register_range_based_variance_component(registry)
    register_directional_asymmetry_component(registry)
    register_acceleration_component(registry)


def default_mvp_registry() -> ComponentRegistry:
    """Return a registry with all MVP components registered."""
    registry = ComponentRegistry()
    register_mvp_components(registry)
    return registry


__all__ = [
    "default_mvp_registry",
    "register_acceleration_component",
    "register_candle_wick_component",
    "register_close_reversal_level_component",
    "register_current_period_extreme_component",
    "register_directional_asymmetry_component",
    "register_ema_component",
    "register_ema_distance_component",
    "register_impulse_follow_through_component",
    "register_impulse_origin_range_component",
    "register_level_distance_component",
    "register_level_role_reversal_component",
    "register_level_sweep_rejection_component",
    "register_matched_extreme_pair_component",
    "register_momentum_macd_component",
    "register_momentum_rsi_component",
    "register_momentum_stochastic_component",
    "register_mvp_components",
    "register_opening_gap_component",
    "register_overlap_window_component",
    "register_previous_period_extreme_component",
    "register_range_based_variance_component",
    "register_range_discontinuity_component",
    "register_range_expansion_component",
    "register_relative_volatility_component",
    "register_session_range_component",
    "register_slope_component",
    "register_statistics_return_autocorrelation_component",
    "register_statistics_return_distribution_component",
    "register_swing_structure_component",
    "register_volatility_components",
]
