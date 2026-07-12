"""Reference catalog of MVP Market Analysis components available to declarative models."""

from dataclasses import dataclass

from trading_framework.market_analysis.components.structure import SwingStructureComponent
from trading_framework.market_analysis.components.trend import EmaComponent
from trading_framework.market_analysis.components.volatility import (
    AtrComponent,
    TrueRangeComponent,
    VolatilityStateComponent,
)
from trading_framework.market_analysis.protocols.batch_component import BatchAnalysisComponent


@dataclass(frozen=True, slots=True)
class ComponentCatalogEntry:
    """One registered semantic component with human-readable metadata."""

    component: BatchAnalysisComponent
    summary: str
    typical_outputs: tuple[str, ...]
    notes: str = ""


def list_mvp_components() -> tuple[ComponentCatalogEntry, ...]:
    """Return the Sprint 003-005 MVP catalog used by ``default_mvp_registry()``."""
    return (
        ComponentCatalogEntry(
            component=TrueRangeComponent(),
            summary="Bar true range from OHLC",
            typical_outputs=("value",),
            notes="Depends on open/high/low/close.",
        ),
        ComponentCatalogEntry(
            component=AtrComponent(),
            summary="Average true range feature",
            typical_outputs=("value",),
            notes="Depends on volatility.true_range.",
        ),
        ComponentCatalogEntry(
            component=VolatilityStateComponent(),
            summary="High-volatility state (0/1) from ATR threshold",
            typical_outputs=("state", "distance_to_threshold"),
            notes="Market Model example: state == 1.",
        ),
        ComponentCatalogEntry(
            component=EmaComponent(),
            summary="Exponential moving average of close",
            typical_outputs=("value",),
            notes="Reference via ComponentOutputReference; pair with MarketFieldReference.",
        ),
        ComponentCatalogEntry(
            component=SwingStructureComponent(),
            summary="Pivot swing structure with HH/HL/LH/LL events",
            typical_outputs=(
                "swing_high_event",
                "higher_low_event",
                "latest_swing_high_level",
            ),
            notes="Use computation_timeframe=Timeframe('5m') for MTF.",
        ),
    )


def describe_component(entry: ComponentCatalogEntry) -> str:
    """Format one catalog entry for CLI output."""
    component = entry.component
    parameter_names = tuple(field.name for field in component.parameter_schema.fields)
    output_names = tuple(field.output_id.value for field in component.output_schema.outputs)
    lines = [
        f"{component.component_id.value} ({component.kind.value}, {component.causality.value})",
        f"  {entry.summary}",
        f"  parameters: {', '.join(parameter_names) or '(none)'}",
        f"  outputs: {', '.join(output_names)}",
    ]
    if entry.notes:
        lines.append(f"  note: {entry.notes}")
    return "\n".join(lines)


def print_component_build_checklist() -> None:
    """Print the steps required to add a new Market Analysis component (Sprint 003+ pattern)."""
    print(
        """
Adding a new Market Analysis component
======================================
1. Semantic class (e.g. ``MyComponent`` in ``market_analysis/components/...``)
   - component_id, component_version, kind, causality
   - parameter_schema, output_schema
   - history_requirement(), data_dependencies(), component_dependencies()

2. Implementation class (e.g. ``NumpyMyImplementation``)
   - implementation_id, implementation_version
   - compute(context, workspace, parameters) -> AnalysisResult

3. Register in ``market_analysis/registry/builtins.py``
   - registry.register(MyComponent(), NumpyMyImplementation(), default=True)

4. Tests under ``tests/unit/market_analysis/``

5. Reference from declarative models via ComponentOutputReference:
   - component_id, canonical parameters, output_id
   - optional computation_timeframe for MTF
   - optional alias for frame column naming

See existing references:
  - FEATURE:  src/trading_framework/market_analysis/components/trend/ema.py
  - STATE:    src/trading_framework/market_analysis/components/volatility/state.py
  - STRUCTURE src/trading_framework/market_analysis/components/structure/swing.py
"""
    )
