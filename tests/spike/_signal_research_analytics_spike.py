"""Spike-only read-only boundary checks for Signal Research analytics."""

from __future__ import annotations

from pathlib import Path

from trading_framework.core.exceptions import ValidationError

FORBIDDEN_ANALYTICS_IMPORTS = frozenset(
    {
        "evaluate_models",
        "compute_forward_outcomes",
        "compute_forward_outcomes_for_horizons",
        "materialize_signal_occurrences",
        "materialize_market_model_observations",
        "align_context_facts_at_available_at",
    }
)

_ANALYTICS_MODULE_DIR = (
    Path(__file__).resolve().parents[2] / "src" / "trading_framework" / "research" / "analytics"
)


def assert_read_only_analytics_package() -> None:
    """Fail if production analytics modules import forbidden compute paths."""
    for path in sorted(_ANALYTICS_MODULE_DIR.glob("*.py")):
        assert_read_only_module(path.read_text(encoding="utf-8"), source=str(path.name))


def assert_read_only_module(source_text: str, *, source: str = "module") -> None:
    """Fail if analytics module imports forbidden compute paths."""
    for line in source_text.splitlines():
        stripped = line.strip()
        if not stripped.startswith(("import ", "from ")):
            continue
        for forbidden in FORBIDDEN_ANALYTICS_IMPORTS:
            if forbidden in stripped:
                msg = f"{source} must not import forbidden symbol: {forbidden}"
                raise ValidationError(msg)


__all__ = [
    "assert_read_only_analytics_package",
    "assert_read_only_module",
]
