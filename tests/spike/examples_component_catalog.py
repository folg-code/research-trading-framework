"""Registry-backed component catalog for spike CLI."""

from trading_framework.market_analysis.catalog import (
    format_component_entry,
    list_documented_components,
)


def describe_component(entry) -> str:
    return format_component_entry(entry)


def list_mvp_components():
    return list_documented_components()


def print_component_build_checklist() -> None:
    print(
        """
Adding a new Market Analysis component
======================================
1. Semantic class (e.g. ``MyComponent`` in ``market_analysis/components/...``)
2. Implementation class (e.g. ``NumpyMyImplementation``)
3. Register in ``market_analysis/registry/builtins.py``
4. Tests under ``tests/unit/market_analysis/``
5. Add documentation entry in ``market_analysis/catalog/documentation.py``
6. Reference from models via ``model_authoring`` or ``ComponentOutputReference``

See:
  - src/trading_framework/market_analysis/components/trend/ema.py
  - src/trading_framework/model_authoring/
"""
    )
