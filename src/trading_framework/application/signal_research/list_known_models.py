"""List built-in model aliases for a read-only local UI consumer.

Thin wrapper over ``trading_framework.research.signal_research.model_registry``,
same pattern as ``list_signal_research_templates``: a UI app like
``apps/workbench`` (which MUST NOT import ``trading_framework.research.*``
per ADR-0037 section 2) reaches this membership-only listing through the
application layer instead. Never builds, imports, or executes a model --
matches ``is_known_*_model_alias``'s own "membership-only" guarantee.
"""

from __future__ import annotations

from dataclasses import dataclass

from trading_framework.research.signal_research.model_registry import (
    list_known_market_model_aliases as _list_market_model_aliases,
)
from trading_framework.research.signal_research.model_registry import (
    list_known_signal_model_aliases as _list_signal_model_aliases,
)

__all__ = ["KnownModelAliases", "list_known_model_aliases"]


@dataclass(frozen=True, slots=True)
class KnownModelAliases:
    market_model_aliases: tuple[str, ...]
    signal_model_aliases: tuple[str, ...]


def list_known_model_aliases() -> KnownModelAliases:
    return KnownModelAliases(
        market_model_aliases=_list_market_model_aliases(),
        signal_model_aliases=_list_signal_model_aliases(),
    )
