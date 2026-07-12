"""Documentation catalog for registered Market Analysis components."""

from dataclasses import dataclass

from trading_framework.market_analysis.identity.component import ComponentId
from trading_framework.market_analysis.models.parameters import ParameterFieldSpec
from trading_framework.market_analysis.registry.builtins import default_mvp_registry
from trading_framework.market_analysis.registry.registry import ComponentRegistry


@dataclass(frozen=True, slots=True)
class ComponentCatalogEntry:
    """User-facing catalog metadata keyed by ``component_id``."""

    component_id: ComponentId
    summary: str
    tags: tuple[str, ...] = ()
    examples: tuple[str, ...] = ()
    notes: str = ""


_DOCUMENTATION: dict[str, ComponentCatalogEntry] = {
    "volatility.true_range": ComponentCatalogEntry(
        component_id=ComponentId("volatility.true_range"),
        summary="Bar true range from OHLC",
        tags=("volatility", "feature"),
        examples=("Used internally by volatility.atr",),
    ),
    "volatility.atr": ComponentCatalogEntry(
        component_id=ComponentId("volatility.atr"),
        summary="Average true range feature",
        tags=("volatility", "feature"),
        examples=("volatility.state(period=14, threshold=2.0)",),
    ),
    "volatility.state": ComponentCatalogEntry(
        component_id=ComponentId("volatility.state"),
        summary="High-volatility state (0/1) from ATR threshold",
        tags=("volatility", "state"),
        examples=("volatility.state(period=14, threshold=2.0) == VolatilityState.HIGH",),
    ),
    "trend.ema": ComponentCatalogEntry(
        component_id=ComponentId("trend.ema"),
        summary="Exponential moving average of close",
        tags=("trend", "feature"),
        examples=(
            "price.close > trend.ema(period=20)",
            "trend.price_above_ema(period=20)",
        ),
    ),
    "structure.swing": ComponentCatalogEntry(
        component_id=ComponentId("structure.swing"),
        summary="Pivot swing structure with HH/HL/LH/LL events",
        tags=("structure", "state", "event"),
        examples=("structure.higher_low_event(pivot_range=15, timeframe='5m')",),
        notes="Use computation timeframe for MTF swing outputs.",
    ),
}


def list_documented_components(
    registry: ComponentRegistry | None = None,
) -> tuple[ComponentCatalogEntry, ...]:
    """Return catalog entries for components registered in the MVP registry."""
    component_registry = registry or default_mvp_registry()
    entries: list[ComponentCatalogEntry] = []
    for component_id in sorted(_DOCUMENTATION):
        entry = _DOCUMENTATION[component_id]
        component_registry.get_component(entry.component_id)
        entries.append(entry)
    return tuple(entries)


def _format_parameter(field: ParameterFieldSpec) -> str:
    default = "" if field.default is None else f" = {field.default!r}"
    return f"{field.name}: {field.type.value}{default}"


def format_component_entry(
    entry: ComponentCatalogEntry,
    *,
    registry: ComponentRegistry | None = None,
) -> str:
    """Render one component entry for CLI or docs."""
    component_registry = registry or default_mvp_registry()
    component = component_registry.get_component(entry.component_id)
    parameter_lines = [_format_parameter(field) for field in component.parameter_schema.fields]
    output_lines = [
        f"{field.output_id.value}: {field.dtype}" for field in component.output_schema.outputs
    ]
    lines = [
        entry.component_id.value,
        "",
        "Kind:",
        f"  {component.kind.value}",
        "",
        "Parameters:",
        *(f"  {line}" for line in parameter_lines),
        "",
        "Outputs:",
        *(f"  {line}" for line in output_lines),
    ]
    if entry.examples:
        lines.extend(["", "Examples:", *(f"  {example}" for example in entry.examples)])
    if entry.notes:
        lines.extend(["", f"Note: {entry.notes}"])
    return "\n".join(lines)
